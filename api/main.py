"""
SmartDrive - FastAPI Backend
REST API over SmartDriveEngine (data structures), FileStorageManager (real files) and AIService (offline AI).
It also serves the built React app (frontend/dist), so one command runs everything:
    python server.py   ->   http://127.0.0.1:8000   (API docs at /docs)

Routes are `async`, so requests run one at a time on the event loop and the
data structures never see two changes at once.
"""
import time, mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from cli import SmartDriveCLI
from models.file_model import FileModel
from services.ai_service import AIService, extract_text
from data_structures.merkle_tree import MerkleTree
from api import explorer
from api.schemas import (TextFileIn, TextVersionIn, MetadataIn, RollbackIn, OptimizeIn, AskIn, ApplyAIIn, PairIn,
                         KnapsackSandboxIn, SandboxIn, file_json, result_json, replace_files)

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_DIFF_CELLS = 4_000_000
MAX_PREVIEW_CHARS = 20_000
MEDIA_MAGIC = (b"%PDF", b"\x89PNG", b"\xff\xd8", b"GIF8", b"ID3", b"RIFF")  # Start bytes of real PDF/PNG/JPG/GIF/MP3/WAV

def timed(fn: Callable, *args):
    """Runs fn(*args) and returns (result, milliseconds) so the UI can show how fast each structure is."""
    start = time.perf_counter()
    result = fn(*args)
    return result, round((time.perf_counter() - start) * 1000, 3)

def is_real_media(data: bytes) -> bool:
    """Demo files are plain text with media extensions; only real media files start with these bytes."""
    return data.startswith(MEDIA_MAGIC)

