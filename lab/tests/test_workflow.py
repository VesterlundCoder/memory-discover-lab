import copy
import csv
import hashlib
import http.server
import json
import math
import os
import tempfile
import threading
import unittest
from pathlib import Path
from memorylab.catalog import Catalog, composition, expand_candidates
from memorylab.common import canonical, digest, read_json, seed, write_json, MissingData
from memorylab.datasets import Client, DownloadError
from memorylab.importers import import_artifact, extract_workbook
from memorylab.runner import enumerate_jobs, run
from memorylab.calibration import bind_observations
from memorylab.units import convert, isotope_id
from memorylab.backends import prepare_external, execute_external

ROOT = Path(__file__).resolve().parent.parent


def fixture_artifact():
    return {"id": "synthetic_fixture", "sha256": "synthetic_fixture_hash",
            "source_id": "test_fixture", "url": "https://example.invalid/fixture",
            "source_revision": "test-only"}


class UnitsAndCandidateTests(unittest.TestCase):
    def test_two_pi_convention(self):
        self.assertAlmostEqual(convert(2*math.pi, "rad/s", "Hz"), 1)
        self.assertEqual(convert(1, "ms", "s"), 0.001)
        self.assertEqual(convert(1, "T", "G"), 10000)
        with self.assertRaises(ValueError):
            convert(1, "Hz", "s")

    def test_stable_separate_seed_streams(self):
        self.assertEqual(seed(1, "a", "bath"), seed(1, "a", "bath"))
        self.assertNotEqual(seed(1, "a", "bath"), seed(1, "a", "network"))
        self.assertNotEqual(seed(1, "a", "bath", 0), seed(1, "a", "bath", 1))

    def test_isotope_nuclear_states_remain_distinct(self):
        self.assertNotEqual(isotope_id("Hf", 178), isotope_id("Hf", 178, "m2"))

    def test_formula_not_silently_guessed(self):
        self.assertEqual(composition("CuC10H20N2S4"), {"Cu": 1, "C": 10, "H": 20, "N": 2, "S": 4})
        self.assertIsNone(composition("Cu(dtc)2"))
        self.assertIsNone(composition("H0"))

    def test_new_combination_count_and_no_fake_material_parameters(self):
        rows = expand_candidates(read_json(ROOT/"examples/new_combinations.json"))
        self.assertEqual(len(rows), 16)
        self.assertEqual(len({r["id"] for r in rows}), 16)
        for r in rows:
            self.assertEqual(r["status"], "unassessed")
            self.assertIsNone(r["bound_state_exists"])
            self.assertNotIn("T2_s", r)
            self.assertEqual((2-r["charge_e"]-r["spin_2S"]) % 2, 0)

    def test_isotope_swap_cannot_change_element(self):
        plan = read_json(ROOT/"examples/new_combinations.json")
        plan["isotope_choices_by_site"]["0"] = ["C-13"]
        with self.assertRaises(ValueError):
            expand_candidates(plan)


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.catalog = Catalog(self.root/"catalog.sqlite")

    def tearDown(self):
        self.catalog.close()
        self.temp.cleanup()

    def test_unknown_units_not_promoted_to_seconds(self):
        path = self.root/"molecular.csv"
        columns = ["number", "chemForm", "T1_10", "T1_80", "T2_10", "T2_80", "spin", "Solvent"]
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerow(dict(zip(columns, ["1", "H2", "10", "20", "3", "4", "0", "fixture"])))
        result = import_artifact("molecular_csv", path, fixture_artifact(), self.catalog)
        self.assertEqual(result["observations_with_unverified_units"], 4)
        rows = self.catalog.rows("observations")
        self.assertTrue(all(r["unit"] == "source_unspecified" for r in rows))
        self.assertTrue(all(r["network_parameter_ready"] is False for r in rows))
        import_artifact("molecular_csv", path, fixture_artifact(), self.catalog)
        self.assertEqual(self.catalog.summary()["observations"], 4)

    def test_ciaaw_intervals_and_row_inheritance(self):
        path = self.root/"isotopes.html"
        path.write_text('<table id="mytable"><tr><td>1</td><td>H</td><td>hydrogen</td>'
                        '<td>1</td><td>[0.99972, 0.99999]</td></tr>'
                        '<tr><td>2</td><td>[0.00001, 0.00028]</td></tr>'
                        '<tr><td>2</td><td>He</td><td>helium</td><td>3</td>'
                        '<td>0.000002(2)</td></tr></table>')
        result = import_artifact("ciaaw_abundances", path, fixture_artifact(), self.catalog)
        self.assertEqual(result["isotopes"], 3)
        rows = {r["subject_id"]: r for r in self.catalog.rows("observations")}
        self.assertEqual(rows["H-2:ground"]["value"], [0.00001, 0.00028])
        self.assertEqual(rows["He-3:ground"]["quoted_parenthesis_uncertainty"], 0.000002)
        self.assertIsNone(rows["H-1:ground"]["nuclear_spin_I"])

    def test_nist_uncertainty_and_masses(self):
        path = self.root/"nist.txt"
        path.write_text("Atomic Number = 6\nAtomic Symbol = C\nMass Number = 13\n"
                        "Relative Atomic Mass = 13.00335483507(23)\n"
                        "Isotopic Composition = 0.0107(8)\n")
        result = import_artifact("nist_isotopes", path, fixture_artifact(), self.catalog)
        self.assertEqual(result["observations"], 2)
        masses = [r for r in self.catalog.rows("observations") if r["quantity"] == "isotope_mass"]
        self.assertAlmostEqual(masses[0]["value"], 13.00335483507)
        self.assertAlmostEqual(masses[0]["quoted_parenthesis_uncertainty"], 0.00000000023)

    def test_immutable_catalog_collision(self):
        self.catalog.put("artifacts", {"id": "x", "value": 1})
        with self.assertRaises(ValueError):
            self.catalog.put("artifacts", {"id": "x", "value": 2})

    def test_failed_import_transaction_is_rolled_back(self):
        with self.assertRaises(ValueError):
            with self.catalog.transaction():
                self.catalog.put("artifacts", {"id": "x", "value": 1})
                raise ValueError("Synthetic parser failure")
        self.assertEqual(self.catalog.summary()["artifacts"], 0)

    def test_binding_rejects_unknown_units(self):
        row = {"id": "o", "subject_id": "fixture", "quantity": "reported_T1", "value": 100,
               "unit": "source_unspecified", "conditions": {}, "provenance": [{"fixture": True}],
               "evidence_kind": "curated_experimental", "source_location": "fixture"}
        self.catalog.put("observations", row)
        binding = {"observation_id": "o", "quantity": "reported_T1", "required_unit": "s",
                   "target": "rates.population.rate_s_inv", "transform": "inverse",
                   "model_justification": "synthetic unit test"}
        with self.assertRaises(MissingData):
            bind_observations(read_json(ROOT/"examples/trapped_atom_ion_profile.json"), [binding], self.catalog)

    def test_binding_inverts_verified_T1_and_records_provenance(self):
        row = {"id": "o", "subject_id": "fixture", "quantity": "reported_T1", "value": 20,
               "unit": "s", "conditions": {"T": 4.2}, "provenance": [{"fixture": True}],
               "evidence_kind": "experimental", "source_location": "synthetic test fixture"}
        self.catalog.put("observations", row)
        binding = {"observation_id": "o", "quantity": "reported_T1", "required_unit": "s",
                   "target": "rates.population.rate_s_inv", "transform": "inverse",
                   "conditions": {"T": 4.2}, "model_justification": "synthetic unit test"}
        profile = bind_observations(read_json(ROOT/"examples/trapped_atom_ion_profile.json"), [binding], self.catalog)
        self.assertEqual(profile["rates"]["population"]["rate_s_inv"], 0.05)
        self.assertEqual(profile["provenance"][-1]["observation_id"], "o")


