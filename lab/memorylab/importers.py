"""Import observations, not automatic material-to-T2 or material-to-fidelity predictions."""
import csv
import html
import json
import math
import re
from pathlib import Path
from .catalog import composition
from .common import digest, optional_import
from .units import convert


def provenance(artifact):
    return [{"artifact_id": artifact["id"], "sha256": artifact["sha256"],
             "source_id": artifact["source_id"], "url": artifact["url"],
             "source_revision": artifact["source_revision"]}]


def number(value):
    if value is None or str(value).strip() in {"", "-", "NA", "N/A", "nan"}:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def put_observation(catalog, artifact, subject, quantity, value, unit, location,
                    conditions, evidence_kind, extra=None):
    row = {"subject_id": subject, "quantity": quantity, "value": value, "unit": unit,
           "uncertainty": None, "conditions": conditions, "evidence_kind": evidence_kind,
           "source_location": location, "provenance": provenance(artifact)}
    row.update(extra or {})
    row["id"] = digest(row)
    catalog.put("observations", row)
    return row


def molecular_csv(path, artifact, catalog, mapping):
    count, candidates, unknown_units = 0, 0, 0
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"number", "chemForm", "T1_10", "T1_80", "T2_10", "T2_80"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Molecular Qubit Dataset schema changed")
        for line, row in enumerate(reader, 2):
            candidate = {"family": "molecular_spin", "composition": composition(row["chemForm"]),
                         "name": row.get("molecule_name") or row.get("molecule_abbreviation"),
                         "formula": row["chemForm"], "formula_with_counterion": row.get("chemFormWCounterIon"),
                         "reported_spin": number(row.get("spin")), "spin_2S": None,
                         "charge_e": None, "host": row.get("Solvent"), "geometry_angstrom": None,
                         "status": "needs_source_review", "bound_state_exists": None,
                         "optical_interface": None, "network_channel_validated": False,
                         "source_row": row, "provenance": provenance(artifact)}
            candidate["id"] = digest([artifact["sha256"], row["number"]])[:24]
            catalog.put("candidates", candidate)
            candidates += 1
            for col in ("T1_10", "T1_80", "T2_10", "T2_80"):
                val = number(row[col])
                if val is None:
                    continue
                reviewed = mapping.get("columns", {}).get(col)
                conditions = {"host_or_solvent": row.get("Solvent"),
                              "concentration_source_text": row.get("qubit_concentration"),
                              "temperature_source_label": col.split("_")[1],
                              "pulse_sequence": None, "optical_readout": None}
                if reviewed:
                    if not reviewed.get("review_source"):
                        raise ValueError("Unit/condition mapping requires review_source")
                    val = convert(val, reviewed["unit"], "s")
                    unit = "s"
                    conditions.update(reviewed.get("conditions", {}))
                else:
                    unit = "source_unspecified"
                    unknown_units += 1
                put_observation(catalog, artifact, candidate["id"],
                                "reported_" + col.split("_")[0], val, unit,
                                f"CSV row {line}, column {col}", conditions,
                                "curated_experimental",
                                {"extraction_method_source_text": row.get("type"),
                                 "original_paper": row.get("Web_address_of_Paper"),
                                 "reviewed_mapping": reviewed, "network_parameter_ready": False})
                count += 1
    return {"candidates": candidates, "observations": count,
            "observations_with_unverified_units": unknown_units}


