"""Reviewed table lookup and deterministic, explicitly scoped coherence models.

No regression, material interpolation, or conversion of unreviewed units.
"""
import itertools
import json
import math
import sqlite3
from pathlib import Path
import numpy as np
from .catalog import Catalog
from .common import finite, read_json, digest
from .spin import exact_coherence


def validate_reference(row):
    for key in ("id", "material_id", "family", "definition", "value_s", "conditions",
                "source", "source_location", "review_scope", "missing_conditions"):
        if key not in row: raise ValueError("Reference lacks " + key)
    if not row["source"] or not row["review_scope"]: raise ValueError("Unreviewed reference")
    finite(row["value_s"], "value_s", 1e-30)
    if row.get("reported_interval_s") is not None:
        lo, hi = row["reported_interval_s"]
        finite(lo, "interval lower", 1e-30); finite(hi, "interval upper", lo)
        if not lo <= row["value_s"] <= hi: raise ValueError("Interval excludes reported value")
    return row


def build_database(root, references, output):
    """Extend the existing SQLite catalog without mutating source observations."""
    catalog = Catalog(output)
    try:
        catalog.db.execute("CREATE TABLE IF NOT EXISTS t2_references (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        refs = read_json(references)
        ids = set()
        for row in refs:
            validate_reference(row)
            if row["id"] in ids: raise ValueError("Duplicate reference identity")
            ids.add(row["id"])
            payload = json.dumps(row, sort_keys=True, allow_nan=False)
            old = catalog.db.execute("SELECT payload FROM t2_references WHERE id=?", (row["id"],)).fetchone()
            if old and old[0] != payload: raise ValueError("Immutable reference collision")
            catalog.db.execute("INSERT OR IGNORE INTO t2_references VALUES (?,?)", (row["id"], payload))
        catalog.db.commit()
        rows_path = Path(root)/"processed/molecular_rows.json"
        rows = read_json(rows_path) if rows_path.exists() else []
        with catalog.transaction():
            for artifact in read_json(Path(root)/"source_lock.json")["artifacts"]:
                catalog.put("artifacts", artifact)
            for row in rows:
                catalog.put("observations", {"id": "t2catalog:"+digest(row), "subject_id": row["material_id"],
                    "quantity": row["target_definition"], "value": row["target_value"], "unit": row["target_unit"],
                    "conditions": row["features"], "provenance": row["provenance"],
                    "evidence_kind": row["evidence_kind"], "source_location": row["id"],
                    "review_status": row["review_status"], "issues": row["review_issues"],
                    "physical_T2_usable": row["review_status"] == "reviewed" and row["target_unit"] == "s"})
        return {"database": str(output), "reviewed_references": len(refs), "provisional_observations":
                sum(r["review_status"] != "reviewed" for r in rows), "catalog": catalog.summary()}
    finally: catalog.close()


def assess_database(database, query):
    """Match reviewed values at supplied reported conditions; never infer new T2."""
    if not query.get("material_id") or not query.get("definition"):
        raise ValueError("Query needs material_id and an explicit coherence definition")
    # Read-only mode: a misspelled path cannot silently create an empty database.
    db = sqlite3.connect(Path(database).absolute().as_uri()+"?mode=ro", uri=True)
    try: rows = [json.loads(r[0]) for r in db.execute("SELECT payload FROM t2_references ORDER BY id")]
    finally: db.close()
    results = []
    supplied = query.get("conditions", {})
    for row in rows:
        if row["material_id"] != query["material_id"] or row["definition"] != query["definition"]: continue
        missing, mismatch = [], []
        for key, expected in row["conditions"].items():
            if key not in supplied or supplied[key] is None: missing.append(key)
            elif supplied[key] != expected: mismatch.append(key)
        unknown = sorted(set(supplied)-set(row["conditions"]))
        status = "condition_mismatch" if mismatch else "insufficient_query_conditions" if missing else "reported_conditions_match"
        results.append({"reference_id": row["id"], "status": status, "missing_query_conditions": missing,
            "mismatched_conditions": mismatch, "unverifiable_query_conditions": unknown,
            "reference_value_s": row["value_s"], "applicable_reference_value_s":
            row["value_s"] if status == "reported_conditions_match" and not unknown else None,
            "reported_interval_s": row.get("reported_interval_s"), "interval_convention": row.get("interval_convention"),
            "reference": row})
    compatible = [r for r in results if r["applicable_reference_value_s"] is not None]
    return {"method": "reviewed_table_lookup", "query": query, "results": results,
        "status": "reference_available" if compatible else "no_applicable_reference",
        "predicted_new_material_T2_s": None, "full_memory_channel_validated": False,
        "limitations": ["Only supplied and reported conditions can be checked",
                        "Unreported conditions remain gaps even when reported conditions match",
                        "No interpolation across temperature, isotope, charge, host or pulse protocol",
                        "A T2 reference alone does not specify write/read fidelity, noise or efficiency"]}


def first_crossing(times_s, envelope):
    t, y = np.asarray(times_s, float), np.asarray(envelope, float)
    if t.ndim != 1 or y.shape != t.shape or len(t) < 2 or t[0] != 0 or np.any(np.diff(t) <= 0):
        raise ValueError("Increasing time grid beginning at zero required")
    if not np.isfinite(t).all() or not np.isfinite(y).all() or np.any(y < 0) or np.any(y > 1+1e-9) or not np.isclose(y[0], 1):
        raise ValueError("Finite normalized coherence envelope required")
    below = np.flatnonzero(y <= math.exp(-1))
    bracket = [float(t[below[0]-1]), float(t[below[0]])] if len(below) else None
    revival = bool(np.any(np.diff(y) > 1e-7))
    return {"descriptor": "first_sampled_one_over_e_crossing", "crossing_bracket_s": bracket,
        "no_sampled_crossing_up_to_s": float(t[-1]) if bracket is None else None,
        "revival_detected": revival, "unique_exponential_T2_identified": False,
        "grid_limit": "Crossings and revivals between samples can be missed; refine the grid",
        "interval_kind": "numerical_bracket_not_statistical_confidence"}


def _markov_rates(spec):
    if spec.get("rate_definition") != "population_and_independent_pure_dephasing":
        raise ValueError("Specify independent population and pure-dephasing rates; total T2 must not be reused as pure dephasing")
    if not spec.get("provenance"): raise ValueError("Rates need provenance or explicit hypothetical assumptions")
    g1 = finite(spec["population_rate_s_inv"], "population_rate", 0)
    gp = finite(spec["pure_dephasing_rate_s_inv"], "pure_dephasing_rate", 0)
    return g1, gp


def calculate(spec):
    kind = spec.get("method")
    if not spec.get("provenance") or spec.get("evidence_kind") not in {"hypothetical", "computed", "experimental", "evaluated_reference"}:
        raise ValueError("Calculation needs explicit evidence and provenance")
    metadata = {"method": kind, "input_hash": digest(spec), "input_evidence_kind": spec["evidence_kind"],
        "provenance": spec["provenance"], "full_memory_channel_validated": False,
        "uncertainty_kind": "conditional_model_or_parameter_range_not_prediction_confidence"}
    if kind == "markov":
        if not spec.get("conditions"):
            raise ValueError("Markov rates need explicit conditions, including storage temperature")
        finite(spec["conditions"]["temperature_K"], "storage temperature_K", 0)
        g1, gp = _markov_rates(spec)
        rate = g1/2+gp
        bounds = spec.get("rate_bounds_s_inv")
        box = None
        if bounds:
            if set(bounds) != {"population", "pure_dephasing"}: raise ValueError("Both rate bounds required")
            for name, center in (("population", g1), ("pure_dephasing", gp)):
                lo, hi = bounds[name]; finite(lo, name, 0); finite(hi, name, lo)
                if not lo <= center <= hi: raise ValueError("Bounds must contain nominal rate")
            corners = [a/2+b for a, b in itertools.product(bounds["population"], bounds["pure_dephasing"])]
            box = {"T2_range_s": [1/max(corners) if max(corners) else None, 1/min(corners) if min(corners) else None],
                   "upper_unbounded": min(corners) == 0, "completed_corner_evaluations": len(corners),
                   "assumption": "Every combination in supplied independent parameter box is admissible"}
        return {**metadata, "conditions": spec["conditions"], "T2_s": 1/rate if rate else None, "total_coherence_rate_s_inv": rate,
            "status": "conditional_model_value" if rate else "no_finite_decay_time_in_model", "parameter_box": box,
            "equation": "1/T2 = population_rate/2 + independent_pure_dephasing_rate",
            "scope": "Independent stationary Markov noise only; temperature dependence must be supplied separately"}
    if kind != "exact_spin_bath": raise ValueError("Supported calculations: markov, exact_spin_bath")
    times = np.asarray(spec["times_s"], float)
    if len(times) > 10000: raise ValueError("Time-grid budget exceeded")
    # Validate grid before exponentiating any Hamiltonians.
    first_crossing(times, np.ones_like(times))
    temp = finite(spec["temperature_K"], "temperature_K", 0)
    L = exact_coherence(spec["spin_bath"], times, temp, spec.get("cpmg_pulses", 0))
    if "independent_markov_rates" in spec:
        g1, gp = _markov_rates(spec["independent_markov_rates"])
        L = L*np.exp(-(g1/2+gp)*times)
    return {**metadata, "status": "conditional_coherence_calculated", "temperature_K": temp,
        "cpmg_pulses": spec.get("cpmg_pulses", 0), "times_s": times.tolist(),
        "coherence_complex": [[float(x.real), float(x.imag)] for x in L], "envelope": np.abs(L).tolist(),
        "T2_s": None, "operational_decay": first_crossing(times, np.abs(L)),
        "completed_time_evaluations": len(times), "random_seed": None,
        "scope": "Finite supplied nuclear bath, central-Sz pure-dephasing approximation, ideal CPMG pulses",
        "missing_physics": ["Transverse central-spin relaxation unless independently supplied", "Phonons",
                            "Unspecified environmental bath", "Optical write/read transfer", "Pulse imperfections"]}
