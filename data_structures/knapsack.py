"""
SmartDrive - 0/1 Knapsack Storage Optimizer
Chooses the set of files with the highest total priority that fits a storage budget.
    - Dynamic Programming: always optimal, O(n * W)
    - Greedy by priority/size ratio: very fast, not always optimal
    - Branch & Bound: optimal, explores far fewer states by pruning with an upper bound
"""
import time
from dataclasses import dataclass, field
from typing import TypeVar, Generic, Optional, List, Dict, Any
from data_structures.binary_heap import MaxBinaryHeap

T = TypeVar('T')

@dataclass
class KnapsackItem(Generic[T]):
    label: str
    weight: int          # Cost in capacity units (e.g. KB)
    value: int           # Benefit (e.g. file priority)
    payload: Optional[T] = None

    def __post_init__(self) -> None:
        if self.weight < 0 or self.value < 0: raise ValueError("Weight and value must be non-negative.")

    @property
    def ratio(self) -> float: return float('inf') if self.weight == 0 else self.value / self.weight

@dataclass
class KnapsackResult(Generic[T]):
    method: str
    capacity: int
    selected: List[KnapsackItem[T]] = field(default_factory=list)
    time_ms: float = 0.0
    nodes_explored: int = 0
    nodes_pruned: int = 0
    is_optimal: bool = True
    unit_bytes: int = 1  # Bytes per capacity unit (1 = bytes, 1024 = KB)

    @property
    def total_value(self) -> int: return sum(i.value for i in self.selected)
    @property
    def total_weight(self) -> int: return sum(i.weight for i in self.selected)
    @property
    def utilization(self) -> float: return self.total_weight / self.capacity * 100 if self.capacity else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method, "capacity": self.capacity, "total_value": self.total_value,
            "total_weight": self.total_weight, "utilization_pct": round(self.utilization, 2),
            "selected": [i.label for i in self.selected], "time_ms": round(self.time_ms, 4),
            "nodes_explored": self.nodes_explored, "nodes_pruned": self.nodes_pruned,
            "is_optimal": self.is_optimal, "unit_bytes": self.unit_bytes,
        }