def nist_isotopes(path, artifact, catalog, mapping):
    """Parse NIST's labelled ASCII blocks while retaining uncertainty and interval text."""
    text = html.unescape(re.sub(r"<[^>]+>", "", Path(path).read_text(encoding="utf-8")))
    blocks = re.split(r"(?=Atomic Number\s*=)", text)
    count, nuclei = 0, set()
    for block in blocks:
        fields = dict(re.findall(r"^([A-Za-z ]+?)\s*=\s*(.*?)\s*$", block, flags=re.M))
        if "Mass Number" not in fields or "Atomic Symbol" not in fields:
            continue
        mass = int(fields["Mass Number"])
        symbol = fields["Atomic Symbol"]
        # NIST occasionally uses D/T as symbols; these are hydrogen isotopes.
        symbol = {"D": "H", "T": "H"}.get(symbol, symbol)
        subject = f"{symbol}-{mass}:ground"
        nuclei.add(subject)
        for key, quantity, unit in (("Relative Atomic Mass", "isotope_mass", "u"),
                                    ("Isotopic Composition", "natural_atom_fraction", "1")):
            raw = fields.get(key, "")
            match = re.fullmatch(r"([0-9.]+)(?:\((\d+)\))?(?:#)?", raw)
            if match:
                value = float(match[1])
                uncertainty = (int(match[2])*10**(-len(match[1].split(".")[1]))
                               if match[2] and "." in match[1] else None)
                extra = {"quoted_parenthesis_uncertainty": uncertainty,
                         "uncertainty_definition": "source_convention_not_reinterpreted",
                         "source_text": raw, "nuclear_spin_I": None}
            elif re.fullmatch(r"\[[0-9., ]+\]", raw):
                value = [float(v) for v in raw.strip("[]").split(",")]
                extra = {"interval": True, "source_text": raw, "nuclear_spin_I": None}
            else:
                continue
            put_observation(catalog, artifact, subject, quantity, value, unit,
                            f"ASCII isotope {symbol}, A={mass}, field={key}", {},
                            "evaluated_reference", extra)
            count += 1
    if not count:
        raise ValueError("No labelled NIST isotope blocks; response may be an HTML error")
    return {"isotopes": len(nuclei), "observations": count}


def ciaaw_abundances(path, artifact, catalog, mapping):
    """Import the CIAAW table, including inherited element cells and abundance intervals."""
    text = Path(path).read_text(encoding="utf-8")
    table = re.search(r'<table[^>]*id=["\']mytable["\'][^>]*>(.*?)</table>', text, re.S | re.I)
    if not table:
        raise ValueError("CIAAW table identifier changed; inspect response")
    symbol, count, elements = None, 0, set()
    for index, segment in enumerate(table[1].split("</tr>"), 1):
        cells = [html.unescape(re.sub("<[^>]*>", "", s)).strip()
                 for s in re.findall(r"<td\b[^>]*>(.*?)</td>", segment, re.S | re.I)]
        if len(cells) >= 5:
            symbol, mass, raw = cells[1], cells[3], cells[4]
        elif len(cells) == 2 and symbol:
            mass, raw = cells
        else:
            continue
        if raw == "-":
            # Radioactive elements without a representative natural composition.
            # A bracketed atomic weight is not an isotope abundance measurement.
            continue
        if not re.fullmatch(r"[A-Z][a-z]?", symbol) or not mass.isdigit():
            raise ValueError("Unexpected CIAAW isotope row")
        raw = re.sub(r"\s+", "", raw)
        match = re.fullmatch(r"([0-9.]+)(?:\((\d+)\))?", raw)
        uncertainty = None
        if match:
            value = float(match[1])
            if match[2]:
                decimals = len(match[1].partition(".")[2])
                uncertainty = int(match[2])*10**(-decimals)
        elif re.fullmatch(r"\[[0-9.,]+\]", raw):
            value = [float(v) for v in raw.strip("[]").split(",")]
            if len(value) != 2 or not 0 <= value[0] <= value[1] <= 1:
                raise ValueError("Invalid abundance interval")
        else:
            raise ValueError("Unrecognized CIAAW abundance representation: " + raw)
        put_observation(catalog, artifact, f"{symbol}-{int(mass)}:ground",
                        "natural_atom_fraction", value, "1", f"CIAAW HTML table isotope row {index}",
                        {}, "evaluated_reference", {"source_text": raw,
                            "interval": isinstance(value, list),
                            "quoted_parenthesis_uncertainty": uncertainty,
                            "uncertainty_definition": "retained_source_convention",
                            "nuclear_spin_I": None, "sample_isotope_purity": None})
        count += 1
        elements.add(symbol)
    if not count:
        raise ValueError("No CIAAW abundances imported")
    return {"isotopes": count, "elements": len(elements), "observations": count}


