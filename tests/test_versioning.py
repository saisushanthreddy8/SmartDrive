"""
Unit tests for SmartDrive Version Control.
Validates version history, validation, rollback, and Merkle root updates.
"""

import unittest
import hashlib
from models.file_model import FileModel
from services.core_engine import SmartDriveEngine


def h(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


class TestVersionControl(unittest.TestCase):
    def setUp(self):
        self.engine = SmartDriveEngine()
        self.f = FileModel(filename="report.txt", file_size=2, sha256_hash=h("v1"))
        self.engine.register_file(self.f)

    def test_initial_version(self):
        self.assertEqual(self.f.current_version, 1)
        self.assertEqual(self.f.get_version(1).description, "Initial version")
        self.assertIsNone(self.f.get_version(0))
        self.assertIsNone(self.f.get_version(2))

    def test_update_changes_hash_and_merkle_root(self):
        root_before = self.engine.merkle.root_hash
        res = self.engine.update_file_version(self.f.file_id, 5, h("v2 ok"), "Second draft")
        self.assertEqual(res["new_version"], 2)
        self.assertEqual(self.f.sha256_hash, h("v2 ok"))
        self.assertNotEqual(res["merkle_root"], root_before)
        self.assertTrue(self.engine.verify_file_integrity(self.f.file_id, h("v2 ok"))[0])
        self.assertFalse(self.engine.verify_file_integrity(self.f.file_id, h("v1"))[0])

    def test_add_version_validation(self):
        with self.assertRaises(ValueError):
            self.f.add_version(-1, h("x"))
        with self.assertRaises(ValueError):
            self.f.add_version(10, "z" * 64)  # Non-hex
        self.assertEqual(self.f.current_version, 1)

    def test_rollback_appends_new_version(self):
        self.engine.update_file_version(self.f.file_id, 2, h("v2"), "v2")
        res = self.engine.rollback_to_version(self.f.file_id, 1)
        self.assertEqual(res["new_version"], 3)
        self.assertEqual(res["restored_from"], 1)
        self.assertEqual(self.f.sha256_hash, h("v1"))
        self.assertEqual(self.f.get_version(3).description, "Rollback to v1")
        self.assertEqual(len(self.engine.get_version_history(self.f.file_id)), 3)

    def test_rollback_invalid(self):
        self.assertIsNone(self.engine.rollback_to_version(self.f.file_id, 9))
        self.assertIsNone(self.engine.rollback_to_version("missing-id", 1))
        self.assertIsNone(self.engine.get_version_history("missing-id"))

    def test_compare_versions(self):
        cmp = self.engine.compare_versions("a\nb", "a\nc")
        self.assertEqual(cmp["lcs_length"], 1)
        self.assertEqual(cmp["stats"]["similarity_pct"], 50.0)

    def test_version_history_round_trip(self):
        self.engine.update_file_version(self.f.file_id, 3, h("v2"), "v2")
        clone = FileModel.from_dict(self.f.to_dict())
        self.assertEqual(clone.current_version, 2)
        self.assertEqual(clone.get_version(2).sha256_hash, h("v2"))


if __name__ == "__main__":
    unittest.main()
