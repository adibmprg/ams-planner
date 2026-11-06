"""Command line:  python3 -m amsplanner plan FILES... --ams "PLA:#000000,PLA:#FFFFFF" """
from __future__ import annotations
import argparse, sys
from .parsers import parse_file
from .history import FilamentHistory
from .planner import plan
from .model import Job


def _ask_missing(job: Job, hist: FilamentHistory) -> Job:
    if not job.missing or not any("colour" in m or "type" in m or "filaments" in m for m in job.missing):
        return job
    print(f"\n{job.name}: could not read {', '.join(job.missing)}")
    qs = hist.quick_select()
    for i, it in enumerate(qs, 1):
        print(f"  [{i}] {it['type']} {it['color']} {it.get('label','')}")
    raw = input("  enter numbers (e.g. 1,3) or TYPE:#RRGGBB entries: ").strip()
    keys = []
    for tok in [t.strip() for t in raw.split(",") if t.strip()]:
        if tok.isdigit() and 1 <= int(tok) <= len(qs):
            keys.append(qs[int(tok) - 1]["key"])
        elif ":" in tok:
            t, c = tok.split(":", 1); keys.append(hist.record(t.upper(), c.upper()))
    job.filaments = frozenset(keys); job.missing = [m for m in job.missing if "print time" in m]
    return job


def main(argv=None):
    ap = argparse.ArgumentParser(prog="amsplanner")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan"); p.add_argument("files", nargs="+")
    p.add_argument("--ams", default="", help="current AMS content, slot order, TYPE:#RRGGBB comma-separated")
    p.add_argument("--method", default="auto", choices=["auto", "fifo", "greedy", "ils", "ga"])
    sub.add_parser("serve")
    a = ap.parse_args(argv)
    if a.cmd == "serve":
        from .webapp import run; run(); return
    hist = FilamentHistory()
    jobs = []
    for f in a.files:
        for j in parse_file(f):
            jobs.append(_ask_missing(j, hist))
    for j in jobs:
        for k in j.filaments:
            t, c = k.split(":", 1)
            if "?" not in k: hist.record(t, c)
    initial = [s.strip().upper() for s in a.ams.split(",") if s.strip()]
    r = plan(jobs, initial, a.method)
    if "comparison" in r:
        print("\nAlgorithm comparison:")
        for c in r["comparison"]:
            print(f"  {c['method']:<7s} {c['total_s']:7.1f} s  {c['events']:3d} visits  {c['swaps']:3d} spools  {c['cpu_s']:.2f} s CPU"
                  + ("   <- best" if c["method"] == r["method"] else ""))
    print(f"\nPrint order ({r['method']}):")
    for n, st in enumerate(r["steps"], 1):
        acts = "; ".join(f"slot {s}: {o or '-'} -> {i or '-'}" for s, o, i in st["actions"]) or "no change"
        print(f" {n:2d}. {st['job']:<40s} {acts}")
    print(f"\nChangeover: {r['total_s']:.0f} s, {r['events']} visits, {r['swaps']} spools "
          f"(FIFO: {r['fifo_total_s']:.0f} s, {r['fifo_events']} visits, {r['fifo_swaps']} spools)")


if __name__ == "__main__":
    main()
