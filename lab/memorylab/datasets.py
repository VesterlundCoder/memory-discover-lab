"""Bounded automatic downloads. Raw bytes, source revision and checksums are retained."""
import fnmatch
import hashlib
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from .common import digest, now, read_json, write_json


class DownloadError(RuntimeError):
    pass


class Client:
    def __init__(self, root, max_bytes=50_000_000, timeout_s=25, retries=2):
        self.root = Path(root)
        self.max_bytes = max_bytes
        self.timeout_s = timeout_s
        self.retries = retries

    def fetch(self, url, source_id, revision=None, license_info=None, refresh=False,
              expected_checksum=None, filename=None):
        if urllib.parse.urlsplit(url).scheme not in {"http", "https"}:
            raise DownloadError("Only HTTP(S) sources are supported")
        key = digest([source_id, url, revision, filename])
        meta = self.root / "manifests" / (key + ".json")
        previous = read_json(meta) if meta.exists() else None
        if meta.exists() and not refresh:
            record = read_json(meta)
            path = self.root / record["relative_path"]
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"]:
                return record
        last = None
        for attempt in range(self.retries + 1):
            partial = None
            try:
                request = urllib.request.Request(url, headers={
                    "User-Agent": "WestQuant-MemoryLab/0.5 (bounded research download)",
                    "Accept": "*/*"})
                with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                    length = response.headers.get("Content-Length")
                    if length and int(length) > self.max_bytes:
                        raise DownloadError("Source exceeds per-file byte budget")
                    tempdir = self.root / "partial"
                    tempdir.mkdir(parents=True, exist_ok=True)
                    sha, md5, size = hashlib.sha256(), hashlib.md5(), 0
                    with tempfile.NamedTemporaryFile(dir=tempdir, delete=False) as f:
                        partial = Path(f.name)
                        while True:
                            block = response.read(65536)
                            if not block:
                                break
                            size += len(block)
                            if size > self.max_bytes:
                                raise DownloadError("Streaming download exceeds byte budget")
                            sha.update(block)
                            md5.update(block)
                            f.write(block)
                    mime = response.headers.get_content_type()
                    final_url = response.url
                if expected_checksum:
                    alg, expected = expected_checksum.split(":", 1)
                    actual = {"sha256": sha.hexdigest(), "md5": md5.hexdigest()}.get(alg)
                    if actual is None or expected.lower() != actual:
                        raise DownloadError("Archive checksum verification failed")
                basename = Path(filename or urllib.parse.unquote(urllib.parse.urlsplit(url).path)).name or "download"
                basename = re.sub(r"[^a-zA-Z0-9_.-]", "_", basename)[:120]
                relative = Path("raw") / sha.hexdigest() / basename
                target = self.root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(partial, target)
                record = {"id": key, "source_id": source_id, "url": url,
                          "resolved_url": final_url, "source_revision": revision,
                          "sha256": sha.hexdigest(), "size_bytes": size, "mime_type": mime,
                          "fetched_at": now(), "relative_path": relative.as_posix(),
                          "file_name": basename,
                          "license": license_info or "not_verified",
                          "redistribution_approved": False}
                record["id"] = digest([source_id, url, revision, sha.hexdigest(), basename, record["license"]])
                if previous and previous["id"] == record["id"]:
                    # A recheck of identical bytes preserves the first immutable retrieval.
                    record = previous
                write_json(meta, record)
                return record
            except (urllib.error.URLError, TimeoutError, OSError, DownloadError) as e:
                last = e
                if partial:
                    partial.unlink(missing_ok=True)
                permanent = isinstance(e, DownloadError) or (
                    isinstance(e, urllib.error.HTTPError) and e.code in (400, 401, 403, 404))
                if permanent or attempt == self.retries:
                    break
                time.sleep(min(2**attempt, 4))
        raise DownloadError(f"{source_id}: {type(last).__name__}: {last}") from last

    def json(self, url, source_id, refresh=False):
        record = self.fetch(url, source_id, refresh=refresh)
        return read_json(self.root / record["relative_path"]), record


