"""Tests for Phase 0: inventory, CIF matching, unit-review hooks."""
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from memorylab.screening.inventory import (
    build_molecular_candidates,
    build_reference_candidates,
    build_atom_ion_candidates,
    build_combination_candidates,
    build_host_candidates,
    generate_unit_review_queue,
    run_inventory,
    _match_cifs_to_rows,
    _parse_cif_formula,
    _stratified_sample,
)

BASE = Path(__file__).resolve().parents[2]


class InventoryStructureTests(unittest.TestCase):
    """Tests for the universe table structure and candidate building."""

    def test_molecular_candidates_built_from_rows(self):
        rows = [
            {"source_row_number": "1", "formula": "C6H12O6", "spin_S": 0.5,
             "metal": "V", "host": "o-terphenyl", "solvent": "o-terphenyl",
             "counterion": "Et3NH", "paper_id": "https://example.invalid/paper1"},
            {"source_row_number": "2", "formula": "C8H8O4", "spin_S": 1.0,
             "metal": "Cu", "host": "toluene", "solvent": "toluene",
             "counterion": None, "paper_id": "https://example.invalid/paper2"},
        ]
        candidates = build_molecular_candidates(rows, {}, None, "test_sha")
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["id"], "mtd:1")
        self.assertEqual(candidates[0]["family"], "molecular_spin")
        self.assertEqual(candidates[0]["status"], "missing_data")
        self.assertIn("No CIF file", candidates[0]["status_reason"])
        self.assertEqual(candidates[1]["id"], "mtd:2")
        self.assertEqual(candidates[1]["metal"], "Cu")

    def test_reference_candidates_built_from_json(self):
        refs_path = BASE / "data" / "t2_references.json"
        if not refs_path.exists():
            self.skipTest("t2_references.json not found")
        candidates = build_reference_candidates(refs_path)
        self.assertEqual(len(candidates), 10)
        self.assertTrue(all(c["evidence_kind"] == "curated_experimental" for c in candidates))
        self.assertTrue(all(c["status"] == "success" for c in candidates))
        # Check that Eu:YSO references are present
        eu_refs = [c for c in candidates if "Eu" in (c.get("formula") or "")]
        self.assertGreaterEqual(len(eu_refs), 5)

    def test_atom_ion_candidates_include_blocked_negatives(self):
        elements_path = BASE / "examples" / "all_elements.json"
        if not elements_path.exists():
            self.skipTest("all_elements.json not found")
        candidates = build_atom_ion_candidates(elements_path)
        self.assertGreater(len(candidates), 100)
        # Negative ions should be blocked
        neg = [c for c in candidates if c.get("charge_e") == -1]
        self.assertTrue(all(c["status"] == "blocked" for c in neg))
        self.assertTrue(all("chi" in c["status_reason"] for c in neg))
        # Neutral atoms should be success
        neutral = [c for c in candidates if c.get("charge_e") == 0]
        self.assertTrue(all(c["status"] == "success" for c in neutral))

    def test_combination_candidates_are_hypothetical(self):
        combos_path = BASE / "examples" / "new_combinations.json"
        if not combos_path.exists():
            self.skipTest("new_combinations.json not found")
        candidates = build_combination_candidates(combos_path)
        self.assertGreater(len(candidates), 0)
        self.assertTrue(all(c["evidence_kind"] == "hypothetical" for c in candidates))

    def test_host_candidates_include_approved_extensions(self):
        candidates = build_host_candidates()
        self.assertEqual(len(candidates), 6)
        names = [c["formula"] for c in candidates]
        self.assertIn("Y2SiO5", names)
        self.assertIn("C", names)  # diamond
        self.assertIn("SiC", names)
        self.assertIn("Si", names)
        self.assertTrue(all(c["status"] == "missing_data" for c in candidates))
        self.assertTrue(all("host_cif_not_yet_fetched" in c["status_reason"] for c in candidates))


