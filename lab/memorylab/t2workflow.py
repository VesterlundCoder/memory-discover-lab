"""Reproduce reviewed tables, negative curve controls and deterministic models."""
from pathlib import Path
import numpy as np
from .common import read_json, write_json, digest, environment
from .t2assessment import build_database, assess_database, calculate
from .t2lab import prepare, baseline, synthetic_demo


def run(root="t2_data", out="t2_runs/deterministic", offline=False, use_sequence=False, reviewed_bundle=None):
    base = Path(__file__).resolve().parents[1]
    output = Path(out)
    if reviewed_bundle is not None:
        from .bundled import prepare_reviewed
        preparation = prepare_reviewed(root, reviewed_bundle)
    else:
        preparation = prepare(root, offline=offline, structures=False)
    database = Path(root)/"t2.sqlite"
    db_result = build_database(root, base/"data/t2_references.json", database)
    table_results = {}
    for name in ("reference", "unknown"):
        result = assess_database(database, read_json(base/f"examples/t2_{name}_query.json"))
        write_json(output/f"table_{name}.json", result); table_results[name] = result["status"]
    calculations = {}
    for name in ("markov_calculation", "spin_bath_0pulse", "spin_bath_1pulse"):
        result = calculate(read_json(base/f"examples/t2_{name}.json"))
        write_json(output/f"{name}.json", result); calculations[name] = result
    control = synthetic_demo(output/"synthetic_control", bootstrap=60)
    negative = baseline(root, output/"experimental_decay", bootstrap=30)
    # The experimental reference is not silently promoted to an optical channel.
    # This supplied write/read scenario is an explicit software integration test.
    from .models import evaluate
    from .network import export, MemoryDevice, link_benchmark
    profile = read_json(base/"examples/molecular_spin_profile.json")
    ages = [0, .0001, .0005]
    analytic = evaluate(profile, ages, "analytic")
    export(analytic, output/"hypothetical_network_device.json", allow_hypothetical=True)
    device = MemoryDevice(analytic, allow_hypothetical=True)
    workload = dict(attempts=2000, attempt_interval_s=.001, storage_age_s=.0005,
                    link_herald_probability=.5, minimum_Bell_fidelity=.8)
    net = link_benchmark(device, device, workload, 20261010)
    write_json(output/"hypothetical_network.json", net)
    simulator = None
    if use_sequence:
        from .sequence_adapter import run_link
        from .channels import choi
        quantum = evaluate(profile, ages, "qutip")
        max_difference = max(float(np.max(np.abs(choi(a.full_kraus())-choi(q.full_kraus()))))
                             for a, q in zip(analytic, quantum))
        if max_difference > 2e-8: raise ValueError("QuTiP channel check failed")
        simulator = run_link(device, device, workload, 20261010)
        simulator["max_choi_difference_qutip_analytic"] = max_difference
        write_json(output/"hypothetical_sequence.json", simulator)
    result = {"schema": "westquant_deterministic_t2_run_v1", "preparation": preparation,
        "database": db_result, "table_assessments": table_results,
        "completed_deterministic_calculations": len(calculations),
        "completed_spin_time_evaluations": sum(v.get("completed_time_evaluations", 0) for v in calculations.values()),
        "completed_rate_box_corners": calculations["markov_calculation"]["parameter_box"]["completed_corner_evaluations"],
        "completed_experimental_curve_fits": negative["completed_fits"],
        "synthetic_count_control": control, "experimental_decay_status": negative["status"],
        "new_material_T2_verified": False, "ML_training_runs": 0,
        "network_scenario": "hypothetical software control with supplied IO parameters",
        "sequence_ran": simulator is not None, "environment": environment(),
        "research_gates": {"reference_units_and_definitions": "pass", "unknown_material_T2": "inconclusive",
             "classical_decay_homogeneous_T2_model": "fail", "synthetic_count_recovery": control["status"],
             "new_material_outperforms_experimental_memory": "inconclusive"}}
    write_json(output/"summary.json", result)
    return result
