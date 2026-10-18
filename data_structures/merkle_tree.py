"""
SmartDrive - Cryptographic Merkle Tree Implementation
Leaves are file SHA-256 hashes; each parent is sha256(left + right).
Changing any file changes the root. An audit proof (one sibling per level) verifies a
single file against the root in O(log n).
"""
import hashlib
from typing import Optional, List, Tuple, Dict, Any
from models.file_model import FileModel

def sha256_hash(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

class MerkleNode:
    def __init__(self, hash_val: str, left: Optional['MerkleNode'] = None, right: Optional['MerkleNode'] = None,
                 file_id: Optional[str] = None, filename: Optional[str] = None):
        self.hash_val, self.left, self.right = hash_val, left, right
        self.file_id, self.filename = file_id, filename

    @property
    def is_leaf(self) -> bool: return self.left is None and self.right is None

class MerkleTree:
    def __init__(self):
        self.root: Optional[MerkleNode] = None
        self._levels: List[List[MerkleNode]] = []   # levels[0] = leaves, levels[-1] = [root]
        self._leaf_map: Dict[str, MerkleNode] = {}  # file_id -> leaf
        self._leaf_index: Dict[str, int] = {}       # file_id -> position among the leaves

    def __len__(self) -> int: return len(self._levels[0]) if self._levels else 0
    @property
    def is_empty(self) -> bool: return self.root is None
    @property
    def root_hash(self) -> Optional[str]: return self.root.hash_val if self.root else None

    # --- Tree Construction ---
    def build_from_files(self, files: List[FileModel]) -> None:
        leaves = []
        for f in files:
            h = f.sha256_hash or sha256_hash(f"{f.filename}_{f.file_size}_{f.priority}")
            leaves.append(MerkleNode(h, file_id=f.file_id, filename=f.filename))
        self._leaf_map = {leaf.file_id: leaf for leaf in leaves}
        self._leaf_index = {leaf.file_id: i for i, leaf in enumerate(leaves)}
        self._levels = [leaves] if leaves else []
        while self._levels and len(self._levels[-1]) > 1:  # Pair up nodes until one root remains
            level, parents = self._levels[-1], []
            for i in range(0, len(level), 2):
                left = level[i]
                # Odd count: the last node is paired with a copy of itself
                right = level[i + 1] if i + 1 < len(level) else MerkleNode(left.hash_val, file_id=left.file_id, filename=left.filename)
                parents.append(MerkleNode(sha256_hash(left.hash_val + right.hash_val), left, right))
            self._levels.append(parents)
        self.root = self._levels[-1][0] if self._levels else None

    # --- Audit Proofs & Verification ---
    def get_audit_proof(self, file_id: str) -> Optional[List[Tuple[str, str]]]:
        """Sibling hash at each level from leaf to root, with the side it sits on."""
        if file_id not in self._leaf_index: return None
        idx, proof = self._leaf_index[file_id], []
        for level in self._levels[:-1]:
            if idx % 2 == 0:  # We are a left child; sibling on the right (itself if missing)
                sibling = level[idx + 1] if idx + 1 < len(level) else level[idx]
                proof.append((sibling.hash_val, 'right'))
            else:
                proof.append((level[idx - 1].hash_val, 'left'))
            idx //= 2
        return proof

    @staticmethod
    def proof_path(leaf_hash: str, proof: List[Tuple[str, str]]) -> List[str]:
        """The hashes recomputed at each level when climbing from the leaf; the last one should be the root."""
        path, current = [], leaf_hash
        for sibling, side in proof:
            current = sha256_hash(current + sibling) if side == 'right' else sha256_hash(sibling + current)
            path.append(current)
        return path

    @staticmethod
    def verify_proof(leaf_hash: str, proof: List[Tuple[str, str]], root_hash: str) -> bool:
        path = MerkleTree.proof_path(leaf_hash, proof)
        return (path[-1] if path else leaf_hash) == root_hash

    # --- Tamper Detection ---
    def verify_file(self, file_id: str, current_hash: str) -> Tuple[bool, str]:
        leaf = self._leaf_map.get(file_id)
        if leaf is None: return (False, f"File ID '{file_id}' not indexed.")
        if leaf.hash_val != current_hash: return (False, f"TAMPER DETECTED: File '{leaf.filename}' modified!")
        if not self.verify_proof(current_hash, self.get_audit_proof(file_id), self.root_hash):
            return (False, "AUDIT PATH FAILED: Root mismatch!")
        return (True, f"File '{leaf.filename}' integrity valid.")

    def detect_tampered_files(self, current_hashes: Dict[str, str]) -> List[Dict[str, Any]]:
        violations = []
        for fid, leaf in self._leaf_map.items():
            actual = current_hashes.get(fid)
            if actual != leaf.hash_val:
                violations.append({"file_id": fid, "filename": leaf.filename, "expected_hash": leaf.hash_val,
                                   "actual_hash": actual or "<Missing>", "status": "TAMPERED" if actual else "MISSING"})
        return violations

    # --- Display ---
    def export_structure(self) -> Optional[Dict[str, Any]]:
        """Nested JSON of hashes (leaves carry filename and file_id) for the web Algorithm Explorer."""
        def export(n: Optional[MerkleNode]) -> Optional[Dict[str, Any]]:
            if not n: return None
            return {"hash": n.hash_val, "leaf": n.is_leaf, "filename": n.filename if n.is_leaf else None,
                    "file_id": n.file_id if n.is_leaf else None, "left": export(n.left), "right": export(n.right)}
        return export(self.root)

    def display_tree(self) -> str:
        if not self.root: return "<Empty Merkle Tree>"
        lines = [f"MerkleTree [Leaves={len(self)}, Root={self.root_hash[:16]}...]", "=" * 60]
        def draw(n, prefix, is_left):
            if not n: return
            tag = f" [{n.filename}] (Leaf)" if n.is_leaf else ""
            lines.append(f"{prefix}{'└── ' if is_left else '┌── '}[{n.hash_val[:12]}...]{tag}")
            draw(n.left, prefix + ("    " if is_left else "│   "), True)
            draw(n.right, prefix + ("│   " if is_left else "    "), False)
        draw(self.root, "", True)
        return "\n".join(lines)
