import json, statistics as st
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from amsplanner.model import SWITCH_TIME_S as TS
fmt_s = lambda v: f"{v:g}"
plt.rcParams.update({"font.family": "Liberation Serif", "font.size": 8, "axes.linewidth": 0.6,
                     "xtick.major.width": 0.6, "ytick.major.width": 0.6, "axes.spines.top": False,
                     "axes.spines.right": False, "legend.frameon": False, "savefig.dpi": 600})
W = 4.72  # text width in inches (12 cm)
R = json.load(open("results/main.json")); SUM = json.load(open("results/summary.json")); CASE = json.load(open("results/case.json"))
COL = {"fifo": "#9a9a9a", "greedy": "#e3a33b", "ils": "#2b6cb0", "ga": "#2e9e6b"}
LAB = {"fifo": "FIFO", "greedy": "Greedy", "ils": "ILS", "ga": "GA"}
HEX = {"BK": "#1d1d1d", "WH": "#ffffff", "RD": "#d62728", "BL": "#1f5fbf", "YE": "#f2d21b", "GN": "#2ca02c",
       "GY": "#8c8c8c", "OR": "#ff7f0e", "PB": "#3a3a3a"}

# Fig 1: three-job example ------------------------------------------------
def slots_panel(ax, title, seq_labels, slots_seq, ks, total):
    ax.set_xlim(0, 3.2); ax.set_ylim(-1.0, 4.6); ax.axis("off")
    ax.text(1.6, 4.45, title, ha="center", fontweight="bold")
    for c, (lab, sl, k) in enumerate(zip(seq_labels, slots_seq, ks)):
        x = 0.15 + c * 1.05
        ax.text(x + 0.4, 4.0, lab, ha="center")
        for s in range(4):
            y = 3.2 - s * 0.8
            code = sl[s]
            fc = HEX.get(code, "#ffffff") if code else "#ffffff"
            ax.add_patch(Rectangle((x, y), 0.8, 0.62, fc=fc, ec="#444", lw=0.5,
                                   hatch="" if code else "///"))
            if code:
                ax.text(x + 0.4, y + 0.31, code, ha="center", va="center", fontsize=7,
                        color="white" if code in ("BK", "BL", "RD", "PB", "GN") else "black")
        ax.text(x + 0.4, 0.62, "no change" if k == 0 else f"{k} spool{'s' if k > 1 else ''}\n{fmt_s(TS[k])} s",
                ha="center", va="top", fontsize=7, color="#b3261e" if k else "#555")
    ax.text(1.6, -0.85, f"Total: {total:.0f} s", ha="center", fontweight="bold")
ex = CASE["example"]
fig, axs = plt.subplots(1, 2, figsize=(W, 2.2))
slots_panel(axs[0], "Order J1 → J2 → J3", ["J1", "J2", "J3"], ex["1-2-3"]["slots"], ex["1-2-3"]["k"], ex["1-2-3"]["time"])
slots_panel(axs[1], "Order J1 → J3 → J2", ["J1", "J3", "J2"], ex["1-3-2"]["slots"], ex["1-3-2"]["k"], ex["1-3-2"]["time"])
fig.text(0.5, 0.005, "Slots 1–4 of the AMS lite shown top to bottom. J1 = {BK, WH, RD, BL}, J2 = {YE, GN}, J3 = {BK, WH, RD}.",
         ha="center", fontsize=7, color="#444")
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig("figs/fig1_example.png"); plt.close(fig)

# Fig 2: measured changeover time ------------------------------------------
k = np.array([1, 2, 3, 4]); t = np.array([TS[1], TS[2], TS[3], TS[4]])
b, a = np.polyfit(k, t, 1); pred = a + b * k
r2 = 1 - ((t - pred) ** 2).sum() / ((t - t.mean()) ** 2).sum()
fig, axs = plt.subplots(1, 2, figsize=(W, 1.85))
ax = axs[0]
ax.plot(k, TS[1] * k, "--", color="#9a9a9a", lw=0.9, label=f"k separate visits ({fmt_s(TS[1])}k)")
ax.plot(np.linspace(0.8, 4.2, 10), a + b * np.linspace(0.8, 4.2, 10), "-", color="#2b6cb0", lw=0.9,
        label=f"fit: {a:.1f} + {b:.1f}k (R² = {r2:.3f})")
