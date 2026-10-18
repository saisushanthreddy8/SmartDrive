"""
SmartDrive - Prefix Trie Implementation
Each edge is one character, so names that share a beginning share a path.
Prefix lookup costs O(k) for a prefix of length k.
"""
from typing import TypeVar, Generic, Optional, List, Tuple, Dict, Any

V = TypeVar('V')

class TrieNode(Generic[V]):
    def __init__(self):
        self.children: Dict[str, 'TrieNode[V]'] = {}
        self.is_end_of_word = False
        self.value: Optional[V] = None
        self.full_word: Optional[str] = None  # Original spelling (the trie itself may be lowercased)

class Trie(Generic[V]):
    def __init__(self, case_sensitive: bool = False):
        self.root: TrieNode[V] = TrieNode()
        self.case_sensitive = case_sensitive
        self._size = 0

    def __len__(self) -> int: return self._size
    @property
    def is_empty(self) -> bool: return self._size == 0
    def _norm(self, s: str) -> str: return s if self.case_sensitive else s.lower()

    def _find(self, prefix: str) -> Optional[TrieNode[V]]:
        """Follows the prefix one character at a time; None if the path breaks."""
        node = self.root
        for char in self._norm(prefix):
            node = node.children.get(char)
            if node is None: return None
        return node

    # --- Insertion ---
    def insert(self, word: str, value: V) -> None:
        if not word: return
        node = self.root
        for char in self._norm(word):
            node = node.children.setdefault(char, TrieNode())
        if not node.is_end_of_word:
            self._size += 1
            node.is_end_of_word = True
        node.value, node.full_word = value, word

    # --- Search & Autocomplete ---
    def search_exact(self, word: str) -> Optional[V]:
        node = self._find(word) if word else None
        return node.value if node and node.is_end_of_word else None

    def starts_with(self, prefix: str) -> bool:
        return not self.is_empty if not prefix else self._find(prefix) is not None

    def autocomplete(self, prefix: str = "", limit: Optional[int] = None) -> List[Tuple[str, V]]:
        """Every word under the prefix node, in alphabetical order (DFS over sorted children)."""
        start = self._find(prefix)
        results: List[Tuple[str, V]] = []
        def collect(node: TrieNode[V]) -> None:
            if limit and len(results) >= limit: return
            if node.is_end_of_word and node.value is not None: results.append((node.full_word, node.value))
            for char in sorted(node.children): collect(node.children[char])
        if start: collect(start)
        return results[:limit] if limit else results

    def get_all_words(self, limit: Optional[int] = None) -> List[Tuple[str, V]]:
        return self.autocomplete("", limit)

    # --- Deletion ---
    def delete(self, word: str) -> bool:
        """Unmarks the word, then prunes nodes that no longer lead to any word."""
        if not word or not self._is_word(word): return False
        path, node = [], self.root
        for char in self._norm(word):
            path.append((node, char))
            node = node.children[char]
        node.is_end_of_word, node.value, node.full_word = False, None, None
        self._size -= 1
        for parent, char in reversed(path):  # Prune bottom-up
            child = parent.children[char]
            if child.children or child.is_end_of_word: break
            del parent.children[char]
        return True

    def _is_word(self, word: str) -> bool:
        node = self._find(word)
        return bool(node and node.is_end_of_word)

    # --- Display ---
    def count_nodes(self) -> int:
        stack, count = [self.root], 0
        while stack:
            count += 1
            stack.extend(stack.pop().children.values())
        return count

    def export_structure(self, prefix: str = "", max_nodes: int = 400) -> Optional[Dict[str, Any]]:
        """Nested JSON of the sub-trie under `prefix` (at most max_nodes nodes) for the web Algorithm Explorer."""
        start = self._find(prefix)
        if start is None: return None
        budget = [max_nodes]
        def export(node: TrieNode[V], char: str) -> Dict[str, Any]:
            budget[0] -= 1
            kids = []
            for c in sorted(node.children):
                if budget[0] <= 0: break
                kids.append(export(node.children[c], c))
            return {"char": char, "end": node.is_end_of_word, "word": node.full_word, "children": kids,
                    "truncated": len(kids) < len(node.children)}
        return export(start, self._norm(prefix) or "root")

    def display_trie(self) -> str:
        if self.is_empty: return "<Empty Trie>"
        lines = [f"PrefixTrie [Words={self._size}]"]
        def draw(node: TrieNode[V], prefix: str) -> None:
            chars = sorted(node.children)
            for i, c in enumerate(chars):
                child, last = node.children[c], i == len(chars) - 1
                mark = f" (✓ '{child.full_word}')" if child.is_end_of_word else ""
                lines.append(f"{prefix}{'└── ' if last else '├── '}{c}{mark}")
                draw(child, prefix + ("    " if last else "│   "))
        draw(self.root, "")
        return "\n".join(lines)
