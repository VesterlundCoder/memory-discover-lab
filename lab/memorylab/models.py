"""Family-specific model dispatch; all optical write/read parameters must be supplied."""
import math
import numpy as np
from scipy.constants import h, k
from .catalog import FAMILIES, EVIDENCE
from .channels import (I2, MemoryChannel, compose, dephasing, depolarizing,
                       thermal_amplitude_damping)
from .common import finite, MissingData, UnsupportedPhysics
from .spin import exact_coherence

# The allowed storage descriptions express a model's scope, not a family's entire physics.
FAMILY_MODELS = {
    "atomic_ensemble": {"markov", "coherence_table"},
    "trapped_atom_ion": {"markov", "coherence_table"},
    "rare_earth_solid": {"markov", "exact_spin_bath", "pycce", "coherence_table"},
    "defect_spin": {"markov", "exact_spin_bath", "pycce", "coherence_table"},
    "molecular_spin": {"markov", "exact_spin_bath", "pycce", "coherence_table"},
    "negative_ion": {"markov", "coherence_table"},
}


def rate(spec, temperature_K):
    """Explicit phenomenological rates; coefficients and temperature validity are input data."""
    temperature = finite(temperature_K, "temperature_K", 0)
    low, high = spec["valid_temperature_K"]
    finite(low, "valid_temperature_K[0]", 0)
    finite(high, "valid_temperature_K[1]", low)
    if not low <= temperature <= high:
        raise MissingData("Temperature outside the rate model's declared validity interval")
    kind = spec["kind"]
    if kind == "constant":
        return finite(spec["rate_s_inv"], "rate_s_inv", 0)
    if kind != "phenomenological_temperature":
        raise UnsupportedPhysics("Unsupported temperature-rate model")
    value = finite(spec.get("base_s_inv", 0), "base_s_inv", 0)
    value += finite(spec.get("direct_s_inv_K_inv", 0), "direct coefficient", 0)*temperature
    exponent = finite(spec.get("raman_exponent", 7), "raman exponent", 0)
    reference = finite(spec.get("reference_K", 1), "reference_K", 1e-12)
    value += finite(spec.get("raman_at_reference_s_inv", 0), "Raman coefficient", 0)*(temperature/reference)**exponent
    amplitude = finite(spec.get("orbach_s_inv", 0), "Orbach coefficient", 0)
    if amplitude:
        gap = finite(spec["orbach_gap_K"], "orbach_gap_K", 1e-12)
        ratio = gap/temperature if temperature else math.inf
        value += amplitude/math.expm1(ratio) if ratio < 700 else 0
    return finite(value, "computed rate", 0)


def validate(spec):
    for name in ("family", "storage_model", "evidence_kind", "provenance", "temperatures_K",
                 "rates", "io", "noise_budget"):
        if name not in spec:
            raise MissingData("Memory recipe lacks " + name)
    family, storage = spec["family"], spec["storage_model"]
    if family not in FAMILIES or storage not in FAMILY_MODELS[family]:
        raise UnsupportedPhysics("Storage model not supported for this family")
    if spec["evidence_kind"] not in EVIDENCE or not spec["provenance"]:
        raise MissingData("Explicit input evidence and provenance required")
    for stage in ("write", "storage", "read"):
        if stage not in spec["temperatures_K"]:
            raise MissingData(stage + " temperature is unknown")
        finite(spec["temperatures_K"][stage], stage + " temperature_K", 0)
    for item in ("population", "pure_dephasing", "erasure"):
        if item not in spec["rates"]:
            raise MissingData("Missing independent rate model: " + item)
        for temperature in spec["temperatures_K"].values():
            rate(spec["rates"][item], temperature)
    io = spec["io"]
    for key in ("eta_write", "eta_read", "write_depolarizing_p", "read_depolarizing_p"):
        finite(io[key], key, 0, 1)
    for key in ("write_duration_s", "read_duration_s", "thermal_transition_s"):
        finite(io[key], key, 0)
    if io["thermal_transition_s"] != 0:
        raise UnsupportedPhysics("A thermal ramp requires a piecewise schedule; no unmodeled ramp accepted")
    if not io.get("logical_encoding") or not io.get("protocol"):
        raise MissingData("Optical encoding and write/read protocol must be declared")
    for key in ("bandwidth_Hz", "wavelength_nm"):
        if io.get(key) is not None:
            finite(io[key], key, 1e-30)
    noise = spec["noise_budget"]
    if spec.get("prediction_purpose") == "material_prediction":
        from .convergence_guard import require_material_convergence
        require_material_convergence(spec)
    if len(noise) != len(set(noise)):
        raise ValueError("Duplicate noise sources would be double counted")
    if storage in ("exact_spin_bath", "pycce", "coherence_table"):
        if not spec.get("additional_dephasing_independent_of_markov"):
            raise UnsupportedPhysics("Declare independence to compose a spin/table coherence with Markov noise")
    if family == "negative_ion":
        if spec.get("candidate", {}).get("charge_e", 0) >= 0:
            raise ValueError("Negative-ion recipe requires an explicitly negative initial charge")
        if spec.get("optical_process") != "photodetachment":
            raise UnsupportedPhysics("This branch implements only a supplied photodetachment overlap model")
        overlap = spec.get("electron_record_overlap")
        if not isinstance(overlap, list) or len(overlap) != 2 or abs(complex(*overlap)) > 1:
            raise MissingData("Complex electron/environment record overlap is required")
    return spec


