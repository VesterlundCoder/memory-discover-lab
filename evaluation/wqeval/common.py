"""Strict configuration, source verification and output helpers."""
import csv
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab"

def read(path):
    def bad(value):
        raise ValueError("Nonfinite JSON: " + value)
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=bad)

def write(path, value):
    from memorylab.common import write_json
    write_json(path, value)

def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def source_path(item, base):
    p = (Path(base) / item["path"]).resolve()
    if hash_file(p) != item["sha256"]:
        raise ValueError("Source SHA256 mismatch: " + str(p))
    return p

def csv_rows(path, rows):
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("Empty table")
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

def audit_identity(config, input_paths=()):
    from memorylab.common import digest, environment, now
    from memorylab.runner import source_fingerprint
    h = hashlib.sha256()
    for p in sorted(Path(__file__).parent.glob("*.py")):
        h.update(p.name.encode()); h.update(p.read_bytes())
    return {"at_utc": now(), "configuration": config, "configuration_sha256": digest(config),
            "evaluation_source_sha256": h.hexdigest(), "lab_source_sha256": source_fingerprint(),
            "inputs": [{"path": str(p), "sha256": hash_file(p)} for p in input_paths],
            "environment": environment(), "thread_environment": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS")}, "prospectively_preregistered": False,
            "hardware_experiments": 0}

def new_output(path):
    """Avoid silently mixing previous and fresh performance measurements."""
    p = Path(path)
    if p.exists() and any(p.iterdir()):
        raise ValueError("Output is not empty. Select a fresh --out directory.")
    p.mkdir(parents=True, exist_ok=True)
    return p
