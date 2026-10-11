"""Reviewed finite-operating-point channels and explicitly scoped data comparisons.

No decay rate is inferred from a fidelity at one age. The fitted isotropic
channel is one admissible effective channel, not process tomography.
"""
import math
import numpy as np
from scipy.optimize import least_squares
from scipy.special import erf
from .channels import MemoryChannel, depolarizing, check_cptp
from .common import MissingData, finite, digest, optional_import


def evaluate_point(spec, times_s, backend="analytic"):
    required = ("family", "evidence_kind", "provenance", "temperatures_K", "io", "point")
    if any(k not in spec for k in required) or not spec["provenance"]:
        raise MissingData("Measured point requires reviewed conditions and provenance")
    if spec["family"] != "rare_earth_solid" or spec["evidence_kind"] != "fit_to_experiment":
        raise MissingData("This measured-point adapter supports reviewed rare-earth fits")
    pt = spec["point"]
    age = finite(pt["end_to_end_age_s"], "end-to-end age", 1e-15)
    times = [finite(t, "requested age", 0) for t in times_s]
    if not times or sorted(set(times)) != times or any(t != age for t in times):
        raise MissingData("Only the measured end-to-end age is supported; T2 is unidentified")
    temps = spec["temperatures_K"]
    if set(temps) != {"write", "storage", "read"} or any(
            finite(t, "temperature", 0) != pt["temperature_K"] for t in temps.values()):
        raise MissingData("No temperature interpolation or thermal-ramp model available")
    if spec["io"].get("protocol") != "AFC_spin_wave_path_qubit":
        raise MissingData("Measured optical protocol does not match")
    f = finite(pt["conditional_average_fidelity"], "fidelity", .5, 1)
    eta = finite(pt["signal_retrieval_probability"], "signal retrieval", 0, 1)
    kraus = depolarizing(2*(1-f))
    if backend == "qutip":
        qt = optional_import("qutip")
        superoperator = sum(qt.to_super(qt.Qobj(k)) for k in kraus)
        kraus = [k.full() for k in qt.to_kraus(superoperator)]
    elif backend != "analytic":
        raise ValueError("Measured point supports analytic or qutip")
    meta = {"family": spec["family"], "storage_model": "measured_operating_point",
            "storage_age_s": age, "total_write_store_read_s": age,
            "age_definition": "optical input to output; includes AFC and spin storage",
            "spin_storage_s": pt["spin_storage_s"], "afc_rephasing_s": pt["afc_rephasing_s"],
            "temperatures_K": temps, "control": spec.get("control", {}),
            "input_evidence_kind": "fit_to_experiment", "result_evidence_kind": "computed",
            "provenance": spec["provenance"], "optical_interface": spec["io"],
            "backend": backend, "profile_hash": digest(spec),
            "T2_s": None, "T2_status": "unidentified_no_storage_time_series",
            "validation_scope": "conditional fidelity calibrated at one operating point",
            "loss_scope": pt["loss_scope"],
            "assumptions": ["isotropic effective qubit channel; not uniquely identified",
                            "state-independent signal loss", "ideal loss flag in network workload",
                            "fidelity includes experimental preparation/analysis and background",
                            "classical transfer efficiencies used for signal loss"],
            "input_probe": "weak coherent states; application to entangled single photons is a model assumption",
            "hardware_validated": False}
    result = MemoryChannel(kraus, eta, meta)
    check_cptp(result.full_kraus())
    return [result]


def parse_indexed_infidelity(path, n_cells, state_labels, index_order, cell_index_base=0):
    """Archive stores three rows, not a conventional observations-as-rows CSV."""
    a = np.loadtxt(path, delimiter=";", comments="#")
    if a.shape != (3, n_cells*len(state_labels)) or not np.isfinite(a).all():
        raise MissingData("Unexpected source-data layout")
    values = np.full((len(state_labels), n_cells), np.nan)
    for inf, i, j in a.T:
        cell, basis = (int(i), int(j)) if index_order == "cell,basis" else (int(j), int(i))
        cell -= cell_index_base
        if i != int(i) or j != int(j) or not 0 <= cell < n_cells or not 0 <= basis < len(state_labels):
            raise ValueError("Invalid source index")
        if not np.isnan(values[basis, cell]) or not 0 <= inf <= 1:
            raise ValueError("Duplicate index or nonphysical infidelity")
        values[basis, cell] = 1-inf
    if np.isnan(values).any():
        raise MissingData("Missing input state/cell")
    return values


def interval_sigma(values, low, high):
    """The supplement defines endpoints as F_MC +/- one std, not hard bounds.

    F need not be the MC mean. Half-width exactly recovers stated std.
    """
    v, lo, hi = [np.asarray(a, float) for a in (values, low, high)]
    if v.shape != lo.shape or v.shape != hi.shape or not np.isfinite(np.r_[v.ravel(), lo.ravel(), hi.ravel()]).all():
        raise ValueError("Invalid fidelity intervals")
    if np.any(lo > v) or np.any(hi < v) or np.any(hi <= lo):
        raise ValueError("Fidelity interval does not bracket estimate")
    return (hi-lo)/2


