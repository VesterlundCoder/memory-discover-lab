import json
import math
import tempfile
import unittest
from pathlib import Path
from lab import (demo, evolve_bloch, export_profile, init_inventory, metrics,
                 photodetachment_overlap_fidelity, screen, stable_seed, validate_profile,
                 usable_horizon)

class PhysicsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"profile.json"
        self.p = demo(self.path)

    def test_identity_and_erasure_separation(self):
        m = metrics(self.p, 0)
        self.assertEqual(m["conditional_storage_average_fidelity"], 1)
        self.assertAlmostEqual(m["retrieval_success_probability"], .56)

    def test_six_state_average_matches_formula(self):
        states = [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
        fs = []
        for r in states:
            out = evolve_bloch(r, 12, 100, 10)
            fs.append((1+sum(a*b for a,b in zip(r,out)))/2)
        m = metrics(self.p, 12)
        self.assertAlmostEqual(sum(fs)/6, m["conditional_storage_average_fidelity"])
        self.assertAlmostEqual(m["conditional_storage_average_fidelity"],
                               (2*m["conditional_storage_entanglement_fidelity"]+1)/3)

    def test_amplitude_damping_special_cases(self):
        self.assertEqual(evolve_bloch((0,0,1), 4, 2, 4), (0,0,1))
        out = evolve_bloch((0,0,-1), 4, 2, 4)
        self.assertAlmostEqual(out[2], 1-2*math.exp(-2))

    def test_physical_bloch_ball(self):
        for T1,T2 in [(1,2),(1,1),(100,.1)]:
            for t in [0,.01,1,1000]:
                for r in [(1,0,0),(0,1,0),(0,0,-1),(.3,.4,.5)]:
                    out = evolve_bloch(r,t,T1,T2)
                    self.assertLessEqual(sum(v*v for v in out),1+1e-12)

    def test_invalid_markov_and_unknown_parameters(self):
        for key,value in [("T2_s",201),("T1_s",None),("eta_read",1.1),("retention_s",0)]:
            p = dict(self.p); p[key] = value
            with self.assertRaises(ValueError): validate_profile(p)
        with self.assertRaises(ValueError): metrics(self.p,-1)

    def test_inventory_never_invents_winners(self):
        file = Path(self.tmp.name)/"inventory.json"
        result = init_inventory(file)
        self.assertEqual(result["inventory_rows"],590)
        data=json.loads(file.read_text())
        self.assertEqual(len({c["symbol"] for c in data["candidates"]}),118)
        self.assertEqual(screen(file)["counts"]["needs_data"],590)

    def test_hypothetical_export_guard(self):
        out=Path(self.tmp.name)/"export.json"
        with self.assertRaises(ValueError): export_profile(self.path,out,False)
        export_profile(self.path,out,True)
        self.assertFalse(json.loads(out.read_text())["validated_for_hardware"])

    def test_environment_records(self):
        self.assertEqual(photodetachment_overlap_fidelity(1),1)
        self.assertAlmostEqual(photodetachment_overlap_fidelity(0),2/3)
        with self.assertRaises(ValueError): photodetachment_overlap_fidelity(2)

    def test_seed_streams(self):
        self.assertEqual(stable_seed(7,"E1","bath",0),stable_seed(7,"E1","bath",0))
        self.assertNotEqual(stable_seed(7,"E1","bath",0),stable_seed(7,"E1","tuning",0))

    def test_horizon_stops_at_first_failure(self):
        rows=[dict(t_s=t,full_channel_fidelity=f,retrieval_success_probability=.2)
              for t,f in [(0,.99),(1,.95),(2,.8),(3,.99)]]
        out=usable_horizon(rows,.9,.1)
        self.assertEqual(out['last_passing_grid_time_s'],1)
        self.assertEqual(out['first_failing_grid_time_s'],2)
        self.assertFalse(out['continuous_horizon_certified'])

    def test_horizon_unknown_and_censored(self):
        self.assertEqual(usable_horizon([], .9,.1)['status'],'inconclusive')
        rows=[dict(t_s=1,full_channel_fidelity=.99,retrieval_success_probability=.2)]
        self.assertEqual(usable_horizon(rows,.9,.1)['status'],'inconclusive')
        rows[0]['t_s']=0
        self.assertEqual(usable_horizon(rows,.9,.1)['status'],'right_censored_on_grid')
        rows[0]['full_channel_fidelity']=None
        self.assertEqual(usable_horizon(rows,.9,.1)['status'],'inconclusive')

if __name__ == "__main__": unittest.main()
