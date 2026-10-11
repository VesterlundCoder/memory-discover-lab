"""Open-data adapters and explicit review gates for coherence tables."""
import csv
import hashlib
import io
import math
import re
import zipfile
from pathlib import Path
import numpy as np
from .catalog import composition
from .common import digest, now, read_json, write_json
from .datasets import Client, DownloadError

MTD_COMMIT = "5263b1d86b39243e7405dde5bf7c58bbd8fcd677"
MTD_BASE = f"https://raw.githubusercontent.com/MTD-group/Molecular_Qubit_Dataset/{MTD_COMMIT}/"
PR_DOI = "10.1103/ftkb-pkvp"
PR_NAMES = ("fig1_norf.out", "fig1_XX.out", "fig1_XY4.out", "fig1_XY16.out", "fig3.npz", "fig2a_histo.npz", "fig2b_histo.npz")


def register_observed(cache, path, url, sid, revision, license_info, checksum=None):
    """Register bytes retrieved by a transport, preserving content-addressed cache format.

    No byte synthesis here. Online fetches and supplied raw files share one format.
    """
    data = Path(path).read_bytes(); sha = hashlib.sha256(data).hexdigest()
    if checksum:
        alg, expected = checksum.split(":", 1)
        if hashlib.new(alg, data).hexdigest() != expected:
            raise DownloadError("Source checksum mismatch")
    basename = Path(path).name
    relative = Path("raw")/sha/basename
    root = Path(cache); target = root/relative; target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    rec = {"id": digest([sid, url, revision, sha, basename, license_info]), "source_id": sid,
           "url": url, "resolved_url": url, "source_revision": revision, "sha256": sha,
           "size_bytes": len(data), "mime_type": "application/octet-stream", "fetched_at": now(),
           "relative_path": relative.as_posix(), "file_name": basename, "license": license_info,
           "redistribution_approved": license_info in ("CC BY 4.0", "cc-by-4.0")}
    key = digest([sid, url, revision, basename])
    write_json(root/"manifests"/(key+".json"), rec)
    return rec


def fetch_sources(root, offline=False, include_structures=False, include_nv=False):
    """Pinned sources, bounded transport, source MD5 verification and offline SHA lock."""
    root = Path(root); cache = root/"cache"; lock = root/"source_lock.json"
    if offline:
        if not lock.exists(): raise DownloadError("Offline mode requires source_lock.json")
        records = read_json(lock)["artifacts"]
        for rec in records:
            p = cache/rec["relative_path"]
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != rec["sha256"]:
                raise DownloadError("Missing/corrupt offline artifact: "+rec["file_name"])
        return records
    client = Client(cache, max_bytes=40_000_000, timeout_s=40, retries=1)
    records = []
    # Exact Zenodo record is a version, never substitute the concept/latest record.
    meta, record = client.json("https://zenodo.org/api/records/21532904", "pr2026")
    records.append(record)
    for f in meta["files"]:
        if f["key"] in PR_NAMES:
            records.append(client.fetch(f["links"]["self"], "pr2026", revision="21532904",
                                       filename=f["key"], license_info="CC BY 4.0", expected_checksum=f["checksum"]))
    if {r["file_name"] for r in records}.intersection(PR_NAMES) != set(PR_NAMES):
        raise DownloadError("Required experimental files missing from pinned Zenodo record")
    for name in ("README.md", "Relaxation_time_data_08_02_24.csv"):
        records.append(client.fetch(MTD_BASE+name, "mtd2024", revision=MTD_COMMIT,
                                    filename=name, license_info="repository_license_not_specified"))
    if include_structures:
        records.append(client.fetch(MTD_BASE+"cifs_of_molecules.zip", "mtd2024", revision=MTD_COMMIT,
                                    filename="cifs_of_molecules.zip", license_info="repository_license_not_specified"))
    if include_nv:
        meta, rec = client.json("https://api.figshare.com/v2/articles/29092316", "nv2025")
        records.append(rec)
        for f in meta["files"]:
            if f["id"] == 54617714:
                records.append(client.fetch(f["download_url"], "nv2025", revision=str(meta["version"]),
                                            filename="nv_raw.zip", license_info="CC BY 4.0",
                                            expected_checksum="md5:"+f["computed_md5"]))
    write_json(lock, {"schema": "westquant_t2_sources_v1", "artifacts": records,
                      "source_revisions_pinned": True, "retrieval_dates_are_not_publication_dates": True})
    return records


def artifact(records, name):
    matching = [r for r in records if r["file_name"] == name]
    if len(matching) != 1: raise ValueError("Expected exactly one artifact: "+name)
    return matching[0]


def raw_path(root, record):
    return Path(root)/"cache"/record["relative_path"]


