"""
SmartDrive - Algorithm Explorer Sandboxes
Runs a list of operations on a fresh data structure and records a snapshot after every step,
so the web app can replay them one at a time. Also builds the DP tables for LCS, edit distance and knapsack.
"""
from typing import List, Dict, Any
from data_structures.avl_tree import AVLTree
from data_structures.hash_table import HashTable
from data_structures.trie import Trie
from data_structures.binary_heap import MaxBinaryHeap
from data_structures.lcs_diff import LCSDiff
from data_structures.edit_distance import EditDistance
from data_structures.knapsack import KnapsackOptimizer, KnapsackItem

def avl_steps(keys: List[str]) -> List[Dict[str, Any]]:
    """'10' inserts 10, '-10' deletes it. Keys are compared as numbers when they are all numbers."""
    numeric = all(k.lstrip("-").isdigit() for k in keys)
    as_key = int if numeric else str
    tree, steps = AVLTree(), []
    for key in keys:
        if key.startswith("-") and len(key) > 1:
            found = tree.delete(as_key(key[1:]))
            op = f"delete {key[1:]}" + ("" if found else " (not found)")
        else:
            tree.insert(as_key(key), key)
            op = f"insert {key}"
        steps.append({"op": op, "rotations": list(tree.rotation_log), "root": tree.export_structure(),
                      "height": tree.get_height(tree.root)})
    return steps

def hash_steps(keys: List[str], capacity: int) -> List[Dict[str, Any]]:
    table, steps = HashTable(capacity=capacity), []
    for key in keys:
        before = table.capacity
        table.insert(key, key)
        resized = table.capacity != before
        steps.append({"op": f"insert {key}", "bucket": table.get_bucket_index(key), **table.export_structure(),
                      "note": f"load factor exceeded 0.75 -> resized {before} -> {table.capacity}, all keys rehashed" if resized else None})
    return steps

def heap_steps(keys: List[str]) -> List[Dict[str, Any]]:
    """Numbers are inserted as priorities; 'pop' extracts the maximum."""
    heap, steps = MaxBinaryHeap(), []
    for key in keys:
        if key.lower() in ("pop", "x", "extract"):
            top = heap.extract_max()
            op = f"extract_max -> {top[0]} ({top[1]})" if top else "extract_max -> empty"
        elif key.lstrip("-").isdigit():
            heap.insert(int(key), f"#{len(steps) + 1}")
            op = f"insert {key}"
        else:
            continue
        steps.append({"op": op, "nodes": heap.export_structure(label=str)})
    return steps

def trie_steps(words: List[str]) -> List[Dict[str, Any]]:
    trie, steps = Trie(), []
    for word in words:
        trie.insert(word, word)
        steps.append({"op": f"insert {word}", "root": trie.export_structure(), "words": len(trie), "nodes": trie.count_nodes()})
    return steps

SANDBOXES = {"avl": avl_steps, "hash": hash_steps, "heap": heap_steps, "trie": trie_steps}

def lcs_table(a: str, b: str, mode: str) -> Dict[str, Any]:
    split = {"lines": str.splitlines, "words": str.split}.get(mode, list)
    seq_a, seq_b = split(a), split(b)
    if (len(seq_a) + 1) * (len(seq_b) + 1) > 2500: raise ValueError("Inputs too long to visualise (max about 50 x 50).")
    table, path, common = LCSDiff.trace(seq_a, seq_b)
    return {"a": seq_a, "b": seq_b, "table": table, "path": path, "lcs": common, "length": len(common)}

def edit_distance_table(a: str, b: str) -> Dict[str, Any]:
    a, b = a[:40], b[:40]
    ops, path = EditDistance.backtrack(a, b)
    return {"a": list(a), "b": list(b), "table": EditDistance.compute_table(a, b), "path": path,
            "distance": EditDistance.distance(a, b), "similarity": round(EditDistance.similarity(a, b), 4),
            "alignment": [{"op": o, "a": x, "b": y} for o, x, y in ops]}

def knapsack_table(items: List[Dict[str, Any]], capacity: int) -> Dict[str, Any]:
    opt = KnapsackOptimizer([KnapsackItem(i["label"], i["weight"], i["value"]) for i in items], capacity)
    return {**opt.dp_table(), "results": [r.to_dict() for r in opt.compare_all()]}
