import json, statistics as st, sys
from scipy.stats import wilcoxon
R = json.load(open("results/main.json")); S = json.load(open("results/small.json"))
M = ["fifo", "greedy", "ils", "ga"]
out = {"main": [], "small": [], "tests": {}}
def ms(v): return (st.mean(v), st.stdev(v))
for n in (10, 20, 30):
    for m in (6, 8, 12):
        rr = [r for r in R if r["n"] == n and r["m"] == m]
        row = {"n": n, "m": m, "distinct": st.mean(r["distinct_filaments"] for r in rr), "mean_k": st.mean(r["mean_k"] for r in rr)}
        for k in M:
            row[k] = {q: ms([r[k][q] for r in rr]) for q in ["time", "swaps", "events", "exact_time", "cpu", "time_ktns"]}
            row[k]["red"] = ms([(r["fifo"]["time"] - r[k]["time"]) / r["fifo"]["time"] * 100 for r in rr])
        out["main"].append(row)
for m in (6, 8, 12):
    ss = [r for r in S if r["m"] == m]
    row = {"m": m, "enum": ms([r["enum"] for r in ss]), "enum_cpu": st.mean(r["enum_cpu"] for r in ss)}
    for k in M:
        row[k] = {"excess": ms([r[k] - r["enum"] for r in ss]), "opt": sum(abs(r[k] - r["enum"]) < 1e-9 for r in ss)}
    out["small"].append(row)
def test(a, b):
    x = [r[a]["time"] for r in R]; y = [r[b]["time"] for r in R]
    d = [i - j for i, j in zip(x, y)]
    w = wilcoxon(x, y, zero_method="wilcox") if any(d) else None
    return {"better": sum(i < j for i, j in zip(x, y)), "tie": sum(i == j for i, j in zip(x, y)),
            "worse": sum(i > j for i, j in zip(x, y)), "p": (w.pvalue if w else 1.0), "stat": (w.statistic if w else None)}
for a, b in [("ga", "fifo"), ("ils", "fifo"), ("greedy", "fifo"), ("ga", "greedy"), ("ils", "greedy"), ("ga", "ils")]:
    out["tests"][f"{a}_vs_{b}"] = test(a, b)
# overall
out["overall"] = {k: {"time": st.mean(r[k]["time"] for r in R), "events": st.mean(r[k]["events"] for r in R),
                      "swaps": st.mean(r[k]["swaps"] for r in R),
                      "red": st.mean((r["fifo"]["time"] - r[k]["time"]) / r["fifo"]["time"] * 100 for r in R),
                      "evred": st.mean((r["fifo"]["events"] - r[k]["events"]) / r["fifo"]["events"] * 100 for r in R),
                      "swred": st.mean((r["fifo"]["swaps"] - r[k]["swaps"]) / r["fifo"]["swaps"] * 100 for r in R),
                      "exact_gain": st.mean(r[k]["time"] - r[k]["exact_time"] for r in R),
                      "exact_better": sum(r[k]["time"] - r[k]["exact_time"] > 1e-9 for r in R),
                      "ktns_vs_best": st.mean(r[k]["time_ktns"] - r[k]["time"] for r in R),
                      "prefetch_better": sum(r[k]["time_ktns"] - r[k]["time"] > 1e-9 for r in R),
                      "cpu": st.mean(r[k]["cpu"] for r in R)} for k in M}
json.dump(out, open("results/summary.json", "w"), indent=1)
for row in out["main"]:
    print(row["n"], row["m"], f"d={row['distinct']:.1f} k={row['mean_k']:.2f}",
          " | ".join(f"{k}:{row[k]['time'][0]:.0f}±{row[k]['time'][1]:.0f} ev{row[k]['events'][0]:.1f} sw{row[k]['swaps'][0]:.1f} r{row[k]['red'][0]:.1f}% cpu{row[k]['cpu'][0]:.2f}" for k in M))
for row in out["small"]:
    print("small", row["m"], row["enum"], row["enum_cpu"], {k: (round(row[k]['excess'][0],2), row[k]['opt']) for k in M})
print(json.dumps(out["tests"], indent=0)); print(json.dumps(out["overall"], indent=0))
