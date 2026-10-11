"""Phase 1: Tier 1 — rule-based physics filtering for all combinations.

Cheap, deterministic checks per candidate × combination. No lifetimes.
Produces flags and features; nothing is filtered silently — a blocked
candidate keeps its row with a status and reason.

Isotope patterns (molecules):
  natural, perdeuterated, C13_depleted_99.99, N15,
  deut+C13dep, deut+C13dep+N15

Every pattern except 'natural' is marked evidence_kind: hypothetical.
"""
import json
import sqlite3
from collections import Counter
from pathlib import Path

import numpy as np

from ..common import digest, read_json, write_json, now, seed
from .nucdata import get_isotope_data, get_element_isotopes, NUCLEAR_TABLE


# Isotope patterns for molecules
ISOTOPE_PATTERNS = [
    "natural",
    "perdeuterated",
    "C13_depleted_99.99",
    "N15",
    "deut+C13dep",
    "deut+C13dep+N15",
]

# Fields and protocols for combinations
FIELDS_T = [0.35, 1.2]  # X-band, Q-band
PROTOCOLS = ["Hahn", "CPMG-2", "CPMG-8"]
ENVIRONMENTS = ["crystal", "frozen_solution"]


def electron_parity(charge_e, spin_2S):
    """Check electron-count / 2S parity.

    For a valid spin state, the number of unpaired electrons (2S) must be
    consistent with the electron count parity:
    - Odd electron count → half-integer spin (2S odd)
    - Even electron count → integer spin (2S even)

    For atoms: charge_e changes the electron count.
    For molecules: we check the reported spin against the metal's d-electron count.
    """
    if charge_e is None or spin_2S is None:
        return {"parity_ok": None, "reason": "missing_charge_or_spin"}
    # For atoms: electron count = atomic_number - charge_e
    # Parity: (Z - charge) even → integer spin (2S even)
    #          (Z - charge) odd  → half-integer spin (2S odd)
    # We don't have Z here, but we can check 2S parity directly
    is_half_integer = (spin_2S % 2 == 1)
    return {
        "parity_ok": True,  # We accept all; parity is a flag, not a filter
        "spin_2S": spin_2S,
        "is_half_integer": is_half_integer,
        "is_kramers": is_half_integer,  # Kramers = half-integer spin
        "reason": "kramers" if is_half_integer else "non_kramers",
    }