def create_app(storage_dir: Optional[str] = None, seed: bool = True) -> FastAPI:
    app = FastAPI(title="SmartDrive API", version="5.0",
                  description="File manager built on AVL, hash table, trie, heap, Merkle tree, LCS, knapsack, edit distance and offline AI.")
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                       allow_methods=["*"], allow_headers=["*"])  # For `npm run dev`

    cli = SmartDriveCLI(storage_dir=storage_dir, seed=seed)  # Same storage + sample files as the CLI
    engine, storage, ai = cli.engine, cli.storage, AIService(cli.engine)

    @app.exception_handler(ValueError)
    async def bad_request(_: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    def get_file(file_id: str) -> FileModel:
        f = engine.get_file_by_id(file_id)
        if not f: raise HTTPException(404, f"File '{file_id}' not found.")
        return f

    def with_file(res: Dict[str, Any]) -> Dict[str, Any]:
        return {**res, "file": file_json(engine.get_file_by_id(res["file_id"]))}

    async def read_upload(file: UploadFile) -> bytes:
        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES: raise HTTPException(413, "File larger than 100 MB.")
        return data

    # --- Overview ---
    @app.get("/api/health")
    async def health():
        return {"status": "ok", "files": len(engine), "storage": str(storage.base_dir),
                "frontend_built": (FRONTEND_DIST / "index.html").is_file()}

    @app.get("/api/stats")
    async def stats(): return engine.get_stats()

    # --- Listing & Lookup (AVL tree, hash tables) ---
    @app.get("/api/files")
    async def list_files(file_type: Optional[str] = None, sort: str = "name", order: str = "asc"):
        """By default the AVL in-order traversal already gives alphabetical order."""
        pairs, took = timed(engine.list_all_files_sorted)
        files = [f for _, f in pairs if not file_type or f.file_type.lower() == file_type.lower()]
        sort_keys = {"size": lambda f: f.file_size, "priority": lambda f: f.priority,
                     "date": lambda f: f.upload_date, "versions": lambda f: f.current_version}
        if sort in sort_keys: files.sort(key=sort_keys[sort])
        if order == "desc": files.reverse()
        return {"files": [file_json(f, brief=True) for f in files], "count": len(files),
                "source": "AVL in-order traversal", "took_ms": took}

    @app.get("/api/files/{file_id}")
    async def file_detail(file_id: str): return file_json(get_file(file_id))

    @app.get("/api/lookup")
    async def lookup(key: str):
        """Exact O(1) lookup by filename, then by file ID (two hash tables)."""
        f, table, matched_by = engine.get_file_by_name(key), engine.hash_by_name, "filename"
        if not f: f, table, matched_by = engine.get_file_by_id(key), engine.hash_by_id, "file_id"
        if not f: raise HTTPException(404, f"'{key}' not found.")
        return {"file": file_json(f, brief=True), "matched_by": matched_by,
                "bucket": table.get_bucket_index(key), "capacity": table.capacity}

    @app.get("/api/range")
    async def name_range(start: str, end: str):
        return {"files": [file_json(f, brief=True) for _, f in engine.get_files_in_range(start, end)], "source": "AVL range search"}

    # --- Search (trie, edit distance, TF-IDF) ---
    @app.get("/api/autocomplete")
    async def autocomplete(q: str = "", limit: int = Query(8, ge=1, le=50)):
        matches, took = timed(engine.search_autocomplete, q, limit) if q else ([], 0.0)
        return {"suggestions": [{"filename": n, "file_id": f.file_id, "file_type": f.file_type} for n, f in matches],
                "took_ms": took, "source": "Trie prefix DFS"}

    @app.get("/api/search")
    async def search(q: str = Query(..., min_length=1, max_length=200)):
        """Runs all three search methods so the UI can compare them."""
        prefix, p_ms = timed(engine.search_autocomplete, q, 20)
        fuzzy, f_ms = timed(engine.fuzzy_search, q, 20)
        semantic, s_ms = timed(ai.semantic_search, q, 10)
        return {
            "query": q,
            "prefix": {"results": [file_json(f, brief=True) for _, f in prefix], "took_ms": p_ms},
            "fuzzy": {"results": [{**file_json(r["file"], brief=True), "distance": r["distance"], "matched": r["matched"],
                                   "method": r["method"]} for r in fuzzy], "took_ms": f_ms},
            "semantic": {"results": [{**file_json(r["file"], brief=True), "score": r["score"], "matched_terms": r["matched_terms"],
                                      "snippet": r["snippet"]} for r in semantic], "took_ms": s_ms},
            "did_you_mean": None if (prefix or fuzzy or semantic) else engine.did_you_mean(q),
        }

    # --- Upload, Edit, Delete (real storage) ---
    @app.post("/api/files", status_code=201)
    async def upload(file: UploadFile = File(...), priority: int = Form(5), description: Optional[str] = Form(None),
                     tags: Optional[str] = Form(None)):
        res = engine.upload_content(Path(file.filename or "").name, await read_upload(file), priority, (description or "").strip() or None)
        if tags: engine.update_metadata(res["file_id"], tags=tags.split(","))
        return with_file(res)

    @app.post("/api/files/text", status_code=201)
    async def create_text(body: TextFileIn):
        res = engine.upload_content(body.filename, body.content, body.priority, (body.description or "").strip() or None)
        if body.tags: engine.update_metadata(res["file_id"], tags=body.tags)
        return with_file(res)

    @app.put("/api/files/{file_id}/content")
    async def new_version(file_id: str, file: UploadFile = File(...), description: Optional[str] = Form(None)):
        get_file(file_id)
        return with_file(engine.update_content(file_id, await read_upload(file), (description or "").strip() or None))

    @app.put("/api/files/{file_id}/text")
    async def new_text_version(file_id: str, body: TextVersionIn):
        get_file(file_id)
        return with_file(engine.update_content(file_id, body.content, (body.description or "").strip() or None))

    @app.patch("/api/files/{file_id}")
    async def edit_metadata(file_id: str, body: MetadataIn):
        get_file(file_id)
        return file_json(engine.update_metadata(file_id, body.priority, body.description, body.tags))

    @app.delete("/api/files/{file_id}")
    async def delete(file_id: str):
        f = get_file(file_id)
        engine.delete_file(f.filename)
        return {"deleted": f.filename, "merkle_root": engine.merkle.root_hash}

    # --- Download & Preview ---
    @app.get("/api/files/{file_id}/download")
    async def download(file_id: str, version: Optional[int] = None, inline: bool = False):
        f = get_file(file_id)
        if version is None:
            path, name = storage.resolve(f.storage_path), f.filename
        else:
            if not f.get_version(version): raise HTTPException(404, f"Version {version} not found.")
            stem, dot, ext = f.filename.rpartition(".")
            path, name = storage.version_path(file_id, version, f.filename), f"{stem}_v{version}.{ext}" if dot else f"{ext}_v{version}"
        if not path.is_file(): raise HTTPException(404, "File missing from disk.")
        return FileResponse(path, filename=name, content_disposition_type="inline" if inline else "attachment")

    @app.get("/api/files/{file_id}/preview")
    async def preview(file_id: str):
        f = get_file(file_id)
        try: data = storage.read_file_content(f.storage_path)
        except FileNotFoundError: data = b""
        mime = mimetypes.guess_type(f.filename)[0] or ""
        if is_real_media(data) and (mime.startswith(("image/", "audio/", "video/")) or mime == "application/pdf"):
            return {"kind": "pdf" if mime == "application/pdf" else mime.split("/")[0], "mime": mime}
        text = extract_text(f.filename, data)
        if not text: return {"kind": "binary", "mime": mime}
        return {"kind": "text", "text": text[:MAX_PREVIEW_CHARS], "truncated": len(text) > MAX_PREVIEW_CHARS}

    # --- Version Control (LCS) ---
    @app.get("/api/files/{file_id}/diff")
    async def diff(file_id: str, v1: int, v2: int):
        f = get_file(file_id)
        if not (f.get_version(v1) and f.get_version(v2)): raise HTTPException(400, "Invalid version number.")
        a, b = engine.read_version_content(file_id, v1), engine.read_version_content(file_id, v2)
        if a is None or b is None: raise HTTPException(404, "Version snapshot missing from storage/versions/.")
        ta, tb = extract_text(f.filename, a), extract_text(f.filename, b)
        if not (ta or tb) and (a or b):
            return {"binary": True, "identical": a == b, "v1": v1, "v2": v2, "sizes": [len(a), len(b)]}
        lines_a, lines_b = len(ta.splitlines()), len(tb.splitlines())
        if lines_a * lines_b > MAX_DIFF_CELLS: raise HTTPException(413, "Files too large for an LCS diff (O(m*n) table).")
        cmp, took = timed(engine.compare_versions, ta, tb)
        return {"binary": False, "v1": v1, "v2": v2, "diff": [{"op": op, "text": line} for op, line in cmp["diff"]],
                "stats": cmp["stats"], "lcs_length": cmp["lcs_length"], "took_ms": took, "table_size": [lines_a + 1, lines_b + 1]}

    @app.post("/api/files/{file_id}/rollback")
    async def rollback(file_id: str, body: RollbackIn):
        f = get_file(file_id)
        if body.version == f.current_version: raise HTTPException(400, "Already the current version.")
        res = engine.rollback_to_version(file_id, body.version)
        if not res: raise HTTPException(400, "Invalid version number or snapshot missing.")
        return with_file(res)

    # --- Integrity (Merkle tree + SHA-256) ---
    @app.get("/api/files/{file_id}/verify")
    async def verify(file_id: str):
        f = get_file(file_id)
        disk_hash = storage.compute_file_hash(f.storage_path)
        valid, message = engine.verify_file_on_disk(file_id)
        proof = engine.get_audit_proof(file_id) or []
        path = MerkleTree.proof_path(disk_hash or "", proof)  # Climb from the hash on disk to the root
        recomputed = path[-1] if path else disk_hash
        return {"file_id": file_id, "filename": f.filename, "valid": valid, "message": message,
                "expected_hash": f.sha256_hash, "disk_hash": disk_hash, "root": engine.merkle.root_hash,
                "proof": [{"sibling": s, "side": side, "result": r} for (s, side), r in zip(proof, path)],
                "recomputed_root": recomputed, "root_matches": recomputed == engine.merkle.root_hash}

    @app.get("/api/integrity/audit")
    async def audit():
        res, took = timed(engine.audit_drive)
        return {**res, "took_ms": took}

    @app.post("/api/files/{file_id}/tamper")
    async def tamper(file_id: str):
        """Demo only: changes the real file on disk behind SmartDrive's back."""
        path = storage.resolve(get_file(file_id).storage_path)
        if not path.is_file(): raise HTTPException(404, "File missing from disk.")
        with open(path, "ab") as fh: fh.write(b"\n[TAMPERED BY DEMO]")
        return {"tampered": path.name, "path": str(path)}

    @app.post("/api/files/{file_id}/repair")
    async def repair(file_id: str):
        """Restores the file from its latest trusted version snapshot."""
        f = get_file(file_id)
        if not storage.restore_version(file_id, f.current_version, f.filename, f.storage_path):
            raise HTTPException(404, "No snapshot available to repair from.")
        valid, message = engine.verify_file_on_disk(file_id)
        return {"repaired": f.filename, "valid": valid, "message": message}

    # --- Priority Queue (max heap) ---
    @app.get("/api/queue")
    async def queue():
        return {"queue": [{"priority": p, "file": file_json(f, brief=True)} for p, f in engine.queue_snapshot()],
                "heap": engine.heap.export_structure(label=lambda f: f.filename)}

    @app.post("/api/queue/next")
    async def queue_next():
        item = engine.process_next_priority_file()
        if not item: raise HTTPException(404, "Queue empty.")
        return {"processed": file_json(item[1], brief=True), "priority": item[0], "remaining": len(engine.heap)}

    @app.post("/api/queue/reset")
    async def queue_reset(): return {"size": engine.requeue_all(), "method": "Floyd build-heap O(n)"}

    # --- Storage Optimizer (0/1 knapsack) ---
    @app.post("/api/optimize")
    async def optimize(body: OptimizeIn):
        cap = int(body.capacity_kb * 1024)
        if body.method == "compare": results = engine.compare_optimizers(cap)
        elif body.method in engine.METHODS: results = [engine.optimize_storage(cap, body.method)]
        else: raise HTTPException(400, "Method must be compare, dp, greedy or bnb.")
        return {"capacity_bytes": cap, "total_bytes": engine.get_stats()["total_bytes"], "results": [result_json(r) for r in results]}

    # --- Offline AI ---
    @app.post("/api/ai/ask")
    async def ai_ask(body: AskIn):
        res, took = timed(ai.ask, body.question)
        return {**replace_files(res), "took_ms": took}

    @app.get("/api/ai/duplicates")
    async def ai_duplicates(): return replace_files(ai.find_duplicates())

    @app.get("/api/files/{file_id}/insights")
    async def insights(file_id: str): return replace_files(ai.insights(get_file(file_id)))

    @app.post("/api/files/{file_id}/ai/apply")
    async def ai_apply(file_id: str, body: ApplyAIIn):
        f = get_file(file_id)
        tags = f.tags + [t["tag"] for t in ai.suggest_tags(f)] if body.tags else None
        priority = ai.suggest_priority(f)["suggested"] if body.priority else None
        return file_json(engine.update_metadata(file_id, priority=priority, tags=tags))

    # --- Algorithm Explorer ---
    @app.get("/api/explorer/{structure}")
    async def live_structure(structure: str, prefix: str = ""): return engine.explorer_snapshot(structure, prefix)

    @app.post("/api/explorer/sandbox/{structure}")
    async def sandbox(structure: str, body: SandboxIn):
        if structure not in explorer.SANDBOXES: raise HTTPException(400, "Sandbox supports avl, hash, heap, trie.")
        keys: List[str] = [k.strip() for k in body.keys if k.strip()]
        steps = explorer.hash_steps(keys, body.capacity) if structure == "hash" else explorer.SANDBOXES[structure](keys)
        return {"structure": structure, "steps": steps}

    @app.post("/api/explorer/lcs")
    async def explorer_lcs(body: PairIn): return explorer.lcs_table(body.a, body.b, body.mode)

    @app.post("/api/explorer/edit-distance")
    async def explorer_edit(body: PairIn): return explorer.edit_distance_table(body.a, body.b)

    @app.post("/api/explorer/knapsack")
    async def explorer_knapsack(body: KnapsackSandboxIn):
        return explorer.knapsack_table([i.model_dump() for i in body.items], body.capacity)

    # --- React app (built files) ---
    if (FRONTEND_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def frontend(full_path: str):
        if full_path.startswith("api/"): raise HTTPException(404, "Unknown API route.")
        file = (FRONTEND_DIST / full_path).resolve()
        if full_path and FRONTEND_DIST in file.parents and file.is_file(): return FileResponse(file)
        if (FRONTEND_DIST / "index.html").is_file(): return FileResponse(FRONTEND_DIST / "index.html")
        return JSONResponse({"message": "SmartDrive API is running. The web app is not built (see README).", "docs": "/docs"})

    return app
