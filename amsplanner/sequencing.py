"""Spool loading (KTNS, KTNS with prefetch, exact DP) and job sequencing
(FIFO, greedy, iterated local search, genetic algorithm, enumeration)."""
from __future__ import annotations
import itertools, random, math
from typing import List, Sequence, FrozenSet, Iterable, Tuple, Dict, Optional
from .model import switch_time, AMS_CAPACITY

Req = Sequence[FrozenSet[str]]


def _next_use(req: Req, order: Sequence[int], pos: int, tool: str) -> float:
    for q in range(pos, len(order)):
        if tool in req[order[q]]:
            return q
    return math.inf


def ktns(req: Req, order: Sequence[int], initial: Iterable[str] = (), C: int = AMS_CAPACITY,
         prefetch: bool = False) -> Dict:
    """Keep-Tool-Needed-Soonest loading for a fixed job order.
    Returns per-position spools exchanged, events, swaps and total time (s).
    With prefetch=True, every changeover visit also replaces spools that are
    never needed again by the spools needed soonest (merges later visits)."""
    mag = set(initial)
    k_per_pos, states = [], []
    for pos, j in enumerate(order):
        need = req[j]
        missing = [t for t in need if t not in mag]
        k = len(missing)
        if k:
            overflow = len(mag) + k - C
            if overflow > 0:
                cand = sorted((t for t in mag if t not in need),
                              key=lambda t: _next_use(req, order, pos + 1, t), reverse=True)
                for t in cand[:overflow]:
                    mag.discard(t)
            mag.update(missing)
            if prefetch:
                # fill free or dead slots with the tools needed soonest
                dead = [t for t in mag if t not in need and _next_use(req, order, pos + 1, t) == math.inf]
                upcoming = []
                for q in range(pos + 1, len(order)):
                    for t in sorted(req[order[q]]):
                        if t not in mag and t not in upcoming:
                            upcoming.append(t)
                free = C - len(mag)
                for t in upcoming:
                    if free > 0:
                        mag.add(t); k += 1; free -= 1
                    elif dead:
                        mag.discard(dead.pop()); mag.add(t); k += 1
                    else:
                        break
        k_per_pos.append(k)
        states.append(frozenset(mag))
    swaps = sum(k_per_pos)
    events = sum(1 for k in k_per_pos if k)
    return {"k": k_per_pos, "states": states, "swaps": swaps, "events": events,
            "time": sum(switch_time(k) for k in k_per_pos)}


def cost(req: Req, order: Sequence[int], initial=(), C=AMS_CAPACITY) -> float:
    """Fitness used by the search: total changeover time under KTNS
    (best of plain KTNS and KTNS with prefetch)."""
    a = ktns(req, order, initial, C)["time"]
    b = ktns(req, order, initial, C, prefetch=True)["time"]
    return min(a, b)


def exact_loading(req: Req, order: Sequence[int], initial=(), C=AMS_CAPACITY) -> Dict:
    """Exact minimum changeover time for a FIXED order by dynamic programming
    over AMS states (all subsets of size <= C of the spools involved)."""
    universe = sorted(set().union(*[req[j] for j in order]) | set(initial))
    idx = {t: i for i, t in enumerate(universe)}
    states = [frozenset(s) for r in range(C + 1) for s in itertools.combinations(universe, r)]
    try:
        import numpy as np
    except ImportError:  # pragma: no cover
        np = None
    S = len(states)
    masks = [sum(1 << idx[t] for t in s) for s in states]
    if np is not None:
        m = np.array(masks, dtype=np.int64)
        new = np.array([[bin(b & ~a).count("1") for b in masks] for a in masks]) if S <= 300 else None
        if new is None:
            # vectorised popcount of (b & ~a)
            diff = (m[None, :] & ~m[:, None])
            new = np.zeros_like(diff)
            x = diff.copy()
            while x.any():
                new += (x & 1); x >>= 1
        tcost = np.vectorize(switch_time)(new).astype(float)
        init_mask = sum(1 << idx[t] for t in initial)
        start = masks.index(init_mask) if init_mask in masks else None
        dp = np.full(S, np.inf); dp[start] = 0.0
        back = []
        for j in order:
            need = sum(1 << idx[t] for t in req[j])
            feas = (m & need) == need
            tot = dp[:, None] + tcost
            arg = tot.argmin(axis=0)
            nd = tot[arg, np.arange(S)]
            nd[~feas] = np.inf
            back.append(arg); dp = nd
        end = int(dp.argmin()); best = float(dp[end])
        path = [end]
        for b in reversed(back[1:]):
            path.append(int(b[path[-1]]))
        path.reverse()
        st = [states[p] for p in path]
        prev = frozenset(initial); ks = []
        for s in st:
            ks.append(len(s - prev)); prev = s
        return {"time": best, "k": ks, "states": st, "swaps": sum(ks), "events": sum(1 for k in ks if k)}
    raise RuntimeError("numpy required for exact loading")


