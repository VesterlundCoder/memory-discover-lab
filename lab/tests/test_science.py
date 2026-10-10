"""Meaningful channel/solver conformance tests. These are not material-discovery results."""
import copy
import importlib.util
import math
import tempfile
import unittest
from pathlib import Path
import numpy as np
from memorylab.channels import (I2, X, MemoryChannel, apply, check_cptp, choi, compose,
                                dephasing, depolarizing, thermal_amplitude_damping)
from memorylab.common import read_json, MissingData, NumericalFailure, UnsupportedPhysics
from memorylab.models import evaluate, rate
from memorylab.spin import exact_coherence, operators
from memorylab.network import MemoryDevice, link_benchmark
from memorylab.calibration import fit_exponential, compare_baseline

ROOT = Path(__file__).resolve().parent.parent


def clean_profile():
    p = read_json(ROOT/"examples/trapped_atom_ion_profile.json")
    for key in ("write_duration_s", "read_duration_s", "write_depolarizing_p", "read_depolarizing_p"):
        p["io"][key] = 0
    p["io"]["eta_write"] = p["io"]["eta_read"] = 1
    p["rates"]["population"].update(kind="constant", rate_s_inv=0.1)
    p["rates"]["pure_dephasing"].update(kind="constant", rate_s_inv=0.2)
    p["rates"]["erasure"]["rate_s_inv"] = 0
    return p


