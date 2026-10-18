"""
SmartDrive - Real Partitioned File Storage Manager
Handles physical disk I/O, partitioned folder storage, per-file version snapshots,
persistent metadata (metadata.json), and real SHA-256 checksums.

Layout (anchored to the project folder, independent of the working directory):
    storage/
    ├── documents/ images/ videos/ audio/ other/   <- current version of every file
    ├── versions/<file_id>/v<N>_<filename>         <- every version snapshot
    └── metadata.json                               <- FileModel records (reloaded on startup)
"""
import os, re, json, shutil, hashlib
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List
from models.file_model import EXT_MAP

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STORAGE_DIR = PROJECT_ROOT / "storage"
CHUNK_SIZE = 1024 * 1024  # 1 MB streaming chunks for hashing large files
TYPE_FOLDERS = {"Document": "documents", "Image": "images", "Video": "videos", "Audio": "audio"}  # Anything else -> other/

class FileStorageManager:
    """Manages physical file storage on disk partitioned by category."""

    CATEGORIES = ["documents", "images", "videos", "audio", "other"]
    VERSIONS_DIR, METADATA_FILE = "versions", "metadata.json"
    _UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

    def __init__(self, base_storage_dir: str | Path | None = None):
        self.base_dir = Path(base_storage_dir or DEFAULT_STORAGE_DIR).resolve()
        self._init_directories()

    def _init_directories(self) -> None:
        """Creates physical category folders on disk if they don't exist."""
        for folder in self.CATEGORIES + [self.VERSIONS_DIR]:
            (self.base_dir / folder).mkdir(parents=True, exist_ok=True)

    # --- Path Safety ---
    def safe_filename(self, filename: str) -> str:
        """Rejects names that could escape the storage folder or are invalid on Windows/Linux."""
        name = (filename or "").strip()
        if not name or name in (".", "..") or self._UNSAFE_CHARS.search(name):
            raise ValueError(f"Invalid filename: {filename!r} (no paths or special characters allowed).")
        return name

    def resolve(self, storage_path: str) -> Path:
        """Turns a stored relative path into an absolute path, guaranteed to stay inside storage/."""
        path = (self.base_dir / storage_path).resolve()
        if path != self.base_dir and self.base_dir not in path.parents:
            raise ValueError(f"Path escapes storage folder: {storage_path}")
        return path

    def _rel(self, path: Path) -> str: return path.relative_to(self.base_dir).as_posix()

    def get_category_folder(self, filename: str) -> str:
        """Folder for a filename, based on the same extension table FileModel uses for file_type."""
        ext = os.path.splitext(filename)[1].lower()
        return TYPE_FOLDERS.get(EXT_MAP.get(ext), "other")

    @staticmethod
    def _source_file(source_path: str) -> Path:
        """A file on the user's PC (surrounding quotes allowed, as Windows "Copy as path" adds them)."""
        src = Path(source_path.strip().strip('"')).expanduser().resolve()
        if not src.is_file(): raise FileNotFoundError(f"Source file not found at: {source_path}")
        return src

    # --- Hashing ---
    @staticmethod
    def hash_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()

    def compute_file_hash(self, storage_path: str) -> Optional[str]:
        """Computes current SHA-256 directly from the physical file (streamed, memory-safe)."""
        path = self.resolve(storage_path)
        if not path.is_file(): return None
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b""): h.update(chunk)
        return h.hexdigest()

    # --- Current File Operations ---
    def save_file_content(self, filename: str, content: bytes | str) -> Tuple[str, str, int]:
        """
        Physically writes content to disk in the appropriate partition.
        Returns: (relative_storage_path, sha256_hash, file_size_in_bytes)
        """
        name = self.safe_filename(filename)
        dest_path = self.base_dir / self.get_category_folder(name) / name
        data = content.encode('utf-8') if isinstance(content, str) else content
        dest_path.write_bytes(data)
        return self._rel(dest_path), self.hash_bytes(data), len(data)

    def import_local_file(self, source_path: str) -> Tuple[str, str, str, int]:
        """
        Copies a real file from the user's PC into the partitioned storage.
        Returns: (filename, relative_storage_path, sha256_hash, file_size)
        """
        src = self._source_file(source_path)
        name = self.safe_filename(src.name)
        dest_path = self.base_dir / self.get_category_folder(name) / name
        if src != dest_path: shutil.copy2(src, dest_path)
        rel = self._rel(dest_path)
        return name, rel, self.compute_file_hash(rel), dest_path.stat().st_size

    def replace_from_local_file(self, storage_path: str, source_path: str) -> Tuple[str, int]:
        """Overwrites an existing stored file with a file from the PC. Returns (sha256, size)."""
        src = self._source_file(source_path)
        dest = self.resolve(storage_path)
        if src != dest: shutil.copy2(src, dest)
        return self.compute_file_hash(storage_path), dest.stat().st_size

    def read_file_content(self, storage_path: str) -> bytes:
        """Reads physical file bytes from disk."""
        path = self.resolve(storage_path)
        if not path.is_file(): raise FileNotFoundError(f"File not found on disk: {storage_path}")
        return path.read_bytes()

    def delete_physical_file(self, storage_path: str) -> bool:
        """Removes the physical file from disk."""
        path = self.resolve(storage_path)
        if path.is_file():
            path.unlink()
            return True
        return False

    # --- Version Snapshots ---
    def version_path(self, file_id: str, version: int, filename: str) -> Path:
        fid = self.safe_filename(file_id)
        return self.base_dir / self.VERSIONS_DIR / fid / f"v{version}_{self.safe_filename(filename)}"

    def snapshot_version(self, file_id: str, version: int, filename: str, storage_path: str) -> str:
        """Copies the current physical file into versions/<file_id>/v<N>_<filename>."""
        dest = self.version_path(file_id, version, filename)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.resolve(storage_path), dest)
        return self._rel(dest)

    def read_version(self, file_id: str, version: int, filename: str) -> Optional[bytes]:
        path = self.version_path(file_id, version, filename)
        return path.read_bytes() if path.is_file() else None

    def restore_version(self, file_id: str, version: int, filename: str, storage_path: str) -> bool:
        """Copies a version snapshot back over the current physical file."""
        src = self.version_path(file_id, version, filename)
        if not src.is_file(): return False
        shutil.copy2(src, self.resolve(storage_path))
        return True

    def delete_versions(self, file_id: str) -> bool:
        folder = self.base_dir / self.VERSIONS_DIR / self.safe_filename(file_id)
        if folder.is_dir():
            shutil.rmtree(folder)
            return True
        return False

    # --- Persistent Metadata ---
    def save_metadata(self, records: List[Dict[str, Any]]) -> None:
        """Atomically writes metadata.json (temp file + replace, so a crash never leaves it half-written)."""
        target = self.base_dir / self.METADATA_FILE
        tmp = target.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"files": records}, f, indent=2)
        os.replace(tmp, target)

    def load_metadata(self) -> List[Dict[str, Any]]:
        target = self.base_dir / self.METADATA_FILE
        if not target.is_file(): return []
        try:
            with open(target, "r", encoding="utf-8") as f:
                return json.load(f).get("files", [])
        except (json.JSONDecodeError, AttributeError) as e:
            raise ValueError(f"Corrupted metadata file: {target} ({e})")

    # --- Statistics ---
    def get_storage_stats(self) -> Dict[str, Any]:
        """File count and bytes per folder. Totals cover current files only (not version snapshots)."""
        stats = {}
        for folder in self.CATEGORIES + [self.VERSIONS_DIR]:
            files = [f for f in (self.base_dir / folder).rglob("*") if f.is_file()]
            stats[folder] = {"count": len(files), "size_bytes": sum(f.stat().st_size for f in files)}
        current = [stats[c] for c in self.CATEGORIES]
        return {"base_dir": str(self.base_dir), "categories": stats,
                "total_files": sum(s["count"] for s in current), "total_size_bytes": sum(s["size_bytes"] for s in current)}
