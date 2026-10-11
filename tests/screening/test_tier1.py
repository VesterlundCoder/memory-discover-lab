"""Tests for Phase 1: Tier 1 rule-based physics filtering."""
import unittest
from pathlib import Path

from memorylab.screening.tier1 import (
    compute_tier1_features,
    count_magnetic_nuclei,
    count_methyl_groups,
    max_atomic_number,
    central_nucleus_spin,
    electron_parity,
    enumerate_combinations,
    ISOTOPE_PATTERNS,
    FIELDS_T,
    PROTOCOLS,
)


class ElectronParityTests(unittest.TestCase):
    """Tests for electron-count / 2S parity checks."""

    def test_half_integer_spin_is_kramers(self):
        result = electron_parity(0, 1)  # 2S=1 → S=1/2
        self.assertTrue(result["is_kramers"])
        self.assertTrue(result["is_half_integer"])
        self.assertEqual(result["reason"], "kramers")

    def test_integer_spin_is_non_kramers(self):
        result = electron_parity(0, 2)  # 2S=2 → S=1
        self.assertFalse(result["is_kramers"])
        self.assertEqual(result["reason"], "non_kramers")

    def test_missing_data(self):
        result = electron_parity(None, 1)
        self.assertIsNone(result["parity_ok"])
        self.assertEqual(result["reason"], "missing_charge_or_spin")


class MagneticNucleiTests(unittest.TestCase):
    """Tests for magnetic nuclei counting per isotope pattern."""

    def test_natural_abundance_h2o(self):
        comp = {"H": 2, "O": 1}
        result = count_magnetic_nuclei(comp, "natural")
        # H-1 is 99.99% magnetic, O-17 is 0.038%
        self.assertGreater(result["magnetic_nuclei_count"], 1.9)
        self.assertTrue(result["has_magnetic_bath"])

    def test_perdeuterated_replaces_h(self):
        comp = {"H": 4, "C": 1, "O": 1}
        natural = count_magnetic_nuclei(comp, "natural")
        deuterated = count_magnetic_nuclei(comp, "perdeuterated")
        # Deuterated should have H-2 instead of H-1
        h1_natural = [m for m in natural["isotopes"] if m["isotope"] == "H-1"]
        h2_deut = [m for m in deuterated["isotopes"] if m["isotope"] == "H-2"]
        self.assertTrue(len(h1_natural) > 0)
        self.assertTrue(len(h2_deut) > 0)
        # H-2 has lower gamma than H-1, so the gamma-weighted bath is weaker
        natural_gamma = sum(m["count"] * abs(m["gamma"]) for m in natural["isotopes"])
        deut_gamma = sum(m["count"] * abs(m["gamma"]) for m in deuterated["isotopes"])
        self.assertLess(deut_gamma, natural_gamma)

    def test_c13_depleted_reduces_carbon_magnetism(self):
        comp = {"C": 10, "H": 10}
        natural = count_magnetic_nuclei(comp, "natural")
        depleted = count_magnetic_nuclei(comp, "C13_depleted_99.99")
        c13_natural = [m for m in natural["isotopes"] if m["isotope"] == "C-13"]
        c13_depleted = [m for m in depleted["isotopes"] if m["isotope"] == "C-13"]
        if c13_natural and c13_depleted:
            self.assertLess(c13_depleted[0]["count"], c13_natural[0]["count"])

    def test_no_formula(self):
        result = count_magnetic_nuclei(None)
        self.assertEqual(result["magnetic_nuclei_count"], 0)


class MethylGroupTests(unittest.TestCase):
    """Tests for methyl rotor detection."""

    def test_methyl_groups_detected(self):
        comp = {"C": 6, "H": 12}
        result = count_methyl_groups(comp)
        self.assertGreater(result["methyl_count"], 0)
        self.assertTrue(result["has_rotors"])

    def test_no_methyl_without_hydrogen(self):
        comp = {"C": 6, "O": 6}
        result = count_methyl_groups(comp)
        self.assertEqual(result["methyl_count"], 0)
        self.assertFalse(result["has_rotors"])


