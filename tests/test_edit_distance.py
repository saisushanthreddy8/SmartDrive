"""
Unit tests for SmartDrive Levenshtein Edit Distance.
Validates the DP table, the space-optimised distance, early exit, similarity, matching and alignment.
"""

import unittest
import random
from data_structures.edit_distance import EditDistance


def naive(a, b):
    if not a: return len(b)
    if not b: return len(a)
    return min(naive(a[1:], b) + 1, naive(a, b[1:]) + 1, naive(a[1:], b[1:]) + (a[0] != b[0]))


class TestEditDistance(unittest.TestCase):
    def test_classic_examples(self):
        self.assertEqual(EditDistance.distance("kitten", "sitting"), 3)
        self.assertEqual(EditDistance.distance("", "abc"), 3)
        self.assertEqual(EditDistance.distance("abc", "abc"), 0)
        self.assertEqual(EditDistance.compute_table("kitten", "sitting")[6][7], 3)

    def test_matches_naive_recursion(self):
        rng = random.Random(7)
        for _ in range(150):
            a = "".join(rng.choice("abc") for _ in range(rng.randint(0, 6)))
            b = "".join(rng.choice("abc") for _ in range(rng.randint(0, 6)))
            self.assertEqual(EditDistance.distance(a, b), naive(a, b))
            self.assertEqual(EditDistance.compute_table(a, b)[len(a)][len(b)], naive(a, b))

    def test_early_exit(self):
        self.assertGreater(EditDistance.distance("aaaaaaaa", "bbbbbbbb", max_dist=2), 2)

    def test_similarity_and_best_matches(self):
        self.assertEqual(EditDistance.similarity("", ""), 1.0)
        self.assertAlmostEqual(EditDistance.similarity("abcd", "abcf"), 0.75)
        self.assertEqual(EditDistance.best_matches("machne", ["machine", "report", "mach"])[0], ("machine", 1))
        self.assertEqual(EditDistance.best_matches("zzzz", ["machine"]), [])

    def test_alignment_is_consistent(self):
        ops = EditDistance.alignment("kitten", "sitting")
        self.assertEqual(sum(o != "=" for o, _, _ in ops), 3)
        self.assertEqual("".join(x for o, x, _ in ops if o != "+"), "kitten")
        self.assertEqual("".join(y for o, _, y in ops if o != "-"), "sitting")


if __name__ == "__main__":
    unittest.main()