def parse_pr2026(root, records):
    curves = []
    for sequence, filename in [("none", "fig1_norf.out"), ("XX", "fig1_XX.out"),
                               ("XY4", "fig1_XY4.out"), ("XY16", "fig1_XY16.out")]:
        rec = artifact(records, filename); a = np.loadtxt(raw_path(root, rec))
        if a.ndim != 2 or a.shape[0] != 3 or a.shape[1] < 6 or not np.isfinite(a).all() or (a[2] <= 0).any():
            raise ValueError("Changed PR2026 3-row time/efficiency/error format")
        curves.append({"id": "pr2026_"+sequence, "times_s": (a[0]*1e-6).tolist(),
                       "values": a[1].tolist(), "standard_errors": a[2].tolist(),
                       "quantity": "classical_retrieval_efficiency", "likelihood": "gaussian",
                       "time_definition": "Figure 1c total storage time; optical AFC interval not subtracted",
                       "decay_factor": 1, "target_definition": "apparent_retrieval_decay_scale",
                       "mapping_review": {"status": "reviewed", "source": PR_DOI+", Figure 1c and main text",
                                          "scope": "Measured total-time efficiency curve; cannot uniquely identify spin T2"},
                       "conditions": {"material": "Pr3+:Y2SiO5", "family": "rare_earth_solid",
                                      "temperature_K": 3, "temperature_scope": "cryostat stage setpoint",
                                      "pulse_sequence": sequence, "field_T": None,
                                      "field_note": "Residual field suspected; not quantitatively measured",
                                      "input_regime": "classical_bright_pulses", "wavelength_nm": 606},
                       "provenance": [{"artifact_sha256": rec["sha256"], "url": rec["url"], "paper_doi": PR_DOI}],
                       "homogeneous_T2_label_allowed": False})
    rec = artifact(records, "fig3.npz")
    with np.load(raw_path(root, rec), allow_pickle=False) as d:
        required = {"st", "eff", "eff_err", "g2", "g2_err", "nf", "nf_err"}
        if not required.issubset(d.files): raise ValueError("Changed Figure 3 schema")
        quantum = {k: d[k].tolist() for k in required}
    # The numeric source times are exactly 100,120,... whereas the paper quotes
    # total optical delays 100.9,... . Do not silently equate the clocks.
    quantum.update({"source_times_us": quantum.pop("st"),
                    "time_review_status": "needs_review_of_0.9us_offset",
                    "efficiency_unit": "percent", "noise_floor_unit": "percent_per_herald",
                    "g2_definition": "signal_idler_cross_correlation", "qubit_fidelity_available": False,
                    "provenance": [{"artifact_sha256": rec["sha256"], "url": rec["url"], "paper_doi": PR_DOI}]})
    return curves, quantum


def numeric(value):
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError): return None


def molecular_rows(root, records, reviews=None):
    rec = artifact(records, "Relaxation_time_data_08_02_24.csv")
    reviews = reviews or {}
    output, excluded = [], []
    with raw_path(root, rec).open(encoding="utf-8-sig", newline="") as f:
        source = list(csv.DictReader(f))
    for r in source:
        comp = composition(r["chemForm"])
        cc = composition(r.get("chemFormWCounterIon", ""))
        base = {"spin_S": numeric(r["spin"]), "metal": r["metal"], "family": "molecular_spin",
                "solvent": r["Solvent"], "host": r["Solvent"] or None, "counterion": r["counterIon"] or None,
                "pulse_sequence": None, "field_T": None,
                "coordination_number": numeric(r["n_neighbors"]), "angle_mean_deg": numeric(r["angles_mean"]),
                "angle_min_deg": numeric(r["angles_min"]), "angle_max_deg": numeric(r["angles_max"]),
                "tau4": numeric(r["tau_4"]), "tau4prime": numeric(r["tau_4_prime"]), "tau5": numeric(r["tau_5"])}
        concentration = re.fullmatch(r"\s*([0-9.eE+-]+)\s*mM\s*", r["qubit_concentration"])
        base["concentration_mM"] = numeric(concentration[1]) if concentration else None
        for prefix, formula in (("fraction", comp), ("counter_fraction", cc)):
            if formula:
                total = sum(formula.values())
                base.update({prefix+":"+el: count/total for el, count in formula.items()})
        # Across studies retain same chemical identity even when temperature,
        # concentration or solvent changes. Study/material leakage is blocked.
        material_id = digest([r["chemForm"], r["ligand"], r["counterIon"]])[:24]
        for column, temp in (("T2_10", 10), ("T2_80", 80)):
            val = numeric(r[column]); row_id = "mtd:"+r["number"]+":"+column
            if val is None or val <= 0:
                excluded.append({"id": row_id, "reason": "missing_nonpositive_or_non_numeric_T2"}); continue
            feat = dict(base, temperature_K=temp)
            out = {"id": row_id, "material_id": material_id, "paper_id": r["Web_address_of_Paper"],
                   "features": feat, "target_value": val, "target_unit": "source_unspecified",
                   "target_definition": "reported_T2_mixed_protocol", "censoring": "exact",
                   "evidence_kind": "curated_experimental", "review_status": "provisional",
                   "review_issues": ["CSV does not specify units", "pulse sequence and field not supplied",
                                     "Tm versus T2 convention and extraction at nominal temperature need original-paper review"],
                   "reported_name": r["molecule_abbreviation"], "source_row_number": r["number"],
                   "extraction_method": r["type"], "measurement_uncertainty": None,
                   "provenance": [{"artifact_sha256": rec["sha256"], "url": rec["url"],
                                   "csv_column": column, "original_paper": r["Web_address_of_Paper"]}]}
            if row_id in reviews:
                review = reviews[row_id]
                for key in ("unit", "target_definition", "source", "pulse_sequence", "temperature_K"):
                    if not review.get(key): raise ValueError("Review lacks "+key)
                factor = {"s": 1, "ms": 1e-3, "us": 1e-6, "ns": 1e-9}.get(review["unit"])
                if factor is None: raise ValueError("Unsupported reviewed time unit")
                out.update(target_value=val*factor, target_unit="s", target_definition=review["target_definition"],
                           review_status="reviewed", review_issues=[], review_source=review["source"])
                out["features"].update({k: review[k] for k in ("pulse_sequence", "temperature_K", "field_T", "host") if k in review})
            output.append(out)
    return output, {"molecular_source_rows": len(source), "positive_T2_labels": len(output),
                    "source_posts_with_T2": len({r["source_row_number"] for r in output}),
                    "original_paper_references": len({r["paper_id"] for r in output}),
                    "excluded": excluded, "reviewed_labels": sum(r["review_status"] == "reviewed" for r in output)}


