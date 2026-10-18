"""
Unit tests for SmartDrive AVL Tree implementation.
Validates all 4 rotation scenarios (LL, RR, LR, RL), insertion, deletion, traversals,
range searches, and the AVL balancing invariant using standard unittest.
"""

import unittest
from data_structures.avl_tree import AVLTree, AVLNode
from models.file_model import FileModel


def verify_avl_invariant(node: AVLNode) -> bool:
    """Helper to verify that every node in the subtree strictly satisfies the AVL balance property."""
    if node is None:
        return True

    left_h = node.left.height if node.left else 0
    right_h = node.right.height if node.right else 0

    # Height invariant
    if node.height != 1 + max(left_h, right_h):
        return False

    # Balance Factor invariant: must be in {-1, 0, +1}
    if abs(left_h - right_h) > 1:
        return False

    return verify_avl_invariant(node.left) and verify_avl_invariant(node.right)


class TestAVLTree(unittest.TestCase):
    def test_empty_tree(self):
        tree = AVLTree[str, int]()
        self.assertTrue(tree.is_empty)
        self.assertEqual(len(tree), 0)
        self.assertIsNone(tree.search("test"))
        self.assertFalse(tree.contains("test"))
        self.assertFalse(tree.delete("test"))
        self.assertIsNone(tree.get_min())
        self.assertIsNone(tree.get_max())
        self.assertEqual(tree.inorder_traversal(), [])
        self.assertEqual(tree.display_tree(), "<Empty AVL Tree>")

    def test_single_insert(self):
        tree = AVLTree[str, str]()
        tree.insert("file_a", "payload_a")
        self.assertFalse(tree.is_empty)
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree.search("file_a"), "payload_a")
        self.assertTrue(tree.contains("file_a"))
        self.assertEqual(tree.get_height(tree.root), 1)
        self.assertEqual(tree.get_balance_factor(tree.root), 0)
        self.assertEqual(tree.get_min(), ("file_a", "payload_a"))
        self.assertEqual(tree.get_max(), ("file_a", "payload_a"))

    def test_duplicate_key_update(self):
        tree = AVLTree[str, str]()
        tree.insert("report.pdf", "version_1")
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree.search("report.pdf"), "version_1")

        # Update existing key
        tree.insert("report.pdf", "version_2")
        self.assertEqual(len(tree), 1)
        self.assertEqual(tree.search("report.pdf"), "version_2")

    def test_ll_rotation_right_rotate(self):
        """
        Left-Left (LL) Case:
        Insert descending keys [30, 20, 10]
        Triggers Right Rotation at node 30.
        Expected root: 20, left: 10, right: 30.
        """
        tree = AVLTree[int, str]()
        tree.insert(30, "val30")
        tree.insert(20, "val20")
        tree.insert(10, "val10")

        self.assertEqual(tree.root.key, 20)
        self.assertEqual(tree.root.left.key, 10)
        self.assertEqual(tree.root.right.key, 30)
        self.assertEqual(tree.root.height, 2)
        self.assertEqual(tree.root.balance_factor, 0)
        self.assertTrue(verify_avl_invariant(tree.root))

    def test_rr_rotation_left_rotate(self):
        """
        Right-Right (RR) Case:
        Insert ascending keys [10, 20, 30]
        Triggers Left Rotation at node 10.
        Expected root: 20, left: 10, right: 30.
        """
        tree = AVLTree[int, str]()
        tree.insert(10, "val10")
        tree.insert(20, "val20")
        tree.insert(30, "val30")

        self.assertEqual(tree.root.key, 20)
        self.assertEqual(tree.root.left.key, 10)
        self.assertEqual(tree.root.right.key, 30)
        self.assertEqual(tree.root.height, 2)
        self.assertEqual(tree.root.balance_factor, 0)
        self.assertTrue(verify_avl_invariant(tree.root))

    def test_lr_rotation_double_left_right(self):
        """
        Left-Right (LR) Case:
        Insert keys [30, 10, 20]
        Triggers Left Rotation on 10, then Right Rotation on 30.
        Expected root: 20, left: 10, right: 30.
        """
        tree = AVLTree[int, str]()
        tree.insert(30, "val30")
        tree.insert(10, "val10")
        tree.insert(20, "val20")

        self.assertEqual(tree.root.key, 20)
        self.assertEqual(tree.root.left.key, 10)
        self.assertEqual(tree.root.right.key, 30)
        self.assertEqual(tree.root.height, 2)
        self.assertTrue(verify_avl_invariant(tree.root))

    def test_rl_rotation_double_right_left(self):
        """
        Right-Left (RL) Case:
        Insert keys [10, 30, 20]
        Triggers Right Rotation on 30, then Left Rotation on 10.
        Expected root: 20, left: 10, right: 30.
        """
        tree = AVLTree[int, str]()
        tree.insert(10, "val10")
        tree.insert(30, "val30")
        tree.insert(20, "val20")

        self.assertEqual(tree.root.key, 20)
        self.assertEqual(tree.root.left.key, 10)
        self.assertEqual(tree.root.right.key, 30)
        self.assertEqual(tree.root.height, 2)
        self.assertTrue(verify_avl_invariant(tree.root))

    def test_deletion_leaf_and_single_child(self):
        tree = AVLTree[int, str]()
        for k in [20, 10, 30, 5]:
            tree.insert(k, f"val_{k}")

        self.assertEqual(len(tree), 4)
        # Delete leaf node 5
        self.assertTrue(tree.delete(5))
        self.assertEqual(len(tree), 3)
        self.assertFalse(tree.contains(5))
        self.assertTrue(verify_avl_invariant(tree.root))

        # Delete node 10 (which now has no children)
        self.assertTrue(tree.delete(10))
        self.assertEqual(len(tree), 2)
        self.assertFalse(tree.contains(10))
        self.assertTrue(verify_avl_invariant(tree.root))

    def test_deletion_two_children_and_rebalance(self):
        tree = AVLTree[int, str]()
        # Insert keys into a balanced tree
        keys = [50, 25, 75, 10, 35, 60, 90, 5, 15, 30, 40]
        for k in keys:
            tree.insert(k, f"val_{k}")

        self.assertEqual(len(tree), len(keys))
        self.assertTrue(verify_avl_invariant(tree.root))

        # Delete node with 2 children (25)
        self.assertTrue(tree.delete(25))
        self.assertEqual(len(tree), len(keys) - 1)
        self.assertFalse(tree.contains(25))
        self.assertTrue(verify_avl_invariant(tree.root))

        # Delete root (50)
        self.assertTrue(tree.delete(50))
        self.assertFalse(tree.contains(50))
        self.assertTrue(verify_avl_invariant(tree.root))

    def test_traversals(self):
        tree = AVLTree[int, str]()
        for k in [40, 20, 60, 10, 30, 50, 70]:
            tree.insert(k, f"v{k}")

        inorder_keys = [k for k, _ in tree.inorder_traversal()]
        self.assertEqual(inorder_keys, [10, 20, 30, 40, 50, 60, 70])

        preorder_keys = [k for k, _ in tree.preorder_traversal()]
        self.assertEqual(preorder_keys, [40, 20, 10, 30, 60, 50, 70])

        postorder_keys = [k for k, _ in tree.postorder_traversal()]
        self.assertEqual(postorder_keys, [10, 30, 20, 50, 70, 60, 40])

        levelorder_keys = [k for k, _ in tree.level_order_traversal()]
        self.assertEqual(levelorder_keys, [40, 20, 60, 10, 30, 50, 70])

    def test_range_search(self):
        tree = AVLTree[int, str]()
        for k in [10, 20, 30, 40, 50, 60, 70, 80, 90]:
            tree.insert(k, f"val_{k}")

        ranged = tree.range_search(25, 65)
        ranged_keys = [k for k, _ in ranged]
        self.assertEqual(ranged_keys, [30, 40, 50, 60])

    def test_avl_with_file_model(self):
        """Validates indexing FileModel domain instances inside AVLTree."""
        tree = AVLTree[str, FileModel]()

        files = [
            FileModel(filename="report.pdf", file_size=2048, priority=5),
            FileModel(filename="assignment.docx", file_size=4096, priority=10),
            FileModel(filename="photo.png", file_size=1024, priority=2),
            FileModel(filename="lecture.mp4", file_size=81920, priority=8),
            FileModel(filename="backup.zip", file_size=16384, priority=4),
        ]

        for f in files:
            tree.insert(f.filename, f)

        self.assertEqual(len(tree), 5)
        self.assertTrue(verify_avl_invariant(tree.root))

        # Search for specific file
        retrieved = tree.search("lecture.mp4")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.priority, 8)
        self.assertEqual(retrieved.file_type, "Video")

        # Sorted in-order filenames
        sorted_filenames = [k for k, _ in tree.inorder_traversal()]
        self.assertEqual(sorted_filenames, sorted([f.filename for f in files]))

        # Delete one file
        self.assertTrue(tree.delete("assignment.docx"))
        self.assertEqual(len(tree), 4)
        self.assertFalse(tree.contains("assignment.docx"))
        self.assertTrue(verify_avl_invariant(tree.root))


if __name__ == "__main__":
    unittest.main()
