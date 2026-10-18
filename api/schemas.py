"""
SmartDrive - API Schemas & Serializers
Pydantic request bodies and JSON converters shared by the FastAPI routes.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from models.file_model import FileModel

# --- Request Bodies ---
class TextFileIn(BaseModel):
    filename: str
    content: str = ""
    priority: int = Field(5, ge=1, le=10)
    description: Optional[str] = None
    tags: List[str] = []

class TextVersionIn(BaseModel):
    content: str
    description: Optional[str] = None

class MetadataIn(BaseModel):
    priority: Optional[int] = Field(None, ge=1, le=10)
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class RollbackIn(BaseModel):
    version: int = Field(..., ge=1)

class OptimizeIn(BaseModel):
    capacity_kb: float = Field(..., ge=0)
    method: str = "compare"  # compare | dp | greedy | bnb

class AskIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)

class ApplyAIIn(BaseModel):
    tags: bool = True
    priority: bool = False

class PairIn(BaseModel):
    a: str = Field("", max_length=400)
    b: str = Field("", max_length=400)
    mode: str = "chars"  # chars | lines | words

class KnapsackItemIn(BaseModel):
    label: str
    weight: int = Field(..., ge=0, le=1000)
    value: int = Field(..., ge=0, le=1000)

class KnapsackSandboxIn(BaseModel):
    items: List[KnapsackItemIn] = Field(..., max_length=12)
    capacity: int = Field(..., ge=0, le=200)

class SandboxIn(BaseModel):
    keys: List[str] = Field(..., max_length=40)
    capacity: int = Field(4, ge=1, le=64)  # Hash sandbox only

# --- Serializers ---
def file_json(f: FileModel, brief: bool = False) -> Dict[str, Any]:
    d = {"file_id": f.file_id, "filename": f.filename, "file_size": f.file_size, "formatted_size": f.formatted_size,
         "priority": f.priority, "file_type": f.file_type, "file_extension": f.file_extension,
         "upload_date": f.upload_date.isoformat(), "description": f.description, "tags": f.tags,
         "current_version": f.current_version, "sha256_hash": f.sha256_hash}
    if not brief:
        d.update({"owner": f.owner, "storage_path": f.storage_path,
                  "version_history": [v.to_dict() for v in f.version_history]})
    return d

def result_json(r) -> Dict[str, Any]:
    """KnapsackResult -> JSON with the chosen files' ids."""
    d = r.to_dict()
    d["selected_files"] = [{"file_id": i.payload.file_id, "filename": i.payload.filename, "size": i.payload.file_size,
                            "priority": i.payload.priority} for i in r.selected if i.payload is not None]
    return d

def replace_files(obj: Any) -> Any:
    """Recursively turns FileModel objects inside AI results into brief JSON."""
    if isinstance(obj, FileModel): return file_json(obj, brief=True)
    if isinstance(obj, dict): return {k: replace_files(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)): return [replace_files(v) for v in obj]
    return obj