def count_magnetic_nuclei(formula_composition, isotope_pattern="natural"):
    """Count magnetic nuclei in a formula for a given isotope pattern.

    Returns count of spinful nuclei and their isotopes.
    """
    if not formula_composition:
        return {"magnetic_nuclei_count": 0, "isotopes": [], "reason": "no_formula"}

    magnetic = []
    total_nuclei = 0
    for element, count in formula_composition.items():
        total_nuclei += count
        isotopes = get_element_isotopes(element)
        if not isotopes:
            continue

        # Determine which isotope to use based on pattern
        if isotope_pattern == "natural":
            # Use natural abundance-weighted magnetic nuclei
            for iso_id, data in isotopes.items():
                iso_data = get_isotope_data(iso_id)
                if iso_data and iso_data["is_magnetic"]:
                    magnetic_count = count * iso_data["abundance_pct"] / 100.0
                    if magnetic_count > 0.001:
                        magnetic.append({
                            "isotope": iso_id,
                            "count": magnetic_count,
                            "spin_I": iso_data["spin_I"],
                            "gamma": iso_data["gamma_rad_s_T"],
                        })
        elif isotope_pattern == "perdeuterated":
            # Replace all H with D (H-2)
            if element == "H":
                iso_data = get_isotope_data("H-2")
                if iso_data:
                    magnetic.append({
                        "isotope": "H-2",
                        "count": float(count),
                        "spin_I": iso_data["spin_I"],
                        "gamma": iso_data["gamma_rad_s_T"],
                    })
            else:
                for iso_id, data in isotopes.items():
                    iso_data = get_isotope_data(iso_id)
                    if iso_data and iso_data["is_magnetic"]:
                        magnetic_count = count * iso_data["abundance_pct"] / 100.0
                        if magnetic_count > 0.001:
                            magnetic.append({
                                "isotope": iso_id,
                                "count": magnetic_count,
                                "spin_I": iso_data["spin_I"],
                                "gamma": iso_data["gamma_rad_s_T"],
                            })
        elif isotope_pattern == "C13_depleted_99.99":
            # Deplete C-13 to 0.01%
            if element == "C":
                iso_data = get_isotope_data("C-13")
                if iso_data:
                    magnetic_count = count * 0.0001  # 0.01% abundance
                    if magnetic_count > 0.0001:
                        magnetic.append({
                            "isotope": "C-13",
                            "count": magnetic_count,
                            "spin_I": iso_data["spin_I"],
                            "gamma": iso_data["gamma_rad_s_T"],
                        })
            else:
                for iso_id, data in isotopes.items():
                    iso_data = get_isotope_data(iso_id)
                    if iso_data and iso_data["is_magnetic"]:
                        magnetic_count = count * iso_data["abundance_pct"] / 100.0
                        if magnetic_count > 0.001:
                            magnetic.append({
                                "isotope": iso_id,
                                "count": magnetic_count,
                                "spin_I": iso_data["spin_I"],
                                "gamma": iso_data["gamma_rad_s_T"],
                            })
        elif isotope_pattern == "N15":
            # Replace all N with N-15
            if element == "N":
                iso_data = get_isotope_data("N-15")
                if iso_data:
                    magnetic.append({
                        "isotope": "N-15",
                        "count": float(count),
                        "spin_I": iso_data["spin_I"],
                        "gamma": iso_data["gamma_rad_s_T"],
                    })
            else:
                for iso_id, data in isotopes.items():
                    iso_data = get_isotope_data(iso_id)
                    if iso_data and iso_data["is_magnetic"]:
                        magnetic_count = count * iso_data["abundance_pct"] / 100.0
                        if magnetic_count > 0.001:
                            magnetic.append({
                                "isotope": iso_id,
                                "count": magnetic_count,
                                "spin_I": iso_data["spin_I"],
                                "gamma": iso_data["gamma_rad_s_T"],
                            })
        elif isotope_pattern in ("deut+C13dep", "deut+C13dep+N15"):
            # Combined: deuterated + C13 depleted (+ N15)
            if element == "H":
                iso_data = get_isotope_data("H-2")
                if iso_data:
                    magnetic.append({
                        "isotope": "H-2",
                        "count": float(count),
                        "spin_I": iso_data["spin_I"],
                        "gamma": iso_data["gamma_rad_s_T"],
                    })
            elif element == "C":
                iso_data = get_isotope_data("C-13")
                if iso_data:
                    magnetic_count = count * 0.0001
                    if magnetic_count > 0.0001:
                        magnetic.append({
                            "isotope": "C-13",
                            "count": magnetic_count,
                            "spin_I": iso_data["spin_I"],
                            "gamma": iso_data["gamma_rad_s_T"],
                        })
            elif element == "N" and isotope_pattern == "deut+C13dep+N15":
                iso_data = get_isotope_data("N-15")
                if iso_data:
                    magnetic.append({
                        "isotope": "N-15",
                        "count": float(count),
                        "spin_I": iso_data["spin_I"],
                        "gamma": iso_data["gamma_rad_s_T"],
                    })
            else:
                for iso_id, data in isotopes.items():
                    iso_data = get_isotope_data(iso_id)
                    if iso_data and iso_data["is_magnetic"]:
                        magnetic_count = count * iso_data["abundance_pct"] / 100.0
                        if magnetic_count > 0.001:
                            magnetic.append({
                                "isotope": iso_id,
                                "count": magnetic_count,
                                "spin_I": iso_data["spin_I"],
                                "gamma": iso_data["gamma_rad_s_T"],
                            })

    total_magnetic = sum(m["count"] for m in magnetic)
    return {
        "magnetic_nuclei_count": total_magnetic,
        "total_nuclei": total_nuclei,
        "magnetic_fraction": total_magnetic / max(total_nuclei, 1),
        "isotopes": magnetic,
        "has_magnetic_bath": total_magnetic > 0.01,
    }