# ---------------------------------------------------------------- sequencing
def fifo(req: Req, initial=(), C=AMS_CAPACITY) -> List[int]:
    return list(range(len(req)))


def greedy(req: Req, initial=(), C=AMS_CAPACITY) -> List[int]:
    """Nearest-neighbour: next job = fewest spools missing from the AMS;
    ties broken by the larger overlap, then by arrival order."""
    left = list(range(len(req))); order = []; mag = set(initial)
    while left:
        j = min(left, key=lambda j: (len(req[j] - mag), -len(req[j] & mag), j))
        order.append(j); left.remove(j)
        r = ktns(req, order, initial, C); mag = set(r["states"][-1])
    return order


def ils(req: Req, initial=(), C=AMS_CAPACITY, budget: int = 6000, seed: int = 0,
        history: Optional[list] = None) -> List[int]:
    """Iterated local search with the same evaluation budget as the GA:
    first-improvement descent over random insertion moves, double-swap kicks,
    better-or-equal acceptance."""
    rng = random.Random(seed); n = len(req); used = [0]

    def f(o):
        used[0] += 1
        return cost(req, o, initial, C)

    def descent(o, c):
        moves = [(i, k) for i in range(n) for k in range(n) if i != k]
        improved = True
        while improved and used[0] < budget:
            improved = False
            rng.shuffle(moves)
            for i, k in moves:
                if used[0] >= budget:
                    break
                o2 = o[:]; x = o2.pop(i); o2.insert(k, x)
                c2 = f(o2)
                if c2 < c - 1e-9:
                    o, c, improved = o2, c2, True
                    if history is not None: history.append((used[0], c))
                    break
        return o, c

    cur = greedy(req, initial, C); cur_c = f(cur)
    cur, cur_c = descent(cur, cur_c)
    best, best_c = cur[:], cur_c
    while used[0] < budget and n > 1:
        o = cur[:]
        for _ in range(2):
            a, b = rng.sample(range(n), 2); o[a], o[b] = o[b], o[a]
        o, c = descent(o, f(o))
        if c <= cur_c + 1e-9:
            cur, cur_c = o, c
        if c < best_c - 1e-9:
            best, best_c = o[:], c
    return best


def _ox(p1, p2, rng):
    n = len(p1); a, b = sorted(rng.sample(range(n), 2))
    child = [None] * n; child[a:b + 1] = p1[a:b + 1]
    fill = [g for g in p2 if g not in child[a:b + 1]]
    it = iter(fill)
    return [g if g is not None else next(it) for g in child]


def genetic(req: Req, initial=(), C=AMS_CAPACITY, pop: int = 40, gens: int = 150,
            pc: float = 0.9, pm: float = 0.2, seed: int = 0, history: Optional[list] = None) -> List[int]:
    """Permutation GA: tournament(3), order crossover, swap mutation, elitism(2);
    the population is seeded with the FIFO and greedy orders."""
    rng = random.Random(seed); n = len(req)
    if n < 2:
        return fifo(req)
    P = [fifo(req), greedy(req, initial, C)] + [rng.sample(range(n), n) for _ in range(pop - 2)]
    F = [cost(req, p, initial, C) for p in P]
    for g in range(gens):
        elite = sorted(range(pop), key=F.__getitem__)[:2]
        newP = [P[i][:] for i in elite]
        while len(newP) < pop:
            def tour():
                c = rng.sample(range(pop), 3); return P[min(c, key=F.__getitem__)]
            a, b = tour(), tour()
            ch = _ox(a, b, rng) if rng.random() < pc else a[:]
            if rng.random() < pm:
                i, k = rng.sample(range(n), 2); ch[i], ch[k] = ch[k], ch[i]
            newP.append(ch)
        P = newP; F = [cost(req, p, initial, C) for p in P]
        if history is not None:
            history.append(min(F))
    return P[min(range(pop), key=F.__getitem__)]


def enumerate_best(req: Req, initial=(), C=AMS_CAPACITY) -> Tuple[List[int], float]:
    best, bc = None, math.inf
    for p in itertools.permutations(range(len(req))):
        c = cost(req, p, initial, C)
        if c < bc:
            best, bc = list(p), c
    return best, bc
