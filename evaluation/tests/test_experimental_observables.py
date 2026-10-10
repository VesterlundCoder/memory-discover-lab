import copy
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from scipy.linalg import expm
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'evaluation'), str(ROOT/'lab')]
from wqeval.common import read
from wqeval import experimental_observables as obs
BASE = ROOT/'evaluation/data/bradley2022_nv0'


class ExperimentalObservableTests(unittest.TestCase):
    def test_real_case_preserves_fail_and_export_block(self):
        with tempfile.TemporaryDirectory() as t:
            r = obs.run(read(BASE/'case.json'), Path(t)/'result', BASE)
            self.assertEqual(r['measured_points'], 24)
            self.assertEqual(r['heldout_points'], 10)
            self.assertTrue(r['metrics']['equatorial_length']['gate_passed'])
            self.assertFalse(r['metrics']['X']['gate_passed'])
            self.assertFalse(r['heldout_observable_gate_passed'])
            self.assertFalse(r['physical_validation_passed'])
            self.assertFalse(r['network_exported'])

    def test_channel_against_density_matrix_hamiltonian(self):
        # Independent matrix exponentiation + analytic off-diagonal damping.
        tau, beta, f = .055, 1.36, 79.8
        rho = np.array([[.4, .2+.13j], [.2-.13j, .6]])
        for t in [0, .001, .1, 1]:
            ks = obs.effective_kraus(t, tau, beta, f)
            np.testing.assert_allclose(sum(k.conj().T@k for k in ks), np.eye(2), atol=1e-14)
            u = expm(-2j*np.pi*t*np.diag([f/2, -f/2]))
            expected = u@rho@u.conj().T
            expected[0, 1] *= np.exp(-(t/tau)**beta)
            expected[1, 0] *= np.exp(-(t/tau)**beta)
            actual = sum(k@rho@k.conj().T for k in ks)
            np.testing.assert_allclose(actual, expected, atol=1e-14)
            self.assertGreaterEqual(np.linalg.eigvalsh(actual).min(), -1e-14)

    def test_heldout_values_cannot_influence_calibration(self):
        c = read(BASE/'case.json'); blocks, _ = obs.load_case(c, BASE)
        masks = [obs.split_mask(b[0], cutoff) for b, cutoff in zip(blocks, [.0803, .00618])]
        p, _ = obs.fit_envelope(blocks[0], masks[0], c['fit'])
        original = obs.fit_ramsey(blocks[1], masks[1], p, 79.8)[1]
        altered = [(t.copy(), y.copy(), e.copy()) for t, y, e in blocks]
        for b, m in zip(altered, masks):
            b[1][~m] += 1000
        p2, _ = obs.fit_envelope(altered[0], masks[0], c['fit'])
        changed = obs.fit_ramsey(altered[1], masks[1], p2, 79.8)[1]
        np.testing.assert_array_equal(p, p2)
        np.testing.assert_array_equal(original, changed)

    def test_integrity_conditions_and_false_evidence_rejected(self):
        c = read(BASE/'case.json')
        for kind in ('hash', 'conditions', 'export', 'population'):
            bad = copy.deepcopy(c)
            if kind == 'hash': bad['source_data']['sha256'] = '0'*64
            if kind == 'conditions': bad['conditions']['temperature_K'] = 300
            if kind == 'export': bad['network_export_allowed'] = True
            if kind == 'population': bad['review']['population_relaxation_separated'] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                obs.load_case(bad, BASE)

    def test_counts_guard(self):
        c = read(BASE/'case.json'); c['split']['envelope_calibration_max_s'] = .0903
        with tempfile.TemporaryDirectory() as t, self.assertRaises(ValueError):
            obs.run(c, Path(t)/'result', BASE)


if __name__ == '__main__':
    unittest.main()
