"""
SmartDrive - File Domain Model
Validated metadata for one file and its version history.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid, os, re

# File extension to category mapping
EXT_MAP = {
    ".pdf": "Document", ".docx": "Document", ".doc": "Document", ".txt": "Document", ".csv": "Document",
    ".xlsx": "Document", ".pptx": "Document", ".md": "Document",
    ".png": "Image", ".jpg": "Image", ".jpeg": "Image", ".webp": "Image", ".svg": "Image",
    ".mp4": "Video", ".mkv": "Video", ".avi": "Video", ".mov": "Video",
    ".mp3": "Audio", ".wav": "Audio", ".flac": "Audio",
    ".zip": "Archive", ".rar": "Archive", ".tar": "Archive", ".gz": "Archive"
}

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")

def _parse_date(value) -> datetime:
    """Dates are stored as ISO strings in metadata.json."""
    if isinstance(value, str): return datetime.fromisoformat(value)
    return value or datetime.now(timezone.utc)

def _validate_version_fields(size: int, sha: str) -> None:
    if size < 0:
        raise ValueError("File size cannot be negative.")
    if sha and not _SHA256_RE.match(sha):
        raise ValueError("SHA-256 hash must be 64 hexadecimal characters.")

@dataclass
class FileVersion:
    """Represents a specific version of a file in the version history."""
    version_number: int
    file_size: int
    sha256_hash: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: str | None = None

    def to_dict(self) -> dict:
        return {
            "version_number": self.version_number,
            "file_size": self.file_size,
            "sha256_hash": self.sha256_hash,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FileVersion":
        return cls(version_number=data["version_number"], file_size=data["file_size"], sha256_hash=data["sha256_hash"],
                   timestamp=_parse_date(data.get("timestamp")), description=data.get("description"))

@dataclass
class FileModel:
    filename: str
    file_size: int
    priority: int = 5
    file_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    owner: str = "default_user"
    upload_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    file_extension: str = ""
    file_type: str = "Other"
    sha256_hash: str = ""
    storage_path: str = ""
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    version_history: list[FileVersion] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.validate()
        _, ext = os.path.splitext(self.filename)
        self.file_extension = (self.file_extension or ext).lower()
        if self.file_type == "Other" and self.file_extension:
            self.file_type = EXT_MAP.get(self.file_extension, "Other")
        if not self.version_history:
            self.add_version(self.file_size, self.sha256_hash, "Initial version")

    def add_version(self, new_size: int, new_hash: str, description: str | None = None) -> FileVersion:
        """Adds a new version to the file's history and updates current state."""
        _validate_version_fields(new_size, new_hash)
        version = FileVersion(len(self.version_history) + 1, new_size, new_hash, description=description)
        self.version_history.append(version)
        self.file_size, self.sha256_hash = new_size, new_hash
        return version

    # --- Version Queries ---
    @property
    def current_version(self) -> int: return len(self.version_history)

    def get_version(self, version_number: int) -> FileVersion | None:
        """Returns a specific version (1-indexed) or None if out of range."""
        return self.version_history[version_number - 1] if 1 <= version_number <= len(self.version_history) else None

    def validate(self) -> None:
        if not self.filename or not self.filename.strip():
            raise ValueError("Filename cannot be empty.")
        if not (1 <= self.priority <= 10):
            raise ValueError("Priority must be between 1 and 10.")
        _validate_version_fields(self.file_size, self.sha256_hash)

    @property
    def formatted_size(self) -> str:
        if self.file_size < 1024: return f"{self.file_size} B"
        size = float(self.file_size)
        for unit in ["KB", "MB", "GB"]:
            size /= 1024.0
            if size < 1024.0 or unit == "GB": return f"{size:.2f} {unit}"

    def to_dict(self) -> dict:
        return {
            "file_id": self.file_id, "filename": self.filename, "file_size": self.file_size,
            "formatted_size": self.formatted_size, "priority": self.priority, "owner": self.owner,
            "upload_date": self.upload_date.isoformat(), "file_extension": self.file_extension,
            "file_type": self.file_type, "sha256_hash": self.sha256_hash,
            "storage_path": self.storage_path, "description": self.description, "tags": self.tags,
            "version_history": [v.to_dict() for v in self.version_history]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FileModel":
        return cls(
            file_id=data.get("file_id", str(uuid.uuid4())), filename=data["filename"],
            file_size=int(data["file_size"]), priority=int(data.get("priority", 5)),
            owner=data.get("owner", "default_user"), upload_date=_parse_date(data.get("upload_date")),
            file_extension=data.get("file_extension", ""), file_type=data.get("file_type", "Other"),
            sha256_hash=data.get("sha256_hash", ""), storage_path=data.get("storage_path", ""),
            description=data.get("description"), tags=data.get("tags", []),
            version_history=[FileVersion.from_dict(v) for v in data.get("version_history", [])]
        )
