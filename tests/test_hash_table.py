"""
Unit tests for SmartDrive Separate-Chaining HashTable implementation.
Validates O(1) operations, collision resolution chains, dynamic resizing/rehashing,
deletion mechanics, and diagnostic statistics.
"""

import unittest
from data_structures.hash_table import HashTable
from models.file_model import FileModel


class TestHashTable(unittest.TestCase):
    def test_empty_table(self):
        ht = HashTable[str, int]()
        self.assertTrue(ht.is_empty)
        self.assertEqual(len(ht), 0)
        self.assertEqual(ht.capacity, 16)
        self.assertEqual(ht.load_factor, 0.0)
        self.assertIsNone(ht.search("missing"))
        self.assertFalse(ht.contains("missing"))
        self.assertFalse(ht.delete("missing"))
        self.assertEqual(ht.keys(), [])
        self.assertEqual(ht.values(), [])
        self.assertEqual(ht.items(), [])

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            HashTable(capacity=0)
        with self.assertRaises(ValueError):
            HashTable(max_load_factor=-0.5)

    def test_insert_and_search(self):
        ht = HashTable[str, str]()
        ht.insert("file_1", "meta_1")
        ht.insert("file_2", "meta_2")

        self.assertEqual(len(ht), 2)
        self.assertFalse(ht.is_empty)
        self.assertEqual(ht.search("file_1"), "meta_1")
        self.assertEqual(ht.search("file_2"), "meta_2")
        self.assertIsNone(ht.search("file_3"))

    def test_duplicate_key_update(self):
        ht = HashTable[str, int]()
        ht.insert("count", 1)
        self.assertEqual(len(ht), 1)
        self.assertEqual(ht.search("count"), 1)

        ht.insert("count", 2)
        self.assertEqual(len(ht), 1)
        self.assertEqual(ht.search("count"), 2)

    def test_collision_handling_separate_chaining(self):
        # Create a small table with capacity=4 to intentionally induce collisions
        ht = HashTable[str, int](capacity=4, max_load_factor=10.0)

        # Insert multiple keys
        keys = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]
        for idx, k in enumerate(keys):
            ht.insert(k, idx * 10)

        self.assertEqual(len(ht), len(keys))
        for idx, k in enumerate(keys):
            self.assertEqual(ht.search(k), idx * 10)

        # Check collision statistics
        stats = ht.get_collision_stats()
        self.assertEqual(stats["total_keys"], 8)
        self.assertGreater(stats["total_collisions"], 0)
        self.assertGreater(stats["max_chain_length"], 1)

    def test_deletion_mechanics(self):
        ht = HashTable[str, int](capacity=4, max_load_factor=10.0)
        ht.insert("k1", 100)
        ht.insert("k2", 200)
        ht.insert("k3", 300)

        self.assertEqual(len(ht), 3)

        # Delete existing key
        self.assertTrue(ht.delete("k2"))
        self.assertEqual(len(ht), 2)
        self.assertIsNone(ht.search("k2"))
        self.assertFalse(ht.contains("k2"))

        # Delete non-existent key
        self.assertFalse(ht.delete("non_existent"))
        self.assertEqual(len(ht), 2)

        # Delete remaining keys
        self.assertTrue(ht.delete("k1"))
        self.assertTrue(ht.delete("k3"))
        self.assertEqual(len(ht), 0)
        self.assertTrue(ht.is_empty)

    def test_dynamic_resizing_and_rehashing(self):
        # Start with capacity=4, max_load_factor=0.5
        # Re-hash will trigger when size exceeds 4 * 0.5 = 2 keys
        ht = HashTable[int, str](capacity=4, max_load_factor=0.5)

        ht.insert(1, "one")
        ht.insert(2, "two")
        self.assertEqual(ht.capacity, 4)

        # Inserting 3rd element triggers resize to capacity=8
        ht.insert(3, "three")
        self.assertEqual(ht.capacity, 8)
        self.assertEqual(len(ht), 3)
        self.assertEqual(ht.search(1), "one")
        self.assertEqual(ht.search(2), "two")
        self.assertEqual(ht.search(3), "three")

        # Insert more to trigger another resize to capacity=16
        for i in range(4, 10):
            ht.insert(i, f"num_{i}")

        self.assertGreaterEqual(ht.capacity, 16)
        self.assertEqual(len(ht), 9)
        for i in range(1, 10):
            self.assertEqual(ht.search(i), f"num_{i}" if i >= 4 else {1: "one", 2: "two", 3: "three"}[i])

    def test_keys_values_items(self):
        ht = HashTable[str, int]()
        data = {"a": 1, "b": 2, "c": 3, "d": 4}
        for k, v in data.items():
            ht.insert(k, v)

        self.assertEqual(set(ht.keys()), set(data.keys()))
        self.assertEqual(set(ht.values()), set(data.values()))
        self.assertEqual(set(ht.items()), set(data.items()))

    def test_hash_table_with_file_model(self):
        """Validates storing and retrieving FileModel instances by File ID and Filename."""
        ht_by_id = HashTable[str, FileModel]()
        ht_by_name = HashTable[str, FileModel]()

        f1 = FileModel(filename="report.pdf", file_size=1024, priority=8)
        f2 = FileModel(filename="dataset.csv", file_size=2048, priority=4)
        f3 = FileModel(filename="diagram.png", file_size=512, priority=2)

        for f in [f1, f2, f3]:
            ht_by_id.insert(f.file_id, f)
            ht_by_name.insert(f.filename, f)

        self.assertEqual(len(ht_by_id), 3)
        self.assertEqual(len(ht_by_name), 3)

        # Query by ID
        res_id = ht_by_id.search(f1.file_id)
        self.assertIsNotNone(res_id)
        self.assertEqual(res_id.filename, "report.pdf")

        # Query by Filename
        res_name = ht_by_name.search("dataset.csv")
        self.assertIsNotNone(res_name)
        self.assertEqual(res_name.file_size, 2048)

        # Display test
        display_str = ht_by_name.display_table()
        self.assertIn("HashTable", display_str)


if __name__ == "__main__":
    unittest.main()
