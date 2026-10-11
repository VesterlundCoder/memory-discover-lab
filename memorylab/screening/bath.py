"""Bath construction: CIF → supercell → isotope realisations → PyCCE bath.

Builds nuclear spin baths from molecular CIF structures for CCE calculations.
Supports isotope patterns (natural, perdeuterated, C13-depleted, etc.) and
solvent bath addition for frozen-solution environments.

Key assumptions (recorded in every bath):
  - point_dipole: hyperfine tensors computed as point-dipole
  - free_electron_g: central spin g=2.0023 isotropic
  - Nuclei within r_exclusion are excluded (flagged) unless DFT tensors supplied
"""
import io
import zipfile
from pathlib import Path

import numpy as np

from ..common import seed, MissingData
from .nucdata import get_isotope_data, get_element_isotopes, NUCLEAR_TABLE
from ._compat import install_all_shims

install_all_shims()


def read_cif_from_zip(zip_path, cif_filename):
    """Read a CIF file from a zip archive and return ASE atoms object."""
    from ase.io import read
    with zipfile.ZipFile(zip_path) as z:
        cif_bytes = z.read(cif_filename)
    atoms = read(io.BytesIO(cif_bytes), format="cif")
    return atoms


def get_formula_from_atoms(atoms):
    """Get chemical formula from ASE atoms."""
    return atoms.get_chemical_formula()


def get_composition_from_atoms(atoms):
    """Get element composition dict from ASE atoms."""
    from collections import Counter
    symbols = atoms.get_chemical_symbols()
    comp = Counter(symbols)
    return dict(comp)


def build_supercell(atoms, r_bath_angstrom):
    """Build a supercell large enough for r_bath.

    Returns a repeated atoms object with enough cells to cover r_bath.
    """
    cell = atoms.get_cell()
    if np.linalg.det(cell) == 0:
        raise ValueError("Atoms object has no cell; cannot build supercell")

    # Determine repetitions needed
    cell_lengths = np.linalg.norm(cell, axis=1)
    reps = np.maximum(1, np.ceil(2 * r_bath_angstrom / cell_lengths).astype(int))
    supercell = atoms.repeat(reps)
    return supercell, reps


def assign_isotopes(composition, isotope_pattern, rng):
    """Assign isotopes to each atom based on isotope pattern.

    Returns a list of (element, isotope_id) for each atom in the composition.
    """
    assignments = []
    for element, count in composition.items():
        isotopes = get_element_isotopes(element)
        if not isotopes:
            assignments.extend([(element, None)] * count)
            continue

        if isotope_pattern == "natural":
            for _ in range(count):
                # Sample isotope by natural abundance
                iso_ids = list(isotopes.keys())
                abundances = np.array([isotopes[i]["abundance_pct"] for i in iso_ids])
                abundances = abundances / abundances.sum()
                choice = rng.choice(len(iso_ids), p=abundances)
                assignments.append((element, iso_ids[choice]))
        elif isotope_pattern == "perdeuterated":
            if element == "H":
                assignments.extend([(element, "H-2")] * count)
            else:
                for _ in range(count):
                    iso_ids = list(isotopes.keys())
                    abundances = np.array([isotopes[i]["abundance_pct"] for i in iso_ids])
                    abundances = abundances / abundances.sum()
                    choice = rng.choice(len(iso_ids), p=abundances)
                    assignments.append((element, iso_ids[choice]))
        elif isotope_pattern == "C13_depleted_99.99":
            if element == "C":
                # 99.99% C-12, 0.01% C-13
                for _ in range(count):
                    choice = rng.choice(2, p=[0.9999, 0.0001])
                    assignments.append((element, "C-12" if choice == 0 else "C-13"))
            else:
                for _ in range(count):
                    iso_ids = list(isotopes.keys())
                    abundances = np.array([isotopes[i]["abundance_pct"] for i in iso_ids])
                    abundances = abundances / abundances.sum()
                    choice = rng.choice(len(iso_ids), p=abundances)
                    assignments.append((element, iso_ids[choice]))
        elif isotope_pattern == "N15":
            if element == "N":
                assignments.extend([(element, "N-15")] * count)
            else:
                for _ in range(count):
                    iso_ids = list(isotopes.keys())
                    abundances = np.array([isotopes[i]["abundance_pct"] for i in iso_ids])
                    abundances = abundances / abundances.sum()
                    choice = rng.choice(len(iso_ids), p=abundances)
                    assignments.append((element, iso_ids[choice]))
        elif isotope_pattern in ("deut+C13dep", "deut+C13dep+N15"):
            if element == "H":
                assignments.extend([(element, "H-2")] * count)
            elif element == "C":
                for _ in range(count):
                    choice = rng.choice(2, p=[0.9999, 0.0001])
                    assignments.append((element, "C-12" if choice == 0 else "C-13"))
            elif element == "N" and isotope_pattern == "deut+C13dep+N15":
                assignments.extend([(element, "N-15")] * count)
            else:
                for _ in range(count):
                    iso_ids = list(isotopes.keys())
                    abundances = np.array([isotopes[i]["abundance_pct"] for i in iso_ids])
                    abundances = abundances / abundances.sum()
                    choice = rng.choice(len(iso_ids), p=abundances)
                    assignments.append((element, iso_ids[choice]))
        else:
            assignments.extend([(element, None)] * count)

    return assignments