def spatial_holdout(values, low, high):
    """Fixed split: cells 1,3,5,7,9 train; cells 2,4,6,8,10 held out.

    Common isotropic effective channel only. Systematic cross-cell covariances
    are absent, so z values are approximate, not independent replication.
    """
    v = np.asarray(values, float)
    sigma = interval_sigma(v, low, high)
    if v.shape != (10,):
        raise ValueError("Ten-cell baseline expected")
    train, held = np.arange(0, 10, 2), np.arange(1, 10, 2)
    weight = 1/sigma[train]**2
    mu = float(np.average(v[train], weights=weight))
    se = float(1/math.sqrt(sum(weight)))
    rows = [{"cell": int(i+1), "observed": float(v[i]), "prediction": mu,
             "experimental_sigma": float(sigma[i]),
             "absolute_z": float(abs(mu-v[i])/math.hypot(se, sigma[i]))} for i in held]
    return {"status": "pass" if all(r["absolute_z"] <= 3 for r in rows) else "model_mismatch",
            "model": "common conditional isotropic channel across cells",
            "training_cells": (train+1).tolist(), "held_out_cells": (held+1).tolist(),
            "fitted_average_fidelity": mu, "fit_standard_error": se,
            "maximum_absolute_z": max(r["absolute_z"] for r in rows), "threshold": 3,
            "comparisons": rows, "scope": "within-dataset spatial holdout; time-bin encoding",
            "uncertainty_assumptions": "uncorrelated supplied MC std; shared systematics unavailable",
            "external_experimental_replication": False, "T2_identified": False}


def window_noise_fit(windows_ns, values, low, high):
    """Phenomenological finite-pulse + flat-background model, fixed storage age.

    F(w)=1/2 + (F_signal-1/2)*erf(w/(sqrt(8)*width)) /
         (erf(...) + background_ratio*w/1000).
    Nested windows share photon counts. No independent-chi2 claim is made.
    """
    x, y = np.asarray(windows_ns, float), np.asarray(values, float)
    sigma = interval_sigma(y, low, high)
    if x.shape != (211,) or y.shape != (3, 211) or np.any(np.diff(x) <= 0):
        raise MissingData("Expected three path pairs and 211 detection windows")
    train, held = x <= 600, x >= 800
    rows = []
    rejected_constant = []
    for i, pair in enumerate(([1, 2], [5, 6], [9, 10])):
        def predict(q):
            fsignal, background, width = q
            fraction = erf(x/(math.sqrt(8)*width))
            return .5+(fsignal-.5)*fraction/(fraction+background*x/1000)
        fit = least_squares(lambda q: (predict(q)[train]-y[i, train])/sigma[i, train],
                            [.99, .15, 80], bounds=([.5, 0, 5], [1, 10, 500]))
        if not fit.success:
            raise ValueError("Noise fit failed")
        prediction = predict(fit.x)
        z = np.abs(prediction[held]-y[i, held])/sigma[i, held]
        constant = float(np.average(y[i, train], weights=1/sigma[i, train]**2))
        constant_z = float(max(abs(constant-y[i, held])/sigma[i, held]))
        rejected_constant.append({"pair": pair, "fitted_constant_fidelity": constant,
                                  "maximum_heldout_pointwise_z": constant_z,
                                  "status": "model_mismatch" if constant_z > 3 else "adequate_pointwise"})
        rows.append({"pair": pair, "parameters": {
            "signal_fidelity": float(fit.x[0]), "background_ratio_per_us": float(fit.x[1]),
            "effective_pulse_sigma_ns": float(fit.x[2])},
            "on_parameter_bound": bool(np.any(fit.active_mask)),
            "maximum_heldout_pointwise_z": float(max(z)),
            "status": "adequate_pointwise" if max(z) <= 3 else "model_mismatch",
            "predictions": prediction.tolist()})
    return {"model": "finite Gaussian pulse plus flat unpolarized background",
            "fitted_pairs": 3, "training_windows": int(sum(train)), "held_out_windows": int(sum(held)),
            "unused_gap_windows": int(sum(~(train | held))), "fits": rows,
            "negative_control_model": {"hypothesis": "readout-window-independent fidelity",
                                       "fits": rejected_constant},
            "storage_time_s": 18e-6, "abscissa_is": "DETECTION_WINDOW_NOT_STORAGE_TIME",
            "scope": "internal model adequacy; nested windows share counts",
            "fit_uncertainties": "not identified without joint covariance; pointwise errors only",
            "not_unique_physical_parameter_inference": True, "T2_identified": False}
