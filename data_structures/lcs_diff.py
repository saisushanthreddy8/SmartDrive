"""
SmartDrive - LCS Diff Algorithm
Implements the Longest Common Subsequence algorithm for text differencing.
"""
from typing import List, Tuple, Any, Dict

class LCSDiff:
    @staticmethod
    def compute_lcs(seq1: List[Any], seq2: List[Any]) -> List[List[int]]:
        """dp[i][j] = length of the LCS of seq1[:i] and seq2[:j]."""
        m, n = len(seq1), len(seq2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if seq1[i - 1] == seq2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        return dp

    @staticmethod
    def trace(seq1: List[Any], seq2: List[Any]) -> Tuple[List[List[int]], List[Tuple[int, int]], List[Any]]:
        """Table, the cells visited while backtracking, and the common subsequence itself (for the web explorer)."""
        dp = LCSDiff.compute_lcs(seq1, seq2)
        i, j, path, common = len(seq1), len(seq2), [], []
        while i > 0 and j > 0:
            path.append((i, j))
            if seq1[i - 1] == seq2[j - 1]:
                common.append(seq1[i - 1])
                i, j = i - 1, j - 1
            elif dp[i - 1][j] > dp[i][j - 1]: i -= 1
            else: j -= 1
        return dp, path[::-1], common[::-1]

    @staticmethod
    def generate_diff(old_text: str, new_text: str) -> List[Tuple[str, str]]:
        """
        Generates a line-by-line diff using the LCS matrix.
        Returns a list of tuples (operation, text), where operation is '-', '+', or ' '.
        """
        old_lines, new_lines = old_text.splitlines(), new_text.splitlines()
        dp = LCSDiff.compute_lcs(old_lines, new_lines)
        i, j, diff = len(old_lines), len(new_lines), []
        while i > 0 and j > 0:
            if old_lines[i - 1] == new_lines[j - 1]:
                diff.append((' ', old_lines[i - 1]))
                i -= 1
                j -= 1
            elif dp[i - 1][j] > dp[i][j - 1]:
                diff.append(('-', old_lines[i - 1]))
                i -= 1
            else:
                diff.append(('+', new_lines[j - 1]))
                j -= 1

        while i > 0:
            diff.append(('-', old_lines[i - 1]))
            i -= 1
        while j > 0:
            diff.append(('+', new_lines[j - 1]))
            j -= 1

        return diff[::-1]  # Reverse because we built it backwards

    @staticmethod
    def lcs_length(old_text: str, new_text: str) -> int:
        """Returns the number of lines common to both versions (LCS length)."""
        a, b = old_text.splitlines(), new_text.splitlines()
        return LCSDiff.compute_lcs(a, b)[len(a)][len(b)]

    @staticmethod
    def diff_stats(diff: List[Tuple[str, str]]) -> Dict[str, Any]:
        """Summarises a diff: lines added / removed / unchanged and similarity %."""
        ops = [op for op, _ in diff]
        added, removed, unchanged = ops.count('+'), ops.count('-'), ops.count(' ')
        old_n, new_n = unchanged + removed, unchanged + added
        similarity = (2 * unchanged / (old_n + new_n) * 100) if (old_n + new_n) else 100.0
        return {"added": added, "removed": removed, "unchanged": unchanged, "similarity_pct": round(similarity, 2)}

    @staticmethod
    def format_diff(diff: List[Tuple[str, str]], use_color: bool = True) -> str:
        """Readable diff for the CLI (green + / red -; colours optional)."""
        colors = {'+': "\033[92m", '-': "\033[91m"}
        lines = []
        for op, line in diff:
            text = f"{op} {line}"
            lines.append(f"{colors[op]}{text}\033[0m" if use_color and op in colors else text)
        return "\n".join(lines)
