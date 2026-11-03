"""Illustrative 12-plate batch (constructed by the authors) and the 3-job example."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from amsplanner import sequencing as sq
from amsplanner.planner import slot_instructions

FIL = {"BK": "PLA Black", "WH": "PLA White", "RD": "PLA Red", "BL": "PLA Blue", "YE": "PLA Yellow",
       "GN": "PLA Green", "GY": "PLA Grey", "OR": "PLA Orange", "PB": "PETG Black"}
JOBS = [("Logo keychains", "BK WH"), ("Name plate", "WH BL"), ("Cable clips", "GY"), ("Phone stand", "BK"),
        ("Mini figure", "RD YE BK WH"), ("Planter", "GN WH"), ("Tool holder", "PB"), ("Coaster set", "OR BK"),
        ("Event badges", "RD WH BL"), ("Toy car", "RD BK GY"), ("Wall bracket", "PB"), ("Shop sign", "YE BK")]
INIT = ["BK", "WH", "RD", "GY"]
req = [frozenset(f.split()) for _, f in JOBS]
res = {}
for name, order in [("FIFO", sq.fifo(req)), ("Greedy", sq.greedy(req, INIT)),
                    ("ILS", sq.ils(req, INIT, seed=7)), ("GA", sq.genetic(req, INIT, seed=7))]:
    a = sq.ktns(req, order, INIT); b = sq.ktns(req, order, INIT, prefetch=True)
    r = a if a["time"] <= b["time"] else b
    ex = sq.exact_loading(req, order, INIT)
    if ex["time"] < r["time"]: r = ex
    steps = slot_instructions(r["states"], INIT)
    res[name] = {"order": order, "k": r["k"], "time": r["time"], "events": r["events"], "swaps": r["swaps"],
                 "slots": [s["slots"] for s in steps], "actions": [s["actions"] for s in steps]}
    print(name, [i + 1 for i in order], r["k"], r["time"], r["events"], r["swaps"])
# three-job example from practice
ex_req = [frozenset("BK WH RD BL".split()), frozenset("YE GN".split()), frozenset("BK WH RD".split())]
exm = {}
for o in ([0, 1, 2], [0, 2, 1]):
    r = sq.exact_loading(ex_req, o, ["BK", "WH", "RD", "BL"])
    st = slot_instructions(r["states"], ["BK", "WH", "RD", "BL"])
    exm["-".join(str(i + 1) for i in o)] = {"k": r["k"], "time": r["time"], "slots": [s["slots"] for s in st]}
    print("example", o, r["k"], r["time"], [s["slots"] for s in st])
json.dump({"jobs": JOBS, "fil": FIL, "init": INIT, "res": res, "example": exm}, open("results/case.json", "w"), indent=1)
