import copy
import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'evaluation'),str(ROOT/'lab')]
from memorylab.channels import MemoryChannel,I2,apply
from memorylab.models import evaluate
from memorylab.protocol import readout_instrument,metrics
from memorylab.common import MissingData,UnsupportedPhysics
from memorylab.convergence_guard import require_material_convergence,profile_identity
from wqeval.common import read
from wqeval.protocol_validation import independent_instrument,audit_experiments
from wqeval.spin_convergence import synthetic_bath,spectral_coherence,split_operator_coherence
from memorylab.spin import exact_coherence
from wqeval.crosssim import external_trace,outcomes
CONFIG=ROOT/'evaluation/config/validation_extension'


class JointProtocolTests(unittest.TestCase):
    def setUp(self):self.detector=read(CONFIG/'protocol.json')['detector']
    def channel(self,eta):
        return MemoryChannel([I2],eta,{'storage_age_s':.01,'total_write_store_read_s':.01,'noise_budget':[]})
    def test_no_signal_background_is_not_signal_efficiency(self):
        d=dict(self.detector,base_rate_s_inv=5000)
        signal=self.channel(0);detected=readout_instrument(signal,d);m=metrics(signal,detected)
        self.assertEqual(m['signal_efficiency'],0)
        self.assertGreater(m['acceptance_probability'],0)
        self.assertAlmostEqual(m['conditional_detected_average_fidelity'],.5)
        self.assertAlmostEqual(m['unconditional_target_overlap'],.5*m['acceptance_probability'])
    def test_full_loss_has_no_conditional_fidelity(self):
        signal=self.channel(0);detected=readout_instrument(signal,self.detector)
        self.assertIsNone(metrics(signal,detected)['conditional_detected_average_fidelity'])
        np.testing.assert_array_equal(apply(detected.full_kraus(),np.diag([1.,0.])),np.diag([0.,0.,1.]))
    def test_full_signal_excludes_false_clicks(self):
        signal=self.channel(1);detected=readout_instrument(signal,dict(self.detector,base_rate_s_inv=1e10))
        self.assertEqual(metrics(signal,detected)['noise_click_probability'],0)
        self.assertAlmostEqual(detected.metrics()['conditional_average_fidelity'],1)
    def test_double_counting_and_unsupported_click_model_rejected(self):
        signal=self.channel(.5);signal.metadata['noise_budget']=['readout_background']
        with self.assertRaises(UnsupportedPhysics):readout_instrument(signal,self.detector)
        with self.assertRaises(UnsupportedPhysics):readout_instrument(self.channel(.5),dict(self.detector,event_model='double_click'))
    def test_photon_correlation_cannot_pass_full_protocol_audit(self):
        audit=audit_experiments(ROOT)
        self.assertEqual(audit['measured_time_points'],9)
        self.assertFalse(audit['joint_experimental_validation_passed'])
        self.assertTrue(all(r['qubit_fidelity'] is None for r in audit['observations']))


