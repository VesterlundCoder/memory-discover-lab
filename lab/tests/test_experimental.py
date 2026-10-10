"""Scientific scope, held-out data, source layout and real simulator checks."""
import copy
import tempfile
import unittest
from pathlib import Path
import numpy as np
from memorylab.channels import MemoryChannel, X, apply, choi, depolarizing, thermal_amplitude_damping
from memorylab.common import MissingData
from memorylab.models import evaluate
from memorylab.experimental import parse_indexed_infidelity, interval_sigma, spatial_holdout
from memorylab.sequence_adapter import apply_to_manager, run_link, seconds_to_ps
from memorylab.network import MemoryDevice


def point_profile():
    return {"family": "rare_earth_solid", "storage_model": "measured_operating_point",
            "evidence_kind": "fit_to_experiment", "provenance": [{"test_fixture": True}],
            "temperatures_K": {"write": 3, "storage": 3, "read": 3},
            "io": {"protocol": "AFC_spin_wave_path_qubit", "read_duration_s": 0},
            "point": {"temperature_K": 3, "end_to_end_age_s": 18e-6,
                      "conditional_average_fidelity": .967, "signal_retrieval_probability": .014,
                      "spin_storage_s": 8e-6, "afc_rephasing_s": 10e-6,
                      "loss_scope": "test fixture"}}


class ExperimentalScopeTests(unittest.TestCase):
    def test_rejects_time_and_temperature_extrapolation(self):
        p = point_profile()
        for grid in ([0], [8e-6], [18e-6, 1.0]):
            with self.assertRaises(MissingData):
                evaluate(p, grid)
        p["temperatures_K"]["read"] = 4
        with self.assertRaises(MissingData):
            evaluate(p, [18e-6])

    def test_finite_point_does_not_invent_t2(self):
        ch = evaluate(point_profile(), [18e-6])[0]
        self.assertIsNone(ch.metadata["T2_s"])
        self.assertAlmostEqual(ch.metrics()["conditional_average_fidelity"], .967)
        self.assertAlmostEqual(ch.metrics()["retrieval_success_probability"], .014)

    def test_point_qutip_choi_and_bell_match(self):
        a, b = [evaluate(point_profile(), [18e-6], backend)[0] for backend in ("analytic", "qutip")]
        np.testing.assert_allclose(choi(a.full_kraus()), choi(b.full_kraus()), atol=1e-12)
        self.assertAlmostEqual(a.metrics()["conditional_entanglement_fidelity"], (3*.967-1)/2)

    def test_mc_sigma_recovers_width_even_if_point_not_mc_mean(self):
        s = interval_sigma([.95], [.93], [.96])
        self.assertAlmostEqual(s[0], .015)

    def test_held_out_values_do_not_change_fitted_parameter(self):
        v = np.full(10, .92)
        a = spatial_holdout(v, v-.01, v+.01)
        v[1::2] = .7
        b = spatial_holdout(v, v-.01, v+.01)
        self.assertEqual(a["fitted_average_fidelity"], b["fitted_average_fidelity"])
        self.assertEqual(b["status"], "model_mismatch")

    def test_rejects_duplicate_and_missing_source_states(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"indexed.csv"
            a = np.array([[.1, .2, .3, .4], [0, 0, 1, 1], [0, 1, 0, 1]])
            np.savetxt(p, a, delimiter=";")
            parsed = parse_indexed_infidelity(p, 2, ["X", "Y"], "basis,cell")
            np.testing.assert_allclose(parsed, [[.9, .8], [.7, .6]])
            a[2] += 1
            np.savetxt(p, a, delimiter=";")
            np.testing.assert_allclose(parse_indexed_infidelity(p, 2, ["X", "Y"], "basis,cell", 1), parsed)
            a[2] -= 1
            a[1, -1] = 0
            a[2, -1] = 0
            np.savetxt(p, a, delimiter=";")
            with self.assertRaises(ValueError):
                parse_indexed_infidelity(p, 2, ["X", "Y"], "basis,cell")


class SequenceIntegrationTests(unittest.TestCase):
    def test_nonunital_channel_on_entangled_middle_key_preserves_joint_state(self):
        from sequence.kernel.quantum_manager import QuantumManagerDensity
        manager = QuantumManagerDensity()
        keys = [manager.new() for _ in range(3)]
        ket = np.zeros(8, complex); ket[[0, 7]] = 1/np.sqrt(2)
        rho = np.outer(ket, ket.conj())
        manager.set(keys, rho)
        ch = MemoryChannel(thermal_amplitude_damping(1, .3), .2, {})
        expected = apply([np.kron(np.eye(2), np.kron(k, np.eye(2))) for k in ch.conditional_kraus], rho)
        actual = apply_to_manager(manager, keys[1], ch)
        np.testing.assert_allclose(actual, expected, atol=1e-12)
        self.assertEqual(manager.get(keys[0]).keys, keys)
        self.assertIs(manager.get(keys[0]), manager.get(keys[2]))
        self.assertAlmostEqual(np.trace(actual).real, 1)

    def test_real_event_workload_preserves_identity_and_repeats_seed(self):
        ch = evaluate(point_profile(), [18e-6])[0]
        ch.success_probability = .8
        device = MemoryDevice([ch])
        workload = {"attempts": 100, "attempt_interval_s": .001, "storage_age_s": 18e-6,
                    "link_herald_probability": .6, "minimum_Bell_fidelity": .5}
        a, b = [run_link(device, device, workload, 14) for _ in range(2)]
        self.assertEqual(a, b)
        self.assertGreater(a["retrieved_pairs"], 0)
        self.assertEqual(a["events_executed"], 100+a["heralded"])
        self.assertLess(a["max_density_error_against_analytic"], 1e-12)
        self.assertAlmostEqual(a["expected_success_probability"], .6*.8*.8)

    def test_picosecond_conversion_does_not_round_unrepresentable_times(self):
        self.assertEqual(seconds_to_ps(18e-6), 18_000_000)
        with self.assertRaises(ValueError):
            seconds_to_ps(1.3e-12)


if __name__ == "__main__":
    unittest.main()
