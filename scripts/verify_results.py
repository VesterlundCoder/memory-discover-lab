"""Check the article's evidence snapshot and generate a claim-to-result map.

These are reporting/reproduction checks, not independent experimental validation.
Run after reproduce.py to verify fresh outputs, or alone to verify archived outputs.
"""
from pathlib import Path
import json
import math
import re
import argparse

ROOT = Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument("--inputs",type=Path,default=ROOT)
ap.add_argument("--numerical-replay",action="store_true",help="Exclude the wider molecular acquisition audit")
args=ap.parse_args();ROOT=args.inputs.resolve()
claims = []

def read(name):
    return json.loads((ROOT / name).read_text())

def record(identifier, claim, source, value, scope):
    claims.append(dict(id=identifier, claim=claim, source=source, value=value, scope=scope))

def near(actual, expected, tol=1e-10):
    if not math.isclose(actual, expected, rel_tol=tol, abs_tol=tol):
        raise AssertionError(f"{actual} does not reproduce {expected}")

teller = read("evidence/teller_summary.json")
a = teller["experimental_reanalysis"]
near(a["path_six_state_average"], 0.9510824228990328)
near(a["time_bin_six_state_average"], 0.9140479475068066)
assert a["raw_state_fidelities"] == 90 and not a["T2_identified"]
record("C1", "Processed state means reproduced", "evidence/teller_summary.json#/experimental_reanalysis",
       [a["path_six_state_average"], a["time_bin_six_state_average"]], "Processed-data reanalysis, not raw-trial replication")
h = read("evidence/teller_holdout.json")
near(h["maximum_absolute_z"], 2.3417323109381942)
assert h["status"] == "pass" and not h["external_experimental_replication"]
record("C2", "Spatial holdout diagnostic", "evidence/teller_holdout.json", h["maximum_absolute_z"],
       "Within one time-bin dataset; approximate uncorrelated MC errors")
assert teller["network_attempts"] == 400000 and teller["network_retrieved_pairs"] == 87
near(teller["simulated_conditional_Bell_fidelity"], 0.9048185746372305)
assert teller["analytic_qutip_max_choi_error"] < 2e-8 and teller["network_max_density_error"] < 1e-9
record("C3", "Ideal-input event-simulator integration", "evidence/teller_summary.json",
       {"attempts": 400000, "pairs": 87, "Bell_fidelity": teller["simulated_conditional_Bell_fidelity"]},
       "Simulation at a calibrated but nonunique operating-point channel")
assert all(x["status"] == "model_mismatch" for x in teller["negative_control_model"]["fits"])
record("C4", "Constant readout-window diagnostic mismatches", "evidence/teller_summary.json#/negative_control_model",
       [x["maximum_heldout_pointwise_z"] for x in teller["negative_control_model"]["fits"]],
       "Nested-window pointwise diagnostics; no lifetime inference")
p = read("evidence/pr2026_curve_summary.json")
statuses = [x["status"] for x in p["results"]]
assert statuses.count("model_mismatch") == 6 and statuses.count("inconclusive") == 2
assert all(x["identified_T2_s"] is None for x in p["results"])
record("C5", "Eight apparent classical-decay fits", "evidence/pr2026_curve_summary.json",
       {"mismatch": 6, "inconclusive": 2}, "No homogeneous physical spin T2 identified")
d = read("evidence/deterministic_summary.json")
assert d["database"]["reviewed_references"] == 10
expected_provisional = 0 if args.numerical_replay else 201
assert d["database"]["provisional_observations"] == expected_provisional
if args.numerical_replay:
    assert d["preparation"]["molecular_source_audit"].startswith("not_reproduced")
assert (d["completed_deterministic_calculations"], d["completed_spin_time_evaluations"],
        d["completed_rate_box_corners"]) == (3, 202, 4)
assert d["ML_training_runs"] == 0 and not d["new_material_T2_verified"]
assert d["table_assessments"]["unknown"] == "no_applicable_reference"
record("C6", "Condition-sensitive database and deterministic work counts", "evidence/deterministic_summary.json",
       {"reviewed": 10, "provisional": expected_provisional, "specifications": 3, "bath_evaluations": 202, "corners": 4},
       "Reference review and specified physics; molecular acquisition excluded" if args.numerical_replay else "Reference review and specified physics; no new-material prediction validation")
s = d["synthetic_count_control"]
near(s["recovered_s"], 0.000979663156865916)
assert s["interval"][0] < 0.001 < s["interval"][1] and not s["experimental_result"]
record("C7", "Known-generator count recovery", "lab/t2_runs/deterministic/synthetic_control/fit.json",
       {"recovered_s": s["recovered_s"], "interval_s": s["interval"]}, "One synthetic instance; not coverage or physical accuracy")
n = read("evidence/mean_fidelity_nonidentifiability.json")
near(n["mean_fidelity"], n["mean_fidelity_phase_flip"])
near(n["difference"], 3*n["depolarizing_p"]**2/8)
record("C8", "Equal means admit different Bell outputs", "evidence/mean_fidelity_nonidentifiability.json",
       n["difference"], "Constructive mean-only example; not two fits to every experimental state")
y = read("evidence/hypothetical_sequence.json")
assert y["retrieved_pairs"] == 321 and y["attempts"] == 2000 and not y["measured_network_performance"]
near(y["analytic_conditional_Bell_fidelity"], 0.9559176317211332)
record("C9", "Separate hypothetical network control", "evidence/hypothetical_sequence.json", 321,
       "Supplied uncalibrated IO parameters; numerical verification")
testlog = (ROOT / "evidence/paper_test_results.log").read_text()
assert re.search(r"Ran 75 tests", testlog) and re.search(r"^OK$", testlog, re.MULTILINE)
record("C10", "Automated suite passes", "evidence/paper_test_results.log", 75, "Software tests; no new hardware experiments")
(ROOT / "evidence/claim_result_map.json").write_text(json.dumps({"schema": "westquant_article_claim_map_v1", "claims": claims}, indent=2)+"\n")
print(f"Verified {len(claims)} reporting invariants; wrote evidence/claim_result_map.json")
