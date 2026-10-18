"""
SmartDrive - Max Binary Heap Implementation
Array-backed priority queue: index i has children 2i+1 and 2i+2.
Insert / extract are O(log n); build-heap (Floyd) is O(n).
Equal priorities come out in insertion order (FIFO) thanks to a sequence number.
"""
from typing import TypeVar, Generic, Optional, List, Tuple, Callable, Dict, Any

T = TypeVar('T')

class HeapNode(Generic[T]):
    def __init__(self, priority: int, value: T, seq: int = 0):
        self.priority, self.value, self.seq = priority, value, seq

    def _rank(self) -> Tuple[int, int]: return (self.priority, -self.seq)  # Higher priority, then older first
    def __lt__(self, other: 'HeapNode[T]') -> bool: return self._rank() < other._rank()
    def __gt__(self, other: 'HeapNode[T]') -> bool: return self._rank() > other._rank()

class MaxBinaryHeap(Generic[T]):
    def __init__(self):
        self._heap: List[HeapNode[T]] = []
        self._seq = 0

    def __len__(self) -> int: return len(self._heap)
    @property
    def is_empty(self) -> bool: return not self._heap

    # --- Heapify Primitives ---
    def _swap(self, i: int, j: int) -> None:
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]

    def _heapify_up(self, idx: int) -> None:
        while idx > 0:
            parent = (idx - 1) // 2
            if not self._heap[idx] > self._heap[parent]: return
            self._swap(idx, parent)
            idx = parent

    def _heapify_down(self, idx: int) -> None:
        size = len(self._heap)
        while True:
            largest = idx
            for child in (2 * idx + 1, 2 * idx + 2):
                if child < size and self._heap[child] > self._heap[largest]: largest = child
            if largest == idx: return
            self._swap(idx, largest)
            idx = largest

    def _heapify_all(self) -> None:
        """Floyd's method: sift down every internal node, bottom-up. O(n)."""
        for i in range(len(self._heap) // 2 - 1, -1, -1):
            self._heapify_down(i)

    # --- Operations ---
    def insert(self, priority: int, value: T) -> None:
        self._seq += 1
        self._heap.append(HeapNode(priority, value, self._seq))
        self._heapify_up(len(self._heap) - 1)

    def peek(self) -> Optional[Tuple[int, T]]:
        return (self._heap[0].priority, self._heap[0].value) if self._heap else None

    def extract_max(self) -> Optional[Tuple[int, T]]:
        if not self._heap: return None
        top = self._heap[0]
        last = self._heap.pop()
        if self._heap:
            self._heap[0] = last  # Move last item to the root, then sift it down
            self._heapify_down(0)
        return (top.priority, top.value)

    def remove_where(self, predicate: Callable[[T], bool]) -> int:
        """Removes every entry whose value matches `predicate`, then re-heapifies in O(n). Returns count removed."""
        before = len(self._heap)
        self._heap = [node for node in self._heap if not predicate(node.value)]
        self._heapify_all()
        return before - len(self._heap)

    def build_heap(self, items: List[Tuple[int, T]]) -> None:
        self._heap = []
        for priority, value in items:
            self._seq += 1
            self._heap.append(HeapNode(priority, value, self._seq))
        self._heapify_all()

    def to_sorted_list(self) -> List[Tuple[int, T]]:
        """Processing order without changing the heap."""
        return [(n.priority, n.value) for n in sorted(self._heap, reverse=True)]

    # --- Display ---
    def export_structure(self, label: Optional[Callable[[T], str]] = None) -> List[Dict[str, Any]]:
        """The underlying array, for the web Algorithm Explorer."""
        return [{"index": i, "priority": n.priority, "seq": n.seq, "label": label(n.value) if label else repr(n.value)}
                for i, n in enumerate(self._heap)]

    def display_heap(self) -> str:
        if self.is_empty: return "<Empty Binary Heap>"
        lines = [f"MaxBinaryHeap [Items={len(self._heap)}]"]
        def draw(idx, prefix, is_left):
            if idx >= len(self._heap): return
            lines.append(f"{prefix}{'└── ' if is_left else '┌── '}[P:{self._heap[idx].priority}] {self._heap[idx].value!r}")
            child_prefix = prefix + ("    " if is_left else "│   ")
            draw(2 * idx + 1, child_prefix, True)
            draw(2 * idx + 2, child_prefix, False)
        draw(0, "", True)
        return "\n".join(lines)