class ChannelTests(unittest.TestCase):
    def test_identity_metrics(self):
        ch = MemoryChannel([I2], 1, {})
        self.assertAlmostEqual(ch.metrics()["conditional_average_fidelity"], 1)
        self.assertAlmostEqual(ch.metrics()["conditional_entanglement_fidelity"], 1)
        check_cptp(ch.full_kraus())

    def test_markov_analytical_limits(self):
        p = clean_profile()
        for t, ch in zip([0, 0.001, 1, 1000], evaluate(p, [0, 0.001, 1, 1000])):
            a, b = math.exp(-0.25*t), math.exp(-0.1*t)
            self.assertAlmostEqual(ch.metrics()["conditional_average_fidelity"], (3+2*a+b)/6, places=10)
            self.assertAlmostEqual(ch.metrics()["conditional_entanglement_fidelity"], (1+2*a+b)/4, places=10)
            check_cptp(ch.full_kraus())

    def test_full_erasure_preserves_trace(self):
        channel = MemoryChannel([I2], 0, {})
        rho = np.outer([1, 1], [1, 1])/2
        result = apply(channel.full_kraus(), rho)
        np.testing.assert_allclose(result, np.diag([0, 0, 1]))
        check_cptp(channel.full_kraus())
        self.assertEqual(channel.metrics()["unconditional_target_overlap"], 0)
        self.assertIsNone(channel.metrics()["conditional_average_fidelity"])

    def test_loss_and_population_relaxation_are_distinct(self):
        channel = MemoryChannel(thermal_amplitude_damping(100, 1), 1, {})
        rho = apply(channel.full_kraus(), np.diag([0, 1]))
        self.assertAlmostEqual(rho[0, 0].real, 1)
        self.assertAlmostEqual(rho[2, 2].real, 0)

    def test_choi_trace_and_rectangular_dimensions(self):
        ch = MemoryChannel(depolarizing(0.3), 0.4, {})
        self.assertEqual(choi(ch.full_kraus()).shape, (6, 6))
        self.assertAlmostEqual(np.trace(choi(ch.full_kraus())).real, 2)
        self.assertEqual(check_cptp(ch.full_kraus())["output_dimension"], 3)

    def test_complex_coherence_phase(self):
        rho = np.outer([1, 1], [1, 1])/2
        value = 0.4+0.3j
        self.assertAlmostEqual(apply(dephasing(value), rho)[0, 1], value/2)

    def test_invalid_coherence_is_not_clipped(self):
        with self.assertRaises(NumericalFailure):
            dephasing(1.1)

    def test_thermal_equilibrium(self):
        result = apply(thermal_amplitude_damping(1000, 1, 0.3), np.diag([1, 0]))
        np.testing.assert_allclose(result, np.diag([0.7, 0.3]), atol=1e-13)

    def test_noncommuting_channel_order(self):
        damping = thermal_amplitude_damping(1, 1)
        first = apply(compose(damping, [X]), np.diag([1, 0]))
        second = apply(compose([X], damping), np.diag([1, 0]))
        self.assertGreater(np.linalg.norm(first-second), 0.5)

    def test_stage_errors_enter_full_fidelity(self):
        p = clean_profile()
        p["io"]["write_depolarizing_p"] = 0.2
        self.assertAlmostEqual(evaluate(p, [0])[0].metrics()["conditional_average_fidelity"], 0.9)

    def test_depolarization_convention(self):
        np.testing.assert_allclose(apply(depolarizing(1), np.diag([1, 0])), np.eye(2)/2)

    def test_serialization_roundtrip(self):
        channel = evaluate(clean_profile(), [1])[0]
        restored = MemoryChannel.from_serialized(channel.serialize())
        np.testing.assert_allclose(choi(restored.full_kraus()), choi(channel.full_kraus()), atol=1e-13)

    def test_all_family_scenarios_are_cptp(self):
        for model in read_json(ROOT/"examples/study.json")["models"]:
            for channel in evaluate(model["profile"], [0, 0.001, 0.1]):
                check_cptp(channel.full_kraus())
                self.assertFalse(channel.serialize()["validated_for_hardware"])

    def test_temperature_extrapolation_rejected(self):
        p = clean_profile()
        p["temperatures_K"]["storage"] = 500
        with self.assertRaises(MissingData):
            evaluate(p, [1])

    def test_thermal_ramp_not_ignored(self):
        p = clean_profile()
        p["io"]["thermal_transition_s"] = 1
        with self.assertRaises(UnsupportedPhysics):
            evaluate(p, [1])

    def test_orbach_zero_temperature_limit(self):
        spec = {"kind": "phenomenological_temperature", "base_s_inv": 1,
                "orbach_s_inv": 10, "orbach_gap_K": 20, "valid_temperature_K": [0, 300]}
        self.assertEqual(rate(spec, 0), 1)
        self.assertGreater(rate(spec, 10), 1)

    def test_activity_decoherence_is_included(self):
        p = clean_profile()
        original = evaluate(p, [1])[0].metrics()
        p["network_activity"] = {"attempt_rate_Hz": 1000, "coherence_loss_per_attempt": 0.01}
        noisy = evaluate(p, [1])[0].metrics()
        self.assertLess(noisy["conditional_average_fidelity"], original["conditional_average_fidelity"])
        self.assertEqual(noisy["retrieval_success_probability"], original["retrieval_success_probability"])

    def test_negative_ion_overlap_limits(self):
        p = clean_profile()
        p.update(family="negative_ion", candidate={"charge_e": -1},
                 optical_process="photodetachment", electron_record_overlap=[0, 0])
        self.assertAlmostEqual(evaluate(p, [0])[0].metrics()["conditional_average_fidelity"], 2/3)
        p["electron_record_overlap"] = [1, 0]
        self.assertAlmostEqual(evaluate(p, [0])[0].metrics()["conditional_average_fidelity"], 1)


