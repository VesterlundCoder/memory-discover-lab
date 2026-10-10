"""Generate supplementary LaTeX tables and CSVs from executed JSON results."""
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "tables"
TABLES.mkdir(exist_ok=True)

def read(path):
    return json.loads((ROOT / path).read_text())

def csv_table(name, rows):
    with (TABLES / f"{name}.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def latex_table(name, columns, headings, rows, caption):
    header = " & ".join(headings) + r" \\"
    body = "\n".join(" & ".join(map(str, row)) + r" \\" for row in rows)
    tex = (r"\begin{table}[htbp]" + "\n" + r"\centering\small" + "\n"
           + r"\begin{tabular}{" + columns + "}\n" + r"\toprule" + "\n"
           + header + "\n" + r"\midrule" + "\n" + body + "\n"
           + r"\bottomrule\end{tabular}" + "\n" + r"\caption{" + caption
           + "}\n" + r"\end{table}" + "\n")
    (TABLES / f"{name}.tex").write_text(tex)

holdout = read("evidence/teller_holdout.json")["comparisons"]
csv_table("holdout", holdout)
latex_table("holdout", "rrrr", ["Cell", "Observed fidelity", "Supplied MC width", r"$|z|$"],
            [[x["cell"], f'{x["observed"]:.6f}', f'{x["experimental_sigma"]:.6f}',
              f'{x["absolute_z"]:.4f}'] for x in holdout],
            "Within-dataset even-cell holdout. All predictions use the odd-cell calibrated mean. "
            "Shared systematics and cross-cell covariance are unavailable.")

fits = read("evidence/pr2026_curve_summary.json")["results"]
csv_table("decay", [{k: v for k, v in x.items() if k != "issues"} for x in fits])
rows = []
boot = []
for x in fits:
    p = x["goodness_p_approx"]
    probability = f"{p:.3g}" if p else r"$<10^{-300}$ (underflow)"
    rows.append([x["curve"].removeprefix("pr2026_"),
                 "Exp." if x["model"] == "exponential" else "Stretch.",
                 f'{x["apparent_decay_scale_s"] * 1e3:.6g}',
                 f'{x["heldout_standardized_rmse"]:.3f}', probability,
                 "Mismatch" if x["status"] == "model_mismatch" else "Inconclusive"])
    full = read(f'lab/t2_runs/deterministic/experimental_decay/{x["curve"]}_{x["model"]}.json')
    boot.append({"curve": x["curve"], "model": x["model"],
                 "requested": full["bootstrap_requested"], "successful": full["bootstrap_success"],
                 "beta": full["beta"], "issues": "; ".join(x["issues"])})
latex_table("decay", "llrrll", ["Sequence", "Model", r"$\tau$ (ms)", "Held RMSE", r"Approx. $p$", "Status"],
            rows, "Apparent classical retrieval scales and diagnostics; none identifies physical spin "
            r"$T_2$. Extremely small probabilities depend on the Gaussian independence model.")
csv_table("bootstrap", boot)
latex_table("bootstrap", "llrrr", ["Sequence", "Model", r"$\beta$", "Requested", "Successful"],
            [[x["curve"].removeprefix("pr2026_"), "Exp." if x["model"] == "exponential" else "Stretch.",
              f'{x["beta"]:.5g}', x["requested"], x["successful"]] for x in boot],
            "Requested and accepted parametric-bootstrap draws. Additional issue flags remain in the full JSON outputs.")
print("Three LaTeX tables and CSV counterparts regenerated")