def discover(client, source, refresh=False):
    """Return exact downloadable targets plus metadata artifacts, without crawling an archive."""
    kind, sid = source["kind"], source["id"]
    metadata, targets = [], []
    if kind == "http":
        for url in source["urls"]:
            targets.append({"url": url, "revision": source.get("revision"),
                            "license_info": source.get("license")})
    elif kind == "github":
        repo, ref = source["repository"], source.get("ref", "HEAD")
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
            raise ValueError("Invalid GitHub repository")
        data, rec = client.json(f"https://api.github.com/repos/{repo}/commits/{urllib.parse.quote(ref, safe='')}",
                                sid, refresh)
        metadata.append(rec)
        commit = data["sha"]
        tree, rec = client.json(f"https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1",
                               sid, refresh)
        metadata.append(rec)
        if tree.get("truncated"):
            raise DownloadError("Truncated GitHub tree; specify a smaller source")
        for item in tree["tree"]:
            if item["type"] == "blob" and any(fnmatch.fnmatch(item["path"], p) for p in source["include"]):
                targets.append({"url": f"https://raw.githubusercontent.com/{repo}/{commit}/{urllib.parse.quote(item['path'])}",
                                "revision": commit, "license_info": source.get("license"),
                                "filename": item["path"]})
    elif kind == "zenodo":
        data, rec = client.json(f"https://zenodo.org/api/records/{int(source['record_id'])}", sid, refresh)
        metadata.append(rec)
        for f in data["files"]:
            if any(fnmatch.fnmatch(f["key"], p) for p in source.get("include", ["*"])):
                targets.append({"url": f["links"].get("self") or f["links"]["download"],
                                "revision": str(data["id"]),
                                "license_info": data.get("metadata", {}).get("license"),
                                "expected_checksum": f.get("checksum"), "filename": f["key"]})
    elif kind == "dryad":
        doi = urllib.parse.quote("doi:" + source["doi"], safe="")
        data, rec = client.json("https://datadryad.org/api/v2/datasets/" + doi, sid, refresh)
        metadata.append(rec)
        version = data["_links"]["stash:version"]["href"]
        data, rec = client.json(urllib.parse.urljoin("https://datadryad.org", version), sid, refresh)
        metadata.append(rec)
        files_url = urllib.parse.urljoin("https://datadryad.org", data["_links"]["stash:files"]["href"])
        # Explicit pagination budget: never silently claim a complete file list.
        page = 1
        while files_url:
            if page > source.get("max_pages", 10):
                raise DownloadError("Dryad pagination exceeds source budget")
            listing, rec = client.json(files_url, sid, refresh)
            metadata.append(rec)
            for f in listing.get("_embedded", {}).get("stash:files", []):
                if any(fnmatch.fnmatch(f["path"], p) for p in source.get("include", ["*"])):
                    targets.append({"url": urllib.parse.urljoin("https://datadryad.org",
                                    f["_links"]["stash:download"]["href"]),
                                    "revision": str(data.get("versionNumber")),
                                    "filename": f["path"],
                                    "license_info": "CC0 (verify dataset metadata)"})
            nxt = listing.get("_links", {}).get("next", {}).get("href")
            files_url = urllib.parse.urljoin("https://datadryad.org", nxt) if nxt else None
            page += 1
    elif kind == "pubchem":
        for cid in source["cids"]:
            cid = int(cid)
            targets.append({"url": f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,CanonicalSMILES/JSON",
                            "revision": None, "license_info": "source_specific"})
            if source.get("geometry_3d"):
                targets.append({"url": f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/SDF?record_type=3d",
                                "revision": None, "license_info": "computed_geometry"})
    elif kind == "bmrb":
        for entry in source["entries"]:
            if not re.fullmatch(r"(?:bmse|bmsm)\d+", entry):
                raise ValueError("Invalid BMRB entry identifier")
            targets.append({"url": f"https://bmrb.io/ftp/pub/bmrb/metabolomics/entry_directories/{entry}/{entry}.str",
                            "revision": None, "license_info": source.get("license")})
    else:
        raise ValueError("Unsupported connector: " + kind)
    limit = source.get("max_files", 10)
    if len(targets) > limit:
        raise DownloadError(f"{sid}: {len(targets)} targets exceeds max_files={limit}; narrow include")
    if not targets:
        raise DownloadError(sid + ": no files matched; inspect source format/version")
    return targets, metadata


def synchronize(plan, root, catalog, refresh=False):
    from .importers import import_artifact
    client = Client(root, **plan.get("download", {}))
    outcomes = []
    total_bytes = 0
    for source in plan["sources"]:
        entry = {"source_id": source["id"], "status": "success", "artifacts": [], "imports": []}
        try:
            targets, metadata = discover(client, source, refresh)
            for record in metadata:
                catalog.put("artifacts", record)
                total_bytes += record["size_bytes"]
            for target in targets:
                record = client.fetch(source_id=source["id"], refresh=refresh, **target)
                total_bytes += record["size_bytes"]
                if total_bytes > plan.get("max_total_bytes", 200_000_000):
                    raise DownloadError("Data plan exceeds total bytes (including cached files)")
                catalog.put("artifacts", record)
                entry["artifacts"].append(record)
                if source.get("importer"):
                    with catalog.transaction():
                        entry["imports"].append(import_artifact(
                            source["importer"], client.root / record["relative_path"],
                            record, catalog, source.get("mapping", {})))
        except (DownloadError, ValueError, KeyError, OSError) as e:
            entry.update(status="failed", error=f"{type(e).__name__}: {e}")
        outcomes.append(entry)
    report = {"schema": "westquant_data_sync_v1", "at": now(), "sources": outcomes,
              "all_success": all(x["status"] == "success" for x in outcomes),
              "catalog": catalog.summary(), "accounted_bytes": total_bytes}
    write_json(Path(root) / "sync_report.json", report)
    return report
