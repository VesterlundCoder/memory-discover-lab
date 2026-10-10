"""Executable optional backends. No backend substitutes electronics for missing coherence data."""
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
from pathlib import Path
import numpy as np
from .common import (BackendUnavailable, MissingData, NumericalFailure, UnsupportedPhysics,
                     digest, finite, optional_import, read_json, write_json, environment)
from .channels import check_cptp, compress


def qutip_markov(duration_s, gamma1, gammaphi, excited_population, detuning_Hz):
    qt = optional_import("qutip")
    H = qt.Qobj(2*math.pi*detuning_Hz*np.diag([0, 1]))
    down = qt.Qobj(np.array([[0, 1], [0, 0]], complex))
    up = down.dag()
    c_ops = [math.sqrt(gamma1*(1-excited_population))*down,
             math.sqrt(gamma1*excited_population)*up,
             math.sqrt(gammaphi/2)*qt.sigmaz()]
    generator = qt.liouvillian(H, c_ops)
    propagator = (generator*duration_s).expm()
    kraus = compress([obj.full() for obj in qt.to_kraus(propagator)])
    check_cptp(kraus, tolerance=2e-8)
    return kraus


def pycce_coherence(spec, times_s, pulses, simulation_seed):
    pc = optional_import("pycce")
    # This adapter supports conventional CCE pure coherence; gCCE density elements have
    # different normalization and must not be exported by dividing them blindly.
    if spec.get("method", "cce") != "cce":
        raise UnsupportedPhysics("Only conventional CCE normalized pure coherence is implemented")
    bath = pc.BathArray(shape=(len(spec["nuclei"]),))
    for i, nucleus in enumerate(spec["nuclei"]):
        if nucleus.get("frame") != "lab":
            raise ValueError("PyCCE coupling tensor must be in the lab frame")
        isotope = nucleus["isotope_id"]
        symbol, mass = isotope.split("-")
        bath["N"][i] = mass+symbol
        bath["xyz"][i] = nucleus["position_angstrom"]
        bath["A"][i] = np.asarray(nucleus["hyperfine_Hz"], float)/1000
        bath["Q"][i] = np.asarray(nucleus.get("quadrupole_Hz", np.zeros((3, 3))), float)/1000
    for pair in spec.get("pairs", []):
        i, j = pair["sites"]
        if i == j or min(i, j) < 0 or max(i, j) >= len(bath):
            raise ValueError("Invalid explicitly supplied PyCCE pair")
        tensor = np.asarray(pair["coupling_Hz"], float)
        if tensor.shape != (3, 3) or not np.isfinite(tensor).all():
            raise ValueError("Invalid explicitly supplied PyCCE pair tensor")
        bath.add_interaction(i, j, tensor/1000)
    if spec.get("require_explicit_zeeman_match"):
        for i, nucleus in enumerate(spec["nuclei"]):
            expected = -float(bath.gyro[i])*np.asarray(spec["magnetic_field_T"])*1e7/(2*np.pi)
            if not np.allclose(expected, nucleus["zeeman_vector_Hz"], atol=1e-5, rtol=1e-9):
                raise UnsupportedPhysics("Explicit Zeeman vector does not match PyCCE field/isotope conventions")
    # PyCCE: time ms, hyperfine/ZFS kHz, field G, gyro rad/ms/G.
    center = spec["center"]
    simulator = pc.Simulator(center["spin_S"], position=center["position_angstrom"],
        alpha=center["alpha_index"], beta=center["beta_index"],
        gyro=center["gyro_rad_s_T"]*1e-7, D=(np.asarray(center["zfs_Hz"])/1000)[None, :, :],
        magnetic_field=np.asarray(spec["magnetic_field_T"])*10000,
        bath=bath, r_bath=spec["r_bath_angstrom"], r_dipole=spec["r_dipole_angstrom"],
        order=spec["order"], pulses=pulses, as_delay=False)
    values = np.asarray(simulator.compute(np.asarray(times_s)*1000, method="cce",
        quantity="coherence", seed=int(simulation_seed) % (2**32), nbstates=spec.get("nbstates", 0)))
    if not np.isfinite(values).all() or np.any(np.abs(values) > 1+1e-9):
        raise NumericalFailure("CCE produced nonphysical coherence; increase convergence/order")
    return values.astype(complex)


