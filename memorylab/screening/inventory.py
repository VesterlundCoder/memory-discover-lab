"""Phase 0: source sync, universe table, CIF matching, unit-review hooks.

Builds screening/results/private/universe.sqlite with one row per base candidate
and family, matching MTD rows to CIF structures and producing a stratified
unit-review queue for the MTD CSV (which lacks explicit units).

No T2 values are produced here. This is inventory and provenance only.
"""
import csv
import hashlib
import io
import json
import re
import sqlite3
import zipfile
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path

from ..common import digest, read_json, write_json, now


FAMILIES = ("molecular_spin", "rare_earth_solid", "defect_spin",
            "trapped_atom_ion", "atomic_ensemble", "negative_ion")

STATUSES = ("success", "unconverged", "missing_data", "unsupported_physics",
            "blocked", "numerical_failure", "timeout", "invalid_config")

EVIDENCE_KINDS = ("experimental", "curated_experimental", "fit_to_experiment",
                  "evaluated_reference", "computed", "hypothetical", "unknown")


def _connect(db_path):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(db_path))
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("""
        CREATE TABLE IF NOT EXISTS universe (
            id TEXT PRIMARY KEY,
            family TEXT NOT NULL,
            formula TEXT,
            formula_with_counterion TEXT,
            spin_S REAL,
            metal TEXT,
            host TEXT,
            solvent TEXT,
            counterion TEXT,
            cif_match TEXT,
            cif_formula TEXT,
            source_row_number TEXT,
            source_id TEXT,
            source_url TEXT,
            license TEXT,
            evidence_kind TEXT NOT NULL,
            status TEXT NOT NULL,
            status_reason TEXT,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            license TEXT,
            url TEXT,
            payload TEXT NOT NULL
        )
    """)
    db.commit()
    return db


def _put_candidate(db, record):
    record = dict(record)
    cid = record["id"]
    payload = json.dumps(record, sort_keys=True, allow_nan=False)
    db.execute(
        "INSERT OR REPLACE INTO universe VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (cid, record.get("family"), record.get("formula"),
         record.get("formula_with_counterion"), record.get("spin_S"),
         record.get("metal"), record.get("host"), record.get("solvent"),
         record.get("counterion"), record.get("cif_match"),
         record.get("cif_formula"), record.get("source_row_number"),
         record.get("source_id"), record.get("source_url"),
         record.get("license"), record.get("evidence_kind"),
         record.get("status"), record.get("status_reason"),
         payload, record.get("created_at", now()))
    )


def _put_artifact(db, record):
    record = dict(record)
    payload = json.dumps(record, sort_keys=True, allow_nan=False)
    db.execute(
        "INSERT OR REPLACE INTO artifacts VALUES (?,?,?,?,?,?,?)",
        (record["id"], record["source_id"], record["file_name"],
         record["sha256"], record.get("license"), record.get("url"), payload)
    )


def _match_cifs_to_rows(rows, cif_zip_path):
    """Match MTD rows to CIF files by number. Returns (lookup, unmatched_rows, errors)."""
    lookup = {}
    errors = []
    try:
        with zipfile.ZipFile(cif_zip_path) as z:
            for info in z.infolist():
                if info.filename.startswith("__MACOSX"):
                    continue
                name = Path(info.filename).name
                m = re.fullmatch(r"(\d+)\.cif", name, flags=re.I)
                if m:
                    if m[1] in lookup:
                        errors.append({"id": m[1], "status": "duplicate_cif", "file": info.filename})
                    else:
                        lookup[m[1]] = {"filename": info.filename, "size": info.file_size}
    except Exception as e:
        errors.append({"status": "zip_read_failure", "error": str(e)})
        return {}, [], errors

    matched = []
    unmatched = []
    for row in rows:
        sid = str(row.get("source_row_number") or row.get("number"))
        if sid in lookup:
            matched.append(sid)
            row["_cif_filename"] = lookup[sid]["filename"]
        else:
            unmatched.append(sid)
    return lookup, unmatched, errors


