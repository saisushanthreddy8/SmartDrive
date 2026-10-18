"""
Unit tests for SmartDrive FileStorageManager.
Validates partitioned storage, path safety, hashing, version snapshots, and metadata persistence.
"""

import unittest
import tempfile
import shutil
import hashlib
from pathlib import Path
from services.file_service import FileStorageManager, DEFAULT_STORAGE_DIR, PROJECT_ROOT


class TestFileStorageManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = FileStorageManager(Path(self.tmp) / "storage")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_default_location_is_inside_project(self):
        self.assertEqual(DEFAULT_STORAGE_DIR, PROJECT_ROOT / "storage")

    def test_folders_created(self):
        for folder in ["documents", "images", "videos", "audio", "other", "versions"]:
            self.assertTrue((self.store.base_dir / folder).is_dir())

    def test_save_partitions_and_hashes(self):
        rel, sha, size = self.store.save_file_content("notes.txt", "hello")
        self.assertEqual(rel, "documents/notes.txt")
        self.assertEqual(sha, hashlib.sha256(b"hello").hexdigest())
        self.assertEqual(size, 5)
        self.assertEqual(self.store.read_file_content(rel), b"hello")
        self.assertEqual(self.store.compute_file_hash(rel), sha)
        self.assertEqual(self.store.save_file_content("pic.PNG", b"\x89PNG")[0], "images/pic.PNG")
        self.assertEqual(self.store.save_file_content("unknown.xyz", b"x")[0], "other/unknown.xyz")

    def test_path_traversal_blocked(self):
        for bad in ["../escape.txt", "..\\escape.txt", "a/b.txt", "", "  ", "..", "bad:name.txt"]:
            with self.assertRaises(ValueError):
                self.store.save_file_content(bad, "x")
        with self.assertRaises(ValueError):
            self.store.resolve("../../outside.txt")
        self.assertFalse((Path(self.tmp) / "escape.txt").exists())

    def test_import_local_file(self):
        src = Path(self.tmp) / "report.pdf"
        src.write_bytes(b"%PDF-demo")
        name, rel, sha, size = self.store.import_local_file(str(src))
        self.assertEqual((name, rel, size), ("report.pdf", "documents/report.pdf", 9))
        self.assertEqual(sha, hashlib.sha256(b"%PDF-demo").hexdigest())
        with self.assertRaises(FileNotFoundError):
            self.store.import_local_file(str(Path(self.tmp) / "missing.pdf"))

    def test_version_snapshots_and_restore(self):
        rel, _, _ = self.store.save_file_content("a.txt", "v1")
        self.store.snapshot_version("fid-1", 1, "a.txt", rel)
        self.store.save_file_content("a.txt", "v2")
        self.store.snapshot_version("fid-1", 2, "a.txt", rel)
        self.assertEqual(self.store.read_version("fid-1", 1, "a.txt"), b"v1")
        self.assertEqual(self.store.read_version("fid-1", 2, "a.txt"), b"v2")
        self.assertIsNone(self.store.read_version("fid-1", 3, "a.txt"))
        self.assertTrue(self.store.restore_version("fid-1", 1, "a.txt", rel))
        self.assertEqual(self.store.read_file_content(rel), b"v1")
        self.assertTrue(self.store.delete_versions("fid-1"))
        self.assertIsNone(self.store.read_version("fid-1", 1, "a.txt"))

    def test_metadata_round_trip_and_corruption(self):
        self.assertEqual(self.store.load_metadata(), [])
        self.store.save_metadata([{"filename": "a.txt"}])
        self.assertEqual(self.store.load_metadata(), [{"filename": "a.txt"}])
        (self.store.base_dir / "metadata.json").write_text("{not json")
        with self.assertRaises(ValueError):
            self.store.load_metadata()

    def test_delete_and_stats(self):
        rel, _, _ = self.store.save_file_content("a.txt", "abc")
        self.store.snapshot_version("fid", 1, "a.txt", rel)
        st = self.store.get_storage_stats()
        self.assertEqual((st["total_files"], st["total_size_bytes"]), (1, 3))
        self.assertEqual(st["categories"]["versions"]["count"], 1)
        self.assertTrue(self.store.delete_physical_file(rel))
        self.assertFalse(self.store.delete_physical_file(rel))
        self.assertIsNone(self.store.compute_file_hash(rel))


if __name__ == "__main__":
    unittest.main()