def import_couplings(kind, output_path, options=None):
    """Actual ORCA/QE -> PyCCE bath import, preserving backend-native conventions explicitly."""
    pc = optional_import("pycce")
    functions = {"orca": pc.read_orca, "qe": pc.read_qe}
    if kind not in functions:
        raise ValueError("Coupling import supports orca or qe")
    bath = functions[kind](str(output_path), **(options or {}))
    return {"schema": "westquant_coupling_import_v1", "backend": kind,
            "source_sha256": hashlib.sha256(Path(output_path).read_bytes()).hexdigest(),
            "native_names": bath["N"].tolist(), "positions_angstrom": bath["xyz"].tolist(),
            "hyperfine_Hz": (np.asarray(bath["A"])*1000).tolist(),
            "quadrupole_Hz": (np.asarray(bath["Q"])*1000).tolist(),
            "frame": "backend_output_frame_requires_alignment",
            "not_automatically_usable_until_frame_and_site_mapping_reviewed": True}


def electronic(candidate, recipe, cache):
    """PySCF vertical electronic calculation at the supplied geometry with a content cache."""
    pyscf = optional_import("pyscf")
    from pyscf import gto, scf, dft, lib
    geometry = candidate.get("geometry_angstrom")
    if not geometry or candidate.get("charge_e") is None or candidate.get("spin_2S") is None:
        raise MissingData("Electronic calculation needs geometry, integer charge and 2S")
    if candidate.get("periodic"):
        raise UnsupportedPhysics("Molecular PySCF adapter cannot treat a periodic host")
    for atom, xyz in geometry:
        if not re.fullmatch(r"[A-Z][a-z]?", atom) or len(xyz) != 3 or not np.isfinite(xyz).all():
            raise ValueError("Invalid atomic geometry")
    threads = recipe.get("threads", 1)
    if not isinstance(threads, int) or threads < 1:
        raise ValueError("Positive integer threads required")
    lib.num_threads(threads)
    identity = digest({"geometry": geometry, "charge": candidate["charge_e"],
                       "spin_2S": candidate["spin_2S"], "recipe": recipe, "pyscf": pyscf.__version__})
    path = Path(cache)/("pyscf_"+identity+".json")
    if path.exists():
        result = read_json(path)
        return {**result, "cache_hit": True}
    mol = gto.M(atom=geometry, unit="Angstrom", charge=candidate["charge_e"],
                spin=candidate["spin_2S"], basis=recipe["basis"], ecp=recipe.get("ecp", {}),
                max_memory=recipe.get("memory_MB", 1024), verbose=0)
    if recipe.get("method", "HF") == "HF":
        mf = scf.UHF(mol) if mol.spin else scf.RHF(mol)
    elif recipe["method"] == "DFT":
        mf = dft.UKS(mol) if mol.spin else dft.RKS(mol)
        mf.xc = recipe["xc"]
    else:
        raise UnsupportedPhysics("Supported molecular methods: HF and DFT")
    if recipe.get("scalar_x2c"):
        mf = mf.x2c()
    mf.conv_tol = recipe.get("conv_tol", 1e-9)
    mf.max_cycle = recipe.get("max_cycle", 100)
    energy = mf.kernel()
    if not mf.converged or not math.isfinite(energy):
        raise NumericalFailure("SCF did not converge; no electronic result accepted")
    result = {"schema": "westquant_electronic_v1", "cache_key": identity,
              "backend": "pyscf", "backend_version": pyscf.__version__, "cache_hit": False,
              "energy_hartree": float(energy), "converged": True,
              "charge_e": mol.charge, "spin_2S": mol.spin, "geometry_angstrom": geometry,
              "geometry_optimized": False, "recipe": recipe, "evidence_kind": "computed",
              "T1_s": None, "T2_s": None, "bound_state_proven": False,
              "limitations": ["Born-Oppenheimer electrons at fixed geometry",
                              "No isotope-resolved spin/phonon dynamics",
                              "A finite-basis energy is not proof of an anion bound state"]}
    if recipe.get("excited_states", 0):
        response = mf.TDA()
        response.nstates = int(recipe["excited_states"])
        energies, _ = response.kernel()
        if not np.all(response.converged):
            raise NumericalFailure("Excited-state response did not converge")
        result["tda_excitation_energy_hartree"] = np.asarray(energies).tolist()
        result["tda_oscillator_strength"] = np.asarray(response.oscillator_strength()).tolist()
    write_json(path, result)
    return result


