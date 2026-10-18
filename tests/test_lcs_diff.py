"""
Unit tests for SmartDrive LCS Diff algorithm.
Validates the LCS table, diff generation, statistics, and formatting.
"""

import unittest
from data_structures.lcs_diff import LCSDiff


class TestLCSDiff(unittest.TestCase):
    def test_lcs_table_classic(self):
        dp = LCSDiff.compute_lcs(list("ABCBDAB"), list("BDCABA"))
        self.assertEqual(dp[7][6], 4)

    def test_identical_texts(self):
        diff = LCSDiff.generate_diff("a\nb\nc", "a\nb\nc")
        self.assertTrue(all(op == ' ' for op, _ in diff))
        self.assertEqual(LCSDiff.diff_stats(diff)["similarity_pct"], 100.0)

    def test_add_remove_modify(self):
        old, new = "line1\nline2\nline3", "line1\nline2 changed\nline3\nline4"
        diff = LCSDiff.generate_diff(old, new)
        self.assertIn(('-', 'line2'), diff)
        self.assertIn(('+', 'line2 changed'), diff)
        self.assertIn(('+', 'line4'), diff)
        stats = LCSDiff.diff_stats(diff)
        self.assertEqual((stats["added"], stats["removed"], stats["unchanged"]), (2, 1, 2))
        self.assertEqual(LCSDiff.lcs_length(old, new), 2)

    def test_diff_reconstructs_both_versions(self):
        old, new = "x\ny\nz\nw", "y\nq\nz\nw\nv"
        diff = LCSDiff.generate_diff(old, new)
        self.assertEqual([l for op, l in diff if op != '+'], old.splitlines())
        self.assertEqual([l for op, l in diff if op != '-'], new.splitlines())

    def test_empty_inputs(self):
        self.assertEqual(LCSDiff.generate_diff("", ""), [])
        self.assertEqual(LCSDiff.generate_diff("", "a"), [('+', 'a')])
        self.assertEqual(LCSDiff.generate_diff("a", ""), [('-', 'a')])
        self.assertEqual(LCSDiff.diff_stats([])["similarity_pct"], 100.0)

    def test_format_plain_and_color(self):
        diff = [('-', 'old'), ('+', 'new'), (' ', 'same')]
        self.assertEqual(LCSDiff.format_diff(diff, use_color=False), "- old\n+ new\n  same")
        self.assertIn("\033[92m", LCSDiff.format_diff(diff))


if __name__ == "__main__":
    unittest.main()
