"""Phase 2: Pilot CCE — measure cost and convergence before production.

Runs CCE on 10 stratified molecules with convergence sweeps to measure:
- CPU time per run
- Memory per run
- Failure rates
- Convergence behavior (CCE order, r_bath, r_dipole, realisations, time-grid)

Outputs pilot_budget.json with projected production cost.
"""
import json
import sqlite3
import time
import tracemalloc
from collections import Counter
from pathlib import Path

import numpy as np

from ..common import digest, read_json, write_json, now, seed
from .nucdata import get_isotope_data
from .bath import (
    read_cif_from_zip, build_pycce_bath, find_central_spin_position,
    get_formula_from_atoms, get_composition_from_atoms,
)
from ._compat import install_all_shims

install_all_shims()


# Pilot configuration
PILOT_MOLECULES = 10
PILOT_PATTERNS = ["natural", "perdeuterated"]
PILOT_FIELD_T = 0.35
PILOT_PROTOCOLS = ["Hahn", "CPMG-2", "CPMG-8"]
PILOT_REALISATIONS = 5

# Convergence sweep parameters
SWEEP_ORDER = [2, 3]
SWEEP_R_BATH = [20.0, 30.0, 40.0]
SWEEP_R_DIPOLE = [6.0, 8.0, 10.0]
SWEEP_REALISATIONS = [5, 10, 20]

# Time grid (in seconds)
PILOT_TIMES_S = np.linspace(0, 0.001, 101).tolist()  # 0 to 1 ms, 101 points


def select_pilot_molecules(universe_db_path, n=10):
    """Select stratified pilot molecules from the universe database.

    Prefers molecules with CIF structures and diverse metals.
    """
    db = sqlite3.connect(str(universe_db_path))
    try:
        rows = db.execute(
            "SELECT payload FROM universe WHERE family='molecular_spin' AND cif_match IS NOT NULL"
        ).fetchall()
    finally:
        db.close()

    candidates = [json.loads(r[0]) for r in rows]
    if not candidates:
        return []

    # Stratify by metal
    by_metal = {}
    for c in candidates:
        metal = c.get("metal") or "none"
        by_metal.setdefault(metal, []).append(c)

    # Select up to n, prioritizing metal diversity
    selected = []
    metals = sorted(by_metal.keys())
    while len(selected) < n and any(by_metal.values()):
        for metal in metals:
            if by_metal[metal] and len(selected) < n:
                selected.append(by_metal[metal].pop(0))

    return selected[:n]


def run_single_cce(bath_spec, times_s, field_T, cpmg_pulses, order=2,
                    simulation_seed=0, backend="pycce"):
    """Run a single CCE calculation and return result + timing.

    Returns:
        dict with: envelope, status, runtime_s, memory_mb, assumptions
    """
    from ..backends import pycce_coherence

    if bath_spec.get("bath") is None or bath_spec.get("bath_size", 0) == 0:
        return {
            "envelope": np.ones(len(times_s)).tolist(),
            "status": "success",
            "runtime_s": 0.0,
            "memory_mb": 0.0,
            "assumptions": bath_spec.get("assumptions", []),
            "bath_size": 0,
            "T2_s": None,
            "first_crossing": None,
        }

    # Build spec for pycce_coherence
    bath = bath_spec["bath"]
    spec = {
        "method": "cce",
        "nuclei": [],
        "center": {
            "spin_S": 0.5,
            "position_angstrom": [0.0, 0.0, 0.0],
            "alpha_index": 0,
            "beta_index": 1,
            "gyro_rad_s_T": 1.760859644e11,
            "zfs_Hz": np.zeros((3, 3)).tolist(),
        },
        "magnetic_field_T": field_T,
        "r_bath_angstrom": 30.0,
        "r_dipole_angstrom": 8.0,
        "order": order,
        "nbstates": 0,
    }

    # Convert bath to nuclei list
    for i in range(len(bath)):
        n = str(bath["N"][i])
        # Parse isotope: PyCCE format is like "1H", "13C"
        # Convert to our format "H-1", "C-13"
        import re
        m = re.match(r'^(\d+)([A-Z][a-z]?)$', n)
        if m:
            mass, symbol = m[1], m[2]
            iso_id = f"{symbol}-{mass}"
        else:
            continue
        spec["nuclei"].append({
            "isotope_id": iso_id,
            "position_angstrom": bath["xyz"][i].tolist(),
            "hyperfine_Hz": (np.asarray(bath["A"][i]) * 1000).tolist(),
            "quadrupole_Hz": (np.asarray(bath["Q"][i]) * 1000).tolist(),
            "frame": "lab",
        })

    # Time and memory tracking
    tracemalloc.start()
    started = time.monotonic()

    try:
        values = pycce_coherence(spec, times_s, cpmg_pulses, simulation_seed)
        runtime = time.monotonic() - started
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        envelope = np.abs(values).tolist()

        # Find first 1/e crossing
        from ..t2assessment import first_crossing
        crossing = first_crossing(times_s, envelope)

        return {
            "envelope": envelope,
            "status": "success",
            "runtime_s": runtime,
            "memory_mb": peak / 1e6,
            "assumptions": bath_spec.get("assumptions", []),
            "bath_size": bath_spec.get("bath_size", 0),
            "near_nuclei_excluded": bath_spec.get("near_nuclei_excluded", 0),
            "T2_s": None,
            "first_crossing": crossing,
        }
    except Exception as e:
        runtime = time.monotonic() - started
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return {
            "envelope": None,
            "status": "numerical_failure",
            "error": str(e),
            "runtime_s": runtime,
            "memory_mb": peak / 1e6,
            "assumptions": bath_spec.get("assumptions", []),
            "bath_size": bath_spec.get("bath_size", 0),
        }