def _parse_cif_formula(cif_bytes):
    """Extract composition from a CIF file using ASE if available."""
    try:
        from ase.io import read
        atoms = read(io.BytesIO(cif_bytes), format="cif")
        if len(atoms) > 5000:
            return None, "CIF atom budget exceeded"
        from ase.formula import Formula
        formula = atoms.get_chemical_formula()
        return formula, None
    except ImportError:
        return None, "ASE not installed"
    except Exception as e:
        return None, str(e)


def _stratified_sample(rows, n_per_stratum=3):
    """Stratified sample by source paper, metal, solvent class."""
    by_stratum = defaultdict(list)
    for row in rows:
        paper = row.get("paper_id", "unknown")
        metal = row.get("metal", "none")
        solvent = row.get("solvent", "none")
        key = (paper, metal, solvent)
        by_stratum[key].append(row)
    sample = []
    for key, group in sorted(by_stratum.items()):
        sample.extend(group[:n_per_stratum])
    return sample


def build_molecular_candidates(rows, cif_lookup, cif_zip_path, artifact_sha):
    """Build candidate records from MTD molecular rows.

    Deduplicates by source_row_number: each molecule is one candidate,
    not one per T2 measurement (T2_10/T2_80 share the same molecule).
    """
    seen = set()
    candidates = []
    for row in rows:
        sid = str(row.get("source_row_number") or row.get("number"))
        if sid in seen:
            continue
        seen.add(sid)
        formula = row.get("formula") or row.get("chemForm")
        cif_match = None
        cif_formula = None
        status = "success"
        status_reason = None

        if sid in cif_lookup:
            try:
                with zipfile.ZipFile(cif_zip_path) as z:
                    cif_bytes = z.read(cif_lookup[sid]["filename"])
                cif_formula, err = _parse_cif_formula(cif_bytes)
                if err:
                    # CIF is matched but formula parsing needs ASE; record match anyway
                    cif_match = cif_lookup[sid]["filename"]
                    status = "success"
                    status_reason = f"CIF matched but formula parse skipped: {err}"
                else:
                    cif_match = cif_lookup[sid]["filename"]
            except Exception as e:
                status = "missing_data"
                status_reason = f"CIF read error: {e}"
        else:
            status = "missing_data"
            status_reason = "No CIF file matching row number"

        candidate = {
            "id": "mtd:" + sid,
            "family": "molecular_spin",
            "formula": formula,
            "formula_with_counterion": row.get("formula_with_counterion"),
            "spin_S": row.get("spin_S"),
            "metal": row.get("metal"),
            "host": row.get("host"),
            "solvent": row.get("solvent"),
            "counterion": row.get("counterion"),
            "cif_match": cif_match,
            "cif_formula": cif_formula,
            "source_row_number": sid,
            "source_id": "mtd2024",
            "source_url": row.get("paper_id"),
            "license": "CC-BY (assumed; MTD repo license not specified)",
            "evidence_kind": "curated_experimental",
            "status": status,
            "status_reason": status_reason,
            "created_at": now(),
            "provenance": [{"artifact_sha256": artifact_sha, "source": "MTD-group/Molecular_Qubit_Dataset"}],
        }
        candidates.append(candidate)
    return candidates


def build_reference_candidates(refs_json_path):
    """Build candidate records from the 10 reviewed T2 references."""
    refs = read_json(refs_json_path)
    candidates = []
    for ref in refs:
        candidate = {
            "id": "ref:" + ref["id"],
            "family": ref["family"],
            "formula": ref.get("material_name"),
            "spin_S": None,
            "metal": None,
            "host": ref.get("conditions", {}).get("host"),
            "solvent": None,
            "counterion": ref.get("conditions", {}).get("counterion"),
            "cif_match": None,
            "cif_formula": None,
            "source_row_number": None,
            "source_id": "t2_references",
            "source_url": ref.get("source"),
            "license": "reviewed_transcription",
            "evidence_kind": "curated_experimental",
            "status": "success",
            "status_reason": None,
            "created_at": now(),
            "provenance": [{"reference_id": ref["id"], "source": ref.get("source")}],
            "reference_value_s": ref.get("value_s"),
            "reference_definition": ref.get("definition"),
            "reference_conditions": ref.get("conditions"),
        }
        candidates.append(candidate)
    return candidates