class SpinTests(unittest.TestCase):
    def test_spin_commutator(self):
        for spin in (0.5, 1, 1.5):
            sx, sy, sz = operators(spin)
            np.testing.assert_allclose(sx@sy-sy@sx, 1j*sz, atol=1e-13)

    def test_fid_matches_single_nucleus_solution(self):
        bath = read_json(ROOT/"examples/molecular_spin_profile.json")["spin_bath"]
        bath["nuclei"][0]["zeeman_vector_Hz"] = [0, 0, 0]
        times = np.linspace(0, 0.0005, 11)
        result = exact_coherence(bath, times, 4.2, 0)
        np.testing.assert_allclose(result, np.cos(np.pi*4000*times), atol=1e-12)

    def test_hahn_cancels_commuting_static_bath(self):
        bath = read_json(ROOT/"examples/molecular_spin_profile.json")["spin_bath"]
        result = exact_coherence(bath, [0, 0.0001, 0.001, 0.01], 4.2, 1)
        np.testing.assert_allclose(result, 1, atol=1e-10)

    def test_dimension_bound(self):
        bath = read_json(ROOT/"examples/molecular_spin_profile.json")["spin_bath"]
        bath["max_dimension"] = 1
        with self.assertRaises(UnsupportedPhysics):
            exact_coherence(bath, [1], 4.2)

    def test_nonexponential_table_revival_retained(self):
        p = clean_profile()
        p.update(storage_model="coherence_table", additional_dephasing_independent_of_markov=True,
            coherence_table={"times_s": [0, 1, 2], "real": [1, 0, 1], "imag": [0, 0, 0],
                             "temperature_K": 4.2, "control": {}, "includes_population_relaxation": False})
        p["rates"]["population"]["rate_s_inv"] = 0
        p["rates"]["pure_dephasing"]["rate_s_inv"] = 0
        values = [c.metrics()["conditional_average_fidelity"] for c in evaluate(p, [0, 1, 2])]
        np.testing.assert_allclose(values, [1, 2/3, 1])

    def test_table_total_T2_not_double_counted(self):
        p = clean_profile()
        p.update(storage_model="coherence_table", additional_dephasing_independent_of_markov=True,
                 coherence_table={"includes_population_relaxation": True})
        with self.assertRaises(UnsupportedPhysics):
            evaluate(p, [0])

    def test_table_extrapolation_rejected(self):
        p = clean_profile()
        p.update(storage_model="coherence_table", additional_dephasing_independent_of_markov=True,
            coherence_table={"times_s": [0, 1], "real": [1, 0], "imag": [0, 0],
                             "temperature_K": 4.2, "control": {}, "includes_population_relaxation": False})
        with self.assertRaises(MissingData):
            evaluate(p, [2])


class NetworkTests(unittest.TestCase):
    def test_bell_state_dephasing_is_not_single_qubit_fidelity(self):
        p = clean_profile()
        p["rates"]["population"]["rate_s_inv"] = 0
        channel = evaluate(p, [1])[0]
        device = MemoryDevice([channel], allow_hypothetical=True)
        workload = {"attempts": 1000, "link_herald_probability": 1, "attempt_interval_s": 1,
                    "storage_age_s": 1, "minimum_Bell_fidelity": 0}
        result = link_benchmark(device, device, workload, 8)
        self.assertAlmostEqual(result["conditional_Bell_fidelity"], (1+math.exp(-0.4))/2)
        self.assertNotAlmostEqual(result["conditional_Bell_fidelity"], channel.metrics()["conditional_average_fidelity"])

    def test_unmeasured_network_use_requires_opt_in(self):
        with self.assertRaises(MissingData):
            MemoryDevice(evaluate(clean_profile(), [0]))

    def test_memory_preserves_entangled_joint_state(self):
        p = clean_profile()
        p["rates"]["population"]["rate_s_inv"] = 0
        p["rates"]["pure_dephasing"]["rate_s_inv"] = 0
        device = MemoryDevice(evaluate(p, [1]), allow_hypothetical=True)
        bell = np.array([1, 0, 0, 1])/math.sqrt(2)
        rho = np.outer(bell, bell)
        output = device.retrieve(rho, 1, np.random.default_rng(1), subsystem=0)
        self.assertTrue(output["success"])
        np.testing.assert_allclose(output["density_matrix"], rho, atol=1e-13)

    def test_missing_age_rejected(self):
        device = MemoryDevice(evaluate(clean_profile(), [0, 1]), allow_hypothetical=True)
        with self.assertRaises(MissingData):
            device.channel_at(0.5)


