"""
Unit tests for the Phase 5 additions to the data structures:
heap arbitrary removal, AVL rotation log, visualization exports, knapsack DP table,
and the engine's metadata editing, fuzzy search, queue and stats.
"""

import unittest
import random
import tempfile
import shutil
from data_structures.avl_tree import AVLTree
from data_structures.binary_heap import MaxBinaryHeap
from data_structures.hash_table import HashTable
from data_structures.trie import Trie
from data_structures.knapsack import KnapsackOptimizer, KnapsackItem
from services.core_engine import SmartDriveEngine
from services.file_service import FileStorageManager


class TestStructureAdditions(unittest.TestCase):
    def test_heap_remove_where_keeps_heap_order(self):
        rng = random.Random(3)
        for _ in range(200):
            h = MaxBinaryHeap[int]()
            xs = [rng.randint(1, 10) for _ in range(rng.randint(0, 20))]
            for i, x in enumerate(xs): h.insert(x, i)
            drop = set(rng.sample(range(len(xs)), k=len(xs) // 2))
            self.assertEqual(h.remove_where(lambda v: v in drop), len(drop))
            self.assertEqual([p for p, _ in h.to_sorted_list()], sorted((x for i, x in enumerate(xs) if i not in drop), reverse=True))

    def test_avl_rotation_log(self):
        t = AVLTree[int, int]()
        t.insert(10, 10); t.insert(20, 20); t.insert(30, 30)
        self.assertEqual(t.rotation_log, ["RR at 10"])
        t.insert(25, 25); t.insert(28, 28)
        self.assertEqual(t.rotation_log, ["LR at 30"])  # 30 left-heavy, child 25 right-heavy
        t.insert(5, 5)
        self.assertEqual(t.rotation_log, [])

    def test_exports(self):
        t = AVLTree[int, str]()
        for k in [2, 1, 3]: t.insert(k, str(k))
        root = t.export_structure()
        self.assertEqual((root["key"], root["left"]["key"], root["right"]["key"], root["height"]), ("2", "1", "3", 2))
        ht = HashTable[str, int](capacity=4)
        for k in "abc": ht.insert(k, 1)
        exp = ht.export_structure()
        self.assertEqual(sum(len(b) for b in exp["buckets"]), 3)
        self.assertEqual(len(exp["buckets"]), exp["capacity"])
        tr = Trie[int]()
        tr.insert("car", 1); tr.insert("cat", 2)
        self.assertEqual(tr.count_nodes(), 5)  # root, c, a, r, t
        self.assertEqual(tr.export_structure("ca")["char"], "ca")
        self.assertIsNone(tr.export_structure("x"))
        h = MaxBinaryHeap[str]()
        h.insert(1, "a"); h.insert(9, "b")
        self.assertEqual(h.export_structure(label=str)[0]["priority"], 9)

    def test_knapsack_dp_table_matches_solver(self):
        rng = random.Random(5)
        for _ in range(40):
            items = [KnapsackItem(f"i{k}", rng.randint(0, 8), rng.randint(0, 9)) for k in range(rng.randint(0, 6))]
            opt = KnapsackOptimizer(items, rng.randint(0, 20))
            table = opt.dp_table()
            self.assertEqual(table["best"], opt.solve_dp().total_value)
            taken = [items[p["row"] - 1] for p in table["path"] if p["take"]]
            self.assertEqual(sum(i.value for i in taken), table["best"])
            self.assertLessEqual(sum(i.weight for i in taken), opt.capacity)
        with self.assertRaises(ValueError):
            KnapsackOptimizer([KnapsackItem("x", 1, 1)] * 10, 1000).dp_table()


class TestEnginePhase5(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.engine = SmartDriveEngine(FileStorageManager(self.tmp))
        for name, prio in [("alpha_notes.txt", 3), ("beta_report.txt", 7), ("gamma_slides.txt", 5)]:
            self.engine.upload_content(name, f"content of {name}", prio)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_priority_change_repositions_heap_and_persists(self):
        f = self.engine.get_file_by_name("alpha_notes.txt")
        self.engine.update_metadata(f.file_id, priority=10, tags=["urgent", "URGENT", " exam "], description="  ")
        self.assertEqual(self.engine.peek_highest_priority()[1].filename, "alpha_notes.txt")
        self.assertEqual(len(self.engine.heap), 3)  # No duplicate heap entry
        self.assertEqual(f.tags, ["urgent", "exam"])
        self.assertIsNone(f.description)
        reloaded = SmartDriveEngine(FileStorageManager(self.tmp)).get_file_by_name("alpha_notes.txt")
        self.assertEqual((reloaded.priority, reloaded.tags), (10, ["urgent", "exam"]))
        with self.assertRaises(ValueError):
            self.engine.update_metadata(f.file_id, priority=11)
        self.assertIsNone(self.engine.update_metadata("missing", priority=5))

    def test_queue_snapshot_and_requeue(self):
        self.assertEqual([f.filename for _, f in self.engine.queue_snapshot()], ["beta_report.txt", "gamma_slides.txt", "alpha_notes.txt"])
        self.engine.process_next_priority_file()
        self.assertEqual(len(self.engine.queue_snapshot()), 2)
        self.assertEqual(self.engine.requeue_all(), 3)
        self.assertEqual(self.engine.peek_highest_priority()[0], 7)

    def test_delete_removes_from_heap(self):
        self.engine.delete_file("beta_report.txt")
        self.assertEqual(len(self.engine.heap), 2)

    def test_fuzzy_search(self):
        names = lambda q: [r["file"].filename for r in self.engine.fuzzy_search(q)]
        self.assertEqual(names("alp"), ["alpha_notes.txt"])            # Trie prefix
        self.assertEqual(names("reprot"), ["beta_report.txt"])         # Transposition = 2 edits
        self.assertEqual(names("slides"), ["gamma_slides.txt"])        # Word inside the name
        self.assertEqual(names("zzzzzz"), [])
        self.assertEqual(self.engine.did_you_mean("gama"), "gamma")

    def test_stats_and_explorer(self):
        st = self.engine.get_stats()
        self.assertEqual((st["total_files"], st["total_versions"], st["heap"]["top"]["filename"]), (3, 3, "beta_report.txt"))
        for s in ["avl", "hash", "trie", "heap", "merkle"]:
            self.assertEqual(self.engine.explorer_snapshot(s)["structure"], s)
        with self.assertRaises(ValueError):
            self.engine.explorer_snapshot("graph")


if __name__ == "__main__":
    unittest.main()
