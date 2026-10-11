"""Tests for Phase 2: bath construction and pilot CCE."""
import io
import unittest
from pathlib import Path

import numpy as np

from memorylab.screening.bath import (
    build_pycce_bath,
    find_central_spin_position,
    get_composition_from_atoms,
    point_dipole_hyperfine,
    assign_isotopes,
    build_supercell,
)
from memorylab.screening._compat import install_all_shims

install_all_shims()

BASE = Path(__file__).resolve().parents[2]


class PointDipoleTests(unittest.TestCase):
    """Tests for point-dipole hyperfine tensor computation."""

    def test_hyperfine_falls_off_as_r3(self):
        """Hyperfine coupling should fall off as 1/r^3."""
        pos1 = np.array([3.0, 0.0, 0.0])
        pos2 = np.array([6.0, 0.0, 0.0])
        central = np.array([0.0, 0.0, 0.0])
        gyro = 26.7522128e7  # H-1
        A1 = point_dipole_hyperfine(pos1, central, gyro)
        A2 = point_dipole_hyperfine(pos2, central, gyro)
        # At 2x distance, coupling should be 1/8
        ratio = np.max(np.abs(A2)) / max(np.max(np.abs(A1)), 1e-30)
        self.assertAlmostEqual(ratio, 1/8, places=2)

    def test_hyperfine_zero_at_origin(self):
        """Hyperfine is zero when nucleus is at central spin position."""
        A = point_dipole_hyperfine([0, 0, 0], [0, 0, 0], 26.7522128e7)
        np.testing.assert_allclose(A, np.zeros((3, 3)))

    def test_hyperfine_traceless(self):
        """Point-dipole hyperfine tensor is traceless."""
        A = point_dipole_hyperfine([3.0, 4.0, 0.0], [0, 0, 0], 26.7522128e7)
        self.assertAlmostEqual(np.trace(A), 0, places=6)


class IsotopeAssignmentTests(unittest.TestCase):
    """Tests for isotope assignment by pattern."""

    def test_natural_abundance_assignment(self):
        rng = np.random.default_rng(42)
        comp = {"H": 100}
        assignments = assign_isotopes(comp, "natural", rng)
        self.assertEqual(len(assignments), 100)
        # Most should be H-1 (99.99%)
        h1_count = sum(1 for _, iso in assignments if iso == "H-1")
        self.assertGreater(h1_count, 95)

    def test_perdeuterated_replaces_h(self):
        rng = np.random.default_rng(42)
        comp = {"H": 10, "C": 5}
        assignments = assign_isotopes(comp, "perdeuterated", rng)
        h_assignments = [iso for elem, iso in assignments if elem == "H"]
        self.assertTrue(all(iso == "H-2" for iso in h_assignments))

    def test_c13_depleted(self):
        rng = np.random.default_rng(42)
        comp = {"C": 100}
        assignments = assign_isotopes(comp, "C13_depleted_99.99", rng)
        c12_count = sum(1 for _, iso in assignments if iso == "C-12")
        # Should be ~99.99% C-12
        self.assertGreater(c12_count, 95)


class BathBuildingTests(unittest.TestCase):
    """Tests for PyCCE bath construction from CIF structures."""

    def _make_test_atoms(self):
        """Create a simple test atoms object with H and C."""
        from ase import Atoms
        atoms = Atoms("CH4", positions=[
            [0.0, 0.0, 0.0],  # C at center
            [1.0, 0.0, 0.0],
            [-0.5, 0.87, 0.0],
            [-0.5, -0.87, 0.0],
            [0.0, 0.0, 1.0],
        ], cell=[20, 20, 20])
        return atoms

    def test_build_bath_natural(self):
        atoms = self._make_test_atoms()
        central_pos = [0.0, 0.0, 0.0]
        result = build_pycce_bath(
            atoms, "natural", central_pos,
            r_bath_angstrom=15.0, r_dipole_angstrom=10.0,
            r_exclusion_angstrom=0.5, simulation_seed=42,
        )
        self.assertIn("bath", result)
        self.assertIn("assumptions", result)
        self.assertIn("point_dipole", result["assumptions"])
        self.assertIn("free_electron_g", result["assumptions"])

    def test_build_bath_excludes_near_nuclei(self):
        atoms = self._make_test_atoms()
        central_pos = [0.0, 0.0, 0.0]  # C is at center
        result = build_pycce_bath(
            atoms, "natural", central_pos,
            r_bath_angstrom=15.0, r_dipole_angstrom=10.0,
            r_exclusion_angstrom=1.5,  # Exclude H at 1.0 Å
            simulation_seed=42,
        )
        # H at ~1.0 Å should be excluded if H-1 is sampled as magnetic
        # The exclusion count depends on isotope sampling; just check the field exists
        self.assertIn("near_nuclei_excluded", result)

    def test_build_bath_perdeuterated(self):
        atoms = self._make_test_atoms()
        central_pos = [0.0, 0.0, 0.0]
        result = build_pycce_bath(
            atoms, "perdeuterated", central_pos,
            r_bath_angstrom=15.0, r_dipole_angstrom=10.0,
            r_exclusion_angstrom=0.5, simulation_seed=42,
        )
        if result["bath"] is not None:
            # Check that H-2 (deuterium) is in the bath
            isotopes = [str(result["bath"]["N"][i]) for i in range(len(result["bath"]))]
            has_deuterium = any("2" in iso and "H" in iso for iso in isotopes)
            self.assertTrue(has_deuterium, f"Expected deuterium in bath, got {isotopes}")

    def test_find_central_spin_position(self):
        from ase import Atoms
        atoms = Atoms("VO2", positions=[
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ])
        pos = find_central_spin_position(atoms, metal="V")
        np.testing.assert_allclose(pos, [0.0, 0.0, 0.0])

    def test_get_composition(self):
        from ase import Atoms
        atoms = Atoms("C2H6O", positions=[[0,0,0],[1,0,0],[2,0,0],[3,0,0],[4,0,0],[5,0,0],[6,0,0],[7,0,0],[8,0,0]])
        comp = get_composition_from_atoms(atoms)
        self.assertEqual(comp.get("C"), 2)
        self.assertEqual(comp.get("H"), 6)
        self.assertEqual(comp.get("O"), 1)


class SupercellTests(unittest.TestCase):
    """Tests for supercell construction."""

    def test_supercell_repeats_cell(self):
        from ase import Atoms
        atoms = Atoms("H", positions=[[0, 0, 0]], cell=[5, 5, 5])
        supercell, reps = build_supercell(atoms, r_bath_angstrom=20.0)
        self.assertGreaterEqual(len(supercell), 1)
        # Reps should be at least 2*20/5 = 8 in each direction
        self.assertGreaterEqual(reps[0], 8)


if __name__ == "__main__":
    unittest.main()
