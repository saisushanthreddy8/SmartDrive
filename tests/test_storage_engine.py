"""
Unit tests for the storage-backed SmartDriveEngine.
Validates real uploads, versions on disk, rollback, deletion, restart persistence,
duplicate protection, and lazy heap deletion.
"""

import unittest
import tempfile
import shutil
import hashlib
from pathlib import Path
from models.file_model import FileModel
from services.core_engine import SmartDriveEngine
from services.file_service import FileStorageManager


class TestStorageEngine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dir = Path(self.tmp) / "storage"
        self.engine = SmartDriveEngine(FileStorageManager(self.dir))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_upload_writes_real_file(self):
        res = self.engine.upload_content("notes.txt", "line1\nline2", priority=7, description="Notes")
        f = self.engine.get_file_by_id(res["file_id"])
        self.assertTrue((self.dir / "documents" / "notes.txt").is_file())
        self.assertEqual(f.file_size, 11)
        self.assertEqual(f.sha256_hash, hashlib.sha256(b"line1\nline2").hexdigest())
        self.assertEqual(self.engine.read_version_content(f.file_id, 1), b"line1\nline2")
        self.assertTrue(self.engine.verify_file_on_disk(f.file_id)[0])

    def test_import_from_pc(self):
        src = Path(self.tmp) / "photo.png"
        src.write_bytes(b"\x89PNG-bytes")
        res = self.engine.import_local_file(str(src), priority=4)
        f = self.engine.get_file_by_id(res["file_id"])
        self.assertEqual(f.storage_path, "images/photo.png")
        self.assertEqual(f.file_type, "Image")

    def test_versions_diff_and_rollback_on_disk(self):
        fid = self.engine.upload_content("a.txt", "x\ny")["file_id"]
        self.engine.update_content(fid, "x\nz", "edit")
        self.assertEqual(self.engine.read_version_content(fid, 2), b"x\nz")
        res = self.engine.rollback_to_version(fid, 1)
        self.assertEqual(res["new_version"], 3)
        self.assertEqual((self.dir / "documents" / "a.txt").read_bytes(), b"x\ny")
        self.assertEqual(self.engine.read_version_content(fid, 3), b"x\ny")
        self.assertTrue(self.engine.verify_file_on_disk(fid)[0])

    def test_update_from_pc_file(self):
        fid = self.engine.upload_content("doc.txt", "old")["file_id"]
        src = Path(self.tmp) / "new_doc.txt"
        src.write_text("brand new")
        self.engine.update_content(fid, description="from PC", source_path=str(src))
        self.assertEqual((self.dir / "documents" / "doc.txt").read_text(), "brand new")
        self.assertEqual(self.engine.get_file_by_id(fid).current_version, 2)

    def test_restart_reloads_everything(self):
        fid = self.engine.upload_content("keep.txt", "v1", priority=9)["file_id"]
        self.engine.update_content(fid, "v2", "second")
        root = self.engine.merkle.root_hash
        reloaded = SmartDriveEngine(FileStorageManager(self.dir))
        f = reloaded.get_file_by_name("keep.txt")
        self.assertEqual(len(reloaded), 1)
        self.assertEqual(f.current_version, 2)
        self.assertEqual(reloaded.merkle.root_hash, root)
        self.assertEqual(reloaded.search_autocomplete("ke")[0][0], "keep.txt")
        self.assertEqual(reloaded.peek_highest_priority()[0], 9)

    def test_delete_removes_disk_versions_and_metadata(self):
        fid = self.engine.upload_content("gone.txt", "bye")["file_id"]
        self.assertTrue(self.engine.delete_file("gone.txt"))
        self.assertFalse((self.dir / "documents" / "gone.txt").exists())
        self.assertFalse((self.dir / "versions" / fid).exists())
        self.assertEqual(len(SmartDriveEngine(FileStorageManager(self.dir))), 0)

    def test_duplicate_and_case_collision_rejected(self):
        self.engine.upload_content("Report.pdf", "a")
        for name in ["Report.pdf", "report.PDF"]:
            with self.assertRaises(ValueError):
                self.engine.upload_content(name, "b")
        self.assertEqual(len(self.engine), 1)
        self.assertEqual((self.dir / "documents" / "Report.pdf").read_text(), "a")  # Not overwritten

    def test_invalid_upload_leaves_no_file(self):
        with self.assertRaises(ValueError):
            self.engine.upload_content("p.txt", "x", priority=11)
        with self.assertRaises(ValueError):
            self.engine.upload_content("../evil.txt", "x")
        self.assertEqual(self.engine.get_storage_stats()["total_files"], 0)

    def test_audit_detects_missing_file(self):
        fid = self.engine.upload_content("m.txt", "data")["file_id"]
        (self.dir / "documents" / "m.txt").unlink()
        audit = self.engine.audit_drive()
        self.assertEqual(audit["violations"][0]["status"], "MISSING")
        self.assertIn("MISSING", self.engine.verify_file_on_disk(fid)[1])

    def test_heap_skips_deleted_files(self):
        self.engine.upload_content("high.txt", "h", priority=10)
        self.engine.upload_content("low.txt", "l", priority=2)
        self.engine.delete_file("high.txt")
        self.assertEqual(self.engine.peek_highest_priority()[1].filename, "low.txt")
        self.assertEqual(self.engine.process_next_priority_file()[1].filename, "low.txt")
        self.assertIsNone(self.engine.process_next_priority_file())

    def test_storage_methods_require_storage(self):
        with self.assertRaises(RuntimeError):
            SmartDriveEngine().upload_content("x.txt", "x")

    def test_register_file_rejects_duplicates_without_storage(self):
        e = SmartDriveEngine()
        e.register_file(FileModel(filename="a.txt", file_size=1))
        with self.assertRaises(ValueError):
            e.register_file(FileModel(filename="A.TXT", file_size=2))


if __name__ == "__main__":
    unittest.main()
