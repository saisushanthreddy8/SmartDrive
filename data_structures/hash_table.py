"""
SmartDrive - Custom Separate-Chaining Hash Table
Built from scratch: each bucket holds a linked list of nodes (no Python dict inside).
"""
from typing import TypeVar, Generic, Optional, List, Tuple, Dict, Any, Iterator

K, V = TypeVar('K'), TypeVar('V')

class HashNode(Generic[K, V]):
    def __init__(self, key: K, value: V, next_node: Optional['HashNode[K, V]'] = None):
        self.key, self.value, self.next = key, value, next_node

class HashTable(Generic[K, V]):
    def __init__(self, capacity: int = 16, max_load_factor: float = 0.75):
        if capacity <= 0 or max_load_factor <= 0: raise ValueError("Invalid capacity or load factor.")
        self._capacity, self._max_load_factor, self._size = capacity, max_load_factor, 0
        self._buckets: List[Optional[HashNode[K, V]]] = [None] * capacity

    def __len__(self) -> int: return self._size
    @property
    def is_empty(self) -> bool: return self._size == 0
    @property
    def capacity(self) -> int: return self._capacity
    @property
    def load_factor(self) -> float: return self._size / self._capacity

    # --- Hashing ---
    def _hash(self, key: K) -> int:
        """Multiplicative hash for ints, polynomial rolling hash (base 31) for everything else."""
        if isinstance(key, int): return ((key * 2654435761) & 0xFFFFFFFF) % self._capacity
        h = 0
        for char in str(key): h = (h * 31 + ord(char)) % 1_000_000_007
        return h % self._capacity

    def get_bucket_index(self, key: K) -> int: return self._hash(key)

    @staticmethod
    def _chain(head: Optional[HashNode[K, V]]) -> Iterator[HashNode[K, V]]:
        """Walks one bucket's linked list."""
        while head:
            yield head
            head = head.next

    # --- Operations ---
    def insert(self, key: K, value: V) -> None:
        idx = self._hash(key)
        for node in self._chain(self._buckets[idx]):
            if node.key == key:
                node.value = value  # Existing key: update
                return
        self._buckets[idx] = HashNode(key, value, self._buckets[idx])  # New key: add at head
        self._size += 1
        if self.load_factor > self._max_load_factor: self._resize(self._capacity * 2)

    def _resize(self, new_capacity: int) -> None:
        """Doubles the bucket array and re-inserts every key (positions change with capacity)."""
        old = self.items()
        self._capacity, self._buckets, self._size = new_capacity, [None] * new_capacity, 0
        for key, value in old: self.insert(key, value)

    def search(self, key: K) -> Optional[V]:
        for node in self._chain(self._buckets[self._hash(key)]):
            if node.key == key: return node.value
        return None

    def contains(self, key: K) -> bool: return self.search(key) is not None

    def delete(self, key: K) -> bool:
        idx = self._hash(key)
        prev = None
        for node in self._chain(self._buckets[idx]):
            if node.key == key:
                if prev: prev.next = node.next
                else: self._buckets[idx] = node.next
                self._size -= 1
                return True
            prev = node
        return False

    def items(self) -> List[Tuple[K, V]]:
        return [(n.key, n.value) for head in self._buckets for n in self._chain(head)]
    def keys(self) -> List[K]: return [k for k, _ in self.items()]
    def values(self) -> List[V]: return [v for _, v in self.items()]

    # --- Statistics & Display ---
    def get_collision_stats(self) -> dict:
        lengths = [len(list(self._chain(head))) for head in self._buckets]
        return {
            "total_keys": self._size,
            "capacity": self._capacity,
            "load_factor": round(self.load_factor, 2),
            "empty_buckets": lengths.count(0),
            "total_collisions": sum(l - 1 for l in lengths if l > 1),
            "max_chain_length": max(lengths, default=0),
        }

    def export_structure(self) -> Dict[str, Any]:
        """Buckets with their chains (head first) for the web Algorithm Explorer."""
        return {"capacity": self._capacity, "size": self._size, "load_factor": round(self.load_factor, 3),
                "max_load_factor": self._max_load_factor, "stats": self.get_collision_stats(),
                "buckets": [[str(n.key) for n in self._chain(head)] for head in self._buckets]}

    def display_table(self) -> str:
        lines = [f"HashTable [Size={self._size}, Cap={self._capacity}, LF={self.load_factor:.2f}]", "=" * 55]
        for i, head in enumerate(self._buckets):
            chain = [f"({n.key!r} -> {n.value!r})" for n in self._chain(head)]
            lines.append(f"Bucket [{i:02d}]: " + (" -> ".join(chain) + " -> None" if chain else "<Empty>"))
        return "\n".join(lines)