ax.plot(k, t, "o", color="#1d1d1d", ms=4, label="measured mean")
for ki, ti in zip(k, t): ax.annotate(f"{fmt_s(ti)} s", (ki, ti), textcoords="offset points", xytext=(6, -10), fontsize=7)
ax.set_xticks(k); ax.set_xlabel("spools exchanged in one visit, k"); ax.set_ylabel("changeover time (s)")
ax.set_ylim(0, 230); ax.legend(fontsize=6.3, loc="upper left")
ax = axs[1]
per = t / k
ax.bar(k, per, color="#2b6cb0", width=0.6)
for ki, p in zip(k, per): ax.text(ki, p + 1, f"{p:.1f}", ha="center", fontsize=7)
ax.set_xticks(k); ax.set_xlabel("spools exchanged in one visit, k"); ax.set_ylabel("time per spool (s)"); ax.set_ylim(0, 55)
fig.tight_layout(); fig.savefig("figs/fig2_switchtime.png"); plt.close(fig)
json.dump({"a": a, "b": b, "r2": r2}, open("results/fit.json", "w"))

# Fig 5: mean changeover time by method -----------------------------------
fig, axs = plt.subplots(1, 3, figsize=(W, 2.1), sharey=True)
for ax, n in zip(axs, (10, 20, 30)):
    rows = [r for r in SUM["main"] if r["n"] == n]
    x = np.arange(3)
    for i, mth in enumerate(["fifo", "greedy", "ils", "ga"]):
        mu = [r[mth]["time"][0] for r in rows]; sd = [r[mth]["time"][1] for r in rows]
        ax.bar(x + (i - 1.5) * 0.2, mu, 0.2, yerr=sd, color=COL[mth], label=LAB[mth],
               error_kw={"elinewidth": 0.5, "capsize": 1.2})
    ax.set_xticks(x); ax.set_xticklabels([str(r["m"]) for r in rows]); ax.set_title(f"n = {n} jobs", fontsize=8)
axs[0].set_ylabel("total changeover time (s)")
axs[1].set_xlabel("filaments in catalogue, m")
axs[1].legend(ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.3), fontsize=7)
fig.subplots_adjust(left=0.1, right=0.99, top=0.9, bottom=0.3, wspace=0.08); fig.savefig("figs/fig5_methods.png"); plt.close(fig)

# Fig 6: reduction distribution ---------------------------------------------
fig, axs = plt.subplots(1, 2, figsize=(W, 1.95))
ax = axs[0]
data = [[(r["fifo"]["time"] - r[m]["time"]) / r["fifo"]["time"] * 100 for r in R] for m in ["greedy", "ils", "ga"]]
bp = ax.boxplot(data, widths=0.5, patch_artist=True, medianprops={"color": "black", "lw": 0.8},
                flierprops={"ms": 2, "marker": "o", "mfc": "none", "mec": "#777"})
for patch, m in zip(bp["boxes"], ["greedy", "ils", "ga"]): patch.set_facecolor(COL[m]); patch.set_alpha(0.75); patch.set_linewidth(0.5)
ax.set_xticklabels(["Greedy", "ILS", "GA"]); ax.set_ylabel("reduction vs FIFO (%)"); ax.set_title("(a) all 270 instances", fontsize=8)
ax = axs[1]
for m, mk in zip((6, 8, 12), ("o", "s", "^")):
    ys = [next(r for r in SUM["main"] if r["n"] == n and r["m"] == m)["ils"]["red"][0] for n in (10, 20, 30)]
    ax.plot((10, 20, 30), ys, marker=mk, ms=3.5, lw=0.9, label=f"m = {m} filaments")
ax.set_xticks((10, 20, 30)); ax.set_xlabel("batch size n (jobs)"); ax.set_ylabel("mean reduction, ILS (%)")
ax.set_ylim(0, 75); ax.legend(fontsize=6.5, loc="lower right"); ax.set_title("(b) effect of n and m", fontsize=8)
fig.tight_layout(); fig.savefig("figs/fig6_reduction.png"); plt.close(fig)

# Fig 7: GA convergence -----------------------------------------------------
fig79, (ax, ax9) = plt.subplots(1, 2, figsize=(W, 1.9))
for m, ls in zip((6, 8, 12), ("-", "--", ":")):
    H = np.array([r["ga_hist"] for r in R if r["n"] == 30 and r["m"] == m])
    rel = H / H[:, -1:].clip(min=1)
    ax.plot(np.arange(1, H.shape[1] + 1), rel.mean(0), ls, color="#2e9e6b", lw=1, label=f"m = {m}")
