"""
SmartDrive - Interactive CLI Engine
Terminal menu for every feature: upload, versions + LCS diff, rollback, trie search, hash lookup,
AVL listing, heap queue, Merkle integrity, knapsack optimizer, and real storage on disk.
"""
from services.core_engine import SmartDriveEngine
from services.file_service import FileStorageManager
from services.sample_data import SAMPLE_FILES, fit_to_size
from data_structures.knapsack import KnapsackOptimizer

KB = 1024
DEMO_BUDGET_KB = 7           # Budget where Greedy is visibly worse than DP / Branch & Bound on the sample files
MAX_DIFF_CELLS = 4_000_000   # LCS table is lines(A) x lines(B); refuse anything bigger

class SmartDriveCLI:
    def __init__(self, storage_dir: str | None = None, seed: bool = True):
        self.storage = FileStorageManager(storage_dir)
        self.engine = SmartDriveEngine(self.storage)  # Reloads storage/metadata.json
        if seed and len(self.engine) == 0:
            for name, size, priority, desc, text in SAMPLE_FILES:  # First run only
                self.engine.upload_content(name, fit_to_size(text, size), priority, desc)

    # --- Input / Output Helpers ---
    @staticmethod
    def _ask(prompt: str, default: str = "") -> str:
        return input(f"{prompt}{f' [{default}]' if default else ''}: ").strip() or default

    @staticmethod
    def _yes(prompt: str) -> bool:
        return input(f"{prompt} (y/n) [y]: ").strip().lower() in ("", "y", "yes")

    @staticmethod
    def _read_text(default: str) -> str:
        print("Enter text (finish with a line containing only END):")
        lines = []
        while True:
            try: line = input()
            except EOFError: break
            if line.strip() == "END": break
            lines.append(line)
        return "\n".join(lines) if lines else default

    def _find_file(self, prompt: str = "Filename"):
        f = self.engine.get_file_by_name(self._ask(prompt))
        if not f: print("File not found.")
        return f

    @staticmethod
    def _print_files(files, status=None) -> None:
        """Table of files; `status(f)` adds an extra column (used by the optimizer)."""
        print(f"{'Filename':<35} | {'Type':<12} | {'Size':<10} | {'Priority':<8}" + (" | Status" if status else ""))
        print("-" * 80)
        for f in files:
            row = f"{f.filename:<35} | {f.file_type:<12} | {f.formatted_size:<10} | {f.priority:<8}"
            print(row + (f" | {status(f)}" if status else ""))

    @staticmethod
    def _print_history(f) -> None:
        for v in f.version_history:
            print(f"  v{v.version_number}: Size {v.file_size} | Hash {v.sha256_hash[:8]}... | {v.description}")

    # --- Files ---
    def upload_file(self) -> None:
        print("\n--- UPLOAD FILE (REAL STORAGE) ---")
        from_pc = self._ask("Source: 1. Import file from PC  2. Type text content", "2") == "1"
        name = self._ask("Full path of the file on your PC" if from_pc else "Filename (e.g. notes.txt)")
        if not name: return
        priority = int(self._ask("Priority (1-10)", "5"))
        desc = self._ask("Description (optional)") or None
        if from_pc: res = self.engine.import_local_file(name, priority, desc)
        else: res = self.engine.upload_content(name, self._read_text(f"Content of {name}"), priority, desc)
        f = self.engine.get_file_by_id(res["file_id"])
        print(f"✓ Saved '{f.filename}' -> storage/{f.storage_path} | {f.formatted_size} | "
              f"SHA-256 {f.sha256_hash[:12]}... | Merkle Root: {res['merkle_root'][:16]}...")

    def update_file(self) -> None:
        print("\n--- UPDATE FILE (NEW VERSION) ---")
        f = self._find_file("Filename to update")
        if not f: return
        if self._ask("New content: 1. Import file from PC  2. Type text content", "2") == "1":
            path = self._ask("Full path of the new file on your PC")
            res = self.engine.update_content(f.file_id, description=self._ask("Version description") or None, source_path=path)
        else:
            content = self._read_text(f"Updated content of {f.filename}")
            res = self.engine.update_content(f.file_id, content, self._ask("Version description") or None)
        print(f"✓ Updated '{f.filename}' to Version {res['new_version']} | Snapshot saved in storage/versions/ "
              f"| Merkle Root: {res['merkle_root'][:16]}...")

    def delete_file(self) -> None:
        print("\n--- DELETE FILE ---")
        name = self._ask("Filename to delete")
        if self.engine.delete_file(name): print(f"✓ Deleted '{name}' from disk, its versions, and all data structures. Merkle Root updated.")
        else: print(f"File '{name}' not found.")

    # --- Version Control (LCS) ---
    def view_history_and_diff(self) -> None:
        print("\n--- VERSION HISTORY & LCS DIFF ---")
        f = self._find_file()
        if not f: return
        print(f"\nHistory for '{f.filename}':")
        self._print_history(f)
        latest = f.current_version
        if latest < 2: print("\nNot enough versions for a diff."); return
        if not self._yes("\nGenerate diff?"): return
        v1 = int(self._ask(f"Older version (1-{latest})", "1"))
        v2 = int(self._ask(f"Newer version (1-{latest})", str(latest)))
        if not (f.get_version(v1) and f.get_version(v2)): print("Invalid version number."); return
        try:
            old = self.engine.read_version_content(f.file_id, v1).decode("utf-8")
            new = self.engine.read_version_content(f.file_id, v2).decode("utf-8")
        except UnicodeDecodeError:
            same = f.get_version(v1).sha256_hash == f.get_version(v2).sha256_hash
            print(f"Binary file: versions are {'identical' if same else 'different'} (text diff not possible)."); return
        if len(old.splitlines()) * len(new.splitlines()) > MAX_DIFF_CELLS: print("Files too large for an LCS diff."); return
        cmp = self.engine.compare_versions(old, new)
        st = cmp["stats"]
        print(f"\n--- DIFF (v{v1} -> v{v2}) ---\n{self.engine.generate_diff(old, new)}\n" + "-" * 30)
        print(f"LCS: {cmp['lcs_length']} common line(s) | +{st['added']} added | -{st['removed']} removed | "
              f"{st['unchanged']} unchanged | Similarity: {st['similarity_pct']}%")

    def rollback_version(self) -> None:
        print("\n--- ROLLBACK TO PREVIOUS VERSION ---")
        f = self._find_file()
        if not f: return
        self._print_history(f)
        if f.current_version < 2: print("Only one version exists. Nothing to roll back."); return
        target = int(self._ask(f"Restore which version (1-{f.current_version - 1})"))
        if target == f.current_version: print("Already the current version."); return
        res = self.engine.rollback_to_version(f.file_id, target)
        if not res: print("Invalid version number or snapshot missing."); return
        print(f"✓ Restored v{target} as v{res['new_version']} on disk | Merkle Root: {res['merkle_root'][:16]}...")

    # --- Search & Listing (Trie, Hash Table, AVL) ---
    def search_autocomplete(self) -> None:
        print("\n--- SEARCH / AUTOCOMPLETE (TRIE) ---")
        results = self.engine.search_autocomplete(self._ask("Search prefix"))
        print(f"\nFound {len(results)} match(es):")
        self._print_files(f for _, f in results)

    def direct_lookup(self) -> None:
        print("\n--- DIRECT LOOKUP (HASH TABLE) ---")
        key = self._ask("Filename or File ID")
        f = self.engine.get_file_by_name(key) or self.engine.get_file_by_id(key)
        if not f: print(f"'{key}' not found."); return
        print(f"✓ Found in Bucket #{self.engine.hash_by_name.get_bucket_index(f.filename)} | ID: {f.file_id} | "
              f"Name: {f.filename} | Size: {f.formatted_size} | P: {f.priority}")
        print(f"  Stored at: {self.storage.resolve(f.storage_path)} | Versions: {f.current_version}")

    def list_files_sorted(self) -> None:
        print("\n--- SORTED DIRECTORY (AVL TREE IN-ORDER) ---")
        files = [f for _, f in self.engine.list_all_files_sorted()]
        self._print_files(files)
        print(f"Total: {len(files)} files | AVL Height: {self.engine.avl_tree.get_height(self.engine.avl_tree.root)}")

    # --- Priority Queue (Max Heap) ---
    def process_priority_queue(self) -> None:
        print("\n--- PRIORITY QUEUE (MAX HEAP) ---")
        top = self.engine.peek_highest_priority()
        if not top: print("Queue empty."); return
        print(f"Next Urgent Task: Priority {top[0]} -> '{top[1].filename}'")
        if self._yes("Extract and process?"):
            priority, f = self.engine.process_next_priority_file()
            print(f"✓ Processed: {f.filename} (P={priority}) | Remaining in Heap: {len(self.engine.heap)}")

    # --- Integrity (Merkle Tree) ---
    def verify_integrity(self) -> None:
        print("\n--- INTEGRITY & AUDIT (MERKLE TREE, REAL DISK HASHES) ---")
        name = self._ask("Filename to verify (blank for full drive audit)")
        if name:
            f = self.engine.get_file_by_name(name)
            if not f: print("File not found."); return
            valid, msg = self.engine.verify_file_on_disk(f.file_id)
            print(f"✓ VALID: {f.filename} | Audit Proof: {len(self.engine.get_audit_proof(f.file_id))} nodes" if valid else f"✗ {msg}")
            return
        res = self.engine.audit_drive()
        print(f"Audit: {res['total_files']} files | Tampered/Missing: {res['tampered_count']} | "
              f"Root: {(res['current_merkle_root'] or '<empty>')[:16]}...")
        for v in res["violations"]: print(f"  [!] Violation: {v['filename']} ({v['status']})")

    def simulate_tampering(self) -> None:
        print("\n--- SIMULATE FILE TAMPERING (DEMO) ---")
        f = self._find_file("Filename to corrupt on disk")
        if not f: return
        path = self.storage.resolve(f.storage_path)
        if not path.is_file(): print("File is already missing from disk."); return
        with open(path, "ab") as fh: fh.write(b"\n[TAMPERED BY DEMO]")
        print(f"(!) Modified real file on disk: {path}\n    Run Option 8 to detect it.")

    # --- Storage Optimizer (Knapsack) & Storage Info ---
    def optimize_storage(self) -> None:
        print("\n--- STORAGE OPTIMIZER (0/1 KNAPSACK) ---")
        print("Goal: keep the highest total-priority set of files within a storage budget.")
        cap_kb = float(self._ask("Storage budget in KB", str(DEMO_BUDGET_KB)))
        print("1. Dynamic Programming | 2. Greedy | 3. Branch & Bound | 4. Compare All")
        choice = self._ask("Method (1-4)", "4")
        if choice == "4":
            results = self.engine.compare_optimizers(int(cap_kb * KB))
            print(KnapsackOptimizer.display_comparison(results))
            best = next(r for r in results if r.is_optimal)
        elif choice in ("1", "2", "3"):
            best = self.engine.optimize_storage(int(cap_kb * KB), {"1": "dp", "2": "greedy", "3": "bnb"}[choice])
            print(f"{best.method}: Value={best.total_value} | Nodes={best.nodes_explored} | Time={best.time_ms:.3f} ms")
        else: print("Invalid choice."); return
        kept = {i.label for i in best.selected}
        print(f"\nSelected by {best.method} ({best.utilization:.1f}% of {cap_kb:g} KB used):")
        self._print_files((f for _, f in self.engine.list_all_files_sorted()), lambda f: "KEEP" if f.filename in kept else "SKIP")

    def storage_info(self) -> None:
        print("\n--- STORAGE INFO (DISK) ---")
        st = self.engine.get_storage_stats()
        print(f"Location: {st['base_dir']}\n{'Folder':<12} | {'Files':<6} | Size\n" + "-" * 40)
        for folder, d in st["categories"].items(): print(f"{folder:<12} | {d['count']:<6} | {d['size_bytes']:,} B")
        print(f"Current files: {st['total_files']} ({st['total_size_bytes']:,} B) | Metadata: metadata.json")

    def display_data_structures(self) -> None:
        print("\n--- ALGORITHM EXPLORER ---")
        print(f"1. AVL Tree | 2. Hash Table | 3. Trie | 4. Max Heap | 5. Merkle Tree | 6. Knapsack ({DEMO_BUDGET_KB} KB) | 7. Back")
        views = {
            "1": self.engine.avl_tree.display_tree,
            "2": lambda: f"{self.engine.hash_by_name.display_table()}\nStats: {self.engine.hash_by_name.get_collision_stats()}",
            "3": self.engine.trie.display_trie,
            "4": self.engine.heap.display_heap,
            "5": self.engine.merkle.display_tree,
            "6": lambda: KnapsackOptimizer.display_comparison(self.engine.compare_optimizers(DEMO_BUDGET_KB * KB)),
        }
        view = views.get(self._ask("Choice (1-7)"))
        if view: print(view())

    # --- Main Loop ---
    MENU = ("1. Upload File        2. Update File (New Version)\n"
            "3. History & Diff     4. Search (Trie)\n"
            "5. Direct Lookup (HT) 6. View Sorted Files (AVL)\n"
            "7. Priority Queue     8. Verify Integrity (Merkle)\n"
            "9. Simulate Tampering 10. Delete File\n"
            "11. Algo Explorer     12. Rollback Version\n"
            "13. Storage Optimizer 14. Storage Info\n"
            "15. Exit")

    def run(self) -> None:
        actions = {
            "1": self.upload_file, "2": self.update_file, "3": self.view_history_and_diff,
            "4": self.search_autocomplete, "5": self.direct_lookup, "6": self.list_files_sorted,
            "7": self.process_priority_queue, "8": self.verify_integrity, "9": self.simulate_tampering,
            "10": self.delete_file, "11": self.display_data_structures, "12": self.rollback_version,
            "13": self.optimize_storage, "14": self.storage_info,
        }
        print(f"Storage folder: {self.storage.base_dir} | Files loaded: {len(self.engine)}")
        while True:
            print("\n" + "=" * 50 + "\n  SMARTDRIVE — ADVANCED DSA CORE\n" + "=" * 50 + "\n" + self.MENU + "\n" + "=" * 50)
            try: choice = input("Enter choice (1-15): ").strip()
            except EOFError: choice = "15"
            if choice == "15": print("\nGoodbye!"); return
            if choice not in actions: print("Invalid choice."); continue
            try: actions[choice]()
            except Exception as e: print(f"[Error] {e}")  # One place for errors: bad input, missing file, etc.

if __name__ == "__main__":
    SmartDriveCLI().run()
