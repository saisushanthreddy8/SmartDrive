"""
Unit tests for SmartDrive FileModel domain entity.
Built with standard library unittest for zero-dependency execution.
"""

import unittest
from models.file_model import FileModel


class TestFileModel(unittest.TestCase):
    def test_valid_file_model_creation(self):
        file = FileModel(
            filename="Machine_Learning_Assignment.pdf",
            file_size=2048576,
            priority=8,
            owner="alice",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            storage_path="storage/documents/Machine_Learning_Assignment.pdf",
            tags=["AI", "Homework"],
        )
        self.assertEqual(file.filename, "Machine_Learning_Assignment.pdf")
        self.assertEqual(file.file_size, 2048576)
        self.assertEqual(file.priority, 8)
        self.assertEqual(file.owner, "alice")
        self.assertEqual(file.file_extension, ".pdf")
        self.assertEqual(file.file_type, "Document")
        self.assertEqual(file.formatted_size, "1.95 MB")
        self.assertTrue(len(file.file_id) > 0)
        self.assertIn("AI", file.tags)

    def test_file_type_auto_inference(self):
        f_doc = FileModel(filename="notes.docx", file_size=1024)
        self.assertEqual(f_doc.file_type, "Document")

        f_img = FileModel(filename="banner.png", file_size=5000)
        self.assertEqual(f_img.file_type, "Image")

        f_vid = FileModel(filename="lecture.mp4", file_size=50000000)
        self.assertEqual(f_vid.file_type, "Video")

        f_aud = FileModel(filename="recording.mp3", file_size=3000000)
        self.assertEqual(f_aud.file_type, "Audio")

        f_arc = FileModel(filename="backup.zip", file_size=9000000)
        self.assertEqual(f_arc.file_type, "Archive")

        f_oth = FileModel(filename="unknown_binary.xyz", file_size=100)
        self.assertEqual(f_oth.file_type, "Other")

    def test_invalid_filename(self):
        with self.assertRaises(ValueError):
            FileModel(filename="", file_size=100)

        with self.assertRaises(ValueError):
            FileModel(filename="   ", file_size=100)

    def test_invalid_file_size(self):
        with self.assertRaises(ValueError):
            FileModel(filename="valid.txt", file_size=-10)

        # Zero size should be valid for empty files
        empty_file = FileModel(filename="empty.txt", file_size=0)
        self.assertEqual(empty_file.file_size, 0)

    def test_invalid_priority(self):
        with self.assertRaises(ValueError):
            FileModel(filename="test.txt", file_size=100, priority=0)

        with self.assertRaises(ValueError):
            FileModel(filename="test.txt", file_size=100, priority=11)

    def test_invalid_sha256_hash(self):
        with self.assertRaises(ValueError):
            FileModel(filename="test.txt", file_size=100, sha256_hash="invalid_short_hash")

    def test_serialization_and_deserialization(self):
        original = FileModel(
            filename="data_analysis.csv",
            file_size=512000,
            priority=7,
            owner="bob",
            sha256_hash="a" * 64,
            storage_path="storage/documents/data_analysis.csv",
            description="Q3 Sales Report Data",
            tags=["finance", "q3"],
        )

        data = original.to_dict()
        self.assertEqual(data["filename"], "data_analysis.csv")
        self.assertEqual(data["priority"], 7)
        self.assertEqual(data["file_type"], "Document")

        reconstructed = FileModel.from_dict(data)
        self.assertEqual(reconstructed.file_id, original.file_id)
        self.assertEqual(reconstructed.filename, original.filename)
        self.assertEqual(reconstructed.file_size, original.file_size)
        self.assertEqual(reconstructed.priority, original.priority)
        self.assertEqual(reconstructed.owner, original.owner)
        self.assertEqual(reconstructed.sha256_hash, original.sha256_hash)
        self.assertEqual(reconstructed.description, original.description)
        self.assertEqual(reconstructed.tags, original.tags)


if __name__ == "__main__":
    unittest.main()
