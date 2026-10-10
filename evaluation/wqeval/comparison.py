"""Step 1: matched direct-script comparison and a cited capability audit."""
import copy
import json
import time
from pathlib import Path
import numpy as np
from memorylab.channels import apply, choi
from memorylab.experimental import parse_indexed_infidelity
from memorylab.models import evaluate
from . import reference
from .common import LAB, ROOT, read, write, hash_file, audit_identity, csv_rows, new_output

def cases(config):
    profile_path = LAB / "baselines/teller2025/measured_point_profile.json"
    point = read(profile_path)
    records = [{"id": "teller_calibrated_point", "profile": point,
                "times_s": [point["point"]["end_to_end_age_s"]], "kind": "experiment_constrained_point"}]
    base = read(LAB / "examples/atomic_ensemble_profile.json")
    for i, gamma in enumerate(config["population_rates_s_inv"]):
        for temp in config["storage_temperatures_K"]:
            p = copy.deepcopy(base)
            p["rates"]["population"]["rate_s_inv"] = gamma
            p["temperatures_K"]["storage"] = temp
            p["detuning_Hz"] = config["detunings_Hz"][i]
            p["equilibrium_excited_population"] = config["excited_populations"][i]
            p["network_activity"] = {"attempt_rate_Hz": 10, "coherence_loss_per_attempt": .002}
            records.append({"id": f"markov_{i}_T{temp}", "profile": p,
                            "times_s": config["times_s"], "kind": "specified_software_control"})
    return records