def build_atom_ion_candidates(all_elements_path):
    """Build candidate records from the element inventory."""
    plan = read_json(all_elements_path)
    candidates = []
    family = plan.get("family", "trapped_atom_ion")
    charges = plan.get("charges_e", [-1, 0, 1, 2, 3])
    spins = plan.get("spin_2S", [0, 1, 2, 3])
    for template in plan.get("templates", []):
        name = template["name"]
        for charge in charges:
            for spin_2s in spins:
                cid = f"atom:{name}:q{charge}:s{spin_2s}"
                status = "success"
                status_reason = None
                if charge == -1:
                    status = "blocked"
                    status_reason = "electron_record_overlap_chi_unavailable"
                candidate = {
                    "id": cid,
                    "family": family,
                    "formula": name,
                    "spin_S": spin_2s / 2.0 if spin_2s else 0,
                    "metal": name if name in _METALS else None,
                    "charge_e": charge,
                    "source_id": "all_elements",
                    "source_url": None,
                    "license": "unassessed_periodic_table_inventory",
                    "evidence_kind": "unknown",
                    "status": status,
                    "status_reason": status_reason,
                    "created_at": now(),
                    "provenance": template.get("provenance", [{"kind": "unassessed_periodic_table_inventory"}]),
                }
                candidates.append(candidate)
    return candidates


_METALS = set("""
Li Be Na Mg Al K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge Rb Sr Y Zr Nb Mo Tc Ru Rh Pd
Ag Cd In Sn Sb Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir
Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr
""".split())


def build_combination_candidates(combinations_path):
    """Build candidate records from the generator combinations."""
    plan = read_json(combinations_path)
    candidates = []
    family = plan.get("family", "molecular_spin")
    charges = plan.get("charges_e", [0])
    spins = plan.get("spin_2S", [0])
    for template in plan.get("templates", []):
        name = template["name"]
        for charge in charges:
            for spin_2s in spins:
                cid = f"combo:{name}:q{charge}:s{spin_2s}"
                candidate = {
                    "id": cid,
                    "family": family,
                    "formula": name,
                    "spin_S": spin_2s / 2.0 if spin_2s else 0,
                    "charge_e": charge,
                    "source_id": "new_combinations",
                    "source_url": None,
                    "license": "software_geometry_template",
                    "evidence_kind": "hypothetical",
                    "status": "success",
                    "status_reason": None,
                    "created_at": now(),
                    "provenance": template.get("provenance", [{"kind": "software_geometry_template"}]),
                    "geometry_angstrom": template.get("geometry_angstrom"),
                }
                candidates.append(candidate)
    return candidates


def build_host_candidates():
    """Build candidate records for host materials (X1: YSO, diamond, SiC, Si)."""
    hosts = [
        {"name": "Y2SiO5", "formula": "Y2SiO5", "source": "COD", "use": "rare_earth_solid"},
        {"name": "YVO4", "formula": "YVO4", "source": "COD", "use": "rare_earth_solid"},
        {"name": "CaWO4", "formula": "CaWO4", "source": "COD", "use": "rare_earth_solid"},
        {"name": "diamond", "formula": "C", "source": "COD", "use": "defect_spin"},
        {"name": "4H-SiC", "formula": "SiC", "source": "COD", "use": "defect_spin"},
        {"name": "Si", "formula": "Si", "source": "COD", "use": "donor_spin"},
    ]
    candidates = []
    for h in hosts:
        cid = f"host:{h['name']}"
        candidate = {
            "id": cid,
            "family": "rare_earth_solid" if h["use"] == "rare_earth_solid" else "defect_spin",
            "formula": h["formula"],
            "host": h["name"],
            "source_id": "cod_host_cifs",
            "source_url": "https://www.crystallography.net/cod/",
            "license": "CC0 (COD)",
            "evidence_kind": "evaluated_reference",
            "status": "missing_data",
            "status_reason": "host_cif_not_yet_fetched",
            "created_at": now(),
            "provenance": [{"kind": "host_structure", "source": h["source"], "use": h["use"]}],
            "is_host": True,
        }
        candidates.append(candidate)
    return candidates


