"""
SmartDrive - Demo Sample Files
Seeded on first run (empty storage/). Realistic text so search, diff and the AI features have
something meaningful to work with. Sizes are fixed so the Knapsack demo (7 KB budget) shows
Greedy losing to DP / Branch & Bound: 23 vs 27.
"""
from typing import List, Tuple

ML_ASSIGNMENT = """Machine Learning Assignment 2: Supervised Learning
Course: Advanced Data Structures and Algorithms / Machine Learning lab
Submission deadline: Friday, 11:59 PM. Late submissions lose 10% per day.

Task 1. Load the housing dataset and split it into training and test sets (80/20).
Train a linear regression model to predict house prices from area, rooms and location.
Report the mean squared error and the R-squared score on the test set.

Task 2. Train a decision tree classifier on the student performance dataset.
Compare accuracy, precision and recall against a k-nearest neighbours classifier.
Explain which model generalises better and why overfitting happens with deep trees.

Task 3. Implement gradient descent from scratch for logistic regression.
Plot the training loss for learning rates 0.1, 0.01 and 0.001.

Deliverables: a PDF report with plots, the Python notebook, and a short README.
This assignment is important for the final exam, so start early and ask questions in the lab.
"""

ML_NOTES = """Supervised learning notes
Supervised learning learns a mapping from labelled inputs to outputs.
Regression predicts continuous values; classification predicts discrete classes.
Overfitting: the model memorises training data. Fix with regularisation or more data.
Always evaluate on a held-out test set.
"""

ARCH_DIAGRAM = """SmartDrive system architecture diagram (exported description)
React frontend talks to the FastAPI backend over REST.
The backend calls the SmartDrive engine, which coordinates the AVL tree, hash tables,
trie, max heap and Merkle tree. File bytes live in the storage folder;
metadata.json persists the index between restarts.
"""

FINAL_REPORT = """ADSA Final Report: SmartDrive, a file manager built on advanced data structures

Abstract
SmartDrive is a Google Drive style file manager whose core operations run on data structures
implemented from scratch. This report summarises the design, the complexity of each operation,
and the results of our evaluation.

1. Design
Every file is a FileModel with a SHA-256 hash, priority, tags and a version history.
An AVL tree keeps filenames sorted so listing the drive is an in-order traversal.
Two hash tables give constant time lookup by filename and by file ID.
A trie answers prefix searches for autocomplete in time proportional to the prefix length.
A max binary heap orders files for priority processing.
A Merkle tree over all file hashes detects tampering and produces logarithmic audit proofs.

2. Version control and optimisation
Each update stores a snapshot. The longest common subsequence algorithm compares two versions line by line.
The storage optimiser solves the 0/1 knapsack problem with dynamic programming, greedy and branch and bound.

3. Results
Branch and bound matched the dynamic programming optimum while exploring far fewer states.
The greedy heuristic was fastest but missed the optimum for small budgets.

4. Conclusion
Combining several data structures, each chosen for one operation, gives a fast and verifiable file system.
Future work: real-time collaboration and smarter AI assistance.
"""

SLIDES = """Review Slides: SmartDrive final review

Slide 1. Title
SmartDrive: intelligent file management with advanced data structures.

Slide 2. Problem
Students keep hundreds of files. Finding, prioritising and trusting them is slow.

Slide 3. Architecture
React frontend, FastAPI backend, DSA engine, real storage on disk.

Slide 4. Data structures
AVL tree for sorted listing. Hash table for exact lookup. Trie for autocomplete.
Max heap for priority processing. Merkle tree for integrity.

Slide 5. Version control
Every save creates a snapshot. LCS shows exactly which lines changed. Rollback restores any version.

Slide 6. Storage optimiser
Knapsack picks the most valuable files that fit a budget. DP and branch and bound are optimal; greedy is fast.

Slide 7. AI assistant
Offline TF-IDF search, summaries, tag suggestions and duplicate detection.

Slide 8. Demo
Upload, search with a typo, edit and diff, tamper and verify, optimise storage.

Slide 9. Results and future work
"""

LECTURE = """Lecture transcript: Heaps and priority queues (Week 9)

Today we look at the binary heap. A heap is a complete binary tree stored in an array.
In a max heap every parent is larger than or equal to its children, so the largest element is always at the root.
The children of index i live at positions two i plus one and two i plus two.
Insertion places the new element at the end of the array and sifts it up while it is larger than its parent.
Extract max swaps the last element into the root and sifts it down, choosing the larger child each time.
Both operations take logarithmic time because the height of a complete tree is log n.
Building a heap from n elements with Floyd's method takes linear time, which surprises many students.
Priority queues are used in schedulers, Dijkstra's shortest path algorithm and event simulation.
For the lab, implement a max heap and use it to process print jobs by priority.
Remember that heaps are not sorted arrays: only the parent child relationship is guaranteed.
Next week we will cover Merkle trees and how hashing makes tampering detectable.
"""

def _sql_dump(size: int) -> str:
    """Distinct INSERT lines so the backup is realistic and every line differs."""
    lines = ["-- SmartDrive SQL snapshot", "CREATE TABLE students (id INT PRIMARY KEY, name TEXT, course TEXT, marks INT);"]
    courses = ["ADSA", "Machine Learning", "Computer Networks", "Robotics", "Software Engineering"]
    i = 1
    while sum(len(l) + 1 for l in lines) < size:
        lines.append(f"INSERT INTO students VALUES ({i}, 'student_{i:04d}', '{courses[i % len(courses)]}', {40 + (i * 37) % 60});")
        i += 1
    return "\n".join(lines)

def fit_to_size(text: str, size: int) -> str:
    """Exactly `size` bytes: trims at the limit or pads with trailing newlines/spaces (invisible in previews)."""
    data = text.encode("utf-8")[:size].decode("utf-8", "ignore")
    pad = size - len(data.encode("utf-8"))
    return data + ("\n" + " " * (pad - 1) if pad > 0 else "")

# (filename, size_bytes, priority, description, text)
SAMPLE_FILES: List[Tuple[str, int, int, str, str]] = [
    ("Machine_Learning_Assignment.pdf", 2001, 10, "Academic", ML_ASSIGNMENT),
    ("Machine_Learning_Notes.docx", 500, 8, "Academic", ML_NOTES),
    ("Project_Architecture_Diagram.png", 1024, 5, "Design", ARCH_DIAGRAM),
    ("Semester_Final_Report.pdf", 4096, 9, "Academic", FINAL_REPORT),
    ("Database_Backup.zip", 51200, 4, "Backup", _sql_dump(51200)),
    ("Presentation_Slides.pptx", 8192, 7, "Presentation", SLIDES),
    ("Lecture_Audio_Recording.mp3", 15360, 3, "Audio", LECTURE),
]