def structure_descriptors(cif_bytes):
    """CIF geometry is a descriptor, not proof of its solution-state conformation."""
    from ase.io import read
    atoms = read(io.BytesIO(cif_bytes), format="cif")
    if len(atoms) > 5000: raise ValueError("CIF atom budget exceeded")
    a, b, c, _, _, _ = atoms.cell.cellpar()
    volume = float(atoms.get_volume())
    if volume <= 0: raise ValueError("Nonpositive CIF cell volume")
    return {"volume_A3": volume, "lattice_a_A": float(a), "lattice_b_A": float(b), "lattice_c_A": float(c),
            "density_kg_m3": float(sum(atoms.get_masses())*1.66053906660e-27/(volume*1e-30))}


def enrich_structures(rows, root, records):
    matches = [r for r in records if r["file_name"] == "cifs_of_molecules.zip"]
    if not matches: return {"status": "not_requested", "enriched_rows": 0, "errors": []}
    rec = matches[0]; enriched, errors = 0, []
    with zipfile.ZipFile(raw_path(root, rec)) as z:
        if sum(a.file_size for a in z.infolist()) > 100_000_000: raise ValueError("Expanded CIF budget exceeded")
        lookup = {}
        for a in z.infolist():
            m = re.fullmatch(r"(\d+)\.cif", Path(a.filename).name, flags=re.I)
            if m and not a.filename.startswith("__MACOSX"):
                if m[1] in lookup: raise ValueError("Duplicate CIF subject identity")
                lookup[m[1]] = a.filename
        by_id = {}
        for row in rows:
            sid = row["source_row_number"]
            if sid not in lookup: continue
            if sid not in by_id:
                try:
                    data = z.read(lookup[sid]); by_id[sid] = structure_descriptors(data)
                except Exception as e:
                    by_id[sid] = None; errors.append({"id": sid, "status": "parse_failure", "error": str(e)})
            if by_id[sid]:
                row["features"].update(by_id[sid]); row["provenance"].append({"artifact_sha256": rec["sha256"], "zip_member": lookup[sid]}); enriched += 1
    return {"status": "completed", "enriched_rows": enriched, "errors": errors}


def join_computations(rows, records):
    """Attach independently calculated inputs by material ID, retaining provenance.

    Computed T2, fitted gamma and measured readout metrics are intentionally not
    accepted as descriptors in the experimental-label model.
    """
    allowed = {"gap_eV", "vertical_excitation_eV", "dipole_debye", "g_anisotropy", "hyperfine_norm_Hz",
               "dipolar_second_moment_Hz2", "lowest_vibration_Hz", "phonon_spectral_density",
               "isotope_spin_fraction", "nuclear_moment_second_moment"}
    indexed = {}
    for rec in records:
        if not rec.get("provenance") or not rec.get("backend") or not rec.get("recipe_hash"):
            raise ValueError("Computation needs backend, recipe hash and provenance")
        if set(rec["features"])-allowed: raise ValueError("Unexpected computed feature/target leakage")
        if rec["material_id"] in indexed: raise ValueError("Ambiguous computation for material")
        indexed[rec["material_id"]] = rec
    for row in rows:
        if row["material_id"] in indexed:
            rec = indexed[row["material_id"]]
            row["features"].update(rec["features"]); row["provenance"].extend(rec["provenance"])
    return rows