class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hits = 0
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                DownloadTests.hits += 1
                payload = b'{"synthetic":true,"value":1}\n'
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(payload)
            def log_message(self, *args):
                pass
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/fixture.json"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_download_checksum_cache_and_corruption_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            client = Client(temp, timeout_s=3, retries=0)
            start = self.hits
            rec = client.fetch(self.url, "fixture")
            self.assertEqual(rec["size_bytes"], 29)
            self.assertEqual(client.fetch(self.url, "fixture")["sha256"], rec["sha256"])
            self.assertEqual(self.hits, start+1)
            (Path(temp)/rec["relative_path"]).write_text("corrupt")
            recovered = client.fetch(self.url, "fixture")
            self.assertEqual(recovered["sha256"], rec["sha256"])
            self.assertEqual(self.hits, start+2)
            refreshed = client.fetch(self.url, "fixture", refresh=True)
            self.assertEqual(refreshed["id"], recovered["id"])

    def test_wrong_checksum_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(DownloadError):
                Client(temp, timeout_s=3, retries=0).fetch(self.url, "fixture", expected_checksum="md5:0000")
            self.assertFalse(list(Path(temp).glob("raw/**/*")))

    def test_size_budget_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(DownloadError):
                Client(temp, max_bytes=2, timeout_s=3, retries=0).fetch(self.url, "fixture")

    def test_non_http_source_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(DownloadError):
                Client(temp).fetch("file:///etc/passwd", "fixture")