def prepare_external(kind, candidate, recipe, directory):
    """Generate real ORCA / Quantum ESPRESSO inputs; execute_external handles bounded subprocesses."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    if kind == "orca":
        geometry = candidate["geometry_angstrom"]
        keywords = recipe.get("keywords", "PBE def2-SVP TightSCF")
        text = "! "+keywords+"\n"+recipe.get("blocks", "")+"\n"
        text += f"* xyz {candidate['charge_e']} {candidate['spin_2S']+1}\n"
        for atom, xyz in geometry:
            if not re.fullmatch(r"[A-Z][a-z]?", atom) or len(xyz) != 3 or not np.isfinite(xyz).all():
                raise ValueError("Invalid ORCA geometry")
            text += atom+" "+" ".join(str(v) for v in xyz)+"\n"
        text += "*\n"
        path = directory/"orca.inp"
        path.write_text(text)
    elif kind == "qe":
        optional_import("ase")
        from ase import Atoms
        from ase.io.espresso import write_espresso_in
        if not candidate.get("periodic") or not candidate.get("cell_angstrom"):
            raise MissingData("QE needs an explicit periodic cell")
        atoms = Atoms(symbols=[x[0] for x in candidate["geometry_angstrom"]],
                      positions=[x[1] for x in candidate["geometry_angstrom"]],
                      cell=candidate["cell_angstrom"], pbc=True)
        path = directory/"qe.in"
        with path.open("w") as f:
            write_espresso_in(f, atoms, input_data=recipe["input_data"],
                             pseudopotentials=recipe["pseudopotentials"],
                             kpts=recipe["kpts"])
    else:
        raise ValueError("External backend must be orca or qe")
    job = {"backend": kind, "input": str(path.resolve()), "directory": str(directory.resolve()),
           "binary": recipe.get("binary"), "timeout_s": recipe.get("timeout_s", 600),
           "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    write_json(directory/"job.json", job)
    return job


def execute_external(job):
    binary = shutil.which(job["binary"] or ("orca" if job["backend"] == "orca" else "pw.x"))
    if not binary:
        raise BackendUnavailable("External binary is not installed/configured")
    command = [binary, job["input"]] if job["backend"] == "orca" else [binary, "-in", job["input"]]
    output = Path(job["directory"])/"backend.out"
    timeout = finite(job["timeout_s"], "timeout_s", 0.01)
    with output.open("w") as f:
        process = subprocess.Popen(command, cwd=job["directory"], stdout=f, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            process.wait()
            raise TimeoutError("External calculation exceeded timeout")
    if code:
        raise NumericalFailure(f"External backend exit={code}; inspect {output}")
    text = output.read_text(errors="replace")
    if job["backend"] == "orca":
        energies = re.findall(r"FINAL SINGLE POINT ENERGY\s+(-?[\d.]+)", text)
        if "ORCA TERMINATED NORMALLY" not in text or not energies:
            raise NumericalFailure("ORCA output did not confirm normal completion and energy")
        result = {"energy_hartree": float(energies[-1])}
    else:
        if "JOB DONE." not in text:
            raise NumericalFailure("QE output did not confirm completion")
        from ase.io import read
        atoms = read(output, format="espresso-out", index=-1)
        result = {"energy_eV": float(atoms.get_potential_energy())}
    return {**result, "backend": job["backend"], "output": str(output),
            "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "evidence_kind": "computed", "T1_s": None, "T2_s": None}


def maxwell_bloch(config, directory):
    """Classical field propagation. This output deliberately has no qubit-fidelity estimate."""
    optional_import("maxwellbloch")
    from maxwellbloch import mb_solve
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    config = dict(config)
    config["savefile"] = str((directory/"propagation").resolve())
    solver = mb_solve.MBSolve().from_json_str(json.dumps(config))
    solver.mbsolve(recalc=True, progress=False)
    path = directory/"fields.npz"
    np.savez_compressed(path, fields=solver.Omegas_zt, times_native=solver.tlist,
                        positions_native=solver.zlist)
    return {"backend": "maxwellbloch", "output": str(path),
            "quantity": "semiclassical_Rabi_field_amplitude", "evidence_kind": "computed",
            "qubit_fidelity": None, "units": "backend-native; rates/frequencies internally multiplied by 2pi",
            "requires_quantum_noise_model_for_memory_channel": True}
