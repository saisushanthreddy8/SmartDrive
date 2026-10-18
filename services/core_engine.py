"""
SmartDrive - Unified DSA Core Engine
Keeps every data structure in sync for each file operation:
    AVL tree (sorted names), two hash tables (by name / by id), trie (prefix search),
    max heap (priority queue), Merkle tree (integrity), LCS (diff), knapsack (optimizer), edit distance (fuzzy search).
With a FileStorageManager attached, files, versions and metadata.json live on disk.
"""
import math, re
from typing import Optional, List, Tuple, Dict, Any
from models.file_model import FileModel
from data_structures.avl_tree import AVLTree
from data_structures.hash_table import HashTable
from data_structures.trie import Trie
from data_structures.binary_heap import MaxBinaryHeap
from data_structures.merkle_tree import MerkleTree
from data_structures.lcs_diff import LCSDiff
from data_structures.knapsack import KnapsackOptimizer, KnapsackItem, KnapsackResult
from data_structures.edit_distance import EditDistance
from services.file_service import FileStorageManager

class SmartDriveEngine:
    def __init__(self, storage: Optional[FileStorageManager] = None):
        self.avl_tree: AVLTree[str, FileModel] = AVLTree()
        self.hash_by_name: HashTable[str, FileModel] = HashTable()
        self.hash_by_id: HashTable[str, FileModel] = HashTable()
        self.trie: Trie[FileModel] = Trie(case_sensitive=False)
        self.heap: MaxBinaryHeap[FileModel] = MaxBinaryHeap()
        self.merkle = MerkleTree()
        self._active_files: Dict[str, FileModel] = {}
        self.storage = storage
        if storage: self.load_from_disk()

    def __len__(self) -> int: return len(self._active_files)

    def _files_by_name(self) -> List[FileModel]:
        return sorted(self._active_files.values(), key=lambda f: f.filename)

    # --- Lookups ---
    def get_file_by_name(self, name: str) -> Optional[FileModel]: return self.hash_by_name.search(name)
    def get_file_by_id(self, fid: str) -> Optional[FileModel]: return self.hash_by_id.search(fid)
    def list_all_files_sorted(self) -> List[Tuple[str, FileModel]]: return self.avl_tree.inorder_traversal()
    def get_files_in_range(self, start: str, end: str) -> List[Tuple[str, FileModel]]: return self.avl_tree.range_search(start, end)
    def search_autocomplete(self, prefix: str, limit: Optional[int] = None) -> List[Tuple[str, FileModel]]:
        return self.trie.autocomplete(prefix, limit)

    def name_exists(self, filename: str) -> bool:
        """Case-insensitive (like Windows), so 'Report.pdf' and 'report.PDF' cannot both exist."""
        return self.trie.search_exact(filename) is not None

    # --- Indexing ---
    def _index(self, f: FileModel) -> None:
        self.avl_tree.insert(f.filename, f)
        self.hash_by_name.insert(f.filename, f)
        self.hash_by_id.insert(f.file_id, f)
        self.trie.insert(f.filename, f)
        self.heap.insert(f.priority, f)
        self._active_files[f.file_id] = f

    def _changed(self) -> None:
        """After any change: rebuild the Merkle tree and save metadata.json."""
        self.merkle.build_from_files(self._files_by_name())
        if self.storage: self.storage.save_metadata([f.to_dict() for f in self._files_by_name()])

    def register_file(self, f: FileModel) -> Dict[str, Any]:
        f.validate()
        if self.name_exists(f.filename):
            raise ValueError(f"A file named '{f.filename}' already exists. Use Update to add a version.")
        if f.file_id in self._active_files: raise ValueError(f"Duplicate file ID '{f.file_id}'.")
        self._index(f)
        self._changed()
        return {"status": "SUCCESS", "file_id": f.file_id, "merkle_root": self.merkle.root_hash}

    def delete_file(self, filename: str) -> bool:
        f = self.hash_by_name.search(filename)
        if not f: return False
        self.avl_tree.delete(filename)
        self.hash_by_name.delete(filename)
        self.hash_by_id.delete(f.file_id)
        self.trie.delete(filename)
        self.heap.remove_where(lambda x: x.file_id == f.file_id)
        del self._active_files[f.file_id]
        if self.storage:
            self.storage.delete_physical_file(f.storage_path)
            self.storage.delete_versions(f.file_id)
        self._changed()
        return True

    def update_metadata(self, file_id: str, priority: Optional[int] = None, description: Optional[str] = None,
                        tags: Optional[List[str]] = None) -> Optional[FileModel]:
        """Edits priority / description / tags. A new priority moves the file inside the heap."""
        f = self.get_file_by_id(file_id)
        if not f: return None
        if priority is not None and int(priority) != f.priority:
            if not 1 <= int(priority) <= 10: raise ValueError("Priority must be between 1 and 10.")
            was_queued = self.heap.remove_where(lambda x: x.file_id == file_id) > 0
            f.priority = int(priority)
            if was_queued: self.heap.insert(f.priority, f)
        if description is not None:
            f.description = description.strip() or None
        if tags is not None:
            unique = {}
            for t in (str(t).strip()[:30] for t in tags):
                if t: unique.setdefault(t.lower(), t)  # Case-insensitive de-duplication, first spelling wins
            f.tags = list(unique.values())[:12]
        self._changed()
        return f

    # --- Real Storage ---
    def _require_storage(self) -> FileStorageManager:
        if not self.storage: raise RuntimeError("No storage attached. Create the engine with SmartDriveEngine(FileStorageManager()).")
        return self.storage

    def load_from_disk(self) -> int:
        """Rebuilds every data structure from storage/metadata.json. Returns the number of files."""
        for record in self._require_storage().load_metadata():
            f = FileModel.from_dict(record)
            if not self.name_exists(f.filename) and f.file_id not in self._active_files: self._index(f)
        self.merkle.build_from_files(self._files_by_name())
        return len(self)

    def _check_new(self, name: str, priority: int) -> str:
        name = self._require_storage().safe_filename(name)
        if self.name_exists(name): raise ValueError(f"A file named '{name}' already exists. Use Update to add a version.")
        if not 1 <= priority <= 10: raise ValueError("Priority must be between 1 and 10.")
        return name

    def _add_stored_file(self, name: str, rel_path: str, sha: str, size: int, priority: int, description: Optional[str]) -> Dict[str, Any]:
        """Indexes a file that is already on disk and saves its first version snapshot."""
        try:
            f = FileModel(filename=name, file_size=size, priority=priority, description=description,
                          sha256_hash=sha, storage_path=rel_path)
            self.storage.snapshot_version(f.file_id, 1, name, rel_path)
            return self.register_file(f)
        except Exception:
            self.storage.delete_physical_file(rel_path)  # Undo the disk write if indexing failed
            raise

    def upload_content(self, filename: str, content: bytes | str, priority: int = 5, description: Optional[str] = None) -> Dict[str, Any]:
        """Writes new content to storage/<category>/ and indexes it everywhere."""
        name = self._check_new(filename, priority)
        rel, sha, size = self.storage.save_file_content(name, content)
        return self._add_stored_file(name, rel, sha, size, priority, description)

    def import_local_file(self, source_path: str, priority: int = 5, description: Optional[str] = None) -> Dict[str, Any]:
        """Copies a file from the PC into storage and indexes it."""
        self._check_new(FileStorageManager._source_file(source_path).name, priority)
        name, rel, sha, size = self.storage.import_local_file(source_path)
        return self._add_stored_file(name, rel, sha, size, priority, description)

    def read_version_content(self, file_id: str, version: int) -> Optional[bytes]:
        f = self.get_file_by_id(file_id)
        if not f or not f.get_version(version): return None
        return self._require_storage().read_version(file_id, version, f.filename)

    def get_storage_stats(self) -> Dict[str, Any]: return self._require_storage().get_storage_stats()

    # --- Version Control (Phase 4) ---
    def update_file_version(self, file_id: str, new_size: int, new_hash: str, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Records a new version. Name and priority are unchanged, so only the Merkle tree needs rebuilding."""
        f = self.get_file_by_id(file_id)
        if not f: return None
        version = f.add_version(new_size, new_hash, description)
        self._changed()
        return {"status": "SUCCESS", "file_id": file_id, "new_version": version.version_number,
                "merkle_root": self.merkle.root_hash}

    def update_content(self, file_id: str, content: bytes | str | None = None, description: Optional[str] = None,
                       source_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Saves new content (text/bytes, or a file from the PC) as the next version on disk."""
        store = self._require_storage()
        f = self.get_file_by_id(file_id)
        if not f: return None
        if source_path: sha, size = store.replace_from_local_file(f.storage_path, source_path)
        else: _, sha, size = store.save_file_content(f.filename, content if content is not None else b"")
        res = self.update_file_version(file_id, size, sha, description)
        store.snapshot_version(file_id, res["new_version"], f.filename, f.storage_path)
        return res

    def rollback_to_version(self, file_id: str, version_number: int) -> Optional[Dict[str, Any]]:
        """Restores an old version by adding it as a NEW version, so history is never rewritten."""
        f = self.get_file_by_id(file_id)
        target = f.get_version(version_number) if f else None
        if not target: return None
        if self.storage and not self.storage.restore_version(file_id, version_number, f.filename, f.storage_path):
            return None
        res = self.update_file_version(file_id, target.file_size, target.sha256_hash, f"Rollback to v{version_number}")
        res["restored_from"] = version_number
        if self.storage: self.storage.snapshot_version(file_id, res["new_version"], f.filename, f.storage_path)
        return res

    def get_version_history(self, file_id: str) -> Optional[List[Dict[str, Any]]]:
        f = self.get_file_by_id(file_id)
        return [v.to_dict() for v in f.version_history] if f else None

    def compare_versions(self, old_text: str, new_text: str) -> Dict[str, Any]:
        """LCS diff plus added / removed / unchanged counts and similarity %."""
        diff = LCSDiff.generate_diff(old_text, new_text)
        return {"diff": diff, "stats": LCSDiff.diff_stats(diff), "lcs_length": LCSDiff.lcs_length(old_text, new_text)}

    def generate_diff(self, old_text: str, new_text: str, use_color: bool = True) -> str:
        return LCSDiff.format_diff(LCSDiff.generate_diff(old_text, new_text), use_color)

    # --- Priority Queue (Max Heap) ---
    def peek_highest_priority(self) -> Optional[Tuple[int, FileModel]]: return self.heap.peek()
    def process_next_priority_file(self) -> Optional[Tuple[int, FileModel]]: return self.heap.extract_max()
    def queue_snapshot(self) -> List[Tuple[int, FileModel]]: return self.heap.to_sorted_list()

    def requeue_all(self) -> int:
        """Rebuilds the queue from every file with Floyd's O(n) build-heap."""
        self.heap.build_heap([(f.priority, f) for f in self._files_by_name()])
        return len(self.heap)

    # --- Integrity (Merkle Tree) ---
    def verify_file_integrity(self, file_id: str, current_hash: str) -> Tuple[bool, str]:
        return self.merkle.verify_file(file_id, current_hash)

    def get_audit_proof(self, file_id: str) -> Optional[List[Tuple[str, str]]]:
        return self.merkle.get_audit_proof(file_id)

    def disk_hashes(self) -> Dict[str, str]:
        """Real SHA-256 of every file on disk. Missing files are left out, so the audit reports them MISSING."""
        store = self._require_storage()
        hashes = {fid: store.compute_file_hash(f.storage_path) for fid, f in self._active_files.items()}
        return {fid: h for fid, h in hashes.items() if h}

    def verify_file_on_disk(self, file_id: str) -> Tuple[bool, str]:
        f = self.get_file_by_id(file_id)
        if not f: return (False, f"File ID '{file_id}' not indexed.")
        h = self._require_storage().compute_file_hash(f.storage_path)
        if h is None: return (False, f"MISSING: '{f.filename}' not found on disk.")
        return self.verify_file_integrity(file_id, h)

    def audit_drive(self, current_hashes: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Checks every file against the Merkle tree (hashes read from disk unless given)."""
        violations = self.merkle.detect_tampered_files(current_hashes if current_hashes is not None else self.disk_hashes())
        return {"is_tampered": bool(violations), "total_files": len(self), "tampered_count": len(violations),
                "violations": violations, "current_merkle_root": self.merkle.root_hash}

    # --- Storage Optimizer (0/1 Knapsack) ---
    METHODS = {"dp": "solve_dp", "greedy": "solve_greedy", "bnb": "solve_branch_and_bound"}
    MAX_DP_CELLS = 5_000_000  # Keeps the DP table fast

    def _build_optimizer(self, capacity_bytes: int, unit_bytes: Optional[int]) -> KnapsackOptimizer[FileModel]:
        """Weight = size in units (rounded up, so chosen files always really fit), value = priority."""
        if capacity_bytes < 0 or (unit_bytes is not None and unit_bytes <= 0):
            raise ValueError("Capacity must be >= 0 and unit > 0.")
        unit = unit_bytes or 1
        while unit_bytes is None and max(1, len(self)) * (capacity_bytes // unit + 1) > self.MAX_DP_CELLS:
            unit *= 1024  # Bytes for small budgets; KB, MB... when the table would get too big
        items = [KnapsackItem(f.filename, math.ceil(f.file_size / unit), f.priority, payload=f) for f in self._files_by_name()]
        return KnapsackOptimizer(items, capacity_bytes // unit, unit_bytes=unit)

    def optimize_storage(self, capacity_bytes: int, method: str = "bnb", unit_bytes: Optional[int] = None) -> KnapsackResult[FileModel]:
        if method not in self.METHODS: raise ValueError(f"Unknown method '{method}'. Use one of {list(self.METHODS)}.")
        return getattr(self._build_optimizer(capacity_bytes, unit_bytes), self.METHODS[method])()

    def compare_optimizers(self, capacity_bytes: int, unit_bytes: Optional[int] = None) -> List[KnapsackResult[FileModel]]:
        return self._build_optimizer(capacity_bytes, unit_bytes).compare_all()

    # --- Fuzzy Search (Edit Distance) ---
    @staticmethod
    def _words(filename: str) -> List[str]:
        """'Machine_Learning_Notes.docx' -> ['machine', 'learning', 'notes', 'machine_learning_notes']"""
        stem = filename.rsplit(".", 1)[0].lower()
        return [w for w in re.split(r"[\s_\-.()\[\]]+", stem) if w] + [stem]

    def fuzzy_search(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        """
        Typo-tolerant search. Trie prefix matches come first (distance 0); every other file is scored by the
        smallest edit distance between the query and any word of its name (or that word's start).
        """
        q = query.strip().lower()
        if not q: return []
        results = {f.file_id: {"file": f, "distance": 0, "matched": name, "method": "trie-prefix"}
                   for name, f in self.trie.autocomplete(q)}
        max_edits = max(1, len(q) // 3)
        for f in self._active_files.values():
            if f.file_id in results: continue
            if q in f.filename.lower():
                results[f.file_id] = {"file": f, "distance": 0, "matched": q, "method": "substring"}
                continue
            dist, word = min((min(EditDistance.distance(q, w, max_edits), EditDistance.distance(q, w[:len(q)], max_edits)), w)
                             for w in self._words(f.filename))
            if dist <= max_edits:
                results[f.file_id] = {"file": f, "distance": dist, "matched": word, "method": "edit-distance"}
        ranked = sorted(results.values(), key=lambda r: (r["distance"], -r["file"].priority, r["file"].filename.lower()))
        return ranked[:limit]

    def did_you_mean(self, query: str) -> Optional[str]:
        """Closest word from any filename, offered when a search finds nothing."""
        vocab = {w for f in self._active_files.values() for w in self._words(f.filename)}
        best = EditDistance.best_matches(query, vocab, limit=1)
        return best[0][0] if best and best[0][1] > 0 else None

    # --- Stats & Algorithm Explorer ---
    def get_stats(self) -> Dict[str, Any]:
        files = list(self._active_files.values())
        by_type: Dict[str, int] = {}
        for f in files: by_type[f.file_type] = by_type.get(f.file_type, 0) + 1
        top = self.peek_highest_priority()
        return {
            "total_files": len(files),
            "total_bytes": sum(f.file_size for f in files),
            "total_versions": sum(f.current_version for f in files),
            "by_type": by_type,
            "avl": {"size": len(self.avl_tree), "height": self.avl_tree.get_height(self.avl_tree.root),
                    "optimal_height": math.ceil(math.log2(len(files) + 1))},
            "hash_table": self.hash_by_name.get_collision_stats(),
            "trie": {"words": len(self.trie), "nodes": self.trie.count_nodes()},
            "heap": {"size": len(self.heap), "top": {"priority": top[0], "filename": top[1].filename} if top else None},
            "merkle": {"leaves": len(self.merkle), "root": self.merkle.root_hash},
            "storage": self.storage.get_storage_stats() if self.storage else None,
        }

    def explorer_snapshot(self, structure: str, prefix: str = "") -> Dict[str, Any]:
        """JSON view of one live data structure for the web Algorithm Explorer."""
        views = {
            "avl": lambda: {"root": self.avl_tree.export_structure(), "size": len(self.avl_tree)},
            "hash": lambda: self.hash_by_name.export_structure(),
            "trie": lambda: {"prefix": prefix, "root": self.trie.export_structure(prefix)},
            "heap": lambda: {"nodes": self.heap.export_structure(label=lambda f: f.filename)},
            "merkle": lambda: {"root": self.merkle.export_structure(), "root_hash": self.merkle.root_hash},
        }
        if structure not in views: raise ValueError(f"Unknown structure '{structure}'. Use avl, hash, trie, heap or merkle.")
        return {"structure": structure, **views[structure]()}
