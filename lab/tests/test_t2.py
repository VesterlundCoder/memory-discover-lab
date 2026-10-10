import json
import math
import tempfile
import unittest
from pathlib import Path
import numpy as np
from memorylab.t2assessment import calculate, first_crossing, build_database, assess_database
from memorylab.t2curves import fit_curve

BASE = Path(__file__).resolve().parents[1]


class DeterministicT2Tests(unittest.TestCase):
    def test_markov_population_factor_and_range(self):
        spec = json.loads((BASE/'examples/t2_markov_calculation.json').read_text())
        result = calculate(spec)
        self.assertAlmostEqual(result['T2_s'], .04)
        self.assertEqual(result['parameter_box']['completed_corner_evaluations'], 4)
        self.assertEqual(result['parameter_box']['T2_range_s'], [1/28, 1/22])
        spec['rate_definition'] = 'total_T2_reused_as_pure'
        with self.assertRaises(ValueError): calculate(spec)

    def test_exact_bath_analytic_free_induction_and_echo(self):
        for pulse in (0, 1):
            spec = json.loads((BASE/f'examples/t2_spin_bath_{pulse}pulse.json').read_text())
            result = calculate(spec)
            expected = np.abs(np.cos(np.pi*4000*np.asarray(spec['times_s']))) if pulse == 0 else np.ones(101)
            np.testing.assert_allclose(result['envelope'], expected, atol=1e-10)
            self.assertIsNone(result['T2_s'])
            if pulse == 0:
                self.assertTrue(result['operational_decay']['revival_detected'])
                self.assertEqual(result['operational_decay']['crossing_bracket_s'], [.00009, .0001])
            else: self.assertEqual(result['operational_decay']['no_sampled_crossing_up_to_s'], .001)

    def test_relaxation_not_double_counted(self):
        spec = json.loads((BASE/'examples/t2_spin_bath_1pulse.json').read_text())
        spec['independent_markov_rates'] = dict(rate_definition='population_and_independent_pure_dephasing',
            population_rate_s_inv=100, pure_dephasing_rate_s_inv=0, provenance=[{'kind':'test'}])
        result = calculate(spec)
        np.testing.assert_allclose(result['envelope'], np.exp(-50*np.asarray(spec['times_s'])), atol=1e-10)

    def test_invalid_grid_cannot_be_censoring_bound(self):
        with self.assertRaises(ValueError): first_crossing([.1,.2], [1,.9])
        with self.assertRaises(ValueError): first_crossing([0,1], [1,1.2])

    def test_reviewed_tables_and_unreviewed_units(self):
        with tempfile.TemporaryDirectory() as d:
            # Test the review gate with explicit synthetic observations, not a
            # private downloaded 201-row cache or a preceding workflow run.
            root = Path(d)/'inputs'; (root/'processed').mkdir(parents=True)
            rows = [{'id':f'synthetic:{i}', 'material_id':'synthetic',
                     'target_definition':'reported_T2_mixed_protocol', 'target_value':i+1,
                     'target_unit':'source_unspecified', 'features':{'temperature_K':10},
                     'provenance':[{'test_fixture':True}], 'evidence_kind':'hypothetical',
                     'review_status':'provisional', 'review_issues':['Synthetic unknown units']} for i in range(2)]
            (root/'source_lock.json').write_text(json.dumps({'artifacts':[]}))
            (root/'processed/molecular_rows.json').write_text(json.dumps(rows))
            db = Path(d)/'t2.sqlite'
            summary = build_database(root, BASE/'data/t2_references.json', db)
            self.assertEqual(summary['reviewed_references'],10)
            self.assertEqual(summary['provisional_observations'],2)
            query = json.loads((BASE/'examples/t2_reference_query.json').read_text())
            result = assess_database(db,query)
            self.assertEqual(result['status'],'reference_available')
            matched = [r for r in result['results'] if r['status']=='reported_conditions_match']
            self.assertAlmostEqual(matched[0]['applicable_reference_value_s'],.23)
            query['conditions']['temperature_K']=300
            self.assertEqual(assess_database(db,query)['status'],'no_applicable_reference')
            del query['conditions']['temperature_K']
            self.assertIn('insufficient_query_conditions', [r['status'] for r in assess_database(db,query)['results']])
            query=json.loads((BASE/'examples/t2_unknown_query.json').read_text())
            self.assertIsNone(assess_database(db,query)['predicted_new_material_T2_s'])

    def test_phase_count_control_recovers_known_time(self):
        curve=json.loads((BASE/'tests/fixtures/synthetic_phase_counts.json').read_text())
        result=fit_curve(curve,bootstrap=0)
        self.assertEqual(result['status'],'pass')
        self.assertLess(abs(result['identified_T2_s']/curve['synthetic_truth_T2_s']-1),.05)
        self.assertLess(result['heldout_standardized_rmse'],3)


if __name__=='__main__': unittest.main()