class CalibrationTests(unittest.TestCase):
    def test_recovers_known_pure_phase_rate(self):
        times = np.linspace(0, 2, 30).tolist()
        result = fit_exponential(times, np.exp(-0.8*np.array(times)).tolist(),
                                 [0.01]*len(times), {"storage_temperature_K": 4.2}, [{"fixture": True}])
        self.assertAlmostEqual(result["rate_s_inv"], 0.8, places=9)
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["does_not_validate_photonic_write_read"])

    def test_resolved_revival_not_fitted_to_T2(self):
        with self.assertRaises(ValueError):
            fit_exponential([0, 1, 2, 3, 4], [1, 0.8, 0.2, 0.9, 0.3], [0.01]*5,
                            {"T": 4.2}, [{"fixture": True}])

    def test_spin_T2_cannot_validate_full_channel(self):
        p = clean_profile()
        b = {"id": "fixture", "evidence_kind": "experimental", "provenance": [{"test_fixture": True}],
             "temperatures_K": p["temperatures_K"], "protocol": p["io"]["protocol"],
             "points": [{"storage_age_s": 1, "quantity": "reported_T2", "value": 0.9, "standard_error": 0.01}]}
        with self.assertRaises(MissingData):
            compare_baseline(p, b)


@unittest.skipUnless(importlib.util.find_spec("qutip"), "optional QuTiP not installed")
class QuTiPTests(unittest.TestCase):
    def test_analytic_vs_qutip_full_channel(self):
        p = clean_profile()
        p["equilibrium_excited_population"] = 0.27
        p["detuning_Hz"] = 2.7
        p["io"]["write_depolarizing_p"] = 0.02
        p["io"]["read_depolarizing_p"] = 0.06
        for a, b in zip(evaluate(p, [0, 0.01, 1]), evaluate(p, [0, 0.01, 1], "qutip")):
            np.testing.assert_allclose(choi(a.full_kraus()), choi(b.full_kraus()), atol=1e-10)


@unittest.skipUnless(importlib.util.find_spec("pyscf"), "optional PySCF not installed")
class PySCFTests(unittest.TestCase):
    def test_h2_energy_and_cache(self):
        from memorylab.backends import electronic
        candidate = read_json(ROOT/"examples/h2_candidate.json")
        recipe = read_json(ROOT/"examples/pyscf_recipe.json")
        with tempfile.TemporaryDirectory() as cache:
            result = electronic(candidate, recipe, cache)
            self.assertAlmostEqual(result["energy_hartree"], -1.1167593074, places=8)
            self.assertTrue(result["converged"])
            self.assertGreater(result["tda_excitation_energy_hartree"][0], 0)
            self.assertIsNone(result["T2_s"])
            self.assertTrue(electronic(candidate, recipe, cache)["cache_hit"])
            recipe["conv_tol"] = 1e-9
            self.assertFalse(electronic(candidate, recipe, cache)["cache_hit"])


@unittest.skipUnless(importlib.util.find_spec("pycce"), "optional PyCCE not installed")
class PyCCETests(unittest.TestCase):
    def test_pycce_single_spin_against_exact_commuting_bath(self):
        from memorylab.backends import pycce_coherence
        bath = read_json(ROOT/"examples/pycce_profile.json")["spin_bath"]
        times = [0, 0.00005, 0.0001]
        coherence = pycce_coherence(bath, times, 0, 5)
        np.testing.assert_allclose(coherence.real, np.cos(np.pi*4000*np.array(times)), atol=1e-8)
        echo = pycce_coherence(bath, times, 1, 5)
        np.testing.assert_allclose(echo, 1, atol=1e-8)


@unittest.skipUnless(importlib.util.find_spec("maxwellbloch"), "optional MaxwellBloch not installed")
class MaxwellBlochTests(unittest.TestCase):
    def test_zero_medium_preserves_input_field(self):
        from memorylab.backends import maxwell_bloch
        config = read_json(ROOT/"examples/lambda_eit.json")
        config["interaction_strengths"] = [0, 0]
        config["z_steps"], config["t_steps"] = 2, 20
        with tempfile.TemporaryDirectory() as directory:
            result = maxwell_bloch(config, directory)
            data = np.load(result["output"])
            fields = data["fields"]
            for field in fields:
                np.testing.assert_allclose(field[0], field[-1], atol=1e-10)
            self.assertIsNone(result["qubit_fidelity"])
