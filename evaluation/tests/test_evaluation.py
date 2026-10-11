from pathlib import Path
import sys, tempfile, unittest, copy
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'evaluation'),str(ROOT/'lab')]
from wqeval.common import read,write,hash_file,new_output
from wqeval import reference,caseflow,ablation
from memorylab.models import evaluate
from memorylab.channels import choi
class EvaluationTests(unittest.TestCase):
    def test_independent_complex_liouvillian(self):
        p=read(ROOT/'lab/examples/atomic_ensemble_profile.json')
        p['detuning_Hz']=321;p['equilibrium_excited_population']=.7;p['rates']['population']['rate_s_inv']=20
        for a,d in zip(evaluate(p,[0,.0003,.01]),reference.evaluate(p,[0,.0003,.01])):
            np.testing.assert_allclose(choi(a.full_kraus()),d['choi'],atol=1e-10,rtol=0)
    def test_control_and_evidence_gate(self):
        base=ROOT/'evaluation/data/software_control';c=read(base/'case.json')
        with tempfile.TemporaryDirectory() as t:
            a=caseflow.run(c,Path(t)/'a',base)
            self.assertFalse(a['network_exported']);self.assertFalse(a['physical_validation_passed'])
            b=caseflow.run(c,Path(t)/'b',base,True)
            self.assertTrue(b['network_exported']);self.assertFalse(b['physical_validation_passed'])
    def test_mismatch_blocks_export(self):
        base=ROOT/'evaluation/data/software_control';c=read(base/'case.json')
        with tempfile.TemporaryDirectory() as t:
            p=read(base/'model.json');p['spin_bath']['nuclei'][0]['hyperfine_Hz'][2][2]=500
            path=Path(t)/'wrong.json';write(path,p);c['model']={'path':str(path),'sha256':hash_file(path)}
            r=caseflow.run(c,Path(t)/'r',base,True)
            self.assertEqual(r['status'],'model_curve_gate_fail');self.assertFalse(r['network_exported'])
    def test_integrity_and_condition_mismatch(self):
        base=ROOT/'evaluation/data/software_control';c=read(base/'case.json')
        with tempfile.TemporaryDirectory() as t:
            bad=copy.deepcopy(c);bad['curve']['sha256']='0'*64
            with self.assertRaises(ValueError):caseflow.run(bad,Path(t)/'hash',base)
            bad=copy.deepcopy(c);bad['conditions']['temperature_K']=77
            with self.assertRaises(ValueError):caseflow.run(bad,Path(t)/'temp',base)
    def test_pending_is_not_validation(self):
        with tempfile.TemporaryDirectory() as t:
            r=caseflow.run(read(ROOT/'evaluation/config/second_family_pending.json'),Path(t)/'r',ROOT)
            self.assertEqual(r['status'],'blocked_missing_reviewed_data');self.assertFalse(r['physical_validation_passed'])
    def test_constructed_faults(self):
        with tempfile.TemporaryDirectory() as t:
            r=ablation.run({'suite':'test'},Path(t)/'r')
            self.assertEqual(r['status'],'pass');self.assertEqual(r['blocked_cases'],7)
            self.assertEqual(r['unit_conversion_control']['converted_s'],.001)
    def test_strict_json_and_occupied_output(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'bad.json';p.write_text('{"x":NaN}')
            with self.assertRaises(ValueError):read(p)
            with self.assertRaises(ValueError):new_output(t)
if __name__=='__main__':unittest.main()
