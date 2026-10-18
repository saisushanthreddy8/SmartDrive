"""
Unit tests for SmartDrive Prefix Trie implementation.
Validates O(k) prefix lookups, case-insensitive autocomplete suggestions,
word deletion mechanics, and FileModel payload integration.
"""

import unittest
from data_structures.trie import Trie
from models.file_model import FileModel


class TestTrie(unittest.TestCase):
    def test_empty_trie(self):
        trie = Trie[str]()
        self.assertTrue(trie.is_empty)
        self.assertEqual(len(trie), 0)
        self.assertIsNone(trie.search_exact("report.pdf"))
        self.assertFalse(trie.starts_with("rep"))
        self.assertEqual(trie.autocomplete("rep"), [])
        self.assertFalse(trie.delete("report.pdf"))
        self.assertEqual(trie.display_trie(), "<Empty Trie>")

    def test_insert_and_exact_search(self):
        trie = Trie[str](case_sensitive=False)
        trie.insert("report.pdf", "doc_1")
        trie.insert("Report_Final.pdf", "doc_2")
        trie.insert("notes.txt", "doc_3")

        self.assertEqual(len(trie), 3)
        self.assertFalse(trie.is_empty)

        # Case-insensitive searches
        self.assertEqual(trie.search_exact("report.pdf"), "doc_1")
        self.assertEqual(trie.search_exact("REPORT.PDF"), "doc_1")
        self.assertEqual(trie.search_exact("Report_Final.pdf"), "doc_2")
        self.assertEqual(trie.search_exact("notes.txt"), "doc_3")
        self.assertIsNone(trie.search_exact("missing.pdf"))

    def test_starts_with(self):
        trie = Trie[int]()
        trie.insert("assignment.docx", 1)
        trie.insert("assign_guide.pdf", 2)

        self.assertTrue(trie.starts_with("assign"))
        self.assertTrue(trie.starts_with("ASSIGN"))
        self.assertTrue(trie.starts_with("a"))
        self.assertFalse(trie.starts_with("asx"))
        self.assertFalse(trie.starts_with("report"))

    def test_autocomplete(self):
        trie = Trie[str]()
        files = [
            ("report.pdf", "f1"),
            ("report.docx", "f2"),
            ("report_final.pdf", "f3"),
            ("report_notes.txt", "f4"),
            ("resume.pdf", "f5"),
            ("project.pptx", "f6"),
        ]
        for name, fid in files:
            trie.insert(name, fid)

        self.assertEqual(len(trie), 6)

        # Autocomplete for "rep"
        rep_results = trie.autocomplete("rep")
        result_names = [name for name, _ in rep_results]
        self.assertEqual(
            sorted(result_names),
            ["report.docx", "report.pdf", "report_final.pdf", "report_notes.txt"]
        )

        # Autocomplete for "res"
        res_results = trie.autocomplete("res")
        self.assertEqual([name for name, _ in res_results], ["resume.pdf"])

        # Autocomplete with limit
        limited = trie.autocomplete("rep", limit=2)
        self.assertEqual(len(limited), 2)

        # Autocomplete for non-existent prefix
        self.assertEqual(trie.autocomplete("xyz"), [])

    def test_deletion_mechanics(self):
        trie = Trie[int]()
        trie.insert("car", 1)
        trie.insert("card", 2)
        trie.insert("care", 3)

        self.assertEqual(len(trie), 3)

        # 1. Delete "card" (leaf branch)
        self.assertTrue(trie.delete("card"))
        self.assertEqual(len(trie), 2)
        self.assertIsNone(trie.search_exact("card"))
        self.assertEqual(trie.search_exact("car"), 1)
        self.assertEqual(trie.search_exact("care"), 3)

        # 2. Delete "car" (prefix of "care")
        self.assertTrue(trie.delete("car"))
        self.assertEqual(len(trie), 1)
        self.assertIsNone(trie.search_exact("car"))
        self.assertEqual(trie.search_exact("care"), 3)

        # 3. Delete non-existent
        self.assertFalse(trie.delete("car"))
        self.assertFalse(trie.delete("zebra"))

        # 4. Delete "care" (last remaining word)
        self.assertTrue(trie.delete("care"))
        self.assertEqual(len(trie), 0)
        self.assertTrue(trie.is_empty)

    def test_trie_with_file_model(self):
        """Validates storing FileModel domain objects in Prefix Trie."""
        trie = Trie[FileModel]()

        f1 = FileModel(filename="Machine_Learning_Notes.pdf", file_size=1024, priority=10)
        f2 = FileModel(filename="Machine_Learning_Project.py", file_size=2048, priority=9)
        f3 = FileModel(filename="Microprocessors_Lab.docx", file_size=4096, priority=6)

        trie.insert(f1.filename, f1)
        trie.insert(f2.filename, f2)
        trie.insert(f3.filename, f3)

        self.assertEqual(len(trie), 3)

        # Search prefix "machine"
        suggestions = trie.autocomplete("machine")
        self.assertEqual(len(suggestions), 2)
        self.assertEqual(suggestions[0][1].file_type, "Document")
        self.assertEqual(suggestions[0][1].priority, 10)

        # Display test
        display_str = trie.display_trie()
        self.assertIn("PrefixTrie", display_str)


if __name__ == "__main__":
    unittest.main()
