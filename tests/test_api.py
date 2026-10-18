"""
Integration tests for the SmartDrive FastAPI backend (uses FastAPI's TestClient).
Skipped automatically if fastapi / httpx are not installed.
"""

import unittest
import tempfile
import shutil

try:
    from fastapi.testclient import TestClient
    from api.main import create_app
    HAS_API = True
except ImportError:  # pragma: no cover
    HAS_API = False


@unittest.skipUnless(HAS_API, "fastapi/httpx not installed (pip install -r requirements.txt)")
class TestAPI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.c = TestClient(create_app(storage_dir=self.tmp))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def upload(self, name="plan.txt", data=b"line a\nline b", **form):
        r = self.c.post("/api/files", files={"file": (name, data)}, data={k: str(v) for k, v in form.items()})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["file_id"]

    def test_health_stats_and_listing(self):
        self.assertEqual(self.c.get("/api/health").json()["files"], 7)
        files = self.c.get("/api/files").json()
        names = [f["filename"] for f in files["files"]]
        self.assertEqual(names, sorted(names))
        self.assertEqual(self.c.get("/api/files", params={"file_type": "image"}).json()["count"], 1)
        by_prio = [f["priority"] for f in self.c.get("/api/files", params={"sort": "priority", "order": "desc"}).json()["files"]]
        self.assertEqual(by_prio, sorted(by_prio, reverse=True))
        self.assertEqual(self.c.get("/api/stats").json()["total_files"], 7)

    def test_upload_lookup_search(self):
        fid = self.upload(priority=7, tags="exam, notes")
        f = self.c.get(f"/api/files/{fid}").json()
        self.assertEqual((f["priority"], f["tags"], f["storage_path"]), (7, ["exam", "notes"], "documents/plan.txt"))
        self.assertEqual(self.c.get("/api/lookup", params={"key": "plan.txt"}).json()["matched_by"], "filename")
        self.assertEqual(self.c.get("/api/lookup", params={"key": "nope"}).status_code, 404)
        self.assertEqual(self.c.get("/api/autocomplete", params={"q": "pla"}).json()["suggestions"][0]["filename"], "plan.txt")
        s = self.c.get("/api/search", params={"q": "machne"}).json()
        self.assertEqual(len(s["fuzzy"]["results"]), 2)
        self.assertEqual(self.c.post("/api/files", files={"file": ("PLAN.TXT", b"x")}).status_code, 400)
        self.assertEqual(self.c.post("/api/files/text", json={"filename": "a.txt", "content": "x", "priority": 11}).status_code, 422)

    def test_versions_diff_rollback_download(self):
        fid = self.upload()
        r = self.c.put(f"/api/files/{fid}/text", json={"content": "line a\nline c", "description": "edit"}).json()
        self.assertEqual(r["new_version"], 2)
        d = self.c.get(f"/api/files/{fid}/diff", params={"v1": 1, "v2": 2}).json()
        self.assertEqual((d["stats"]["added"], d["stats"]["removed"], d["lcs_length"]), (1, 1, 1))
        self.assertEqual(self.c.post(f"/api/files/{fid}/rollback", json={"version": 1}).json()["new_version"], 3)
        self.assertEqual(self.c.get(f"/api/files/{fid}/download").content, b"line a\nline b")
        self.assertEqual(self.c.get(f"/api/files/{fid}/download", params={"version": 2}).content, b"line a\nline c")
        self.assertEqual(self.c.post(f"/api/files/{fid}/rollback", json={"version": 3}).status_code, 400)
        new = self.c.put(f"/api/files/{fid}/content", files={"file": ("x", b"uploaded")}).json()
        self.assertEqual(new["file"]["current_version"], 4)
        self.assertEqual(self.c.get(f"/api/files/{fid}/preview").json()["text"], "uploaded")

    def test_integrity_tamper_repair(self):
        fid = self.upload()
        v = self.c.get(f"/api/files/{fid}/verify").json()
        self.assertTrue(v["valid"] and v["root_matches"])
        self.c.post(f"/api/files/{fid}/tamper")
        self.assertFalse(self.c.get(f"/api/files/{fid}/verify").json()["valid"])
        self.assertEqual(self.c.get("/api/integrity/audit").json()["tampered_count"], 1)
        self.assertTrue(self.c.post(f"/api/files/{fid}/repair").json()["valid"])
        self.assertFalse(self.c.get("/api/integrity/audit").json()["is_tampered"])

    def test_queue_and_metadata(self):
        fid = self.upload()
        self.c.patch(f"/api/files/{fid}", json={"priority": 10})
        q = self.c.get("/api/queue").json()["queue"]
        self.assertEqual(len(q), 8)
        self.assertEqual(q[0]["priority"], 10)
        first = self.c.post("/api/queue/next").json()
        self.assertEqual(first["remaining"], 7)
        self.assertEqual(self.c.post("/api/queue/reset").json()["size"], 8)

    def test_optimizer(self):
        res = self.c.post("/api/optimize", json={"capacity_kb": 7}).json()["results"]
        self.assertEqual([r["total_value"] for r in res], [27, 23, 27])
        self.assertTrue(res[0]["selected_files"])
        self.assertEqual(self.c.post("/api/optimize", json={"capacity_kb": 7, "method": "magic"}).status_code, 400)

    def test_ai_endpoints(self):
        fid = self.upload("ml.txt", b"Supervised learning uses labelled data. The exam deadline is Friday.")
        self.assertTrue(self.c.post("/api/ai/ask", json={"question": "When is the exam deadline?"}).json()["found"])
        self.assertTrue(self.c.get("/api/search", params={"q": "supervised"}).json()["semantic"]["results"])
        ins = self.c.get(f"/api/files/{fid}/insights").json()
        self.assertIn("summary", ins)
        applied = self.c.post(f"/api/files/{fid}/ai/apply", json={"tags": True, "priority": True}).json()
        self.assertTrue(applied["tags"])
        self.assertIn("exact", self.c.get("/api/ai/duplicates").json())

    def test_explorer(self):
        for s in ["avl", "hash", "trie", "heap", "merkle"]:
            self.assertEqual(self.c.get(f"/api/explorer/{s}").status_code, 200)
        self.assertEqual(self.c.get("/api/explorer/graph").status_code, 400)
        avl = self.c.post("/api/explorer/sandbox/avl", json={"keys": ["9", "10", "11"]}).json()["steps"]
        self.assertEqual((avl[-1]["rotations"], avl[-1]["root"]["key"]), (["RR at 9"], "10"))
        h = self.c.post("/api/explorer/sandbox/hash", json={"keys": list("abcd"), "capacity": 4}).json()["steps"]
        self.assertTrue(h[-1]["note"])  # 4/4 > 0.75 triggers resize
        heap = self.c.post("/api/explorer/sandbox/heap", json={"keys": ["3", "9", "pop"]}).json()["steps"]
        self.assertIn("9", heap[-1]["op"])
        self.assertEqual(self.c.post("/api/explorer/lcs", json={"a": "ABCBDAB", "b": "BDCABA"}).json()["length"], 4)
        self.assertEqual(self.c.post("/api/explorer/edit-distance", json={"a": "kitten", "b": "sitting"}).json()["distance"], 3)
        k = self.c.post("/api/explorer/knapsack", json={"items": [{"label": "A", "weight": 10, "value": 60}, {"label": "B", "weight": 20, "value": 100},
                                                                 {"label": "C", "weight": 30, "value": 120}], "capacity": 50}).json()
        self.assertEqual(k["best"], 220)

    def test_delete_and_unknown_routes(self):
        fid = self.upload()
        self.assertEqual(self.c.delete(f"/api/files/{fid}").json()["deleted"], "plan.txt")
        self.assertEqual(self.c.get(f"/api/files/{fid}").status_code, 404)
        self.assertEqual(self.c.get("/api/does-not-exist").status_code, 404)


if __name__ == "__main__":
    unittest.main()