def generate_unit_review_queue(rows, out_path):
    """Generate a stratified unit-review queue CSV for MTD rows."""
    sample = _stratified_sample(rows, n_per_stratum=3)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "source_row_number", "molecule_abbreviation", "chemForm",
            "T2_10", "T2_80", "T1_10", "T1_80",
            "metal", "solvent", "spin", "Web_address_of_Paper",
            "reviewed_unit", "reviewed_pulse_sequence", "reviewed_field_T",
            "reviewed_temperature_K", "review_source", "review_notes"
        ])
        writer.writeheader()
        for row in sample:
            writer.writerow({
                "source_row_number": row.get("source_row_number", row.get("number")),
                "molecule_abbreviation": row.get("reported_name", row.get("molecule_abbreviation")),
                "chemForm": row.get("formula", row.get("chemForm")),
                "T2_10": row.get("T2_10"),
                "T2_80": row.get("T2_80"),
                "T1_10": row.get("T1_10"),
                "T1_80": row.get("T1_80"),
                "metal": row.get("metal"),
                "solvent": row.get("solvent"),
                "spin": row.get("spin_S"),
                "Web_address_of_Paper": row.get("paper_id"),
            })
    return len(sample)


def run_inventory(config, output_dir):
    """Run the full Phase 0 inventory pipeline.

    Config keys:
        t2_data_root: path to t2_data/ with source_lock.json and processed/
        cif_zip_path: path to cifs_of_molecules.zip (optional, auto-detected)
        references_json: path to data/t2_references.json
        all_elements_json: path to examples/all_elements.json
        combinations_json: path to examples/new_combinations.json
        include_hosts: bool — include X1 host candidates
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    private_dir = output_dir / "private"
    private_dir.mkdir(parents=True, exist_ok=True)

    t2_root = Path(config.get("t2_data_root", "t2_data"))
    cif_zip_path = config.get("cif_zip_path")
    if not cif_zip_path:
        # Try to find it in the cache
        source_lock = read_json(t2_root / "source_lock.json")
        for rec in source_lock.get("artifacts", []):
            if rec.get("file_name") == "cifs_of_molecules.zip":
                cif_zip_path = str(t2_root / "cache" / rec["relative_path"])
                break

    # Load molecular rows
    rows_path = t2_root / "processed" / "molecular_rows.json"
    rows = read_json(rows_path) if rows_path.exists() else []

    # Match CIFs
    cif_lookup = {}
    cif_unmatched = []
    cif_errors = []
    if cif_zip_path and Path(cif_zip_path).exists():
        cif_lookup, cif_unmatched, cif_errors = _match_cifs_to_rows(rows, cif_zip_path)

    # Get artifact SHA for MTD
    source_lock = read_json(t2_root / "source_lock.json")
    mtd_sha = None
    for rec in source_lock.get("artifacts", []):
        if rec.get("file_name") == "Relaxation_time_data_08_02_24.csv":
            mtd_sha = rec.get("sha256")
            break

    # Build candidates
    molecular = build_molecular_candidates(rows, cif_lookup, cif_zip_path, mtd_sha or "unknown")

    refs_path = config.get("references_json", "data/t2_references.json")
    references = build_reference_candidates(refs_path) if Path(refs_path).exists() else []

    elements_path = config.get("all_elements_json", "examples/all_elements.json")
    atoms = build_atom_ion_candidates(elements_path) if Path(elements_path).exists() else []

    combos_path = config.get("combinations_json", "examples/new_combinations.json")
    combinations = build_combination_candidates(combos_path) if Path(combos_path).exists() else []

    hosts = build_host_candidates() if config.get("include_hosts", True) else []

    all_candidates = molecular + references + atoms + combinations + hosts

    # Write universe database
    db_path = private_dir / "universe.sqlite"
    db = _connect(db_path)
    try:
        with db:
            for c in all_candidates:
                _put_candidate(db, c)
            # Record artifacts
            for rec in source_lock.get("artifacts", []):
                _put_artifact(db, {
                    "id": rec.get("id", digest(rec)),
                    "source_id": rec.get("source_id", "unknown"),
                    "file_name": rec.get("file_name", "unknown"),
                    "sha256": rec.get("sha256", "unknown"),
                    "license": rec.get("license"),
                    "url": rec.get("url"),
                    "payload": json.dumps(rec, sort_keys=True),
                })
    finally:
        db.close()

    # Generate unit review queue
    review_queue_path = output_dir / "unit_review_queue.csv"
    review_count = generate_unit_review_queue(rows, review_queue_path)

    # Build inventory report
    family_counts = Counter(c["family"] for c in all_candidates)
    status_counts = Counter(c["status"] for c in all_candidates)
    source_counts = Counter(c["source_id"] for c in all_candidates)
    cif_match_rate = len([c for c in molecular if c.get("cif_match")]) / max(len(molecular), 1)

    license_status = {
        "MTD_CSV": "not_specified (assumed CC-BY)",
        "MTD_CIFs": "not_specified (assumed CC-BY)",
        "t2_references": "reviewed_transcription",
        "Teller_2025": "CC BY 4.0",
        "Pr_2026": "CC BY 4.0",
        "Bradley_2022": "CC BY 4.0",
        "NV_2025": "CC BY 4.0",
        "Dryad_optical": "to_verify",
        "COD_hosts": "CC0",
    }

    data_gaps = [
        "nuclear_spin_I_gamma_Q (Phase 0b will address via IAEA/NUBASE)",
        "NIST_ASD_atomic_levels (Extension X2, deferred)",
        "electron_affinities_for_negative_ions (Extension X3, deferred)",
        "host_CIFs_for_Y2SiO5_diamond_SiC_Si (Extension X1, approved)",
        "Dryad_optical_license (to verify in Phase 0)",
    ]

    report = {
        "schema": "westquant_screening_inventory_v1",
        "created_at": now(),
        "total_candidates": len(all_candidates),
        "family_counts": dict(family_counts),
        "status_counts": dict(status_counts),
        "source_counts": dict(source_counts),
        "molecular_rows": len(rows),
        "molecular_cif_matched": len([c for c in molecular if c.get("cif_match")]),
        "molecular_cif_unmatched": len(cif_unmatched),
        "cif_match_rate": cif_match_rate,
        "cif_errors": cif_errors,
        "review_references": len(references),
        "atom_ion_candidates": len(atoms),
        "combination_candidates": len(combinations),
        "host_candidates": len(hosts),
        "unit_review_queue_size": review_count,
        "unit_review_queue_path": str(review_queue_path),
        "license_status": license_status,
        "data_gaps": data_gaps,
        "universe_db_path": str(db_path),
        "extensions_approved": ["X1_host_CIFs", "X4_nuclear_data"],
        "extensions_deferred": ["X2_NIST_ASD", "X3_electron_affinities"],
    }

    report_path = output_dir / "inventory_report.json"
    write_json(report_path, report)

    # Write manifest
    manifest = {
        "phase": "inventory",
        "created_at": now(),
        "config_hash": digest(config),
        "report_path": str(report_path),
        "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "universe_db_sha256": hashlib.sha256(db_path.read_bytes()).hexdigest(),
    }
    write_json(output_dir / "manifest.json", manifest)

    return report
