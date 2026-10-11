"""Nuclear spin I, gyromagnetic ratio γ, quadrupole moment Q, and natural abundance.

Built from IAEA/NUBASE2020 evaluation and CODATA2018 recommended values.
The gyromagnetic ratios are in units of 10^7 rad T^-1 s^-1 (as commonly tabulated)
and converted to rad s^-1 T^-1 internally.

Sources:
  - NUBASE2020: Kondev et al., Chinese Phys. C 45, 030001 (2021)
    https://www-nds.iaea.org/amdc/ame2020/NUBASE2020.pdf
  - Gyromagnetic ratios: IAEA table of recommended nuclear magnetic moments,
    converted using CODATA2018 values (nuclear magneton and Planck constant)
  - Natural abundances: CIAAW (Commission on Isotopic Abundances and Atomic Weights)
  - Quadrupole moments: Stone (2015), "Table of nuclear quadrupole moments",
    Atomic Data and Nuclear Data Tables 111-112, 1-2

Values are for ground-state isotopes only. Isomers are not included.
Only stable isotopes and isotopes with half-life > 1 year are included.
"""
import json
from pathlib import Path
from ..common import write_json, read_json, now

# Gyromagnetic ratio in units of 10^7 rad T^-1 s^-1
# Spin I as number (0, 0.5, 1, 1.5, 2, ...)
# Quadrupole moment Q in barn (10^-28 m^2)
# Natural abundance in percent (0-100)

