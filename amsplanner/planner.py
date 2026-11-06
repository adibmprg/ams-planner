"""High-level planning: sequence jobs and produce slot-level operator instructions."""
from __future__ import annotations
from typing import List, Dict, Sequence
from .model import Job, AMS_CAPACITY, switch_time
from . import sequencing as sq

METHODS = {"fifo": sq.fifo, "greedy": sq.greedy, "ils": sq.ils, "ga": sq.genetic}
PRIORITY = ["ils", "ga", "greedy", "fifo"]


def slot_instructions(states, initial_slots: List[str], C: int = AMS_CAPACITY):
    """Translate AMS content sets into 'slot s: remove A, load B' steps.
    Spools are only removed when their slot is needed for a new spool, and
    spools that stay keep their slot."""
    slots = list(initial_slots) + [None] * (C - len(initial_slots))
    steps = []
    for st in states:
        acts = []
        for t in sorted(st):
            if t in slots:
                continue
            if None in slots:
                i = slots.index(None); acts.append([i + 1, None, t])
            else:
                i = next(i for i, x in enumerate(slots) if x not in st)
                acts.append([i + 1, slots[i], t])
            slots[i] = t
        steps.append({"slots": slots[:], "actions": acts})
    return steps


def plan(jobs: Sequence[Job], initial: List[str], method: str = "auto", exact: bool = True, seed: int = 0) -> Dict:
    """method="auto" runs every algorithm and returns the best plan, with a
    comparison table under "comparison"."""
    if method == "auto":
        res = [plan(jobs, initial, m, exact, seed) for m in PRIORITY]
        best = min(res, key=lambda r: (r["total_s"], r["events"], PRIORITY.index(r["method"])))
        best = dict(best)
        best["comparison"] = [{k: r[k] for k in ("method", "total_s", "events", "swaps", "cpu_s")} for r in res]
        return best
    import time as _t
    _t0 = _t.perf_counter()
    req = [j.filaments for j in jobs]
    for j in jobs:
        if len(j.filaments) > AMS_CAPACITY:
            raise ValueError(f"{j.name} needs more than {AMS_CAPACITY} filaments")
    order = METHODS[method](req, initial, seed=seed) if method in ("ils", "ga") else METHODS[method](req, initial)
    def best_loading(o):
        r = min(sq.ktns(req, o, initial), sq.ktns(req, o, initial, prefetch=True), key=lambda x: x["time"])
        if exact:
            try:
                ex = sq.exact_loading(req, o, initial)
                if ex["time"] < r["time"] - 1e-9:
                    r = ex
            except Exception:
                pass
        return r
    base = best_loading(list(range(len(jobs))))      # FIFO evaluated with the same loading rules
    res = best_loading(order)
    steps = slot_instructions(res["states"], initial)
    return {
        "method": method, "cpu_s": _t.perf_counter() - _t0,
        "order": [jobs[i].name for i in order],
        "order_idx": order,
        "steps": [{"job": jobs[i].name, **s, "k": k, "seconds": switch_time(k)}
                  for i, s, k in zip(order, steps, res["k"])],
        "total_s": res["time"], "events": res["events"], "swaps": res["swaps"],
        "fifo_total_s": base["time"], "fifo_events": base["events"], "fifo_swaps": base["swaps"],
    }
