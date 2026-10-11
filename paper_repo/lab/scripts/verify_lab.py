"""Re-run tests and compare every paired analytic/QuTiP Choi matrix."""
import argparse
import json
import os
import sys
import unittest
from pathlib import Path
import numpy as np
from memorylab.channels import decode
from memorylab.common import environment, now, read_json, write_json
from memorylab.runner import run, source_fingerprint

ROOT = Path(__file__).resolve().parent.parent


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"test": test.id(), "status": "pass"})

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.records.append({"test": test.id(), "status": "fail"})

    def addError(self, test, error):
        super().addError(test, error)
        self.records.append({"test": test.id(), "status": "error"})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.records.append({"test": test.id(), "status": "skip", "reason": reason})


def compare_pairs(directory):
    directory = Path(directory)
    paths = [directory/id/"result.json" for id in read_json(directory/"manifest.json")["job_ids"]]
    paired = {}
    for path in paths:
        config = read_json(path.parent/"job.json")["config"]
        key = (config["model_id"], json.dumps(config["parameters"], sort_keys=True), config["replicate"])
        paired.setdefault(key, {})[config["backend"]] = path.parent
    largest, rows = 0, []
    for key, backends in paired.items():
        if set(backends) != {"analytic", "qutip"}:
            raise ValueError("Unpaired backend operating point")
        a = read_json(backends["analytic"]/"channels.json")["samples"]
        b = read_json(backends["qutip"]/"channels.json")["samples"]
        if len(a) != len(b):
            raise ValueError("Backend grids have different lengths")
        difference = max(float(np.max(np.abs(decode(x["choi"])-decode(y["choi"]))))
                         for x, y in zip(a, b))
        largest = max(largest, difference)
        rows.append({"model_id": key[0], "parameters": json.loads(key[1]), "replicate": key[2],
                     "max_choi_difference": difference, "pass": difference < 1e-8})
    return {"operating_point_pairs": len(rows), "maximum_choi_difference": largest,
            "tolerance": 1e-8, "all_pass": all(r["pass"] for r in rows), "comparisons": rows}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="verification")
    ap.add_argument("--cross-backend", action="store_true")
    args = ap.parse_args()
    os.chdir(ROOT)
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    suite = unittest.defaultTestLoader.discover(str(ROOT/"tests"))
    suite.addTests(unittest.defaultTestLoader.discover(str(ROOT), pattern="test_lab.py"))
    with (output/"tests.txt").open("w") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=RecordedResult).run(suite)
    report = {"at": now(), "source_sha256": source_fingerprint(), "environment": environment(),
              "tests_run": result.testsRun, "successful": result.wasSuccessful(),
              "skipped": len(result.skipped), "test_results": result.records,
              "scope": "software/solver tests; synthetic fixtures are not experimental baselines",
              "hardware_validated": False}
    if args.cross_backend:
        summary = run(read_json(ROOT/"examples/cross_backend_study.json"), output/"cross_backend_runs")
        report["cross_backend_runs"] = summary
        if summary["all_success"]:
            report["cross_backend_comparison"] = compare_pairs(output/"cross_backend_runs")
        else:
            report["successful"] = False
    write_json(output/"report.json", report)
    print(json.dumps({k: v for k, v in report.items() if k not in ("environment", "test_results")}, indent=2))
    if not report["successful"] or report.get("cross_backend_comparison", {}).get("all_pass") is False:
        sys.exit(2)


if __name__ == "__main__":
    main()