def stage_channel(spec, stage, duration_s, backend="analytic"):
    temperature = spec["temperatures_K"][stage]
    gamma1 = rate(spec["rates"]["population"], temperature)
    gammaphi = rate(spec["rates"]["pure_dephasing"], temperature)
    activity = spec.get("network_activity", {})
    if stage == "storage":
        gammaphi += finite(activity.get("attempt_rate_Hz", 0), "attempt_rate_Hz", 0)*finite(
            activity.get("coherence_loss_per_attempt", 0), "coherence_loss_per_attempt", 0, 2)
    population = finite(spec.get("equilibrium_excited_population", 0), "equilibrium population", 0, 1)
    if spec.get("thermal_detailed_balance"):
        frequency = finite(spec["qubit_frequency_Hz"], "qubit_frequency_Hz", 0)
        ratio = h*frequency/(k*temperature) if temperature else math.inf
        population = 1/(1+math.exp(ratio)) if ratio < 700 else 0
    detuning = finite(spec.get("detuning_Hz", 0), "detuning_Hz")
    if backend == "qutip":
        from .backends import qutip_markov
        return qutip_markov(duration_s, gamma1, gammaphi, population, detuning)
    if backend != "analytic":
        raise ValueError("Unknown channel backend")
    relaxation = thermal_amplitude_damping(duration_s, gamma1, population)
    phase = dephasing(np.exp(-gammaphi*duration_s + 2j*math.pi*detuning*duration_s))
    return compose(phase, relaxation)


def extra_coherence(spec, times_s):
    kind = spec["storage_model"]
    if kind == "markov":
        return np.ones(len(times_s), complex)
    if kind == "exact_spin_bath":
        return exact_coherence(spec["spin_bath"], times_s, spec["temperatures_K"]["storage"],
                               spec.get("control", {}).get("cpmg_pulses", 0))
    if kind == "pycce":
        from .backends import pycce_coherence
        return pycce_coherence(spec["spin_bath"], times_s,
                              spec.get("control", {}).get("cpmg_pulses", 0),
                              spec.get("simulation_seed", 0))
    table = spec["coherence_table"]
    if table.get("includes_population_relaxation") is not False:
        raise UnsupportedPhysics("Table must describe pure dephasing separately from population relaxation")
    if table["temperature_K"] != spec["temperatures_K"]["storage"] or table["control"] != spec.get("control", {}):
        raise MissingData("Coherence table conditions do not match this experiment")
    grid = np.asarray(table["times_s"], float)
    real = np.asarray(table["real"], float)
    imag = np.asarray(table["imag"], float)
    if grid.ndim != 1 or len(grid) < 2 or real.shape != grid.shape or imag.shape != grid.shape:
        raise ValueError("Coherence table arrays must have identical one-dimensional shape")
    if not np.isfinite(grid).all() or np.any(np.diff(grid) <= 0) or grid[0] != 0:
        raise ValueError("Coherence table needs a finite, increasing grid starting at zero")
    if abs(complex(real[0], imag[0])-1) > 1e-9 or np.any(np.abs(real+1j*imag) > 1+1e-10):
        raise ValueError("Unnormalized or nonphysical coherence table")
    if min(times_s) < grid[0] or max(times_s) > grid[-1]:
        raise MissingData("No coherence-table extrapolation is allowed")
    return np.interp(times_s, grid, real) + 1j*np.interp(times_s, grid, imag)


def evaluate(spec, times_s, backend="analytic"):
    if spec.get("storage_model") == "measured_operating_point":
        from .experimental import evaluate_point
        return evaluate_point(spec, times_s, backend)
    validate(spec)
    times = [finite(t, "storage age_s", 0) for t in times_s]
    if not times or sorted(set(times)) != times:
        raise ValueError("Time grid must be nonempty, unique and increasing")
    if spec.get("prediction_purpose") == "material_prediction":
        from .convergence_guard import require_material_convergence
        require_material_convergence(spec, times)
    L = extra_coherence(spec, times)
    io = spec["io"]
    write = compose(depolarizing(io["write_depolarizing_p"]),
                    stage_channel(spec, "write", io["write_duration_s"], backend))
    if spec["family"] == "negative_ion":
        write = compose(dephasing(complex(*spec["electron_record_overlap"])), write)
    read = compose(depolarizing(io["read_depolarizing_p"]),
                   stage_channel(spec, "read", io["read_duration_s"], backend))
    fixed_loss = sum(rate(spec["rates"]["erasure"], spec["temperatures_K"][s])*io[s+"_duration_s"]
                     for s in ("write", "read"))
    rows = []
    for age, coherence in zip(times, L):
        storage = compose(dephasing(coherence), stage_channel(spec, "storage", age, backend))
        conditional = compose(read, compose(storage, write))
        probability = io["eta_write"]*io["eta_read"]*math.exp(
            -fixed_loss-rate(spec["rates"]["erasure"], spec["temperatures_K"]["storage"])*age)
        metadata = {"family": spec["family"], "storage_model": spec["storage_model"],
                    "storage_age_s": age, "total_write_store_read_s": age+io["write_duration_s"]+io["read_duration_s"],
                    "temperatures_K": spec["temperatures_K"], "control": spec.get("control", {}),
                    "network_activity": spec.get("network_activity", {}),
                    "input_evidence_kind": spec["evidence_kind"], "result_evidence_kind": "computed",
                    "provenance": spec["provenance"], "noise_budget": spec["noise_budget"],
                    "optical_interface": io, "backend": backend,
                    "additional_pure_coherence": [float(coherence.real), float(coherence.imag)],
                    "scope": "parameterized qubit write-store-read model; hardware validation pending",
                    "age_semantics": "apply complete channel once to the original input state",
                    "assumptions": ["state-independent heralding", "independent specified noise sources",
                                    "constant temperature within each stage", "no unmodeled thermal transitions"]}
        rows.append(MemoryChannel(conditional, probability, metadata))
    return rows
