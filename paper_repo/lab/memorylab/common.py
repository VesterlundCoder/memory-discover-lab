"""Stable identity, strict JSON, atomic output and common error types."""
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class MissingData(ValueError):
    pass


class UnsupportedPhysics(ValueError):
    pass


class NumericalFailure(RuntimeError):
    pass


class BackendUnavailable(RuntimeError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def seed(master, identity, stream, replicate=0):
    return int(digest([master, identity, stream, replicate])[:16], 16)


def read_json(path):
    def bad_constant(v):
        raise ValueError("Nonfinite JSON number: " + v)
    return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=bad_constant)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False, suffix=".partial") as f:
        name = f.name
        try:
            json.dump(value, f, indent=2, ensure_ascii=False, allow_nan=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            Path(name).unlink(missing_ok=True)
            raise
    os.replace(name, path)


def now():
    return datetime.now(timezone.utc).isoformat()


def finite(value, name, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + " must be a finite number")
    if minimum is not None and value < minimum:
        raise ValueError(name + " is below its allowed range")
    if maximum is not None and value > maximum:
        raise ValueError(name + " is above its allowed range")
    return float(value)


def optional_import(module):
    import importlib
    try:
        if module == "pycce":
            # PyCCE 1.1.1 imports a moved SciPy utility. Restore exactly the
            # shipped utility, without modifying a physics calculation.
            import scipy.sparse.sputils as legacy
            if not hasattr(legacy, "isintlike"):
                from scipy.sparse._sputils import isintlike
                legacy.isintlike = isintlike
            import numpy as np
            if not hasattr(np, "unicode_"):
                # Alias of the same Unicode dtype; removed name in NumPy 2.
                np.unicode_ = np.str_
        loaded = importlib.import_module(module)
        if module == "pyscf" and sys.platform.startswith("linux"):
            try:
                loaded.lib.current_memory()
            except FileNotFoundError:
                # Some container PID namespaces expose /proc/self but not the
                # numeric PID returned by getpid(). Preserve PySCF's exact units
                # and RSS/VMS formula, using the current-process proc alias.
                PathProbe = __import__("pathlib").Path
                if not PathProbe("/proc/self/statm").is_file(): raise
                def current_memory_self():
                    with open("/proc/self/statm") as f:
                        vms, rss = [int(x)*os.sysconf("SC_PAGE_SIZE") for x in f.readline().split()[:2]]
                    return rss/1e6, vms/1e6
                loaded.lib.current_memory = current_memory_self
                loaded.lib.misc.current_memory = current_memory_self
        return loaded
    except ImportError as e:
        raise BackendUnavailable(f"{module}: {e}. Install the corresponding optional extra.") from e


def environment():
    versions = {}
    for name in ("numpy", "scipy", "qutip", "pyscf", "pycce", "ase", "maxwellbloch",
                 "pynmrstar", "openpyxl", "sequence", "pandas"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                text=True, timeout=3).stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        commit = None
    return {"python": sys.version, "platform": platform.platform(), "packages": versions,
            "git_commit": commit}
