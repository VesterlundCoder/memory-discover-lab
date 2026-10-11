"""Tests for Phase 0b: nuclear data table and PyCCE cross-check."""
import json
import unittest
from pathlib import Path

from memorylab.screening.nucdata import (
    NUCLEAR_TABLE,
    get_isotope_data,
    get_element_isotopes,
    cross_check_pycce,
    export_table,
)


class NuclearDataTests(unittest.TestCase):
    """Tests for the bundled nuclear data table."""

    def test_known_isotopes_present(self):
        """Key isotopes for molecular qubits and quantum memories are present."""
        required = [
            "H-1", "H-2", "C-12", "C-13", "N-14", "N-15",
            "O-16", "O-17", "F-19", "Si-28", "Si-29", "P-31",
            "V-51", "Cr-53", "Mn-55", "Fe-57", "Co-59",
            "Cu-63", "Cu-65", "Zn-67",
            "Eu-151", "Eu-153", "Er-167", "Yb-171", "Pr-141",
            "Bi-209", "I-127",
        ]
        for iso in required:
            self.assertIn(iso, NUCLEAR_TABLE, f"Missing isotope: {iso}")

    def test_spin_values_correct(self):
        """Known spin values are correct."""
        self.assertEqual(get_isotope_data("H-1")["spin_I"], 0.5)
        self.assertEqual(get_isotope_data("H-2")["spin_I"], 1.0)
        self.assertEqual(get_isotope_data("C-12")["spin_I"], 0.0)
        self.assertEqual(get_isotope_data("C-13")["spin_I"], 0.5)
        self.assertEqual(get_isotope_data("Eu-151")["spin_I"], 2.5)
        self.assertEqual(get_isotope_data("Er-167")["spin_I"], 3.5)
        self.assertEqual(get_isotope_data("Bi-209")["spin_I"], 4.5)

    def test_gyromagnetic_ratios_correct(self):
        """Known gyromagnetic ratios are correct within 0.1%."""
        data = get_isotope_data("H-1")
        self.assertAlmostEqual(data["gamma_rad_s_T"], 26.7522128e7, delta=0.1e7)
        data = get_isotope_data("C-13")
        self.assertAlmostEqual(data["gamma_rad_s_T"], 6.7283e7, delta=0.01e7)
        data = get_isotope_data("Si-29")
        self.assertAlmostEqual(data["gamma_rad_s_T"], -5.3190e7, delta=0.01e7)

    def test_magnetic_flag(self):
        """is_magnetic is True for spinful isotopes with nonzero gamma."""
        self.assertTrue(get_isotope_data("H-1")["is_magnetic"])
        self.assertTrue(get_isotope_data("C-13")["is_magnetic"])
        self.assertFalse(get_isotope_data("C-12")["is_magnetic"])
        self.assertFalse(get_isotope_data("O-16")["is_magnetic"])
        self.assertTrue(get_isotope_data("Eu-151")["is_magnetic"])

    def test_abundances_sum_reasonably(self):
        """Natural abundances for key elements sum close to 100%."""
        si_isotopes = get_element_isotopes("Si")
        total = sum(v["abundance_pct"] for v in si_isotopes.values())
        self.assertAlmostEqual(total, 100.0, delta=1.0)

        eu_isotopes = get_element_isotopes("Eu")
        total = sum(v["abundance_pct"] for v in eu_isotopes.values())
        self.assertAlmostEqual(total, 100.0, delta=0.1)

    def test_unknown_isotope_returns_none(self):
        """Unknown isotope IDs return None."""
        self.assertIsNone(get_isotope_data("X-999"))
        self.assertIsNone(get_isotope_data("U-238"))  # not in table (radioactive, not needed)

    def test_quadrupole_moments_present(self):
        """Quadrupole moments are present for I > 1/2 isotopes."""
        data = get_isotope_data("H-2")
        self.assertAlmostEqual(data["Q_barn"], 0.00286, delta=0.0001)
        data = get_isotope_data("N-14")
        self.assertAlmostEqual(data["Q_barn"], 2.044, delta=0.01)
        data = get_isotope_data("Eu-151")
        self.assertAlmostEqual(data["Q_barn"], 90.3, delta=1.0)

    def test_export_table(self):
        """Export produces a valid JSON table."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "nucdata.json"
            result = export_table(path)
            self.assertTrue(path.exists())
            self.assertGreater(result["total_isotopes"], 50)
            loaded = json.loads(path.read_text())
            self.assertEqual(loaded["schema"], "westquant_nuclear_data_v1")
            self.assertIn("H-1", loaded["isotopes"])

    def test_cross_check_runs_without_pycce(self):
        """Cross-check runs even when PyCCE is not installed."""
        result = cross_check_pycce()
        self.assertIn("pycce_available", result)
        self.assertIn("discrepancy_count", result)
        # If PyCCE is not available, discrepancies should be empty
        if not result["pycce_available"]:
            self.assertEqual(result["discrepancy_count"], 0)


if __name__ == "__main__":
    unittest.main()