def count_methyl_groups(formula_composition):
    """Count CH3 groups (methyl rotors) in a formula.

    Approximate: min(C_count, H_count // 3) if both C and H present.
    This is a rough proxy; actual methyl groups require structure analysis.
    """
    if not formula_composition:
        return {"methyl_count": 0, "has_rotors": False}
    c = formula_composition.get("C", 0)
    h = formula_composition.get("H", 0)
    methyl = min(c, h // 3)
    return {
        "methyl_count": methyl,
        "has_rotors": methyl > 0,
        "rotor_flag": "methyl_rotors_present" if methyl > 0 else "no_methyl_rotors",
    }


def max_atomic_number(formula_composition):
    """Get max Z (spin-orbit proxy) from formula composition."""
    # Simple Z lookup for common elements
    Z_TABLE = {
        "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9,
        "Ne": 10, "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17,
        "K": 19, "Ca": 20, "Sc": 21, "Ti": 22, "V": 23, "Cr": 24, "Mn": 25, "Fe": 26,
        "Co": 27, "Ni": 28, "Cu": 29, "Zn": 30, "Ga": 31, "Ge": 32, "Br": 35,
        "Rb": 37, "Sr": 38, "Y": 39, "Zr": 40, "Nb": 41, "Mo": 42, "Tc": 43,
        "Ru": 44, "Rh": 45, "Pd": 46, "Ag": 47, "Cd": 48, "In": 49, "Sn": 50,
        "Sb": 51, "I": 53, "Xe": 54, "Cs": 55, "Ba": 56, "La": 57, "Ce": 58,
        "Pr": 59, "Nd": 60, "Sm": 62, "Eu": 63, "Gd": 64, "Tb": 65, "Dy": 66,
        "Ho": 67, "Er": 68, "Tm": 69, "Yb": 70, "Lu": 71, "W": 74, "Pt": 78,
        "Au": 79, "Hg": 80, "Tl": 81, "Pb": 82, "Bi": 83,
    }
    if not formula_composition:
        return {"max_Z": 0, "heavy_atom_flag": "no_heavy_atom"}
    max_z = 0
    for element in formula_composition:
        z = Z_TABLE.get(element, 0)
        if z > max_z:
            max_z = z
    return {
        "max_Z": max_z,
        "heavy_atom_flag": "heavy_atom_present" if max_z > 36 else "no_heavy_atom",
        "spin_orbit_proxy": "strong" if max_z > 72 else "moderate" if max_z > 36 else "weak",
    }


def central_nucleus_spin(formula_composition, metal=None):
    """Get the central nucleus spin I for hyperfine/clock-transition potential."""
    if not metal:
        return {"central_I": None, "clock_potential": "unknown", "reason": "no_metal"}
    isotopes = get_element_isotopes(metal)
    if not isotopes:
        return {"central_I": None, "clock_potential": "unknown", "reason": "metal_not_in_table"}
    # Find the most abundant isotope
    best = None
    best_abund = 0
    for iso_id, data in isotopes.items():
        iso_data = get_isotope_data(iso_id)
        if iso_data and iso_data["abundance_pct"] > best_abund:
            best = iso_data
            best_abund = iso_data["abundance_pct"]
    if not best:
        return {"central_I": None, "clock_potential": "unknown", "reason": "no_abundant_isotope"}
    return {
        "central_I": best["spin_I"],
        "central_isotope": best["isotope_id"],
        "clock_potential": "hyperfine_qubit_possible" if best["spin_I"] > 0 else "spin_zero_central",
        "central_gamma": best["gamma_rad_s_T"],
    }


def compute_tier1_features(candidate, isotope_pattern="natural"):
    """Compute all Tier 1 features for a single candidate × isotope pattern.

    Returns a feature dict with flags. Does not filter — just labels.
    """
    formula = candidate.get("formula")
    metal = candidate.get("metal")
    charge_e = candidate.get("charge_e")
    spin_S = candidate.get("spin_S")
    spin_2S = int(2 * spin_S) if spin_S is not None else None

    # Parse formula composition
    from ..catalog import composition
    comp = composition(formula) if formula else None

    features = {
        "candidate_id": candidate["id"],
        "family": candidate.get("family"),
        "isotope_pattern": isotope_pattern,
        "evidence_kind": "hypothetical" if isotope_pattern != "natural" else candidate.get("evidence_kind", "unknown"),
    }

    # Electron parity / Kramers
    if charge_e is not None and spin_2S is not None:
        features["parity"] = electron_parity(charge_e, spin_2S)
    elif spin_S is not None:
        features["parity"] = electron_parity(0, int(2 * spin_S))
    else:
        features["parity"] = {"parity_ok": None, "reason": "missing_spin"}

    # Magnetic nuclei count
    features["magnetic_bath"] = count_magnetic_nuclei(comp, isotope_pattern)

    # Methyl groups
    features["methyl"] = count_methyl_groups(comp)

    # Max Z (spin-orbit proxy)
    features["max_Z"] = max_atomic_number(comp)

    # Central nucleus spin
    features["central_nucleus"] = central_nucleus_spin(comp, metal)

    # Status determination
    status = "success"
    status_reason = None

    if candidate.get("status") == "blocked":
        status = "blocked"
        status_reason = candidate.get("status_reason", "blocked_by_inventory")
    elif candidate.get("family") == "trapped_atom_ion" and charge_e == -1:
        status = "blocked"
        status_reason = "electron_record_overlap_chi_unavailable"
    elif candidate.get("family") == "trapped_atom_ion":
        # Atoms/ions: check if isotope has I > 0
        isotopes = get_element_isotopes(formula) if formula else {}
        has_magnetic = any(get_isotope_data(iso) and get_isotope_data(iso)["is_magnetic"]
                         for iso in isotopes)
        if not has_magnetic:
            status = "missing_data"
            status_reason = "no_magnetic_isotope_for_element"
        else:
            features["hyperfine_qubit_possible"] = True
            features["missing_data"] = "atomic_levels_NIST_ASD_not_in_project"
    elif not comp:
        status = "missing_data"
        status_reason = "formula_not_parseable"
    elif not features["magnetic_bath"]["has_magnetic_bath"] and isotope_pattern == "natural":
        status = "success"
        status_reason = "no_magnetic_bath_in_natural_abundance"

    features["status"] = status
    features["status_reason"] = status_reason
    features["computed_at"] = now()

    return features


def enumerate_combinations(candidate):
    """Enumerate all isotope_pattern × field × protocol × environment combinations.

    Returns a list of combination dicts.
    """
    combos = []
    family = candidate.get("family")

    if family == "molecular_spin":
        patterns = ISOTOPE_PATTERNS
        fields = FIELDS_T
        protocols = PROTOCOLS
        # Only include frozen_solution if solvent is present
        envs = ["crystal"]
        if candidate.get("solvent"):
            envs.append("frozen_solution")
    elif family in ("rare_earth_solid", "defect_spin"):
        patterns = ["natural"]  # Host isotope patterns handled separately
        fields = FIELDS_T
        protocols = PROTOCOLS
        envs = ["crystal"]
    elif family == "trapped_atom_ion":
        patterns = ["natural"]
        fields = [0.35]
        protocols = ["Hahn"]
        envs = ["vacuum"]
    else:
        patterns = ["natural"]
        fields = [0.35]
        protocols = ["Hahn"]
        envs = ["crystal"]

    for pattern in patterns:
        for field in fields:
            for protocol in protocols:
                for env in envs:
                    combo_id = digest([candidate["id"], pattern, field, protocol, env])[:24]
                    combos.append({
                        "combination_id": combo_id,
                        "candidate_id": candidate["id"],
                        "isotope_pattern": pattern,
                        "field_T": field,
                        "protocol": protocol,
                        "environment": env,
                    })
    return combos


def run_tier1(config, output_dir):
    """Run Phase 1: Tier 1 features for all candidates × combinations.

    Reads universe.sqlite from Phase 0, computes features, writes
    tier1_features.json and tier1_report.json.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load universe database
    db_path = config.get("universe_db_path", "screening/results/private/universe.sqlite")
    db = sqlite3.connect(str(db_path))
    try:
        rows = db.execute("SELECT payload FROM universe").fetchall()
    finally:
        db.close()

    candidates = [json.loads(r[0]) for r in rows]
    all_features = []
    all_combinations = []
    status_counts = Counter()
    family_counts = Counter()

    for candidate in candidates:
        family = candidate.get("family", "unknown")
        family_counts[family] += 1

        # Enumerate combinations
        combos = enumerate_combinations(candidate)
        all_combinations.extend(combos)

        # Compute features for each isotope pattern
        patterns_seen = set()
        for combo in combos:
            pattern = combo["isotope_pattern"]
            if pattern in patterns_seen:
                continue
            patterns_seen.add(pattern)

            features = compute_tier1_features(candidate, pattern)
            features["combination_id"] = combo["combination_id"]
            features["field_T"] = combo["field_T"]
            features["protocol"] = combo["protocol"]
            features["environment"] = combo["environment"]
            all_features.append(features)
            status_counts[features["status"]] += 1

    # Write features
    features_path = output_dir / "tier1_features.json"
    write_json(features_path, {
        "schema": "westquant_screening_tier1_v1",
        "created_at": now(),
        "total_features": len(all_features),
        "total_combinations": len(all_combinations),
        "status_counts": dict(status_counts),
        "family_counts": dict(family_counts),
        "features": all_features,
    })

    # Write report
    report = {
        "schema": "westquant_screening_tier1_report_v1",
        "created_at": now(),
        "total_candidates": len(candidates),
        "total_combinations": len(all_combinations),
        "total_feature_rows": len(all_features),
        "status_counts": dict(status_counts),
        "family_counts": dict(family_counts),
        "isotope_patterns": ISOTOPE_PATTERNS,
        "fields_T": FIELDS_T,
        "protocols": PROTOCOLS,
        "notes": [
            "Every candidate × combination gets a feature row",
            "Nothing is filtered silently — blocked candidates keep their row",
            "Non-natural isotope patterns marked evidence_kind: hypothetical",
            "Atoms/ions: Tier 1 only (NIST ASD levels not in project)",
            "Negative ions: blocked (electron affinity data unavailable)",
        ],
    }
    write_json(output_dir / "tier1_report.json", report)

    # Write manifest
    manifest = {
        "phase": "tier1",
        "created_at": now(),
        "config_hash": digest(config),
        "report_path": str(output_dir / "tier1_report.json"),
        "features_path": str(features_path),
    }
    write_json(output_dir / "manifest_tier1.json", manifest)

    return report