NUCLEAR_TABLE = {
    # Format: "Symbol-Mass": {"spin_I": float, "gamma_1e7_rad_s_T": float, "Q_barn": float, "abundance_pct": float}
    # gamma = 0 means spin-0 (no magnetic moment)

    # Hydrogen
    "H-1":  {"spin_I": 0.5,   "gamma_1e7": 26.7522128, "Q_barn": 0.0,       "abundance_pct": 99.9885},
    "H-2":  {"spin_I": 1.0,   "gamma_1e7": 4.1066272,  "Q_barn": 0.00286,   "abundance_pct": 0.0115},
    "H-3":  {"spin_I": 0.5,   "gamma_1e7": 28.5349579, "Q_barn": 0.0,       "abundance_pct": 0.0},  # radioactive

    # Helium
    "He-3": {"spin_I": 0.5,   "gamma_1e7": -20.380,    "Q_barn": 0.0,       "abundance_pct": 0.0002},
    "He-4": {"spin_I": 0.0,   "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 99.9998},

    # Lithium
    "Li-6": {"spin_I": 1.0,   "gamma_1e7": 3.9371,    "Q_barn": -0.000808,  "abundance_pct": 4.85},
    "Li-7": {"spin_I": 1.5,   "gamma_1e7": 10.3976,   "Q_barn": -4.01,      "abundance_pct": 95.15},

    # Beryllium
    "Be-9": {"spin_I": 1.5,   "gamma_1e7": -3.7577,   "Q_barn": 5.288,     "abundance_pct": 100.0},

    # Boron
    "B-10": {"spin_I": 3.0,   "gamma_1e7": 2.8747,    "Q_barn": 8.459,     "abundance_pct": 19.65},
    "B-11": {"spin_I": 1.5,   "gamma_1e7": 8.5847,    "Q_barn": 4.059,     "abundance_pct": 80.35},

    # Carbon
    "C-12": {"spin_I": 0.0,   "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 98.93},
    "C-13": {"spin_I": 0.5,   "gamma_1e7": 6.7283,    "Q_barn": 0.0,       "abundance_pct": 1.07},
    "C-14": {"spin_I": 0.0,   "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 0.0},  # radioactive, spin 0

    # Nitrogen
    "N-14": {"spin_I": 1.0,   "gamma_1e7": 1.9338,    "Q_barn": 2.044,     "abundance_pct": 99.6205},
    "N-15": {"spin_I": 0.5,   "gamma_1e7": -2.7126,   "Q_barn": 0.0,       "abundance_pct": 0.3795},

    # Oxygen
    "O-16": {"spin_I": 0.0,   "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 99.757},
    "O-17": {"spin_I": 2.5,   "gamma_1e7": -3.6281,   "Q_barn": -2.558,    "abundance_pct": 0.0383},
    "O-18": {"spin_I": 0.0,   "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 0.2047},

    # Fluorine
    "F-19": {"spin_I": 0.5,   "gamma_1e7": 25.1812,   "Q_barn": 0.0,       "abundance_pct": 100.0},

    # Neon
    "Ne-20": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 90.48},
    "Ne-21": {"spin_I": 1.5,  "gamma_1e7": -2.1130,   "Q_barn": 10.155,    "abundance_pct": 0.27},
    "Ne-22": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 9.25},

    # Sodium
    "Na-23": {"spin_I": 1.5,  "gamma_1e7": 7.0808,    "Q_barn": 10.4,      "abundance_pct": 100.0},

    # Magnesium
    "Mg-24": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 78.951},
    "Mg-25": {"spin_I": 2.5,  "gamma_1e7": -1.6390,   "Q_barn": 19.94,     "abundance_pct": 10.011},
    "Mg-26": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 11.038},

    # Aluminium
    "Al-27": {"spin_I": 2.5,  "gamma_1e7": 6.9762,    "Q_barn": 14.66,     "abundance_pct": 100.0},

    # Silicon
    "Si-28": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 92.197},
    "Si-29": {"spin_I": 0.5,  "gamma_1e7": -5.3190,   "Q_barn": 0.0,       "abundance_pct": 4.673},
    "Si-30": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 3.130},

    # Phosphorus
    "P-31":  {"spin_I": 0.5,  "gamma_1e7": 10.839,    "Q_barn": 0.0,       "abundance_pct": 100.0},

    # Sulfur
    "S-32": {"spin_I": 0.0,   "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 94.85},
    "S-33": {"spin_I": 1.5,   "gamma_1e7": 2.055,     "Q_barn": -6.78,     "abundance_pct": 0.76},
    "S-34": {"spin_I": 0.0,   "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 4.28},
    "S-36": {"spin_I": 0.0,   "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 0.11},

    # Chlorine
    "Cl-35": {"spin_I": 1.5,  "gamma_1e7": 2.624,     "Q_barn": -8.16,     "abundance_pct": 75.76},
    "Cl-37": {"spin_I": 1.5,  "gamma_1e7": 2.184,     "Q_barn": -6.44,     "abundance_pct": 24.24},

    # Potassium
    "K-39": {"spin_I": 1.5,   "gamma_1e7": 1.250,     "Q_barn": 5.85,      "abundance_pct": 93.2581},
    "K-40": {"spin_I": 4.0,   "gamma_1e7": 0.585,     "Q_barn": -5.85,    "abundance_pct": 0.0117},
    "K-41": {"spin_I": 1.5,   "gamma_1e7": 0.686,     "Q_barn": 7.11,      "abundance_pct": 6.7302},

    # Calcium
    "Ca-40": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 96.941},
    "Ca-43": {"spin_I": 3.5,  "gamma_1e7": -1.803,   "Q_barn": -4.08,     "abundance_pct": 0.135},
    "Ca-44": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 2.086},

    # Titanium
    "Ti-46": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 8.25},
    "Ti-47": {"spin_I": 2.5,  "gamma_1e7": -1.511,   "Q_barn": 3.02,      "abundance_pct": 7.44},
    "Ti-48": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 73.72},
    "Ti-49": {"spin_I": 3.5,  "gamma_1e7": -1.511,   "Q_barn": 2.47,      "abundance_pct": 5.41},
    "Ti-50": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 5.18},

    # Vanadium
    "V-50": {"spin_I": 6.0,   "gamma_1e7": 2.614,    "Q_barn": 2.6,       "abundance_pct": 0.250},
    "V-51": {"spin_I": 3.5,   "gamma_1e7": 7.046,    "Q_barn": -4.3,      "abundance_pct": 99.750},

    # Chromium
    "Cr-50": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 4.345},
    "Cr-52": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 83.789},
    "Cr-53": {"spin_I": 1.5,  "gamma_1e7": -1.516,   "Q_barn": -15.0,     "abundance_pct": 9.501},
    "Cr-54": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 2.365},

    # Manganese
    "Mn-55": {"spin_I": 2.5,  "gamma_1e7": 6.645,    "Q_barn": 33.0,      "abundance_pct": 100.0},

    # Iron
    "Fe-54": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 5.845},
    "Fe-56": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 91.754},
    "Fe-57": {"spin_I": 0.5,  "gamma_1e7": 0.868,    "Q_barn": 0.0,       "abundance_pct": 2.119},
    "Fe-58": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 0.282},

    # Cobalt
    "Co-59": {"spin_I": 3.5,  "gamma_1e7": 6.317,    "Q_barn": 42.0,      "abundance_pct": 100.0},

    # Nickel
    "Ni-58": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 68.077},
    "Ni-60": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 26.223},
    "Ni-61": {"spin_I": 1.5,  "gamma_1e7": -2.394,   "Q_barn": 16.2,      "abundance_pct": 1.140},
    "Ni-62": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 3.634},
    "Ni-64": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 0.926},

    # Copper
    "Cu-63": {"spin_I": 1.5,  "gamma_1e7": 7.111,    "Q_barn": -22.0,     "abundance_pct": 69.15},
    "Cu-65": {"spin_I": 1.5,  "gamma_1e7": 7.615,    "Q_barn": -19.5,     "abundance_pct": 30.85},

    # Zinc
    "Zn-64": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 48.63},
    "Zn-66": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 27.90},
    "Zn-67": {"spin_I": 2.5,  "gamma_1e7": 1.677,    "Q_barn": 15.0,      "abundance_pct": 4.10},
    "Zn-68": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 18.75},
    "Zn-70": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 0.62},

    # Yttrium
    "Y-89": {"spin_I": 0.5,   "gamma_1e7": -1.316,   "Q_barn": 0.0,       "abundance_pct": 100.0},

    # Zirconium (all spin-0 except 91Zr)
    "Zr-90": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 51.45},
    "Zr-91": {"spin_I": 2.5,  "gamma_1e7": -1.391,   "Q_barn": -17.6,     "abundance_pct": 11.22},
    "Zr-92": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 17.15},

    # Tungsten
    "W-182": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 26.494},
    "W-183": {"spin_I": 0.5,  "gamma_1e7": 1.128,    "Q_barn": 0.0,       "abundance_pct": 14.313},
    "W-184": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 30.642},
    "W-186": {"spin_I": 0.0,  "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 28.426},

    # Rare earth isotopes relevant to quantum memory
    # Praseodymium
    "Pr-141": {"spin_I": 2.5, "gamma_1e7": 1.711,    "Q_barn": -5.89,     "abundance_pct": 100.0},

    # Neodymium
    "Nd-142": {"spin_I": 0.0, "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 27.2},
    "Nd-143": {"spin_I": 3.5, "gamma_1e7": -1.080,   "Q_barn": -49.0,     "abundance_pct": 12.2},
    "Nd-145": {"spin_I": 3.5, "gamma_1e7": -0.666,   "Q_barn": -33.0,     "abundance_pct": 8.3},

    # Samarium
    "Sm-147": {"spin_I": 3.5, "gamma_1e7": -0.838,   "Q_barn": -25.0,     "abundance_pct": 15.0},
    "Sm-149": {"spin_I": 2.5, "gamma_1e7": -0.694,   "Q_barn": 7.97,      "abundance_pct": 13.8},

    # Europium
    "Eu-151": {"spin_I": 2.5, "gamma_1e7": 2.937,    "Q_barn": 90.3,      "abundance_pct": 47.81},
    "Eu-153": {"spin_I": 2.5, "gamma_1e7": 1.298,    "Q_barn": 241.2,     "abundance_pct": 52.19},

    # Gadolinium
    "Gd-155": {"spin_I": 1.5, "gamma_1e7": 0.825,    "Q_barn": 127.0,     "abundance_pct": 14.8},
    "Gd-157": {"spin_I": 1.5, "gamma_1e7": 1.094,    "Q_barn": 135.0,     "abundance_pct": 15.7},

    # Terbium
    "Tb-159": {"spin_I": 1.5, "gamma_1e7": 2.534,    "Q_barn": 143.2,     "abundance_pct": 100.0},

    # Dysprosium
    "Dy-161": {"spin_I": 2.5, "gamma_1e7": 0.860,    "Q_barn": 250.7,     "abundance_pct": 18.91},
    "Dy-163": {"spin_I": 2.5, "gamma_1e7": 1.190,   "Q_barn": 264.8,     "abundance_pct": 24.90},

    # Holmium
    "Ho-165": {"spin_I": 3.5, "gamma_1e7": 1.711,    "Q_barn": 358.0,     "abundance_pct": 100.0},

    # Erbium
    "Er-166": {"spin_I": 0.0, "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 33.6},
    "Er-167": {"spin_I": 3.5, "gamma_1e7": -0.817,   "Q_barn": 356.0,     "abundance_pct": 22.95},
    "Er-168": {"spin_I": 0.0, "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 26.8},
    "Er-170": {"spin_I": 0.0, "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 14.9},

    # Thulium
    "Tm-169": {"spin_I": 0.5, "gamma_1e7": -2.210,   "Q_barn": 0.0,       "abundance_pct": 100.0},

    # Ytterbium
    "Yb-168": {"spin_I": 0.0, "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 0.13},
    "Yb-170": {"spin_I": 0.0, "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 3.04},
    "Yb-171": {"spin_I": 0.5, "gamma_1e7": 4.732,    "Q_barn": 0.0,       "abundance_pct": 14.28},
    "Yb-172": {"spin_I": 0.0, "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 21.83},
    "Yb-173": {"spin_I": 2.5, "gamma_1e7": -1.310,   "Q_barn": 28.0,      "abundance_pct": 16.13},
    "Yb-174": {"spin_I": 0.0, "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 31.83},
    "Yb-176": {"spin_I": 0.0, "gamma_1e7": 0.0,       "Q_barn": 0.0,       "abundance_pct": 12.76},

    # Bismuth
    "Bi-209": {"spin_I": 4.5, "gamma_1e7": 4.336,    "Q_barn": -51.6,     "abundance_pct": 100.0},

    # Iodine
    "I-127": {"spin_I": 2.5,  "gamma_1e7": 5.390,    "Q_barn": -71.5,     "abundance_pct": 100.0},

    # Bromine
    "Br-79": {"spin_I": 1.5,  "gamma_1e7": 6.725,    "Q_barn": 31.3,      "abundance_pct": 50.69},
    "Br-81": {"spin_I": 1.5,  "gamma_1e7": 7.250,    "Q_barn": 26.2,      "abundance_pct": 49.31},
}


def get_isotope_data(isotope_id):
    """Get nuclear data for an isotope.

    Args:
        isotope_id: e.g. "C-13", "Si-29", "Eu-151"

    Returns:
        dict with keys: spin_I, gamma_rad_s_T, Q_barn, abundance_pct, is_magnetic
        or None if isotope not in table.
    """
    entry = NUCLEAR_TABLE.get(isotope_id)
    if entry is None:
        return None
    gamma = entry["gamma_1e7"] * 1e7  # convert to rad s^-1 T^-1
    return {
        "isotope_id": isotope_id,
        "spin_I": entry["spin_I"],
        "gamma_rad_s_T": gamma,
        "Q_barn": entry["Q_barn"],
        "abundance_pct": entry["abundance_pct"],
        "is_magnetic": entry["spin_I"] > 0 and abs(gamma) > 0,
    }


def get_element_isotopes(symbol):
    """Get all isotopes for an element symbol from the bundled table."""
    prefix = symbol + "-"
    return {k: v for k, v in NUCLEAR_TABLE.items() if k.startswith(prefix)}


def cross_check_pycce(output_path=None, tolerance=0.001):
    """Cross-check the bundled table against PyCCE's built-in isotope table.

    Returns a dict with discrepancies above the tolerance (0.1% by default).
    """
    discrepancies = []
    pycce_available = False
    try:
        import pycce as pc
        pycce_available = True
        pycce_elements = {}
        # PyCCE stores isotope data in pc.elements or similar
        # The exact API depends on the version
        try:
            from pycce.elements import ELEMENTS
            for key, val in ELEMENTS.items():
                # PyCCE keys may be like "1H", "13C", etc.
                # Convert to our format "H-1", "C-13"
                if isinstance(key, str) and key[0].isdigit():
                    mass = int("".join(c for c in key if c.isdigit()))
                    elem = "".join(c for c in key if c.isalpha())
                    our_key = f"{elem}-{mass}"
                    if our_key in NUCLEAR_TABLE:
                        our = NUCLEAR_TABLE[our_key]
                        # Compare spin
                        if hasattr(val, "spin") and val.spin is not None:
                            if abs(float(val.spin) - our["spin_I"]) > 0.01:
                                discrepancies.append({
                                    "isotope": our_key,
                                    "field": "spin_I",
                                    "ours": our["spin_I"],
                                    "pycce": float(val.spin),
                                    "relative_diff": abs(float(val.spin) - our["spin_I"]) / max(our["spin_I"], 0.01),
                                })
                        # Compare gyromagnetic ratio
                        if hasattr(val, "gyro") and val.gyro is not None:
                            pycce_gamma = float(val.gyro)  # PyCCE uses rad/ms/G = 1e7 rad/s/T
                            our_gamma = our["gamma_1e7"]
                            if abs(pycce_gamma) > 0 and abs(our_gamma) > 0:
                                rel_diff = abs(pycce_gamma - our_gamma) / abs(our_gamma)
                                if rel_diff > tolerance:
                                    discrepancies.append({
                                        "isotope": our_key,
                                        "field": "gamma",
                                        "ours": our_gamma,
                                        "pycce": pycce_gamma,
                                        "relative_diff": rel_diff,
                                    })
        except ImportError:
            pycce_available = False
    except ImportError:
        pycce_available = False

    result = {
        "schema": "westquant_nucdata_crosscheck_v1",
        "created_at": now(),
        "pycce_available": pycce_available,
        "tolerance": tolerance,
        "total_isotopes_in_bundled_table": len(NUCLEAR_TABLE),
        "discrepancies_above_tolerance": discrepancies,
        "discrepancy_count": len(discrepancies),
        "source": "IAEA/NUBASE2020 + CODATA2018 + CIAAW abundances + Stone(2015) quadrupole moments",
    }
    if output_path:
        write_json(output_path, result)
    return result


def export_table(output_path):
    """Export the full nuclear data table to JSON."""
    table = {}
    for isotope_id, entry in NUCLEAR_TABLE.items():
        data = get_isotope_data(isotope_id)
        if data:
            table[isotope_id] = data
    result = {
        "schema": "westquant_nuclear_data_v1",
        "created_at": now(),
        "source": "IAEA/NUBASE2020 + CODATA2018 + CIAAW abundances + Stone(2015) quadrupole moments",
        "total_isotopes": len(table),
        "isotopes": table,
        "notes": [
            "Ground-state isotopes only; isomers not included",
            "gamma in rad s^-1 T^-1 (converted from 10^7 rad T^-1 s^-1 tabulated values)",
            "Q in barn (10^-28 m^2)",
            "Abundance in percent (0-100)",
            "is_magnetic = True when spin_I > 0 and gamma != 0",
        ],
    }
    write_json(output_path, result)
    return result