class RunnerTests(unittest.TestCase):
    def test_count_and_cross_backend_common_seeds(self):
        study = read_json(ROOT/"examples/cross_backend_study.json")
        jobs = enumerate_jobs(study)
        self.assertEqual(len(jobs), 36)
        self.assertEqual(jobs[0]["config"]["seeds"], jobs[1]["config"]["seeds"])
        self.assertNotEqual(jobs[0]["run_id"], jobs[1]["run_id"])

    def test_run_checkpoint_and_raw_channel_export(self):
        study = read_json(ROOT/"examples/study.json")
        study["models"] = study["models"][:1]
        study["grid"] = {}
        study["replicates"] = 1
        study.pop("network_workload")
        with tempfile.TemporaryDirectory() as temp:
            result = run(study, temp)
            self.assertTrue(result["all_success"])
            self.assertEqual(result["statuses"], {"success": 1})
            self.assertEqual(run(study, temp)["resumed_runs"], 1)
            sample = next(Path(temp).glob("*/channels.json"))
            self.assertEqual(len(read_json(sample)["samples"]), len(study["times_s"]))

    def test_timeout_is_saved_and_not_reported_as_success(self):
        study = read_json(ROOT/"examples/study.json")
        study["models"] = study["models"][:1]
        study["grid"], study["replicates"] = {}, 1
        study["resources"]["timeout_s"] = 0.00001
        with tempfile.TemporaryDirectory() as temp:
            result = run(study, temp)
            self.assertEqual(result["statuses"], {"timeout": 1})
            self.assertFalse(result["all_success"])
            self.assertEqual(run(study, temp)["resumed_runs"], 1)

    def test_invalid_config_gets_explicit_status(self):
        study = read_json(ROOT/"examples/study.json")
        study["models"] = study["models"][:1]
        study["grid"], study["replicates"] = {}, 1
        study["models"][0]["profile"]["io"]["eta_write"] = -1
        with tempfile.TemporaryDirectory() as temp:
            result = run(study, temp)
            self.assertEqual(result["statuses"], {"invalid_config": 1})

    def test_unknown_combination_search_requires_baseline_gate(self):
        study = read_json(ROOT/"examples/study.json")
        study["stage"] = "discovery"
        with self.assertRaises(ValueError):
            enumerate_jobs(study)

    def test_duplicate_grid_and_run_budget_rejected(self):
        study = read_json(ROOT/"examples/study.json")
        study["grid"] = {"temperatures_K.storage": [4.2, 4.2]}
        with self.assertRaises(ValueError):
            enumerate_jobs(study)
        study = read_json(ROOT/"examples/study.json")
        study["resources"]["max_runs"] = 2
        with self.assertRaises(ValueError):
            enumerate_jobs(study)


class ExternalAdapterTests(unittest.TestCase):
    def test_orca_input_and_bounded_mock_execution(self):
        candidate = read_json(ROOT/"examples/h2_candidate.json")
        recipe = read_json(ROOT/"examples/orca_recipe.json")
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp)/"mock orca"
            binary.write_text("#!/bin/sh\nprintf 'FINAL SINGLE POINT ENERGY -1.0\\nORCA TERMINATED NORMALLY\\n'\n")
            binary.chmod(0o700)
            recipe["binary"] = str(binary)
            job = prepare_external("orca", candidate, recipe, Path(temp)/"job")
            self.assertIn("* xyz 0 1", Path(job["input"]).read_text())
            result = execute_external(job)
            self.assertEqual(result["energy_hartree"], -1)
            self.assertIsNone(result["T2_s"])
