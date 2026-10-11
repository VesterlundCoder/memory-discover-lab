"""Independent recomputation of the Teller et al. (PRX 15, 031053) baseline.

Uses NumPy and SciPy only. Imports nothing from memorylab. Reads the released
CSV files from the archive cache and compares each recomputed number with the
value the lab reports. Usage: independent_check.py <lab dir> <out.json>
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np
from scipy.stats import binomtest

lab = Path(sys.argv[1]); base = lab / "baselines" / "teller2025"
rows = []
def check(name, mine, theirs, tol, note=""):
    d = abs(mine - theirs); rows.append({"check": name, "independent": mine, "lab": theirs, "abs_diff": d, "tolerance": tol, "pass": bool(d <= tol), "note": note})

# 1. source bytes: every cached raw file sits in a directory named by its SHA-256
raw = [p for p in (base / "cache" / "raw").rglob("*") if p.is_file()]
bad = [p.name for p in raw if hashlib.sha256(p.read_bytes()).hexdigest() != p.parent.name]
rows.append({"check": "raw source files match their SHA-256 directory names", "independent": len(raw) - len(bad), "lab": len(raw), "abs_diff": len(bad), "tolerance": 0, "pass": not bad, "note": ""})
find = lambda n: next(p for p in raw if p.name == n)
def table(n, sep=";"):
    out = []
    for line in find(n).read_text().splitlines():
        if line.startswith("#") or not line.strip(): continue
        out.append([float(x) for x in line.strip().strip(sep).split(sep)])
    return out
S = json.loads((base / "summary.json").read_text()); R = S["experimental_reanalysis"]; H = S["spatial_holdout"]; O = S["operating_point"]

# 2. path qubits (Fig. 4): 30 infidelities = 6 states x 5 pairs
inf, state, pair = (np.array(r) for r in table("4.csv"))
Fp = 1 - inf
check("path qubits: mean of 30 state fidelities", float(Fp.mean()), R["path_six_state_average"], 1e-12)
pair_avg = np.array([Fp[pair == k].mean() for k in range(5)])
win = np.array([r[0] for r in table("5_xaxis.csv")]); i270 = int(np.argmin(abs(win - 270)))
F5 = np.array(table("5_yaxis2_F.csv")); Fmin = np.array(table("5_yaxis2_Fmin.csv")); Fmax = np.array(table("5_yaxis2_Fmax.csv"))
for row, k, lab_ in ((0, 0, "(1,2)"), (1, 2, "(5,6)"), (2, 4, "(9,10)")):
    check(f"Fig. 4 six-state mean vs Fig. 5 at 270 ns, pair {lab_}", float(pair_avg[k]), float(F5[row, i270]), 1e-12, "data-consistency check inside one data set")
check("operating point: conditional average fidelity, pair (5,6), 270 ns", float(pair_avg[2]), O["conditional_average_fidelity"], 1e-12)
check("operating point: fidelity uncertainty (Fmax - Fmin)/2", float((Fmax[1, i270] - Fmin[1, i270]) / 2), O["fidelity_standard_error"], 1e-12)

# 3. time-bin qubits (Fig. 8a): 60 infidelities = 6 states x 10 cells
inf8, st8, cell8 = (np.array(r) for r in table("8a.csv"))
Ft = 1 - inf8
check("time-bin qubits: mean of 60 state fidelities", float(Ft.mean()), R["time_bin_six_state_average"], 1e-12)
cell_avg = np.array([Ft[cell8 == c].mean() for c in range(1, 11)])
F8 = np.array(table("8b_F.csv")).ravel(); F8lo = np.array(table("8b_Fmin.csv")).ravel(); F8hi = np.array(table("8b_Fmaxn.csv")).ravel()
check("Fig. 8a per-cell means vs Fig. 8b, worst cell", float(np.max(abs(cell_avg - F8))), 0.0, 1e-12, "data-consistency check inside one data set")

# 4. published density matrix (Fig. 3b) against the X-state fidelity of pair (5,6)
rho = np.array([[complex(x) for x in l.split(",")] for l in find("3b.csv").read_text().splitlines() if not l.startswith("#")])
plus = np.array([1, 1]) / np.sqrt(2)
fx = float(np.real(plus.conj() @ rho @ plus))
check("Fig. 3b density matrix: fidelity with |X>", fx, R["released_density_matrix_X_fidelity"], 1e-9)
check("Fig. 3b fidelity vs Fig. 4 X state of pair (5,6)", fx, float(Fp[(pair == 2) & (state == 0)][0]), 1e-9, "released matrix has 10 decimals")

# 5. spatial hold-out: calibrate on odd cells, predict even cells
sig = (F8hi - F8lo) / 2
odd, even = np.arange(0, 10, 2), np.arange(1, 10, 2)
w = 1 / sig[odd] ** 2
fit = float(np.sum(w * F8[odd]) / np.sum(w)); se = float(np.sqrt(1 / np.sum(w)))
z = abs(F8[even] - fit) / np.sqrt(sig[even] ** 2 + se ** 2)
check("hold-out: inverse-variance mean of cells 1,3,5,7,9", fit, H["fitted_average_fidelity"], 1e-12)
check("hold-out: standard error of that mean", se, H["fit_standard_error"], 1e-12)
check("hold-out: largest |z| over cells 2,4,6,8,10", float(z.max()), H["maximum_absolute_z"], 1e-9, "threshold 3")

# 6. isotropic channel from the measured average fidelity, built from scratch
F = float(pair_avg[2]); p = 2 * (1 - F)
I2 = np.eye(2); X = np.array([[0, 1], [1, 0]]); Y = np.array([[0, -1j], [1j, 0]]); Z = np.diag([1.0, -1.0])
K = [np.sqrt(1 - 3 * p / 4) * I2] + [np.sqrt(p / 4) * P for P in (X, Y, Z)]
probes = [np.array(v, complex) / np.linalg.norm(v) for v in ([1, 1], [1, -1], [1, 1j], [1, -1j], [1, 0], [0, 1])]
favg = float(np.mean([np.real(v.conj() @ sum(k @ np.outer(v, v.conj()) @ k.conj().T for k in K) @ v) for v in probes]))
check("isotropic channel: six-state average fidelity returns the input", favg, F, 1e-12, "self-consistency of the construction")
sample = json.loads((base / "channel_samples.json").read_text())["samples"][0]
check("entanglement fidelity (3F - 1)/2", (3 * F - 1) / 2, sample["metrics"]["conditional_entanglement_fidelity"], 1e-12)
bell = np.array([1, 0, 0, 1], complex) / np.sqrt(2); rb = np.outer(bell, bell.conj())
out = sum(np.kron(a, b) @ rb @ np.kron(a, b).conj().T for a in K for b in K)
check("two memories on a Bell pair: conditional Bell fidelity", float(np.real(bell.conj() @ out @ bell)), S["simulated_conditional_Bell_fidelity"], 1e-12)

# 7. acceptance probability from the supplement's Table I, pair (5,6), and the 42 % window fraction
comp = [(0.16, 0.01), (0.42, 0.02), (0.50, 0.04)]; eta_d = 0.42
eta = float(np.prod([c[0] for c in comp]) * eta_d)
check("signal acceptance eta_AFC * eta_TW * eta_AOD * eta_D", eta, O["signal_retrieval_probability"], 1e-15)
check("its propagated standard error (independent components)", eta * float(np.sqrt(sum((s / v) ** 2 for v, s in comp))), O["retrieval_standard_error_conditional_on_window_fraction"], 1e-12)
check("two-memory success probability eta^2", eta ** 2, S["network_expected_success_probability"], 1e-15)
choi = np.array(sample["choi"]["real"]) + 1j * np.array(sample["choi"]["imag"])
check("lab Choi matrix: trace equals input dimension", float(np.real(np.trace(choi))), 2.0, 1e-12)
check("lab Choi matrix: smallest eigenvalue is non-negative", float(np.linalg.eigvalsh((choi + choi.conj().T) / 2).min()), sample["cptp"]["choi_min_eigenvalue"], 1e-12)
# rebuild the 2 -> 3 (qubit + erasure) Choi matrix with column vectorisation and compare element-wise
K3 = [np.sqrt(eta) * np.vstack([k, np.zeros((1, 2))]) for k in K] + [np.sqrt(1 - eta) * np.array([[0, 0], [0, 0], [1, 0]]), np.sqrt(1 - eta) * np.array([[0, 0], [0, 0], [0, 1]])]
mine = sum(np.outer(k.reshape(-1, order="F"), k.reshape(-1, order="F").conj()) for k in K3)
check("lab Choi matrix vs matrix rebuilt from scratch, largest element difference", float(np.max(abs(mine - choi))), 0.0, 1e-12)

# 8. event simulation: four seeds, 100 000 attempts each
runs = [json.loads(p.read_text()) for p in sorted((base / "sequence_runs").glob("seed_*.json"))]
n = sum(r["attempts"] for r in runs); k = sum(r["retrieved_pairs"] for r in runs)
bt = binomtest(k, n, eta ** 2)
rows.append({"check": "SeQUeNCe: retrieved pairs against binomial expectation", "independent": n * eta ** 2, "lab": k, "abs_diff": abs(k - n * eta ** 2), "tolerance": None, "pass": bool(bt.pvalue > 0.05), "note": f"{k} of {n} attempts; two-sided exact binomial p = {bt.pvalue:.3f}; per seed {[r['retrieved_pairs'] for r in runs]}"})
check("SeQUeNCe: observed conditional Bell fidelity, worst seed", float(max(abs(r["observed_conditional_Bell_fidelity"] - np.real(bell.conj() @ out @ bell)) for r in runs)), 0.0, 1e-12)

json.dump({"n_checks": len(rows), "n_pass": sum(r["pass"] for r in rows), "rows": rows}, open(sys.argv[2], "w"), indent=1)
for r in rows: print(("PASS " if r["pass"] else "FAIL ") + f"{r['check']}: {r['independent']!r} vs {r['lab']!r} (diff {r['abs_diff']:.3g}) {r['note']}")
print(sum(r["pass"] for r in rows), "of", len(rows), "pass")
