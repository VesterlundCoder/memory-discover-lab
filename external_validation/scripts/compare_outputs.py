"""Compare a re-run tree against the archived tree: bytes first, then numbers."""
import hashlib, json, math, sys
from pathlib import Path
ref, new = Path(sys.argv[1]), Path(sys.argv[2])
subdirs = sys.argv[3:]
def walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b: out.append((path + "/" + k, "key only in " + ("new" if k in b else "archive"), None))
            else: walk(a[k], b[k], path + "/" + str(k), out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): out.append((path, f"list length {len(a)} vs {len(b)}", None)); return
        for i, (x, y) in enumerate(zip(a, b)): walk(x, y, f"{path}[{i}]", out)
    elif isinstance(a, bool) or isinstance(b, bool) or a is None or b is None or isinstance(a, str) or isinstance(b, str):
        if a != b: out.append((path, "value", (a, b)))
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a != b:
            d = abs(a - b); rel = d / max(abs(a), abs(b), 1e-300)
            out.append((path, "number", (a, b, d, rel)))
    elif a != b: out.append((path, "type/value", (type(a).__name__, type(b).__name__)))
rows = []
for sd in subdirs:
    files = sorted(set(p.relative_to(ref) for p in (ref / sd).rglob("*") if p.is_file()) | set(p.relative_to(new) for p in (new / sd).rglob("*") if p.is_file()))
    for f in files:
        if "/cache/" in str(f) or "__pycache__" in str(f): continue
        a, b = ref / f, new / f
        if not a.exists() or not b.exists(): rows.append({"file": str(f), "status": "only in " + ("new" if b.exists() else "archive")}); continue
        if hashlib.sha256(a.read_bytes()).digest() == hashlib.sha256(b.read_bytes()).digest(): rows.append({"file": str(f), "status": "identical bytes"}); continue
        if f.suffix == ".json":
            out = []; walk(json.loads(a.read_text()), json.loads(b.read_text()), "", out)
            nums = [o for o in out if o[1] == "number"]; other = [o for o in out if o[1] != "number"]
            rows.append({"file": str(f), "status": "differs", "n_numeric": len(nums), "max_abs": max((o[2][2] for o in nums), default=0.0),
                         "max_rel": max((o[2][3] for o in nums), default=0.0), "worst": max(nums, key=lambda o: o[2][3])[0] if nums else None,
                         "non_numeric_paths": sorted({o[0].split("[")[0] for o in other})[:12], "n_non_numeric": len(other)})
        else: rows.append({"file": str(f), "status": "differs (non-JSON)", "size": [a.stat().st_size, b.stat().st_size]})
json.dump(rows, open(sys.argv[2] + "/../compare.json", "w"), indent=1)
from collections import Counter
print(Counter(r["status"] for r in rows))
for r in rows:
    if r["status"] != "identical bytes": print(json.dumps(r)[:420])
