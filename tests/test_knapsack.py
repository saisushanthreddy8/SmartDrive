"""
Unit tests for SmartDrive 0/1 Knapsack Storage Optimizer.
Validates DP and Branch & Bound optimality against brute force, Greedy sub-optimality,
edge cases, and SmartDriveEngine integration.
"""

import unittest
import random
from itertools import combinations
from data_structures.knapsack import KnapsackOptimizer, KnapsackItem
from models.file_model import FileModel
from services.core_engine import SmartDriveEngine


def brute_force(items, capacity):
    best = 0
    for r in range(len(items) + 1):
        for combo in combinations(items, r):
            if sum(i.weight for i in combo) <= capacity:
                best = max(best, sum(i.value for i in combo))
    return best


class TestKnapsackOptimizer(unittest.TestCase):
    def setUp(self):
        # Classic counter-example where ratio-greedy is NOT optimal
        self.items = [KnapsackItem("A", 10, 60), KnapsackItem("B", 20, 100), KnapsackItem("C", 30, 120)]
        self.opt = KnapsackOptimizer(self.items, 50)

    def test_dp_optimal(self):
        res = self.opt.solve_dp()
        self.assertEqual(res.total_value, 220)
        self.assertEqual([i.label for i in res.selected], ["B", "C"])
        self.assertEqual(res.total_weight, 50)

    def test_branch_and_bound_optimal(self):
        res = self.opt.solve_branch_and_bound()
        self.assertEqual(res.total_value, 220)
        self.assertEqual([i.label for i in res.selected], ["B", "C"])
        self.assertGreater(res.nodes_explored, 0)

    def test_greedy_suboptimal_but_valid(self):
        res = self.opt.solve_greedy()
        self.assertEqual(res.total_value, 160)
        self.assertLessEqual(res.total_weight, 50)

    def test_compare_all_flags_optimality(self):
        results = {r.method: r for r in self.opt.compare_all()}
        self.assertTrue(results["Dynamic Programming"].is_optimal)
        self.assertTrue(results["Branch & Bound"].is_optimal)
        self.assertFalse(results["Greedy (Ratio)"].is_optimal)
        self.assertIn("Knapsack Comparison", KnapsackOptimizer.display_comparison(list(results.values())))

    def test_random_instances_match_brute_force(self):
        rng = random.Random(42)
        for _ in range(60):
            n = rng.randint(0, 10)
            items = [KnapsackItem(f"f{k}", rng.randint(0, 25), rng.randint(0, 10)) for k in range(n)]
            cap = rng.randint(0, 60)
            expected = brute_force(items, cap)
            opt = KnapsackOptimizer(items, cap)
            for res in (opt.solve_dp(), opt.solve_branch_and_bound()):
                self.assertEqual(res.total_value, expected, res.method)
                self.assertLessEqual(res.total_weight, cap)
            g = opt.solve_greedy()
            self.assertLessEqual(g.total_value, expected)
            self.assertLessEqual(g.total_weight, cap)

    def test_edge_cases(self):
        self.assertEqual(KnapsackOptimizer([], 100).solve_dp().total_value, 0)
        self.assertEqual(KnapsackOptimizer(self.items, 0).solve_branch_and_bound().total_value, 0)
        zero = KnapsackOptimizer([KnapsackItem("empty", 0, 5), KnapsackItem("big", 99, 9)], 10)
        for res in (zero.solve_dp(), zero.solve_greedy(), zero.solve_branch_and_bound()):
            self.assertEqual(res.total_value, 5)
        with self.assertRaises(ValueError):
            KnapsackItem("bad", -1, 5)
        with self.assertRaises(ValueError):
            KnapsackOptimizer(self.items, -1)

    def test_dp_memory_guard(self):
        opt = KnapsackOptimizer(self.items, KnapsackOptimizer.MAX_DP_CELLS)
        with self.assertRaises(MemoryError):
            opt.solve_dp()
        # compare_all still returns Greedy + B&B when DP is skipped
        self.assertEqual(len(opt.compare_all()), 2)


class TestEngineStorageOptimization(unittest.TestCase):
    def setUp(self):
        self.engine = SmartDriveEngine()
        for name, size, prio in [("a.pdf", 3000, 9), ("b.pdf", 5000, 6), ("c.pdf", 4000, 8), ("d.pdf", 1000, 2)]:
            self.engine.register_file(FileModel(filename=name, file_size=size, priority=prio))

    def test_optimize_storage_methods(self):
        cap = 8 * 1024  # 8 KB
        dp = self.engine.optimize_storage(cap, "dp")
        bnb = self.engine.optimize_storage(cap, "bnb")
        self.assertEqual(dp.total_value, bnb.total_value)
        self.assertEqual(dp.total_value, 19)  # a + c + d
        self.assertLessEqual(sum(i.payload.file_size for i in dp.selected), cap)
        self.assertIsInstance(dp.selected[0].payload, FileModel)

    def test_invalid_method_and_capacity(self):
        with self.assertRaises(ValueError):
            self.engine.optimize_storage(1024, "magic")
        with self.assertRaises(ValueError):
            self.engine.optimize_storage(-1, "dp")


if __name__ == "__main__":
    unittest.main()
