"""Fetch two pinned experimental files; atomic cache and SHA256 checks."""
import os
import tempfile
import urllib.request
from pathlib import Path
from .common import ROOT, LAB, read, hash_file

def ensure_teller(*, offline=False):
    manifest = read(ROOT / 'evaluation/data/teller_sources.json')
    cache = ROOT / 'evaluation/data/cache'
    cache.mkdir(parents=True, exist_ok=True)
    old = LAB / 'baselines/teller2025/fetch_manifest.json'
    legacy = read(old) if old.exists() else None
    for name, item in manifest['artifacts'].items():
        destination = cache / name
        if destination.exists():
            if hash_file(destination) != item['sha256']:
                raise ValueError('Cache hash mismatch: ' + name)
            continue
        # Reuse verified local bytes from the archived baseline if available.
        bundled = ROOT / 'data/experimental/teller2025' / name
        source = bundled if bundled.exists() else (LAB / 'baselines/teller2025/cache' / legacy['artifacts'][name]['relative_path'] if legacy else None)
        if source and source.exists():
            data = source.read_bytes()
        else:
            if offline:
                raise ValueError('Pinned input missing: ' + name + '. Restore data/experimental/ or explicitly fetch online.')
            request = urllib.request.Request(item['url'], headers={'User-Agent': 'WestQuant-memory-lab/0.6'})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise ValueError('Unexpectedly large dataset')
        import hashlib
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Downloaded source changed: ' + name)
        fd, temporary = tempfile.mkstemp(dir=cache, prefix='.download-')
        try:
            with os.fdopen(fd, 'wb') as f:
                f.write(data); f.flush(); os.fsync(f.fileno())
            os.replace(temporary, destination)
        finally:
            Path(temporary).unlink(missing_ok=True)
    return manifest, cache
