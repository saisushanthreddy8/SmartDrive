# SmartDrive

A Google Drive style file manager whose core operations run on data structures and algorithms
implemented from scratch: AVL tree, hash table, trie, max heap, Merkle tree, LCS diff,
0/1 knapsack (DP, greedy, branch and bound), edit distance and an offline TF-IDF AI.

## Run it

On Windows you can simply double-click `run.bat` (installs the packages, then starts the web app).

```bash
pip install -r requirements.txt
python server.py          # web app at http://127.0.0.1:8000 (opens your browser)
python cli.py             # original terminal menu (no extra packages needed)
python -m unittest discover -s tests -t .    # 124 tests
```

The React frontend is already built into `frontend/dist`, so Node.js is not needed to run the app.
API documentation is generated at http://127.0.0.1:8000/docs.

Files live in `storage/` (created on first run, seeded with 7 sample files). Delete `storage/` to start fresh.

## Project structure

```
ADSA_Code/
├── cli.py                    Terminal app (Phases 1-4)
├── server.py                 Web app launcher (Phase 5)
├── run.bat                   Windows one-click start (install + launch)
├── models/
│   └── file_model.py         FileModel + FileVersion
├── data_structures/
│   ├── avl_tree.py           Sorted index, range search, rotation log
│   ├── hash_table.py         Separate chaining, polynomial hash, auto-resize
│   ├── trie.py               Prefix search / autocomplete
│   ├── binary_heap.py        Priority queue, arbitrary removal
│   ├── merkle_tree.py        SHA-256 integrity, audit proofs
│   ├── lcs_diff.py           Version comparison
│   ├── knapsack.py           Storage optimizer: DP, Greedy, Branch & Bound
│   └── edit_distance.py      Levenshtein DP for typo-tolerant search
├── services/
│   ├── core_engine.py        SmartDriveEngine: keeps every structure in sync
│   ├── file_service.py       Real storage: category folders, versions, metadata.json
│   ├── ai_service.py         Offline AI: TF-IDF, inverted index, summaries, tags
│   └── sample_data.py        Demo files seeded on first run
├── api/
│   ├── main.py               FastAPI routes (also serves the React build)
│   ├── explorer.py           Step-by-step sandboxes and DP tables for the Algorithm Explorer
│   └── schemas.py            Request bodies and JSON serializers
├── frontend/                 React + Vite web app (source in src/, build in dist/)
├── tests/                    unittest suites, one per component
└── storage/                  Runtime data (git-ignored)
```

## Phases

| Phase | Scope | Where |
|---|---|---|
| 1 | File model, AVL indexing | `models/`, `avl_tree.py` |
| 2 | Hash table lookup, trie prefix search | `hash_table.py`, `trie.py` |
| 3 | Heap priority processing, Merkle + SHA-256 integrity | `binary_heap.py`, `merkle_tree.py` |
| 4 | Version history, LCS diff, knapsack optimizer | `lcs_diff.py`, `knapsack.py`, `core_engine.py` |
| 5 | Real storage, FastAPI, React, AI, Algorithm Explorer | `file_service.py`, `api/`, `frontend/`, `ai_service.py`, `edit_distance.py` |

## Web app pages

| Page | What it shows | Structures |
|---|---|---|
| Drive | Upload (button or drag and drop), list, sort, filter, preview, edit metadata, download, delete | AVL, Hash Table, Trie, Heap, Merkle |
| File panel: Versions | Edit as text or upload a new version, LCS diff with similarity, restore any version | LCS |
| File panel: Integrity | Re-hash from disk, Merkle audit proof step by step, tamper and repair demo | Merkle, SHA-256 |
| File panel: AI insights | Summary, keywords, suggested tags and priority with reasons, similar files | TF-IDF |
| Search | Prefix, typo-tolerant and content search side by side, with timings | Trie, Edit Distance, TF-IDF |
| Priority queue | Processing order, heap drawn as a tree and as its array | Max Heap |
| Integrity | Whole-drive audit, Merkle tree with failing leaves in red | Merkle |
| Storage optimizer | Budget slider, DP vs Greedy vs Branch & Bound, which files each keeps | Knapsack |
| Algorithm explorer | Live view of each structure plus step-by-step sandboxes and DP tables | All |
| AI assistant | Ask questions answered from your files, duplicate and near-duplicate finder | TF-IDF, SHA-256, Edit Distance |

The trace strip at the bottom records which data structure handled each action and how long it took.

## AI features (offline)

No API key and no internet. Built from scratch in `services/ai_service.py`:
- Text extraction from txt/md/csv/code, docx/pptx/xlsx (zip XML) and PDF (if `pypdf` is installed)
- TF-IDF vectors with an inverted index and cosine similarity for content search, similar files and Q&A
- Extractive summaries, keywords, rule-based tag suggestions, explainable priority suggestions
- Duplicate detection: identical SHA-256, near-identical text (cosine >= 0.85), similar names (edit distance)

## Suggested review demo

1. Drive: type `mach` (Trie autocomplete), press Enter (Search page compares three algorithms; try `machne`).
2. Upload a text file, open Versions, edit it, see the LCS diff, restore v1.
3. Integrity tab: Simulate tampering, Verify (fails, proof root mismatch), Repair.
4. Storage optimizer at 7 KB: Greedy 23 vs DP / Branch & Bound 27.
5. Algorithm explorer: AVL sandbox (LL/RR/LR/RL rotations), hash resize, LCS and knapsack tables.
6. AI assistant: "When is the assignment deadline?"

## Frontend development (optional)

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, proxies /api to python server.py on :8000
npm run build    # refresh frontend/dist
```
