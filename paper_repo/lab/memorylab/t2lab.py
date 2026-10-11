"""Experimental tables and deterministic T2 CLI: python -m memorylab.t2lab --help."""
import argparse
import sys
from pathlib import Path
import numpy as np
from .common import read_json, write_json, digest, environment
from .t2data import fetch_sources, parse_pr2026, molecular_rows, enrich_structures, join_computations
from .t2curves import fit_curve


def prepare(root, offline=False, structures=False, reviews=None, computations=None):
    records = fetch_sources(root, offline, structures)
    curves, quantum = parse_pr2026(root, records)
    rows, audit = molecular_rows(root, records, read_json(reviews) if reviews else None)
    structural = enrich_structures(rows, root, records) if structures else {"status": "not_requested", "enriched_rows": 0}
    if computations: rows = join_computations(rows, read_json(computations))
    target = Path(root)/"processed"
    for c in curves: write_json(target/"curves"/(c["id"]+".json"), c)
    write_json(target/"quantum_readout.json", quantum)
    write_json(target/"molecular_rows.json", rows)
    audit["structures"] = structural
    audit["processed_data_hash"] = digest(rows)
    write_json(target/"audit.json", audit)
    return {"artifacts": len(records), "curves": len(curves), "provisional_observations": len(rows),
            "reviewed_observations": audit["reviewed_labels"], "physical_T2_requires_review": True,
            "output": str(target), "molecular_parameter_gate": "blocked_for_physical_T2" if not audit["reviewed_labels"] else "select_reviewed_subset"}


def baseline(root, out, bootstrap=100):
    output = Path(out); output.mkdir(parents=True, exist_ok=True)
    curves = sorted((Path(root)/"processed"/"curves").glob("*.json"))
    if not curves: raise ValueError("Prepare data before baseline")
    results = []
    for path in curves:
        curve = read_json(path)
        for model in ("exponential", "stretched"):
            result = fit_curve(curve, model, bootstrap=bootstrap)
            write_json(output/(path.stem+"_"+model+".json"), result)
            results.append({"curve": path.stem, "model": model, "status": result["status"],
                            "identified_T2_s": result["identified_T2_s"], "issues": result["issues"],
                            "apparent_decay_scale_s": result["apparent_decay_scale_s"],
                            "heldout_standardized_rmse": result["heldout_standardized_rmse"],
                            "goodness_p_approx": result["goodness_p_approx"]})
    summary = {"baseline": "PRL2026_21532904", "planned_fits": 2*len(curves), "completed_fits": len(results),
               "results": results, "conditions": "Pr3+:Y2SiO5, 3K cryostat stage, four rephasing sequences",
               "status": "negative_control_reproduced" if any(r["status"] == "model_mismatch" for r in results) else "inconclusive",
               "physical_spin_T2_identified": False, "full_qubit_memory_channel_identified": False,
               "limitations": ["Classical efficiency decay is not qubit process tomography",
                               "Residual field and modulation prevent unique homogeneous T2 inference",
                               "Separate heralded-photon data do not measure qubit fidelity",
                               "No values substituted for missing T1, phase transfer or optical AFC interval"]}
    write_json(output/"summary.json", summary)
    return summary


def synthetic_demo(out, bootstrap=100):
    """Known physics/counts control, explicitly not an experimental baseline."""
    rng = np.random.default_rng(20261010)
    ages = np.r_[0, np.geomspace(1e-5, 0.004, 20)]
    times = np.repeat(ages, 4); phases = np.tile([0, np.pi/2, np.pi, 3*np.pi/2], len(ages))
    probability = (1+0.8*np.exp(-times/0.001)*np.cos(phases))/2
    trials = np.full(len(times), 4000)
    curve = {"times_s": times.tolist(), "phases_rad": phases.tolist(), "counts_plus": rng.binomial(trials, probability).tolist(),
             "trials": trials.tolist(), "likelihood": "binomial", "quantity": "phase_resolved_projection",
             "decay_factor": 1, "target_definition": "T2_synthetic_total_coherence", "time_definition": "Total free evolution time in seconds",
             "conditions": {"temperature_K": 3, "pulse_sequence": "Ramsey", "T1_included": False},
             "mapping_review": {"status": "reviewed", "source": "Analytic generated count probability"},
             "provenance": [{"evidence_kind": "hypothetical", "generator_seed": 20261010}],
             "synthetic_truth_T2_s": 0.001}
    result = fit_curve(curve, bootstrap=bootstrap)
    result["evidence_kind"] = "hypothetical"
    result["experimental_T2_identified"] = False
    write_json(Path(out)/"curve.json", curve); write_json(Path(out)/"fit.json", result)
    return {"status": result["status"], "synthetic_truth_s": 0.001, "recovered_s": result["identified_T2_s"],
            "interval": result["conditional_bootstrap_95_interval_s"], "experimental_result": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--root", default="t2_data"); p.add_argument("--offline", action="store_true")
    p.add_argument("--structures", action="store_true"); p.add_argument("--reviews"); p.add_argument("--computations")
    p = sub.add_parser("baseline"); p.add_argument("--root", default="t2_data"); p.add_argument("--out", default="t2_runs/baseline")
    p.add_argument("--bootstrap", type=int, default=100)
    p = sub.add_parser("fit"); p.add_argument("curve"); p.add_argument("--model", choices=["exponential", "stretched"], default="exponential")
    p.add_argument("--bootstrap", type=int, default=200); p.add_argument("--out", default="t2_runs/fit.json")
    p = sub.add_parser("demo"); p.add_argument("--out", default="t2_runs/synthetic_demo"); p.add_argument("--bootstrap", type=int, default=100)
    p = sub.add_parser("database"); p.add_argument("--root", default="t2_data"); p.add_argument("--references", default="data/t2_references.json"); p.add_argument("--out", default="t2_data/t2.sqlite")
    p = sub.add_parser("assess"); p.add_argument("query"); p.add_argument("--database", default="t2_data/t2.sqlite"); p.add_argument("--out", default="t2_runs/assessment.json")
    p = sub.add_parser("calculate"); p.add_argument("specification"); p.add_argument("--out", default="t2_runs/calculation.json")
    p = sub.add_parser("run"); p.add_argument("--offline", action="store_true"); p.add_argument("--sequence", action="store_true")
    p.add_argument("--root", default="t2_data"); p.add_argument("--out", default="t2_runs/deterministic")
    args = ap.parse_args()
    try:
        if args.command == "prepare": result = prepare(args.root, args.offline, args.structures, args.reviews, args.computations)
        elif args.command == "baseline": result = baseline(args.root, args.out, args.bootstrap)
        elif args.command == "fit":
            result = fit_curve(read_json(args.curve), args.model, args.bootstrap); write_json(args.out, result)
        elif args.command == "database":
            from .t2assessment import build_database
            result = build_database(args.root, args.references, args.out)
        elif args.command == "assess":
            from .t2assessment import assess_database
            result = assess_database(args.database, read_json(args.query)); write_json(args.out, result)
        elif args.command == "calculate":
            from .t2assessment import calculate
            result = calculate(read_json(args.specification)); write_json(args.out, result)
        elif args.command == "run":
            from .t2workflow import run
            result = run(args.root, args.out, args.offline, args.sequence)
        else: result = synthetic_demo(args.out, args.bootstrap)
        print(__import__("json").dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        if isinstance(result, dict) and result.get("failed_model_fits", 0): return 1
        return 0
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr); return 2


if __name__ == "__main__":
    sys.exit(main())