class ConvergenceTests(unittest.TestCase):
    def test_noncommuting_spectral_and_control_resolution(self):
        bath=synthetic_bath(2);times=np.linspace(0,.0004,11)
        for pulses in [0,1,4]:
            exact=exact_coherence(bath,times,4.2,pulses)
            np.testing.assert_allclose(spectral_coherence(bath,times,pulses),exact,atol=1e-12)
            coarse=max(abs(split_operator_coherence(bath,times,pulses,8)-exact))
            fine=max(abs(split_operator_coherence(bath,times,pulses,128)-exact))
            self.assertLess(fine,coarse/20)
    def test_material_request_blocked_without_evidence(self):
        p=read(ROOT/'lab/examples/defect_spin_profile.json');p['prediction_purpose']='material_prediction'
        with self.assertRaises(MissingData):evaluate(p,[0,.0001])
    def test_certificate_identity_and_window_are_enforced(self):
        p=read(ROOT/'lab/examples/defect_spin_profile.json');p['prediction_purpose']='material_prediction';p['evidence_kind']='computed'
        cert={'status':'pass','profile_sha256':profile_identity(p),'bath_size_converged':True,'cluster_order_converged':True,
              'pair_cutoff_converged':True,'control_resolution_converged':True,'time_grid_converged':True,
              'tolerance':.001,'maximum_error':1e-5,'independent_physical_model_review':True,'validated_storage_age_s':[0,.001]}
        p['convergence_certificate']=cert
        require_material_convergence(p,[0,.001])
        with self.assertRaises(MissingData):require_material_convergence(p,[.01])
        wrong=copy.deepcopy(p);wrong['spin_bath']['nuclei'][0]['hyperfine_Hz'][2][2]+=1
        with self.assertRaises(MissingData):require_material_convergence(wrong,[0,.001])
        wrong=copy.deepcopy(p);wrong['convergence_certificate']['cluster_order_converged']=False
        with self.assertRaises(MissingData):require_material_convergence(wrong)
    @unittest.skipUnless(importlib.util.find_spec('pycce'),'optional PyCCE not installed')
    def test_pycce_explicit_pairs_match_exact_and_are_not_ignored(self):
        from memorylab.backends import pycce_coherence
        bath=synthetic_bath(2);bath['order']=2;times=np.linspace(0,.0004,17)
        actual=pycce_coherence(bath,times,1,0)
        np.testing.assert_allclose(actual,exact_coherence(bath,times,4.2,1),atol=1e-8)
        changed=copy.deepcopy(bath);changed['pairs'][0]['coupling_Hz']=(np.diag([1,1,-2])*1000).tolist()
        altered=pycce_coherence(changed,times,1,0)
        self.assertGreater(max(abs(altered-actual)),.001)
        wrong=copy.deepcopy(bath);wrong['nuclei'][0]['zeeman_vector_Hz'][2]*=-1
        with self.assertRaises(UnsupportedPhysics):pycce_coherence(wrong,times,1,0)


class PairedTraceTests(unittest.TestCase):
    def test_reproducible_independent_streams_and_full_loss(self):
        config=read(CONFIG/'crosssim_pilot.json')
        a,seeds=external_trace(config,1101);b,again=external_trace(config,1101)
        np.testing.assert_array_equal(a,b);self.assertEqual(seeds,again)
        self.assertEqual(len(set(seeds.values())),3)
        self.assertFalse(np.array_equal(a[:,0],a[:,1]))
        signal=MemoryChannel([I2],0,{});accepted=MemoryChannel([I2],0,{})
        self.assertTrue(all(left==right=='loss' for h,left,right in outcomes(a,1,signal,accepted)))
    @unittest.skipUnless(importlib.util.find_spec('qunetsim') and importlib.util.find_spec('qutip'),'optional QuNetSim/QuTiP not installed')
    def test_custom_backend_preserves_nonadjacent_joint_state_and_consumes_qubits(self):
        from memorylab.qunetsim_adapter import DensityBackend
        from types import SimpleNamespace
        backend=DensityBackend()
        q=[SimpleNamespace(qubit=backend.create_qubit('A')) for _ in range(3)]
        backend.H(q[0]);backend.cnot(q[0],q[1]);backend.cnot(q[1],q[2])
        pe=.7;down=np.array([[0,1],[0,0]],complex);rho=backend.joint_state(q)
        # Independent generalized amplitude damping Kraus map on the middle key.
        from memorylab.channels import thermal_amplitude_damping
        ks=thermal_amplitude_damping(.1,3,pe)
        local=np.zeros((4,4),complex)
        for a,b in np.ndindex(2,2):
            e=np.zeros((2,2));e[a,b]=1;local[:,a+2*b]=apply(ks,e).reshape(-1,order='F')
        backend.apply_superoperator(q[1],local)
        expected=apply([np.kron(np.kron(I2,k),I2) for k in ks],rho)
        np.testing.assert_allclose(backend.joint_state(q),expected,atol=1e-12)
        reverse=expected.reshape([2]*6).transpose(2,1,0,5,4,3).reshape(8,8)
        np.testing.assert_allclose(backend.joint_state(q[::-1]),reverse,atol=1e-12)
        for qubit in q:backend.release(qubit)
        self.assertEqual(backend.groups,{})


if __name__=='__main__':unittest.main()
