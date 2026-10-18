"""
Unit tests for SmartDrive CLI engine and full cross-DSA coordination.
Each test runs against a temporary storage folder (never the real storage/).
"""

import unittest
import tempfile
import shutil
from cli import SmartDriveCLI, DEMO_BUDGET_KB, KB


class TestSmartDriveCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cli = SmartDriveCLI(storage_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_seeded_data_loaded_in_engine(self):
        # 7 sample files seeded
        self.assertEqual(len(self.cli.engine.avl_tree), 7)
        self.assertEqual(len(self.cli.engine.hash_by_name), 7)
        self.assertEqual(len(self.cli.engine.trie), 7)
        self.assertEqual(len(self.cli.engine.heap), 7)
        self.assertEqual(len(self.cli.engine.merkle), 7)
        self.assertIsNotNone(self.cli.engine.merkle.root_hash)
        self.assertEqual(self.cli.engine.get_storage_stats()["total_files"], 7)

    def test_seed_runs_only_once(self):
        again = SmartDriveCLI(storage_dir=self.tmp)
        self.assertEqual(len(again.engine), 7)
        self.assertEqual(again.engine.merkle.root_hash, self.cli.engine.merkle.root_hash)

    def test_cross_dsa_search_and_lookup(self):
        # Trie Autocomplete
        results = self.cli.engine.search_autocomplete("machine")
        self.assertEqual(len(results), 2)

        # Hash Table direct lookup
        file_obj = self.cli.engine.get_file_by_name("Machine_Learning_Assignment.pdf")
        self.assertIsNotNone(file_obj)
        self.assertEqual(file_obj.priority, 10)

        # AVL sorted in-order
        sorted_files = self.cli.engine.list_all_files_sorted()
        self.assertEqual(len(sorted_files), 7)
        filenames = [name for name, _ in sorted_files]
        self.assertEqual(filenames, sorted(filenames))

        # Heap priority peek
        top_priority = self.cli.engine.peek_highest_priority()
        self.assertIsNotNone(top_priority)
        self.assertEqual(top_priority[0], 10)
        self.assertEqual(top_priority[1].filename, "Machine_Learning_Assignment.pdf")

    def test_integrity_and_tamper_simulation(self):
        file_obj = self.cli.engine.get_file_by_name("Semester_Final_Report.pdf")
        self.assertIsNotNone(file_obj)

        # 1. Verify clean file (hash read from the real file on disk)
        is_valid, _ = self.cli.engine.verify_file_on_disk(file_obj.file_id)
        self.assertTrue(is_valid)

        # 2. Tamper with the real file on disk
        with open(self.cli.storage.resolve(file_obj.storage_path), "ab") as fh:
            fh.write(b"MODIFIED_TAMPERED_CONTENT")
        is_valid, msg = self.cli.engine.verify_file_on_disk(file_obj.file_id)
        self.assertFalse(is_valid)
        self.assertIn("TAMPER DETECTED", msg)
        self.assertEqual(self.cli.engine.audit_drive()["tampered_count"], 1)

    def test_phase4_storage_optimizer_on_seeded_data(self):
        results = self.cli.engine.compare_optimizers(DEMO_BUDGET_KB * KB)  # Demo budget where Greedy loses
        self.assertEqual([r.method for r in results], ["Dynamic Programming", "Greedy (Ratio)", "Branch & Bound"])
        dp, greedy, bnb = results
        self.assertEqual((dp.total_value, bnb.total_value, greedy.total_value), (27, 27, 23))
        self.assertLessEqual(dp.total_weight, dp.capacity)


if __name__ == "__main__":
    unittest.main()