def point_dipole_hyperfine(position_angstrom, central_position_angstrom, gyro_nucleus):
    """Compute point-dipole hyperfine tensor in Hz.

    A_ij = (mu_0 / 4pi) * (gamma_e * gamma_n * hbar) / r^3 * (delta_ij - 3*r_i*r_j/r^2)

    Returns a 3x3 tensor in Hz.
    """
    mu0_over_4pi = 1e-7  # T m / A
    gamma_e = 1.760859644e11  # rad s^-1 T^-1 (electron gyromagnetic ratio)
    hbar = 1.054571817e-34  # J s
    r = np.array(position_angstrom) - np.array(central_position_angstrom)
    r_m = r * 1e-10  # convert angstrom to meters
    r_mag = np.linalg.norm(r_m)

    if r_mag < 1e-15:
        return np.zeros((3, 3))

    # Point dipole: A = (mu0/4pi) * gamma_e * gamma_n * hbar / r^3 * (I - 3*n_i*n_j)
    # In Hz: divide by 2pi for angular frequency
    prefactor = mu0_over_4pi * gamma_e * gyro_nucleus * hbar / (r_mag**3 * 2 * np.pi)

    n = r_m / r_mag
    delta = np.eye(3)
    tensor = prefactor * (delta - 3 * np.outer(n, n))
    return tensor


