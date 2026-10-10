"""Reproduce study outputs from pinned offline caches by default.

--online fetches remote sources and constitutes a new source snapshot.
External package installation is a separate explicit setup step.
"""
from pathlib import Path
import argparse
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "lab"
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--online", action="store_true", help="Fetch remote sources instead of checking the archived caches")
args = ap.parse_args()
offline = [] if args.online else ["--offline"]

tasks = [
    ([sys.executable, "-m", "memorylab", "reproduce", "examples/teller2025_baseline.json", "--out", "baselines/teller2025", *offline], "paper_teller_reproduction.log"),
    ([sys.executable, "-m", "memorylab.t2lab", "run", "--sequence", *offline], "paper_t2_reproduction.log"),
    ([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], "paper_test_results.log"),
]
for command, logname in tasks:
    print("Running:", " ".join(command), flush=True)
    with (ROOT / "evidence" / logname).open("w") as log:
        subprocess.run(command, cwd=LAB, stdout=log, stderr=subprocess.STDOUT, check=True)

copies = {
    "baselines/teller2025/summary.json": "teller_summary.json",
    "baselines/teller2025/spatial_holdout.json": "teller_holdout.json",
    "baselines/teller2025/readout_window_noise_fit.json": "teller_window_fits.json",
    "t2_runs/deterministic/summary.json": "deterministic_summary.json",
    "t2_runs/deterministic/experimental_decay/summary.json": "pr2026_curve_summary.json",
    "t2_runs/deterministic/hypothetical_sequence.json": "hypothetical_sequence.json",
}
for source, target in copies.items():
    shutil.copy2(LAB / source, ROOT / "evidence" / target)
for script in ["make_figures.py", "make_tables.py", "verify_results.py"]:
    subprocess.run([sys.executable, str(ROOT / "scripts" / script)], cwd=ROOT, check=True)
print("Reproduction complete. Compile paper PDFs with make pdf.")