class CIFMatchingTests(unittest.TestCase):
    """Tests for CIF-to-row matching."""

    def test_match_cifs_by_number(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            zip_path = Path(d) / "test_cifs.zip"
            with zipfile.ZipFile(zip_path, "w") as z:
                z.writestr("1.cif", "data_test1\n_cell_length_a 5.0\n")
                z.writestr("2.cif", "data_test2\n_cell_length_a 6.0\n")
                z.writestr("__MACOSX/._1.cif", "junk")
                z.writestr("notes.txt", "not a cif")
            rows = [{"source_row_number": "1"}, {"source_row_number": "2"},
                    {"source_row_number": "3"}]
            lookup, unmatched, errors = _match_cifs_to_rows(rows, zip_path)
            self.assertIn("1", lookup)
            self.assertIn("2", lookup)
            self.assertNotIn("3", lookup)
            self.assertEqual(len(unmatched), 1)
            self.assertEqual(unmatched[0], "3")
            self.assertEqual(len(errors), 0)

    def test_universe_database_writes_and_reads(self):
        from memorylab.screening.inventory import _connect, _put_candidate
        with tempfile.TemporaryDirectory() as d:
            db_path = Path(d) / "test.sqlite"
            db = _connect(db_path)
            try:
                _put_candidate(db, {
                    "id": "test:1", "family": "molecular_spin", "formula": "H2O",
                    "evidence_kind": "curated_experimental", "status": "success",
                    "created_at": "2026-01-01T00:00:00Z",
                })
                db.commit()
                row = db.execute("SELECT id, family, formula, status FROM universe WHERE id=?", ("test:1",)).fetchone()
                self.assertEqual(row[0], "test:1")
                self.assertEqual(row[1], "molecular_spin")
                self.assertEqual(row[2], "H2O")
                self.assertEqual(row[3], "success")
            finally:
                db.close()


class UnitReviewQueueTests(unittest.TestCase):
    """Tests for the stratified unit-review queue."""

    def test_stratified_sample_covers_strata(self):
        rows = [
            {"source_row_number": "1", "metal": "V", "solvent": "o-terphenyl",
             "paper_id": "paper_A"},
            {"source_row_number": "2", "metal": "V", "solvent": "o-terphenyl",
             "paper_id": "paper_A"},
            {"source_row_number": "3", "metal": "Cu", "solvent": "toluene",
             "paper_id": "paper_B"},
            {"source_row_number": "4", "metal": "Cr", "solvent": "DCM",
             "paper_id": "paper_C"},
        ]
        sample = _stratified_sample(rows, n_per_stratum=2)
        # 3 strata: (paper_A, V, o-terphenyl), (paper_B, Cu, toluene), (paper_C, Cr, DCM)
        self.assertEqual(len(sample), 4)  # 2 + 1 + 1

    def test_unit_review_queue_csv_generated(self):
        rows = [
            {"source_row_number": "1", "metal": "V", "solvent": "o-terphenyl",
             "paper_id": "https://example.invalid/paper1",
             "reported_name": "V-complex-1", "formula": "C12H8O4V",
             "T2_10": 2.25, "T2_80": 0.5, "T1_10": 10, "T1_80": 1,
             "spin_S": 0.5},
        ]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "review_queue.csv"
            count = generate_unit_review_queue(rows, path)
            self.assertEqual(count, 1)
            self.assertTrue(path.exists())
            import csv
            with path.open() as f:
                reader = csv.DictReader(f)
                row = next(reader)
                self.assertEqual(row["source_row_number"], "1")
                self.assertEqual(row["metal"], "V")
                self.assertEqual(row["T2_10"], "2.25")


class FullInventoryRunTests(unittest.TestCase):
    """Integration test for the full inventory run."""

    def test_run_inventory_from_existing_data(self):
        t2_data = BASE / "t2_data"
        if not (t2_data / "source_lock.json").exists():
            self.skipTest("t2_data not prepared")
        config = {
            "t2_data_root": str(t2_data),
            "references_json": str(BASE / "data" / "t2_references.json"),
            "all_elements_json": str(BASE / "examples" / "all_elements.json"),
            "combinations_json": str(BASE / "examples" / "new_combinations.json"),
            "include_hosts": True,
        }
        with tempfile.TemporaryDirectory() as d:
            report = run_inventory(config, d)
            self.assertIn("total_candidates", report)
            self.assertGreater(report["total_candidates"], 100)
            self.assertIn("family_counts", report)
            self.assertIn("molecular_spin", report["family_counts"])
            self.assertIn("unit_review_queue_path", report)
            self.assertTrue(Path(report["unit_review_queue_path"]).exists())
            self.assertIn("data_gaps", report)
            # Universe DB should exist
            db_path = Path(report["universe_db_path"])
            self.assertTrue(db_path.exists())
            # Check it has rows
            db = sqlite3.connect(str(db_path))
            count = db.execute("SELECT COUNT(*) FROM universe").fetchone()[0]
            db.close()
            self.assertEqual(count, report["total_candidates"])


if __name__ == "__main__":
    unittest.main()