def mapped_csv(path, artifact, catalog, mapping):
    """Explicit column-to-observation mapping for experiments, digitized data and calculations."""
    if not mapping.get("review_source") or mapping.get("evidence_kind") not in {
        "experimental", "curated_experimental", "fit_to_experiment", "computed", "hypothetical"}:
        raise ValueError("CSV mapping needs review_source and declared evidence_kind")
    count = 0
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=mapping.get("delimiter", ","))
        for line, row in enumerate(reader, 2):
            subject = row[mapping["subject_column"]] if mapping.get("subject_column") else mapping["subject_id"]
            for item in mapping["measurements"]:
                value = number(row[item["value_column"]])
                if value is None:
                    continue
                unit = item["unit"]
                if item.get("target_unit"):
                    value = convert(value, unit, item["target_unit"])
                    unit = item["target_unit"]
                conditions = dict(mapping.get("conditions", {}))
                for target, column in mapping.get("condition_columns", {}).items():
                    conditions[target] = number(row[column]) if number(row[column]) is not None else row[column]
                put_observation(catalog, artifact, subject, item["quantity"], value, unit,
                                f"CSV row {line}, column {item['value_column']}", conditions,
                                mapping["evidence_kind"],
                                {"review_source": mapping["review_source"],
                                 "uncertainty": number(row.get(item.get("uncertainty_column", ""))),
                                 "network_parameter_ready": False})
                count += 1
    return {"observations": count}


def bmrb_star(path, artifact, catalog, mapping):
    star = optional_import("pynmrstar")
    entry = star.Entry.from_file(str(path))
    count = 0
    # Chemical shifts constrain spin Hamiltonians; they are not coherence lifetimes.
    for loop in entry.get_loops_by_category("_Atom_chem_shift"):
        tags = [tag.split(".")[-1] for tag in loop.tags]
        for i, values in enumerate(loop.data):
            row = dict(zip(tags, values))
            val = number(row.get("Val"))
            if val is None:
                continue
            subject = f"BMRB:{entry.entry_id}:{row.get('Comp_ID')}:{row.get('Atom_ID')}"
            put_observation(catalog, artifact, subject, "chemical_shift", val, "ppm",
                            f"STAR chemical shift loop row {i+1}", {"sample_conditions": "see retained STAR"},
                            "experimental", {"raw_row": row, "not_a_T2_measurement": True})
            count += 1
    if not count:
        raise ValueError("No Atom_chem_shift values; inspect STAR schema")
    return {"observations": count, "entry_id": entry.entry_id}


def import_artifact(kind, path, artifact, catalog, mapping=None):
    registry = {"molecular_csv": molecular_csv, "nist_isotopes": nist_isotopes,
                "ciaaw_abundances": ciaaw_abundances,
                "mapped_csv": mapped_csv, "bmrb_star": bmrb_star}
    if kind not in registry:
        raise ValueError("Unknown importer: " + kind)
    return registry[kind](path, artifact, catalog, mapping or {})


def extract_workbook(path, output, sheet_names, max_cells=2_000_000):
    """Export selected raw spreadsheet sheets; preserve data vs fit columns for later mapping."""
    openpyxl = optional_import("openpyxl")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    records, cells = [], 0
    try:
        for name in sheet_names:
            sheet = wb[name]
            filename = re.sub(r"[^A-Za-z0-9_.-]", "_", name) + ".csv"
            target = output / filename
            if any(r["path"] == str(target) for r in records):
                raise ValueError("Sanitized worksheet filename collision")
            with target.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                for row in sheet.iter_rows(values_only=True):
                    cells += len(row)
                    if cells > max_cells:
                        raise ValueError("Workbook exceeds explicit cell budget")
                    writer.writerow(row)
            records.append({"sheet": name, "path": str(target),
                            "source_sha256": __import__("hashlib").sha256(Path(path).read_bytes()).hexdigest(),
                            "formulas_retained_as_text": True, "evidence_kind": "requires_mapping"})
    finally:
        wb.close()
    return records
