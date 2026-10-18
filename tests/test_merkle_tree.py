"""
Unit tests for SmartDrive MerkleTree implementation.
Validates bottom-up cryptographic tree construction, odd/even leaf handling,
audit proof generation and verification, and tamper detection.
"""

import unittest
from data_structures.merkle_tree import MerkleTree, sha256_hash
from models.file_model import FileModel


class TestMerkleTree(unittest.TestCase):
    def test_empty_merkle_tree(self):
        tree = MerkleTree()
        self.assertTrue(tree.is_empty)
        self.assertEqual(len(tree), 0)
        self.assertIsNone(tree.root_hash)
        self.assertIsNone(tree.get_audit_proof("any_id"))
        self.assertEqual(tree.display_tree(), "<Empty Merkle Tree>")

    def test_single_leaf_tree(self):
        tree = MerkleTree()
        f1 = FileModel(filename="single.txt", file_size=100, sha256_hash="a" * 64)
        tree.build_from_files([f1])

        self.assertFalse(tree.is_empty)
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree.root_hash, "a" * 64)
        self.assertEqual(tree.get_audit_proof(f1.file_id), [])

    def test_even_leaves_tree(self):
        tree = MerkleTree()
        h1 = sha256_hash("file_content_1")
        h2 = sha256_hash("file_content_2")
        expected_root = sha256_hash(h1 + h2)

        f1 = FileModel(filename="f1.txt", file_size=10, sha256_hash=h1)
        f2 = FileModel(filename="f2.txt", file_size=20, sha256_hash=h2)

        tree.build_from_files([f1, f2])

        self.assertEqual(len(tree), 2)
        self.assertEqual(tree.root_hash, expected_root)

        # Audit proof for f1
        proof_f1 = tree.get_audit_proof(f1.file_id)
        self.assertIsNotNone(proof_f1)
        self.assertEqual(proof_f1, [(h2, 'right')])
        self.assertTrue(MerkleTree.verify_proof(h1, proof_f1, expected_root))

    def test_odd_leaves_tree(self):
        """Validates that odd leaf counts duplicate the last node to maintain binary balance."""
        tree = MerkleTree()
        h1 = sha256_hash("content_1")
        h2 = sha256_hash("content_2")
        h3 = sha256_hash("content_3")

        # 3 leaves: h1, h2, h3 -> h3 duplicated as h3
        # Level 1: H12 = H(h1 + h2), H33 = H(h3 + h3)
        # Root: H(H12 + H33)
        h12 = sha256_hash(h1 + h2)
        h33 = sha256_hash(h3 + h3)
        expected_root = sha256_hash(h12 + h33)

        f1 = FileModel(filename="f1.txt", file_size=10, sha256_hash=h1)
        f2 = FileModel(filename="f2.txt", file_size=20, sha256_hash=h2)
        f3 = FileModel(filename="f3.txt", file_size=30, sha256_hash=h3)

        tree.build_from_files([f1, f2, f3])

        self.assertEqual(len(tree), 3)
        self.assertEqual(tree.root_hash, expected_root)

        # Verify audit proof for f3
        proof_f3 = tree.get_audit_proof(f3.file_id)
        self.assertIsNotNone(proof_f3)
        self.assertTrue(MerkleTree.verify_proof(h3, proof_f3, expected_root))

    def test_tamper_detection(self):
        tree = MerkleTree()
        f1 = FileModel(filename="assignment.pdf", file_size=1000, sha256_hash=sha256_hash("legitimate_data"))
        f2 = FileModel(filename="report.docx", file_size=2000, sha256_hash=sha256_hash("report_data"))

        tree.build_from_files([f1, f2])

        # 1. Verification of legitimate hash
        valid, msg = tree.verify_file(f1.file_id, sha256_hash("legitimate_data"))
        self.assertTrue(valid)

        # 2. Verification of modified hash (tamper simulation)
        tampered_hash = sha256_hash("malicious_tampered_data")
        valid, msg = tree.verify_file(f1.file_id, tampered_hash)
        self.assertFalse(valid)
        self.assertIn("TAMPER DETECTED", msg)

        # 3. Drive-wide tamper audit
        current_hashes = {
            f1.file_id: tampered_hash,
            f2.file_id: sha256_hash("report_data"),
        }
        violations = tree.detect_tampered_files(current_hashes)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["filename"], "assignment.pdf")
        self.assertEqual(violations[0]["status"], "TAMPERED")

    def test_display_merkle_tree(self):
        tree = MerkleTree()
        files = [
            FileModel(filename=f"doc_{i}.txt", file_size=100 * i, sha256_hash=sha256_hash(f"c_{i}"))
            for i in range(1, 5)
        ]
        tree.build_from_files(files)
        display_str = tree.display_tree()
        self.assertIn("MerkleTree", display_str)
        self.assertIn("doc_1.txt", display_str)


if __name__ == "__main__":
    unittest.main()