def run_pilot(config, output_dir):
    """Run the Phase 2 pilot CCE campaign.

    Measures cost and convergence on 10 stratified molecules.
    Outputs pilot_budget.json with projected production cost.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    universe_db = config.get("universe_db_path", "screening/results/private/universe.sqlite")
    cif_zip_path = config.get("cif_zip_path")

    # Auto-detect CIF zip if not provided
    if not cif_zip_path:
        t2_root = Path(config.get("t2_data_root", "t2_data"))
        source_lock = read_json(t2_root / "source_lock.json")
        for rec in source_lock.get("artifacts", []):
            if rec.get("file_name") == "cifs_of_molecules.zip":
                cif_zip_path = str(t2_root / "cache" / rec["relative_path"])
                break

    # Select pilot molecules
    molecules = select_pilot_molecules(universe_db, PILOT_MOLECULES)
    if not molecules:
        return {"status": "no_molecules_with_cif", "error": "No molecules with CIF structures found"}

    results = []
    all_runtimes = []
    all_memory = []
    status_counts = Counter()
    bath_sizes = []

    master_seed = 20261011  # Pilot seed

    for mol_idx, mol in enumerate(molecules):
        mol_id = mol["id"]
        cif_filename = mol.get("cif_match")
        if not cif_filename or not cif_zip_path:
            continue

        # Read CIF
        try:
            atoms = read_cif_from_zip(cif_zip_path, cif_filename)
        except Exception as e:
            results.append({
                "molecule_id": mol_id, "status": "cif_read_error",
                "error": str(e), "runtime_s": 0,
            })
            status_counts["cif_read_error"] += 1
            continue

        # Find central spin position
        central_pos = find_central_spin_position(atoms, mol.get("metal"))

        for pattern in PILOT_PATTERNS:
            for protocol in PILOT_PROTOCOLS:
                cpmg_pulses = {"Hahn": 1, "CPMG-2": 2, "CPMG-8": 8}[protocol]

                for realisation in range(PILOT_REALISATIONS):
                    bath_seed = seed(master_seed, [mol_id, pattern, protocol], "bath", realisation)

                    # Build bath
                    try:
                        bath_spec = build_pycce_bath(
                            atoms, pattern, central_pos,
                            r_bath_angstrom=30.0, r_dipole_angstrom=8.0,
                            r_exclusion_angstrom=3.0,
                            simulation_seed=bath_seed,
                        )
                    except Exception as e:
                        results.append({
                            "molecule_id": mol_id, "pattern": pattern,
                            "protocol": protocol, "realisation": realisation,
                            "status": "bath_build_error", "error": str(e),
                            "runtime_s": 0,
                        })
                        status_counts["bath_build_error"] += 1
                        continue

                    # Run CCE
                    cce_seed = seed(master_seed, [mol_id, pattern, protocol], "cce", realisation)
                    result = run_single_cce(
                        bath_spec, PILOT_TIMES_S, PILOT_FIELD_T,
                        cpmg_pulses, order=2, simulation_seed=cce_seed,
                    )

                    result["molecule_id"] = mol_id
                    result["pattern"] = pattern
                    result["protocol"] = protocol
                    result["realisation"] = realisation
                    result["cif_filename"] = cif_filename
                    results.append(result)

                    status_counts[result["status"]] += 1
                    if result["status"] == "success":
                        all_runtimes.append(result["runtime_s"])
                        all_memory.append(result["memory_mb"])
                        bath_sizes.append(result.get("bath_size", 0))

    # Convergence sweep on first 3 molecules
    convergence_results = []
    for mol in molecules[:3]:
        mol_id = mol["id"]
        cif_filename = mol.get("cif_match")
        if not cif_filename:
            continue

        try:
            atoms = read_cif_from_zip(cif_zip_path, cif_filename)
        except Exception:
            continue

        central_pos = find_central_spin_position(atoms, mol.get("metal"))

        for order in SWEEP_ORDER:
            for r_bath in SWEEP_R_BATH:
                for r_dipole in SWEEP_R_DIPOLE:
                    bath_seed = seed(master_seed, [mol_id, "convergence"], "bath", 0)
                    try:
                        bath_spec = build_pycce_bath(
                            atoms, "natural", central_pos,
                            r_bath_angstrom=r_bath, r_dipole_angstrom=r_dipole,
                            r_exclusion_angstrom=3.0, simulation_seed=bath_seed,
                        )
                    except Exception as e:
                        convergence_results.append({
                            "molecule_id": mol_id, "order": order,
                            "r_bath": r_bath, "r_dipole": r_dipole,
                            "status": "bath_build_error", "error": str(e),
                        })
                        continue

                    cce_seed = seed(master_seed, [mol_id, "convergence"], "cce", 0)
                    result = run_single_cce(
                        bath_spec, PILOT_TIMES_S, PILOT_FIELD_T,
                        1, order=order, simulation_seed=cce_seed,
                    )
                    result["molecule_id"] = mol_id
                    result["order"] = order
                    result["r_bath"] = r_bath
                    result["r_dipole"] = r_dipole
                    convergence_results.append(result)

    # Compute statistics
    if all_runtimes:
        mean_runtime = float(np.mean(all_runtimes))
        median_runtime = float(np.median(all_runtimes))
        p90_runtime = float(np.percentile(all_runtimes, 90))
        mean_memory = float(np.mean(all_memory))
        mean_bath_size = float(np.mean(bath_sizes))
    else:
        mean_runtime = 0
        median_runtime = 0
        p90_runtime = 0
        mean_memory = 0
        mean_bath_size = 0

    # Project production cost
    # Full matrix: ~180,000 runs (from plan)
    # With mean runtime per run
    projected_cpu_hours = (180000 * mean_runtime) / 3600
    projected_wall_hours_8workers = projected_cpu_hours / 8

    report = {
        "schema": "westquant_screening_pilot_v1",
        "created_at": now(),
        "pilot_seed": master_seed,
        "molecules_selected": len(molecules),
        "total_runs": len(results),
        "status_counts": dict(status_counts),
        "runtime_stats": {
            "mean_s": mean_runtime,
            "median_s": median_runtime,
            "p90_s": p90_runtime,
            "total_cpu_s": sum(all_runtimes),
        },
        "memory_stats": {
            "mean_mb": mean_memory,
            "max_mb": max(all_memory) if all_memory else 0,
        },
        "bath_stats": {
            "mean_size": mean_bath_size,
            "max_size": max(bath_sizes) if bath_sizes else 0,
        },
        "convergence_sweep_results": len(convergence_results),
        "projected_production_cost": {
            "total_runs": 180000,
            "projected_cpu_hours": projected_cpu_hours,
            "projected_wall_hours_8workers": projected_wall_hours_8workers,
            "mean_runtime_per_run_s": mean_runtime,
            "assumption": "180k runs × mean pilot runtime / 8 workers",
        },
        "times_grid_s": {"start": 0, "end": 0.001, "points": 101},
        "field_T": PILOT_FIELD_T,
        "protocols": PILOT_PROTOCOLS,
        "patterns": PILOT_PATTERNS,
        "realisations": PILOT_REALISATIONS,
        "notes": [
            "Pilot measures actual cost before production matrix is locked",
            "Convergence sweeps on 3 molecules: CCE order, r_bath, r_dipole",
            "If mean runtime > 5 CPU-min/run, reduce matrix before production",
            "All results are computed (nuclear-spin-bath-limited coherence bound), not predictions",
        ],
    }

    # Write detailed results
    write_json(output_dir / "pilot_results.json", {
        "schema": "westquant_screening_pilot_results_v1",
        "created_at": now(),
        "results": results,
        "convergence_results": convergence_results,
    })

    # Write budget report
    write_json(output_dir / "pilot_budget.json", report)

    # Write manifest
    write_json(output_dir / "manifest_pilot.json", {
        "phase": "pilot",
        "created_at": now(),
        "config_hash": digest(config),
        "report_path": str(output_dir / "pilot_budget.json"),
    })

    return report


def run_tier2_production(config, output_dir):
    """Phase 5: Tier 2 production CCE runs. (Not yet implemented — requires pilot budget lock.)"""
    raise NotImplementedError(
        "Tier 2 production requires pilot budget to be locked in PREREGISTRATION.md first. "
        "Run `screen pilot` and review pilot_budget.json before proceeding."
    )