class MaxZTests(unittest.TestCase):
    """Tests for max atomic number (spin-orbit proxy)."""

    def test_heavy_atom_detected(self):
        comp = {"C": 6, "Bi": 1}
        result = max_atomic_number(comp)
        self.assertEqual(result["max_Z"], 83)
        self.assertEqual(result["spin_orbit_proxy"], "strong")

    def test_light_atoms_only(self):
        comp = {"C": 6, "H": 12, "O": 6}
        result = max_atomic_number(comp)
        self.assertEqual(result["max_Z"], 8)
        self.assertEqual(result["spin_orbit_proxy"], "weak")


class CentralNucleusTests(unittest.TestCase):
    """Tests for central nucleus spin."""

    def test_vanadium_central_spin(self):
        result = central_nucleus_spin({"V": 1}, "V")
        self.assertEqual(result["central_I"], 3.5)  # V-51: I=7/2
        self.assertEqual(result["clock_potential"], "hyperfine_qubit_possible")

    def test_no_metal(self):
        result = central_nucleus_spin({"C": 6}, None)
        self.assertIsNone(result["central_I"])
        self.assertEqual(result["reason"], "no_metal")


class CombinationEnumerationTests(unittest.TestCase):
    """Tests for combination enumeration."""

    def test_molecular_combinations(self):
        candidate = {
            "id": "mtd:1",
            "family": "molecular_spin",
            "formula": "C6H12O6V",
            "metal": "V",
            "solvent": "o-terphenyl",
        }
        combos = enumerate_combinations(candidate)
        # 6 patterns × 2 fields × 3 protocols × 2 envs (crystal + frozen_solution)
        self.assertEqual(len(combos), 6 * 2 * 3 * 2)
        # Check that frozen_solution is included (solvent present)
        envs = set(c["environment"] for c in combos)
        self.assertIn("frozen_solution", envs)

    def test_no_solvent_means_no_frozen_solution(self):
        candidate = {
            "id": "mtd:2",
            "family": "molecular_spin",
            "formula": "C6H12O6",
            "solvent": None,
        }
        combos = enumerate_combinations(candidate)
        envs = set(c["environment"] for c in combos)
        self.assertNotIn("frozen_solution", envs)
        self.assertIn("crystal", envs)

    def test_atom_ion_combinations(self):
        candidate = {
            "id": "atom:H:q0:s1",
            "family": "trapped_atom_ion",
            "formula": "H",
            "charge_e": 0,
        }
        combos = enumerate_combinations(candidate)
        # 1 pattern × 1 field × 1 protocol × 1 env
        self.assertEqual(len(combos), 1)


class FullTier1FeatureTests(unittest.TestCase):
    """Tests for the full Tier 1 feature computation."""

    def test_molecular_candidate_features(self):
        candidate = {
            "id": "mtd:1",
            "family": "molecular_spin",
            "formula": "C12H8O4V",
            "metal": "V",
            "spin_S": 0.5,
            "solvent": "o-terphenyl",
            "evidence_kind": "curated_experimental",
        }
        features = compute_tier1_features(candidate, "natural")
        self.assertEqual(features["candidate_id"], "mtd:1")
        self.assertEqual(features["isotope_pattern"], "natural")
        self.assertEqual(features["status"], "success")
        self.assertIn("magnetic_bath", features)
        self.assertTrue(features["magnetic_bath"]["has_magnetic_bath"])
        self.assertIn("methyl", features)
        self.assertIn("max_Z", features)
        self.assertIn("central_nucleus", features)

    def test_hypothetical_pattern_marked(self):
        candidate = {
            "id": "mtd:1",
            "family": "molecular_spin",
            "formula": "C6H12O6",
            "evidence_kind": "curated_experimental",
        }
        features = compute_tier1_features(candidate, "perdeuterated")
        self.assertEqual(features["evidence_kind"], "hypothetical")

    def test_negative_ion_blocked(self):
        candidate = {
            "id": "atom:H:q-1:s1",
            "family": "trapped_atom_ion",
            "formula": "H",
            "charge_e": -1,
            "spin_S": 0.5,
        }
        features = compute_tier1_features(candidate, "natural")
        self.assertEqual(features["status"], "blocked")
        self.assertIn("chi", features["status_reason"])


if __name__ == "__main__":
    unittest.main()