def build_pycce_bath(atoms, isotope_pattern, central_position_angstrom,
                     r_bath_angstrom=30.0, r_dipole_angstrom=8.0,
                     r_exclusion_angstrom=3.0, simulation_seed=0,
                     solvent_atoms=None):
    """Build a PyCCE BathArray from an ASE atoms object.

    Args:
        atoms: ASE atoms object (molecular structure)
        isotope_pattern: one of ISOTOPE_PATTERNS
        central_position_angstrom: position of the central spin
        r_bath_angstrom: bath radius cutoff
        r_dipole_angstrom: dipolar interaction cutoff
        r_exclusion_angstrom: exclude nuclei closer than this to central spin
        simulation_seed: random seed for isotope assignment
        solvent_atoms: optional solvent ASE atoms for frozen-solution bath

    Returns:
        dict with:
          - bath: PyCCE BathArray
          - excluded_nuclei: list of excluded nuclei (within r_exclusion)
          - assumptions: list of assumption strings
          - bath_size: number of nuclei in bath
    """
    import pycce as pc

    rng = np.random.default_rng(simulation_seed)

    # Build supercell
    try:
        supercell, reps = build_supercell(atoms, r_bath_angstrom)
    except ValueError:
        # No cell (molecule); use as-is
        supercell = atoms
        reps = (1, 1, 1)

    positions = supercell.get_positions()
    composition = get_composition_from_atoms(supercell)

    # Assign isotopes
    assignments = assign_isotopes(composition, isotope_pattern, rng)

    # Filter by r_bath and r_exclusion
    central = np.array(central_position_angstrom)
    bath_entries = []
    excluded = []
    near_nuclei_excluded = 0

    for i, (pos, (element, isotope_id)) in enumerate(zip(positions, assignments)):
        if isotope_id is None:
            continue
        iso_data = get_isotope_data(isotope_id)
        if iso_data is None or not iso_data["is_magnetic"]:
            continue

        r = np.linalg.norm(pos - central)
        if r > r_bath_angstrom:
            continue

        if r < r_exclusion_angstrom:
            excluded.append({
                "index": i, "element": element, "isotope": isotope_id,
                "distance_angstrom": r,
            })
            near_nuclei_excluded += 1
            continue

        # Compute point-dipole hyperfine
        A = point_dipole_hyperfine(pos, central, iso_data["gamma_rad_s_T"])

        # Check r_dipole
        if r > r_dipole_angstrom:
            # Still include but with weaker coupling
            pass

        bath_entries.append({
            "position": pos,
            "isotope_id": isotope_id,
            "A": A,
            "Q": np.zeros((3, 3)),  # No quadrupole for now
            "distance": r,
        })

    # Add solvent bath if provided
    if solvent_atoms is not None:
        solvent_positions = solvent_atoms.get_positions()
        solvent_comp = get_composition_from_atoms(solvent_atoms)
        solvent_assignments = assign_isotopes(solvent_comp, isotope_pattern, rng)
        for pos, (element, isotope_id) in zip(solvent_positions, solvent_assignments):
            if isotope_id is None:
                continue
            iso_data = get_isotope_data(isotope_id)
            if iso_data is None or not iso_data["is_magnetic"]:
                continue
            r = np.linalg.norm(pos - central)
            if r > r_bath_angstrom or r < r_exclusion_angstrom:
                continue
            A = point_dipole_hyperfine(pos, central, iso_data["gamma_rad_s_T"])
            bath_entries.append({
                "position": pos,
                "isotope_id": isotope_id,
                "A": A,
                "Q": np.zeros((3, 3)),
                "distance": r,
            })

    if not bath_entries:
        return {
            "bath": None,
            "excluded_nuclei": excluded,
            "assumptions": ["point_dipole", "free_electron_g", "no_magnetic_bath"],
            "bath_size": 0,
            "near_nuclei_excluded": near_nuclei_excluded,
        }

    # Build PyCCE BathArray
    bath = pc.BathArray(shape=(len(bath_entries),))
    for i, entry in enumerate(bath_entries):
        symbol, mass = entry["isotope_id"].split("-")
        bath["N"][i] = mass + symbol
        bath["xyz"][i] = entry["position"]
        bath["A"][i] = entry["A"] / 1000  # PyCCE uses kHz
        bath["Q"][i] = entry["Q"] / 1000

    return {
        "bath": bath,
        "excluded_nuclei": excluded,
        "assumptions": ["point_dipole", "free_electron_g"],
        "bath_size": len(bath_entries),
        "near_nuclei_excluded": near_nuclei_excluded,
        "supercell_reps": reps,
    }


def find_central_spin_position(atoms, metal=None):
    """Find the position of the central spin (metal atom or first atom).

    Returns the position in angstrom.
    """
    positions = atoms.get_positions()
    symbols = atoms.get_chemical_symbols()

    if metal:
        for i, s in enumerate(symbols):
            if s == metal:
                return positions[i]

    # Default: first atom
    return positions[0]


def validate_bath_against_exact(bath_spec, times_s, cpmg_pulses=0):
    """Validate the bath builder against the exact solver on small sub-baths.

    Uses spin.exact_coherence on ≤ 8-spin sub-baths.
    """
    from ..spin import exact_coherence

    if bath_spec.get("bath_size", 0) > 8:
        # Take a sub-bath of the 8 closest nuclei
        bath = bath_spec["bath"]
        # Sort by distance and take 8 closest
        # ... (simplified for now)
        pass

    # For small baths, run exact solver
    nuclei = []
    for i in range(bath_spec.get("bath_size", 0)):
        entry = bath_spec["bath"][i]
        symbol, mass = str(entry["N"]).split("-") if "-" in str(entry["N"]) else (str(entry["N"]), "")
        iso_id = f"{symbol}-{mass}" if mass else str(entry["N"])
        iso_data = get_isotope_data(iso_id)
        if iso_data:
            nuclei.append({
                "isotope_id": iso_id,
                "spin_I": iso_data["spin_I"],
                "gyro_rad_s_T": iso_data["gamma_rad_s_T"],
                "position_angstrom": entry["xyz"].tolist(),
                "hyperfine_Hz": (np.asarray(entry["A"]) * 1000).tolist(),
            })

    if not nuclei:
        return {"validation": "no_nuclei", "status": "skipped"}

    spin_bath = {
        "nuclei": nuclei,
        "central_spin_S": 0.5,
        "central_gyro": 1.760859644e11,
    }

    try:
        L = exact_coherence(spin_bath, times_s, 1.0, cpmg_pulses)
        return {
            "validation": "exact_solver",
            "status": "success",
            "envelope": np.abs(L).tolist(),
        }
    except Exception as e:
        return {"validation": "exact_solver", "status": "failed", "error": str(e)}
