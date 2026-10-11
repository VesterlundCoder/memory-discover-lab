"""Run the lab's own SeQUeNCe workload for 40 seeds that were not in the archive.

Calls the lab's network function unchanged; only the seed list is new.
Usage (from the lab directory): extra_seeds.py <out.json>
"""
import inspect, json, sys, time
import numpy as np
from scipy.stats import chi2, binomtest
from memorylab.common import read_json
import memorylab.baseline_workflow as bw
from memorylab.network import load_device

run_link = bw.run_link
cfg = read_json("examples/teller2025_baseline.json")
device = load_device("baselines/teller2025/network_device.json")
p = 0.16 * 0.42 * 0.50 * 0.42
p2 = p * p
seeds = list(range(1, 41)); n = cfg["network_workload"]["attempts"]
t0 = time.time(); counts, fids = [], []
for s in seeds:
    r = run_link(device, device, cfg["network_workload"], s)
    counts.append(r["retrieved_pairs"]); fids.append(r["observed_conditional_Bell_fidelity"])
k = np.array(counts); mu = n * p2
x_known = float(np.sum((k - mu) ** 2 / mu)); x_hom = float(np.sum((k - k.mean()) ** 2 / k.mean()))
out = {"seeds": seeds, "attempts_per_seed": n, "expected_per_seed": mu, "retrieved_pairs": counts,
       "total": int(k.sum()), "expected_total": mu * len(seeds),
       "binomial_p_value_total": binomtest(int(k.sum()), n * len(seeds), p2).pvalue,
       "dispersion_index_variance_over_mean": float(k.var(ddof=1) / k.mean()),
       "chi2_against_known_mean": x_known, "p_against_known_mean": float(chi2.sf(x_known, len(seeds))),
       "chi2_homogeneity": x_hom, "p_homogeneity": float(chi2.sf(x_hom, len(seeds) - 1)),
       "bell_fidelity_min_max": [float(np.nanmin([f for f in fids if f is not None])), float(np.nanmax([f for f in fids if f is not None]))],
       "seconds": round(time.time() - t0, 1)}
json.dump(out, open(sys.argv[1], "w"), indent=1); print(json.dumps(out)[:900])