ax.set_xlabel("generation"); ax.set_ylabel("best / final best"); ax.set_ylim(0.98, None)
ax.legend(fontsize=6.5); ax.set_title("(a) GA convergence, n = 30", fontsize=8)

# Fig 8: case study slot chart ----------------------------------------------
fig, axs = plt.subplots(2, 1, figsize=(W, 2.6))
for ax, name in zip(axs, ["FIFO", "ILS"]):
    res = CASE["res"][name]; n = len(res["order"])
    for c in range(n):
        for s in range(4):
            code = res["slots"][c][s]
            ax.add_patch(Rectangle((c, 3 - s), 0.9, 0.85, fc=HEX[code], ec="#555", lw=0.4))
            ax.text(c + 0.45, 3 - s + 0.42, code, ha="center", va="center", fontsize=5.5,
                    color="white" if code in ("BK", "BL", "RD", "PB", "GN") else "black")
        if res["k"][c]:
            ax.text(c + 0.45, 4.05, f"+{res['k'][c]}", ha="center", fontsize=6.5, color="#b3261e", fontweight="bold")
    ax.set_xlim(-0.1, n); ax.set_ylim(-0.1, 4.5)
    ax.set_xticks(np.arange(n) + 0.45); ax.set_xticklabels([f"J{o+1}" for o in res["order"]], fontsize=6.5)
    ax.set_yticks([3.42, 2.42, 1.42, 0.42]); ax.set_yticklabels(["S1", "S2", "S3", "S4"], fontsize=6.5)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.tick_params(length=0)
    ax.set_title(f"{name}: {res['time']:.0f} s, {res['events']} operator visits, {res['swaps']} spools", fontsize=7.5, loc="left")
fig.tight_layout(h_pad=0.6); fig.savefig("figs/fig8_case.png"); plt.close(fig)

# Fig 9: operator response delay scenario -----------------------------------
row = next(r for r in SUM["main"] if r["n"] == 20 and r["m"] == 8)
Rd = np.array([0, 5, 10, 15, 30])
ax = ax9
for mth in ["fifo", "greedy", "ils"]:
    ev = row[mth]["events"][0]; ct = row[mth]["time"][0]
    ax.plot(Rd, (ev * Rd * 60 + ct) / 60, marker="o", ms=3, lw=0.9, color=COL[mth], label=LAB[mth])
ax.set_xlabel("operator response delay per visit, δ (min)"); ax.set_ylabel("printer idle time (min)")
ax.set_xlabel("operator delay per visit, δ (min)")
ax.legend(fontsize=6.5); ax.set_title("(b) idle time, n = 20, m = 8", fontsize=8)
fig79.tight_layout(); fig79.savefig("figs/fig7_conv_delay.png"); plt.close(fig79)
print("figures ok", a, b, r2)

# ---- compact single-panel versions for the 12-page manuscript ----
fig, ax = plt.subplots(figsize=(3.3, 1.75))
ax.plot(k, TS[1] * k, "--", color="#9a9a9a", lw=0.9, label=f"k separate visits ({fmt_s(TS[1])}k)")
ax.plot(np.linspace(0.8, 4.2, 10), a + b * np.linspace(0.8, 4.2, 10), "-", color="#2b6cb0", lw=0.9,
        label=f"fit: {a:.1f} + {b:.1f}k (R² = {r2:.3f})")
ax.plot(k, t, "o", color="#1d1d1d", ms=4, label="measured mean")
for ki, ti in zip(k, t): ax.annotate(f"{fmt_s(ti)} s", (ki, ti), textcoords="offset points", xytext=(6, -10), fontsize=7)
ax.set_xticks(k); ax.set_xlabel("spools exchanged in one visit, k"); ax.set_ylabel("changeover time (s)")
ax.set_ylim(0, 230); ax.legend(fontsize=6.3, loc="upper left")
fig.tight_layout(); fig.savefig("figs/fig2_single.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(3.3, 1.75))
for mth in ["fifo", "greedy", "ils"]:
    ev = row[mth]["events"][0]; ct = row[mth]["time"][0]
    ax.plot(Rd, (ev * Rd * 60 + ct) / 60, marker="o", ms=3, lw=0.9, color=COL[mth], label=LAB[mth])
ax.set_xlabel("operator delay per visit, δ (min)"); ax.set_ylabel("printer idle time (min)")
ax.legend(fontsize=6.5)
fig.tight_layout(); fig.savefig("figs/fig7_delay.png"); plt.close(fig)
