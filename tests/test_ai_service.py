"""
Unit tests for the SmartDrive offline AI service.
Validates tokenising/stemming, text extraction, TF-IDF + inverted index search, Q&A,
summaries, keywords, tags, priority suggestions and duplicate detection.
"""

import unittest
import tempfile
import shutil
import io
import zipfile
from services.ai_service import AIService, TFIDFIndex, tokenize, stem, extract_text, split_sentences
from services.core_engine import SmartDriveEngine
from services.file_service import FileStorageManager

NOTES = ("Supervised learning learns a mapping from labelled inputs to outputs. Regression predicts continuous values. "
         "Classification predicts discrete classes. The final exam deadline is next week, so submit the assignment early.")


class TestTextProcessing(unittest.TestCase):
    def test_tokenize_and_stem(self):
        self.assertEqual(tokenize("The Insertion of inserts, inserting!"), ["insert", "insert", "insert"])
        self.assertNotIn("the", tokenize("the and of"))
        self.assertEqual(stem("class"), "class")  # "ss" endings are kept
        self.assertEqual(split_sentences("Short. This sentence is long enough.\nAnother line here ok"), ["This sentence is long enough.", "Another line here ok"])

    def test_extract_text_formats(self):
        self.assertEqual(extract_text("a.txt", b"hello world"), "hello world")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("word/document.xml", "<w:document><w:p><w:t>Merkle trees detect tampering</w:t></w:p></w:document>")
        self.assertIn("Merkle trees detect tampering", extract_text("r.docx", buf.getvalue()))
        self.assertEqual(extract_text("photo.png", b"\x89PNG\r\n\x1a\n\x00\xff\xfe"), "")

    def test_tfidf_index(self):
        idx = TFIDFIndex()
        idx.build({"a": ["heap", "heap", "tree"], "b": ["tree", "hash"], "c": ["graph"]})
        self.assertEqual(idx.inverted["tree"], {"a", "b"})
        self.assertGreater(idx.idf["graph"], idx.idf["tree"])  # Rarer terms weigh more
        self.assertEqual(idx.search(["heap"])[0][0], "a")
        self.assertEqual(idx.search(["missing"]), [])
        self.assertAlmostEqual(TFIDFIndex.cosine(idx.vectors["a"], idx.vectors["a"]), 1.0, places=6)


class TestAIService(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.engine = SmartDriveEngine(FileStorageManager(self.tmp))
        self.ai = AIService(self.engine)
        self.notes = self.engine.upload_content("ml_notes.txt", NOTES, 5, "Course notes")["file_id"]
        self.copy = self.engine.upload_content("ml_notes_copy.txt", NOTES + " Extra line.", 3)["file_id"]
        self.engine.upload_content("budget.csv", "item,cost\nlaptop invoice,50000\nbank payment receipt,300", 4)
        self.engine.upload_content("same_a.txt", "identical content here", 2)
        self.engine.upload_content("same_b.txt", "identical content here", 2)
        self.engine.upload_content("report_v1.txt", "first draft of the report", 2)
        self.engine.upload_content("report_v2.txt", "second draft with changes", 2)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_semantic_search_ranks_by_content(self):
        res = self.ai.semantic_search("regression classification")
        self.assertIn(res[0]["file"].filename, {"ml_notes.txt", "ml_notes_copy.txt"})
        self.assertIn("regression", res[0]["matched_terms"])
        self.assertTrue(res[0]["snippet"])
        self.assertEqual(self.ai.semantic_search("quantum chromodynamics"), [])

    def test_ask_returns_relevant_sentence(self):
        ans = self.ai.ask("When is the exam deadline?")
        self.assertTrue(ans["found"])
        self.assertIn("deadline", ans["answers"][0]["text"])
        self.assertFalse(self.ai.ask("zebra migration patterns")["found"])

    def test_insights(self):
        f = self.engine.get_file_by_id(self.notes)
        ins = self.ai.insights(f)
        self.assertTrue(ins["has_text"])
        self.assertLessEqual(len(ins["summary"]), 3)
        self.assertTrue(all(" " not in k["term"] for k in ins["keywords"]))
        self.assertIn("Machine Learning", [t["tag"] for t in ins["tags"]])
        self.assertGreater(ins["priority"]["suggested"], 5)  # deadline / exam / assignment words
        self.assertEqual(ins["similar"][0]["file"].filename, "ml_notes_copy.txt")

    def test_index_refreshes_after_changes(self):
        self.assertEqual(self.ai.semantic_search("blockchain"), [])
        self.engine.update_content(self.notes, "Blockchain ledgers use Merkle trees.", "rewrite")
        self.assertEqual(self.ai.semantic_search("blockchain")[0]["file"].file_id, self.notes)

    def test_duplicates(self):
        d = self.ai.find_duplicates()
        self.assertEqual(len(d["exact"]), 1)
        self.assertEqual({f.filename for f in d["exact"][0]["files"]}, {"same_a.txt", "same_b.txt"})
        self.assertEqual(d["wasted_bytes"], len("identical content here"))
        self.assertTrue(any({f.filename for f in g["files"]} == {"ml_notes.txt", "ml_notes_copy.txt"} for g in d["near"]))
        name_pairs = [{f.filename for f in g["files"]} for g in d["similar_names"]]
        self.assertIn({"report_v1.txt", "report_v2.txt"}, name_pairs)
        self.assertNotIn({"same_a.txt", "same_b.txt"}, name_pairs)  # Already reported as exact duplicates


if __name__ == "__main__":
    unittest.main()