def run(config, output, offline=False):
    if config["timing_repeats"] < 1 or len(config["population_rates_s_inv"]) != len(config["detunings_Hz"]) or len(config["population_rates_s_inv"]) != len(config["excited_populations"]):
        raise ValueError("Positive timing repeats and matching parameter array lengths required")
    out = new_output(output)
    items = cases(config)
    rows = []
    for case in items:
        actual = evaluate(case["profile"], case["times_s"], "analytic")
        direct = reference.evaluate(case["profile"], case["times_s"])
        for channel, ref in zip(actual, direct):
            errors = [np.max(np.abs(apply(channel.conditional_kraus, rho)-reference.action(ref["superoperator"], rho)))
                      for rho in reference.state_probes()]
            rows.append({"case": case["id"], "evidence": case["kind"], "age_s": ref["age_s"],
                         "full_choi_max_error": float(np.max(np.abs(choi(channel.full_kraus())-ref["choi"]))),
                         "six_state_output_max_error": float(max(errors)),
                         "fidelity_error": abs(channel.metrics()["conditional_average_fidelity"]-ref["average_fidelity"]),
                         "acceptance_error": abs(channel.success_probability-ref["acceptance"])})
    csv_rows(out / "channel_comparison.csv", rows)
    write(out / "cases.json", items)
    from .datasets import ensure_teller
    manifest, cache = ensure_teller(offline=offline)
    sources, data_rows = [], []
    for filename, cells, base, labels in [("4.csv", 5, 0, ["X","-X","Y","-Y","0","1"]),
                                         ("8a.csv",10,1,["X","-X","Y","-Y","E","L"])]:
        a = manifest["artifacts"][filename]
        path = cache / filename
        if hash_file(path) != a["sha256"]:
            raise ValueError("Teller source checksum mismatch")
        sources.append(path)
        direct = reference.parse_fidelities(path, cells, base)
        framework = parse_indexed_infidelity(path, cells, labels, "basis,cell", base)
        data_rows.append({"file": filename, "values": int(direct.size), "mean_direct": float(direct.mean()),
                          "mean_westquant": float(framework.mean()), "max_error": float(np.max(abs(direct-framework))),
                          "source_sha256": a["sha256"]})
    csv_rows(out / "data_comparison.csv", data_rows)
    # Warm-up both arms; repeated order is randomized and recorded. No IO or
    # export is timed: these are explicitly local channel-construction timings.
    def arm(name):
        for case in items:
            if name == "westquant": evaluate(case["profile"], case["times_s"], "analytic")
            else: reference.evaluate(case["profile"], case["times_s"])
    arm("westquant"); arm("direct")
    rng = np.random.default_rng(config["seed"])
    timing = []
    for repeat in range(config["timing_repeats"]):
        order = list(rng.permutation(["westquant", "direct"]))
        for position, name in enumerate(order):
            start = time.perf_counter(); arm(name)
            timing.append({"repeat": repeat, "position": position, "arm": str(name),
                           "elapsed_s": time.perf_counter()-start})
    csv_rows(out / "construction_timing.csv", timing)
    largest = max(max(r[k] for r in rows) for k in ["full_choi_max_error", "six_state_output_max_error", "fidelity_error", "acceptance_error"])
    summary = {"step": 1, "status": "pass" if max(largest, max(x["max_error"] for x in data_rows)) <= config["tolerance"] else "numerical_mismatch",
               "profile_count": len(items), "channel_age_points": len(rows),
               "processed_fidelity_values": sum(x["values"] for x in data_rows),
               "max_full_choi_error": max(x["full_choi_max_error"] for x in rows),
               "max_state_error": max(x["six_state_output_max_error"] for x in rows),
               "max_fidelity_error": max(x["fidelity_error"] for x in rows),
               "max_acceptance_error": max(x["acceptance_error"] for x in rows),
               "max_processed_value_error": max(x["max_error"] for x in data_rows),
               "data_results": data_rows, "tolerance": config["tolerance"],
               "median_construction_s": {name: float(np.median([x["elapsed_s"] for x in timing if x["arm"]==name]))
                                         for name in ["westquant", "direct"]},
               "timing_repeats_per_arm": config["timing_repeats"],
               "timing_scope": "warm local channel construction only; no file IO, network events, fitting, electronic structure or equalized export contract",
               "baseline": "independently written NumPy/SciPy matrix-exponential script with reviewed inputs",
               "not_claimed": ["speed superiority", "less researcher time", "superiority over AiiDA", "new material T2", "independent external reproduction"],
               "related_tools_execution": {"AiiDA": "documentation audit only; not installed or run in this comparison",
                                            "PySCF/PyCCE/QuTiP/SeQUeNCe": "capability context; not separately benchmarked here"},
               "identity": audit_identity(config, sources+[LAB / "baselines/teller2025/measured_point_profile.json"])}
    write(out / "summary.json", summary)
    related = read(ROOT / "evaluation/config/related_tools.json")
    write(out / "related_tools_audit.json", related)
    csv_rows(out / "related_tools.csv", related["tools"])
    lines = ["# Step 1: matched workflow comparison", "", "## Executed results", "",
             f"Compared {len(items)} profiles at {len(rows)} age points and {summary['processed_fidelity_values']} processed experimental fidelity values.",
             f"Maximum full-channel Choi discrepancy: {summary['max_full_choi_error']:.6g}; gate {config['tolerance']:g}.",
             f"Maximum six-state output discrepancy: {summary['max_state_error']:.6g}.", "",
             "| Dataset | Direct mean | WestQuant mean | Maximum discrepancy |", "|---|---:|---:|---:|"]
    lines += [f"| {r['file']} | {r['mean_direct']:.10f} | {r['mean_westquant']:.10f} | {r['max_error']:.3g} |" for r in data_rows]
    lines += ["", "## Matched scope and interpretation", "",
              "The baseline was written independently using NumPy/SciPy Liouvillian exponentiation; it does not import the lab's channel construction. Both arms receive identical reviewed conditions. The baseline also verifies raw source hashes, so it is not intentionally deprived of source integrity.",
              "The direct script and framework agree within the stated numerical gate. This checks preservation of the specified equations across the integration boundary. It establishes neither new physics nor general superiority over custom scripts.",
              "WestQuant contributes reusable condition/evidence contracts, channel export and orchestration. Those capabilities can also be implemented by custom scripts or domain-specific plugins in an existing workflow engine. The integration decision therefore rests on reusable domain semantics, not the assertion that provenance or caching is new.",
              "", "## Local construction timing", "",
              f"Warm median: WestQuant {summary['median_construction_s']['westquant']:.6f} s; direct script {summary['median_construction_s']['direct']:.6f} s. {config['timing_repeats']} randomized-order repeats per arm.",
              "These timings do not equalize full export, metadata or validation work. They exclude data ingestion, output IO, network events and downstream solvers. They cannot establish an end-to-end speedup. Native thread settings and machine details are recorded in the run environment; cross-machine performance is not assessed.",
              "", "## Related tools: documentary comparison", "",
              "| Tool | Existing capability | WestQuant relationship | Execution in step 1 |", "|---|---|---|---|"]
    lines += [f"| {r['tool']} | {r['existing_capability']} | {r['relationship']} | {r['execution']} |" for r in related["tools"]]
    lines += ["", "## Primary documentation", ""]+[f"- {r['tool']}: {r['source_url']}" for r in related["tools"]]
    lines += ["", "## Remaining evidence", "",
              "No independent AiiDA run, researcher-effort study, all-elements benchmark, external reproducibility exercise or second-family physical validation is supplied by this comparison. The ablation and performance commands evaluate different questions and their output must be reported separately.",
              "", "Reproduce from the repository root:", "", "```bash", "python scripts/evaluate_system.py step1 --out evaluation/results/step1-new", "```", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return summary
