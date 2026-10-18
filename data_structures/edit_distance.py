"""
SmartDrive - Levenshtein Edit Distance
Dynamic-programming edit distance for typo-tolerant ("fuzzy") filename search and "did you mean" suggestions.
"""
from typing import List, Tuple, Optional, Iterable

class EditDistance:
    @staticmethod
    def compute_table(a: str, b: str) -> List[List[int]]:
        """
        Full DP table: dp[i][j] = edits to turn a[:i] into b[:j]
        (insert, delete, substitute each cost 1). O(m*n) time and space.
        """
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1): dp[i][0] = i
        for j in range(n + 1): dp[0][j] = j
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if a[i - 1] == b[j - 1] else 1
                dp[i][j] = min(dp[i - 1][j] + 1,         # Delete
                               dp[i][j - 1] + 1,         # Insert
                               dp[i - 1][j - 1] + cost)  # Substitute / match
        return dp

    @staticmethod
    def distance(a: str, b: str, max_dist: Optional[int] = None) -> int:
        """Two-row DP: O(m*n) time, O(min(m, n)) space. Stops early once every cell exceeds max_dist."""
        if len(a) < len(b): a, b = b, a
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i] + [0] * len(b)
            for j, cb in enumerate(b, 1):
                cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
            if max_dist is not None and min(cur) > max_dist: return max_dist + 1
            prev = cur
        return prev[-1]

    @staticmethod
    def similarity(a: str, b: str) -> float:
        """1.0 = identical, 0.0 = completely different (normalised by the longer string)."""
        longest = max(len(a), len(b))
        return 1.0 if longest == 0 else 1 - EditDistance.distance(a, b) / longest

    @staticmethod
    def best_matches(query: str, candidates: Iterable[str], limit: int = 5, max_ratio: float = 0.4) -> List[Tuple[str, int]]:
        """Candidates within max_ratio * len(query) edits, closest first."""
        q = query.lower()
        budget = max(1, int(len(q) * max_ratio))
        scored = []
        for c in candidates:
            d = EditDistance.distance(q, c.lower(), budget)
            if d <= budget: scored.append((c, d))
        return sorted(scored, key=lambda x: (x[1], x[0]))[:limit]

    @staticmethod
    def backtrack(a: str, b: str) -> Tuple[List[Tuple[str, str, str]], List[Tuple[int, int]]]:
        """
        Walks the table from the bottom-right corner back to (0, 0).
        Returns the edit operations ('=' keep, '~' replace, '-' delete, '+' insert) and the cells visited.
        """
        dp, i, j = EditDistance.compute_table(a, b), len(a), len(b)
        ops, cells = [], [(i, j)]
        while i > 0 or j > 0:
            if i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
                ops.append(('=' if a[i - 1] == b[j - 1] else '~', a[i - 1], b[j - 1]))
                i, j = i - 1, j - 1
            elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
                ops.append(('-', a[i - 1], ''))
                i -= 1
            else:
                ops.append(('+', '', b[j - 1]))
                j -= 1
            cells.append((i, j))
        return ops[::-1], cells[::-1]

    @staticmethod
    def alignment(a: str, b: str) -> List[Tuple[str, str, str]]:
        return EditDistance.backtrack(a, b)[0]
