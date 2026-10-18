"""
Unit tests for SmartDrive MaxBinaryHeap implementation.
Validates max-heap ordering, heapify_up and heapify_down, Floyd's build_heap,
stable tie-breaking for equal priorities, and FileModel integration.
"""

import unittest
from data_structures.binary_heap import MaxBinaryHeap
from models.file_model import FileModel


class TestMaxBinaryHeap(unittest.TestCase):
    def test_empty_heap(self):
        heap = MaxBinaryHeap[str]()
        self.assertTrue(heap.is_empty)
        self.assertEqual(len(heap), 0)
        self.assertIsNone(heap.peek())
        self.assertIsNone(heap.extract_max())
        self.assertEqual(heap.to_sorted_list(), [])
        self.assertEqual(heap.display_heap(), "<Empty Binary Heap>")

    def test_insert_and_peek(self):
        heap = MaxBinaryHeap[str]()
        heap.insert(5, "task_5")
        self.assertFalse(heap.is_empty)
        self.assertEqual(len(heap), 1)
        self.assertEqual(heap.peek(), (5, "task_5"))

        # Insert higher priority
        heap.insert(10, "task_10")
        self.assertEqual(len(heap), 2)
        self.assertEqual(heap.peek(), (10, "task_10"))

        # Insert lower priority
        heap.insert(2, "task_2")
        self.assertEqual(len(heap), 3)
        self.assertEqual(heap.peek(), (10, "task_10"))

    def test_extract_max_order(self):
        heap = MaxBinaryHeap[str]()
        items = [(3, "v3"), (9, "v9"), (1, "v1"), (7, "v7"), (5, "v5"), (10, "v10")]
        for priority, val in items:
            heap.insert(priority, val)

        self.assertEqual(len(heap), 6)

        extracted = []
        while not heap.is_empty:
            item = heap.extract_max()
            self.assertIsNotNone(item)
            extracted.append(item)

        expected_priorities = [10, 9, 7, 5, 3, 1]
        self.assertEqual([p for p, _ in extracted], expected_priorities)
        self.assertTrue(heap.is_empty)

    def test_duplicate_priorities_tie_breaking(self):
        """Validates FIFO tie-breaking for equal priority tasks."""
        heap = MaxBinaryHeap[str]()
        heap.insert(8, "first_8")
        heap.insert(8, "second_8")
        heap.insert(8, "third_8")

        self.assertEqual(heap.extract_max(), (8, "first_8"))
        self.assertEqual(heap.extract_max(), (8, "second_8"))
        self.assertEqual(heap.extract_max(), (8, "third_8"))

    def test_build_heap_floyds_algorithm(self):
        """Validates O(n) Floyd's bottom-up heap construction."""
        heap = MaxBinaryHeap[int]()
        raw_items = [(4, 4), (10, 10), (3, 3), (5, 5), (1, 1), (15, 15), (7, 7)]
        heap.build_heap(raw_items)

        self.assertEqual(len(heap), len(raw_items))
        self.assertEqual(heap.peek(), (15, 15))

        sorted_res = [p for p, _ in heap.to_sorted_list()]
        self.assertEqual(sorted_res, [15, 10, 7, 5, 4, 3, 1])

    def test_heap_with_file_model(self):
        """Validates priority queue behavior when managing FileModel instances."""
        heap = MaxBinaryHeap[FileModel]()

        files = [
            FileModel(filename="notes.txt", file_size=100, priority=2),
            FileModel(filename="urgent_assignment.pdf", file_size=5000, priority=10),
            FileModel(filename="project_report.docx", file_size=2000, priority=8),
            FileModel(filename="backup.zip", file_size=50000, priority=5),
        ]

        for f in files:
            heap.insert(f.priority, f)

        self.assertEqual(len(heap), 4)

        # Most urgent file should be extracted first
        first = heap.extract_max()
        self.assertIsNotNone(first)
        self.assertEqual(first[0], 10)
        self.assertEqual(first[1].filename, "urgent_assignment.pdf")

        # Second most urgent
        second = heap.extract_max()
        self.assertIsNotNone(second)
        self.assertEqual(second[0], 8)
        self.assertEqual(second[1].filename, "project_report.docx")

        # Display test
        display_str = heap.display_heap()
        self.assertIn("MaxBinaryHeap", display_str)


if __name__ == "__main__":
    unittest.main()
