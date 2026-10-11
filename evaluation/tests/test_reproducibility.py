"""Regression checks for clean-clone input, comparison and reporting failures."""
import copy,json,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'evaluation'),str(ROOT/'lab')]
from wqeval import datasets
from wqeval.verification import compare,numeric_compare,channel_projection
from memorylab.channels import MemoryChannel,depolarizing,encode,decode
import numpy as np
from memorylab.bundled import install_group
class ReproducibilityTests(unittest.TestCase):
    def bundle(self,root):
        (root/'evaluation/data').mkdir(parents=True)
        shutil.copyfile(ROOT/'evaluation/data/teller_sources.json',root/'evaluation/data/teller_sources.json')
        shutil.copytree(ROOT/'data/experimental',root/'data/experimental')
    def test_offline_pinned_sources_without_legacy_cache_or_network(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.bundle(root)
            with patch.object(datasets,'ROOT',root),patch.object(datasets,'LAB',root/'lab'),patch('urllib.request.urlopen',side_effect=AssertionError('Network forbidden')):
                manifest,cache=datasets.ensure_teller(offline=True)
                for name,item in manifest['artifacts'].items():self.assertEqual(datasets.hash_file(cache/name),item['sha256'])
    def test_corrupt_bundled_source_is_not_replaced_online(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.bundle(root);(root/'data/experimental/teller2025/4.csv').write_bytes(b'corrupt')
            with patch.object(datasets,'ROOT',root),patch.object(datasets,'LAB',root/'lab'),patch('urllib.request.urlopen',side_effect=AssertionError('Network forbidden')):
                with self.assertRaisesRegex(ValueError,'source changed'):datasets.ensure_teller(offline=True)
    def test_group_validation_precedes_cache_writes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.bundle(root);(root/'data/experimental/teller2025/8a.csv').unlink()
            with self.assertRaisesRegex(ValueError,'input missing'):install_group(root/'data/experimental','teller2025',root/'cache')
            self.assertFalse((root/'cache').exists())
    def paired_step3(self,root):
        source=ROOT/'evaluation/results/step3-confirmation'
        for name in ['a','b']:shutil.copytree(source,root/name)
        summary=json.loads((root/'b/summary.json').read_text());summary['identity']['at_utc']='different execution';summary['identity']['environment']={'different':'host'}
        (root/'b/summary.json').write_text(json.dumps(summary));return root/'a',root/'b'
    def test_comparison_ignores_execution_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=self.paired_step3(Path(d));self.assertEqual(compare(a,b,True)['status'],'pass')
    def test_comparison_rejects_scientific_change(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=self.paired_step3(Path(d));s=json.loads((b/'summary.json').read_text());s['unit_conversion_control']['density_matrix_max_error']+=.1;(b/'summary.json').write_text(json.dumps(s))
            with self.assertRaisesRegex(ValueError,'Numeric mismatch'):compare(a,b)
    def test_source_mismatch_reported_and_strict_mode_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=self.paired_step3(Path(d));s=json.loads((b/'summary.json').read_text());s['identity']['lab_source_sha256']='different';(b/'summary.json').write_text(json.dumps(s))
            self.assertFalse(compare(a,b)['source_fingerprints']['lab_source_sha256']['matches'])
            with self.assertRaisesRegex(ValueError,'fingerprint mismatch'):compare(a,b,True)
    def test_nested_channel_change_not_discarded(self):
        with self.assertRaises(ValueError):numeric_compare({'channels':[[1.,0.]]},{'channels':[[1.,.01]]})
    def test_kraus_unitary_gauge_preserves_channel_comparison(self):
        a=MemoryChannel(depolarizing(.1),.7,{}).serialize();b=copy.deepcopy(a)
        # Hadamard mix of operators plus complex global phases, preserving map.
        for key in ['kraus','conditional_kraus']:
            operators=[decode(k) for k in b[key]]
            operators[:2]=[(operators[0]+operators[1])/np.sqrt(2),(operators[0]-operators[1])/np.sqrt(2)]
            b[key]=[encode(k*np.exp(1j*(i+.3))) for i,k in enumerate(operators)]
        numeric_compare(channel_projection(a),channel_projection(b))
    def test_changed_conditional_map_is_rejected_with_identical_metrics(self):
        a=MemoryChannel(depolarizing(.1),.7,{}).serialize();b=copy.deepcopy(a)
        b['conditional_kraus']=MemoryChannel(depolarizing(.2),.7,{}).serialize()['conditional_kraus']
        with self.assertRaisesRegex(ValueError,'Numeric mismatch'):numeric_compare(channel_projection(a),channel_projection(b))
    def test_changed_full_operators_cannot_hide_behind_stored_choi(self):
        a=MemoryChannel(depolarizing(.1),.7,{}).serialize()
        a['kraus'][0]['real'][0][0]+=.01
        with self.assertRaisesRegex(ValueError,'exported_choi_consistency'):channel_projection(a)
    def test_missing_figure_inputs_preserve_existing_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);out=root/'figures';out.mkdir();(out/'architecture.pdf').write_bytes(b'untouched')
            run=subprocess.run([sys.executable,str(ROOT/'scripts/make_figures.py'),'--inputs',str(root/'missing'),'--out',str(out)],capture_output=True,text=True)
            self.assertEqual(run.returncode,2);self.assertIn('No figure was written',run.stderr)
            self.assertEqual((out/'architecture.pdf').read_bytes(),b'untouched')
if __name__=='__main__':unittest.main()