class KnapsackOptimizer(Generic[T]):
    MAX_DP_CELLS = 50_000_000  # Refuse DP tables that would use too much memory

    def __init__(self, items: List[KnapsackItem[T]], capacity: int, unit_bytes: int = 1):
        if capacity < 0: raise ValueError("Capacity must be non-negative.")
        self.items, self.capacity, self.unit_bytes = list(items), capacity, unit_bytes
        self.by_ratio = sorted(self.items, key=lambda i: (-i.ratio, -i.value))  # Best priority-per-KB first

    def _result(self, method: str) -> KnapsackResult[T]:
        return KnapsackResult(method=method, capacity=self.capacity, unit_bytes=self.unit_bytes)

    @staticmethod
    def _finish(res: KnapsackResult[T], start: float) -> KnapsackResult[T]:
        res.time_ms = (time.perf_counter() - start) * 1000
        res.selected.sort(key=lambda i: i.label)
        return res

    def _greedy_pick(self) -> List[KnapsackItem[T]]:
        """Take items in ratio order while they still fit."""
        chosen, remaining = [], self.capacity
        for item in self.by_ratio:
            if item.weight <= remaining:
                chosen.append(item)
                remaining -= item.weight
        return chosen

    # --- Dynamic Programming ---
    def solve_dp(self) -> KnapsackResult[T]:
        """
        best[w] = best value with capacity w. Scanning w downwards uses each item at most once.
        take[i][w] remembers whether item i was used, so the chosen set can be traced back.
        """
        res, start = self._result("Dynamic Programming"), time.perf_counter()
        n, W = len(self.items), self.capacity
        if n * (W + 1) > self.MAX_DP_CELLS:
            raise MemoryError(f"DP table too large ({n} x {W + 1}). Use a coarser unit or Branch & Bound.")
        best = [0] * (W + 1)
        take = [bytearray(W + 1) for _ in range(n)]
        for i, item in enumerate(self.items):
            for w in range(W, item.weight - 1, -1):
                if best[w - item.weight] + item.value > best[w]:
                    best[w] = best[w - item.weight] + item.value
                    take[i][w] = 1
            res.nodes_explored += W + 1
        w = W
        for i in range(n - 1, -1, -1):  # Trace back from full capacity
            if take[i][w]:
                res.selected.append(self.items[i])
                w -= self.items[i].weight
        return self._finish(res, start)

    # --- Greedy ---
    def solve_greedy(self) -> KnapsackResult[T]:
        res, start = self._result("Greedy (Ratio)"), time.perf_counter()
        res.selected = self._greedy_pick()
        res.nodes_explored = len(self.items)
        res.is_optimal = False  # Heuristic: compare_all() confirms if it happened to match the optimum
        return self._finish(res, start)

    # --- Branch & Bound ---
    def _upper_bound(self, idx: int, weight: int, value: int) -> float:
        """Best value still reachable if items from idx on could be taken fractionally."""
        bound, room = float(value), self.capacity - weight
        for item in self.by_ratio[idx:]:
            if item.weight <= room:
                room -= item.weight
                bound += item.value
            else:
                return bound + room * item.ratio
        return bound

    def solve_branch_and_bound(self) -> KnapsackResult[T]:
        """Best-first search over include/exclude decisions, using the Phase 3 max heap ordered by upper bound."""
        res, start = self._result("Branch & Bound"), time.perf_counter()
        order = self.by_ratio
        best_set = self._greedy_pick()  # Start from the greedy answer so pruning works early
        best_val = sum(i.value for i in best_set)

        queue: MaxBinaryHeap[tuple] = MaxBinaryHeap()
        queue.insert(self._upper_bound(0, 0, 0), (0, 0, 0, ()))  # (next index, weight, value, taken indexes)
        while not queue.is_empty:
            bound, (idx, weight, value, taken) = queue.extract_max()
            res.nodes_explored += 1
            if bound <= best_val or idx == len(order):
                res.nodes_pruned += 1
                continue
            item = order[idx]
            branches = [(idx + 1, weight, value, taken)]                       # Skip the item
            if weight + item.weight <= self.capacity:                          # Take the item
                branches.append((idx + 1, weight + item.weight, value + item.value, taken + (idx,)))
                if value + item.value > best_val:
                    best_val, best_set = value + item.value, [order[k] for k in taken + (idx,)]
            for state in branches:
                b = self._upper_bound(state[0], state[1], state[2])
                if b > best_val: queue.insert(b, state)
                else: res.nodes_pruned += 1
        res.selected = list(best_set)
        return self._finish(res, start)

    # --- Full 2-D table for the web explorer (small inputs only) ---
    def dp_table(self, max_cells: int = 4000) -> Dict[str, Any]:
        """dp[i][w] = best value using the first i items with capacity w, plus the traced-back path."""
        n, W = len(self.items), self.capacity
        if (n + 1) * (W + 1) > max_cells: raise ValueError(f"Table too large to visualise ({n + 1} x {W + 1}).")
        dp = [[0] * (W + 1) for _ in range(n + 1)]
        for i, item in enumerate(self.items, 1):
            for w in range(W + 1):
                dp[i][w] = dp[i - 1][w]
                if item.weight <= w: dp[i][w] = max(dp[i][w], dp[i - 1][w - item.weight] + item.value)
        path, w = [], W
        for i in range(n, 0, -1):
            took = dp[i][w] != dp[i - 1][w]
            path.append({"row": i, "col": w, "take": took})
            if took: w -= self.items[i - 1].weight
        return {"items": [{"label": i.label, "weight": i.weight, "value": i.value} for i in self.items],
                "capacity": W, "table": dp, "path": path[::-1], "best": dp[n][W]}

    # --- Comparison ---
    def compare_all(self) -> List[KnapsackResult[T]]:
        results = [self.solve_greedy(), self.solve_branch_and_bound()]
        try: results.insert(0, self.solve_dp())
        except MemoryError: pass  # Budget too large for DP; Branch & Bound is still exact
        best = max(r.total_value for r in results)
        for r in results: r.is_optimal = r.total_value == best
        return results

    @staticmethod
    def display_comparison(results: List[KnapsackResult[Any]], unit: Optional[str] = None) -> str:
        if not results: return "<No Knapsack Results>"
        unit = unit or {1: "B", 1024: "KB", 1024 ** 2: "MB"}.get(results[0].unit_bytes, f"x{results[0].unit_bytes} B")
        lines = [f"Knapsack Comparison [Capacity={results[0].capacity} {unit}]", "=" * 78,
                 f"{'Method':<22} | {'Value':<6} | {'Used':<12} | {'Util%':<6} | {'Nodes':<7} | {'Time(ms)':<9} | Opt",
                 "-" * 78]
        for r in results:
            lines.append(f"{r.method:<22} | {r.total_value:<6} | {r.total_weight:<12} | {r.utilization:<6.1f} | "
                         f"{r.nodes_explored:<7} | {r.time_ms:<9.3f} | {'✓' if r.is_optimal else '✗'}")
        return "\n".join(lines)
