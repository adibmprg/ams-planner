"""High-level planning: sequence jobs and produce slot-level operator instructions."""
from __future__ import annotations
from typing import List, Dict, Sequence
from .model import Job, AMS_CAPACITY, switch_time
from . import sequencing as sq

METHODS = {"fifo": sq.fifo, "greedy": sq.greedy, "ils": sq.ils, "ga": sq.genetic}


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


def plan(jobs: Sequence[Job], initial: List[str], method: str = "ga", exact: bool = True, seed: int = 0) -> Dict:
    req = [j.filaments for j in jobs]
    for j in jobs:
        if len(j.filaments) > AMS_CAPACITY:
            raise ValueError(f"{j.name} needs more than {AMS_CAPACITY} filaments")
    order = METHODS[method](req, initial, seed=seed) if method in ("ils", "ga") else METHODS[method](req, initial)
    base = sq.ktns(req, list(range(len(jobs))), initial)
    res = sq.ktns(req, order, initial)
    pre = sq.ktns(req, order, initial, prefetch=True)
    if pre["time"] < res["time"]:
        res = pre
    if exact:
        try:
            ex = sq.exact_loading(req, order, initial)
            if ex["time"] < res["time"]:
                res = ex
        except Exception:
            pass
    steps = slot_instructions(res["states"], initial)
    return {
        "order": [jobs[i].name for i in order],
        "order_idx": order,
        "steps": [{"job": jobs[i].name, **s, "k": k, "seconds": switch_time(k)}
                  for i, s, k in zip(order, steps, res["k"])],
        "total_s": res["time"], "events": res["events"], "swaps": res["swaps"],
        "fifo_total_s": base["time"], "fifo_events": base["events"], "fifo_swaps": base["swaps"],
    }
