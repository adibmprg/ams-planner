"""Computational study. Usage: python3 experiments/run_experiments.py"""
import sys, os, json, time, random, itertools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from multiprocessing import Pool
from amsplanner import sequencing as sq

K_PROBS = [0.40, 0.30, 0.20, 0.10]   # P(job uses 1,2,3,4 filaments)
ZIPF_S = 1.0
C = 4


def make_instance(n, m, seed):
    rng = random.Random(seed)
    F = [f"F{i+1}" for i in range(m)]
    w = [1 / (i + 1) ** ZIPF_S for i in range(m)]
    req = []
    for _ in range(n):
        k = rng.choices([1, 2, 3, 4], K_PROBS)[0]
        chosen, ww, pool = [], w[:], F[:]
        for _ in range(k):
            x = rng.choices(range(len(pool)), ww)[0]
            chosen.append(pool.pop(x)); ww.pop(x)
        req.append(frozenset(chosen))
    return req, F[:C]


def evaluate(req, init, order):
    a = sq.ktns(req, order, init); b = sq.ktns(req, order, init, prefetch=True)
    r = a if a["time"] <= b["time"] else b
    ex = sq.exact_loading(req, order, init)
    return {"time": r["time"], "swaps": r["swaps"], "events": r["events"],
            "time_ktns": a["time"], "exact_time": ex["time"], "exact_events": ex["events"],
            "exact_swaps": ex["swaps"], "order": order}


def run_main(args):
    n, m, rep = args
    seed = 1000 * n + 100 * m + rep
    req, init = make_instance(n, m, seed)
    out = {"n": n, "m": m, "rep": rep, "seed": seed}
    for name in ["fifo", "greedy", "ils", "ga"]:
        t = time.process_time()
        if name == "fifo": o = sq.fifo(req)
        elif name == "greedy": o = sq.greedy(req, init)
        elif name == "ils": o = sq.ils(req, init, seed=seed)
        else:
            h = []; o = sq.genetic(req, init, seed=seed, history=h); out["ga_hist"] = h
        cpu = time.process_time() - t
        out[name] = evaluate(req, init, o); out[name]["cpu"] = cpu
    out["distinct_filaments"] = len(set().union(*req))
    out["mean_k"] = sum(len(r) for r in req) / n
    return out


def run_small(args):
    m, rep = args; n = 8
    seed = 50000 + 100 * m + rep
    req, init = make_instance(n, m, seed)
    t = time.process_time(); best, bc = sq.enumerate_best(req, init); te = time.process_time() - t
    out = {"m": m, "rep": rep, "enum": bc, "enum_cpu": te}
    for name, fn in [("fifo", lambda: sq.fifo(req)), ("greedy", lambda: sq.greedy(req, init)),
                     ("ils", lambda: sq.ils(req, init, seed=seed)), ("ga", lambda: sq.genetic(req, init, seed=seed))]:
        out[name] = sq.cost(req, fn(), init)
    return out


if __name__ == "__main__":
    REPS = 30
    grid = [(n, m, r) for n in (10, 20, 30) for m in (6, 8, 12) for r in range(REPS)]
    small = [(m, r) for m in (6, 8, 12) for r in range(REPS)]
    t0 = time.time()
    with Pool(2) as p:
        S = p.map(run_small, small, chunksize=3)
        json.dump(S, open("results/small.json", "w"))
        print("small done", time.time() - t0, flush=True)
        R = p.map(run_main, grid, chunksize=2)
    json.dump(R, open("results/main.json", "w"))
    print("main done", time.time() - t0, flush=True)
