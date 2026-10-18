"""
SmartDrive - Self-Balancing AVL Tree
Keeps filenames sorted. Insert, delete and search are O(log n) because the tree
rotates whenever a node's left and right heights differ by more than 1.
"""
from typing import TypeVar, Generic, Optional, List, Tuple, Dict, Any
from collections import deque

K, V = TypeVar('K'), TypeVar('V')

def _height(node) -> int:
    return node.height if node else 0

class AVLNode(Generic[K, V]):
    def __init__(self, key: K, value: V):
        self.key, self.value = key, value
        self.height = 1
        self.left: Optional['AVLNode[K, V]'] = None
        self.right: Optional['AVLNode[K, V]'] = None

    @property
    def balance_factor(self) -> int:
        return _height(self.left) - _height(self.right)

    def update_height(self) -> None:
        self.height = 1 + max(_height(self.left), _height(self.right))


class AVLTree(Generic[K, V]):
    def __init__(self):
        self.root: Optional[AVLNode[K, V]] = None
        self._size = 0
        self.rotation_log: List[str] = []  # Rotations done by the most recent insert/delete

    def __len__(self) -> int: return self._size
    @property
    def is_empty(self) -> bool: return self.root is None
    def get_height(self, n: Optional[AVLNode]) -> int: return _height(n)
    def get_balance_factor(self, n: Optional[AVLNode]) -> int: return n.balance_factor if n else 0

    # --- Rotations ---
    def _rotate_right(self, z: AVLNode[K, V]) -> AVLNode[K, V]:
        y = z.left
        z.left = y.right
        y.right = z
        z.update_height()
        y.update_height()
        return y

    def _rotate_left(self, z: AVLNode[K, V]) -> AVLNode[K, V]:
        y = z.right
        z.right = y.left
        y.left = z
        z.update_height()
        y.update_height()
        return y

    def _rebalance(self, node: AVLNode[K, V]) -> AVLNode[K, V]:
        node.update_height()
        if node.balance_factor > 1:                      # Left heavy
            if node.left.balance_factor < 0:             # LR: rotate child left first
                self.rotation_log.append(f"LR at {node.key}")
                node.left = self._rotate_left(node.left)
            else:
                self.rotation_log.append(f"LL at {node.key}")
            return self._rotate_right(node)
        if node.balance_factor < -1:                     # Right heavy
            if node.right.balance_factor > 0:            # RL: rotate child right first
                self.rotation_log.append(f"RL at {node.key}")
                node.right = self._rotate_right(node.right)
            else:
                self.rotation_log.append(f"RR at {node.key}")
            return self._rotate_left(node)
        return node

    # --- Insertion ---
    def insert(self, key: K, value: V) -> None:
        self.rotation_log = []
        self.root = self._insert(self.root, key, value)

    def _insert(self, node: Optional[AVLNode[K, V]], key: K, value: V) -> AVLNode[K, V]:
        if node is None:
            self._size += 1
            return AVLNode(key, value)
        if key < node.key:
            node.left = self._insert(node.left, key, value)
        elif key > node.key:
            node.right = self._insert(node.right, key, value)
        else:
            node.value = value  # Same key: update the value
            return node
        return self._rebalance(node)

    # --- Search ---
    def search(self, key: K) -> Optional[V]:
        node = self.root
        while node:
            if key == node.key: return node.value
            node = node.left if key < node.key else node.right
        return None

    def contains(self, key: K) -> bool: return self.search(key) is not None

    # --- Deletion ---
    def delete(self, key: K) -> bool:
        self.rotation_log = []
        size_before = self._size
        self.root = self._delete(self.root, key)
        return self._size < size_before

    def _delete(self, node: Optional[AVLNode[K, V]], key: K) -> Optional[AVLNode[K, V]]:
        if node is None: return None
        if key < node.key:
            node.left = self._delete(node.left, key)
        elif key > node.key:
            node.right = self._delete(node.right, key)
        else:
            if node.left is None or node.right is None:  # 0 or 1 child: replace by that child
                self._size -= 1
                return node.left or node.right
            successor = self._leftmost(node.right)       # 2 children: copy in-order successor
            node.key, node.value = successor.key, successor.value
            node.right = self._delete(node.right, successor.key)
        return self._rebalance(node)

    @staticmethod
    def _leftmost(node: AVLNode[K, V]) -> AVLNode[K, V]:
        while node.left: node = node.left
        return node

    def get_min(self) -> Optional[Tuple[K, V]]:
        if not self.root: return None
        node = self._leftmost(self.root)
        return (node.key, node.value)

    def get_max(self) -> Optional[Tuple[K, V]]:
        if not self.root: return None
        node = self.root
        while node.right: node = node.right
        return (node.key, node.value)

    # --- Traversals ---
    def inorder_traversal(self) -> List[Tuple[K, V]]:
        """Left, root, right: gives keys in sorted order."""
        out: List[Tuple[K, V]] = []
        def walk(n):
            if n:
                walk(n.left)
                out.append((n.key, n.value))
                walk(n.right)
        walk(self.root)
        return out

    def preorder_traversal(self) -> List[Tuple[K, V]]:
        out: List[Tuple[K, V]] = []
        def walk(n):
            if n:
                out.append((n.key, n.value))
                walk(n.left)
                walk(n.right)
        walk(self.root)
        return out

    def postorder_traversal(self) -> List[Tuple[K, V]]:
        out: List[Tuple[K, V]] = []
        def walk(n):
            if n:
                walk(n.left)
                walk(n.right)
                out.append((n.key, n.value))
        walk(self.root)
        return out

    def level_order_traversal(self) -> List[Tuple[K, V]]:
        out: List[Tuple[K, V]] = []
        queue = deque([self.root] if self.root else [])
        while queue:
            n = queue.popleft()
            out.append((n.key, n.value))
            if n.left: queue.append(n.left)
            if n.right: queue.append(n.right)
        return out

    def range_search(self, low: K, high: K) -> List[Tuple[K, V]]:
        """All keys in [low, high], skipping subtrees that cannot contain them."""
        out: List[Tuple[K, V]] = []
        def walk(n):
            if not n: return
            if n.key > low: walk(n.left)
            if low <= n.key <= high: out.append((n.key, n.value))
            if n.key < high: walk(n.right)
        walk(self.root)
        return out

    # --- Display ---
    def export_structure(self) -> Optional[Dict[str, Any]]:
        """Nested JSON (key, height, balance) for the web Algorithm Explorer."""
        def export(n):
            if not n: return None
            return {"key": str(n.key), "height": n.height, "balance": n.balance_factor,
                    "left": export(n.left), "right": export(n.right)}
        return export(self.root)

    def display_tree(self) -> str:
        """ASCII drawing for the CLI."""
        if not self.root: return "<Empty AVL Tree>"
        lines = []
        def draw(n, prefix, is_left):
            if not n: return
            lines.append(f"{prefix}{'└── ' if is_left else '┌── '}[{n.key}] (h={n.height}, bf={n.balance_factor:+d})")
            draw(n.left, prefix + ("    " if is_left else "│   "), True)
            draw(n.right, prefix + ("│   " if is_left else "    "), False)
        draw(self.root, "", True)
        return "\n".join(lines)
