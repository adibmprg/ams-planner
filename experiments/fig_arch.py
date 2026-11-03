import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
plt.rcParams.update({"font.family": "Liberation Serif", "font.size": 7, "savefig.dpi": 600, "mathtext.fontset": "stix"})
fig, ax = plt.subplots(figsize=(4.72, 2.35)); ax.set_xlim(0, 4.72); ax.set_ylim(0, 2.35); ax.axis("off")
def box(x, y, w, h, title, body, fc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.06", fc=fc, ec="#444", lw=0.6))
    ax.text(x + w / 2, y + h - 0.07, title, ha="center", va="top", fontweight="bold", fontsize=7)
    ax.text(x + w / 2, y + h - 0.21, body, ha="center", va="top", fontsize=6.2, linespacing=1.15)
    return (x, y, w, h)
def arrow(p, q, ls="-", lab=None, lp=None):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=6, lw=0.6, color="#444", linestyle=ls, shrinkA=0, shrinkB=0))
    if lab: ax.text(*lp, lab, fontsize=6, ha="center", color="#333", style="italic")
ins = [(".gcode", "colour, type, time,\nslots from M620/T"),
       (".gcode.3mf", "slice_info: per plate\ncolour, type, time"),
       (".3mf project", "project/model settings:\ncolour, type"),
       ("Manual entry", "fields not readable")]
ax.text(0.6, 2.28, "Inputs", ha="center", fontsize=7, color="#555")
ys = [1.72, 1.17, 0.62, 0.07]
for (t, b), y in zip(ins, ys):
    box(0.02, y, 1.16, 0.46, t, b)
P = box(1.38, 0.72, 0.78, 0.8, "Parser", "reads file\nmetadata;\nflags missing\nfields", "#eef3fb")
H = box(2.4, 1.5, 0.95, 0.62, "Filament history", "JSON store,\nquick-select by\nfrequency of use", "#fff6e5")
Jb = box(2.4, 0.4, 0.95, 0.62, "Job set", "jobs $j \\in J$ with\nfilament sets $K_j$,\n$|K_j| \\leq C = 4$", "#eef3fb")
O = box(3.58, 1.18, 1.12, 0.94, "Optimiser", "sequence: greedy,\nILS, GA\nloading: KTNS,\nprefetch, exact DP\ncost: measured t(k)", "#e8f5ee")
U = box(3.58, 0.1, 1.12, 0.84, "Operator plan", "print order,\nslot-level actions,\nchangeover time\nand visits vs FIFO", "#f2f2f2")
for y in ys:
    arrow((1.18, y + 0.23), (1.38, 1.15))
arrow((2.16, 1.3), (2.4, 1.75), "--", "missing", (2.2, 1.6))
arrow((2.16, 0.95), (2.4, 0.75), "-", "complete", (2.24, 0.66))
arrow((2.87, 1.5), (2.87, 1.02), "--", "selected", (3.07, 1.24))
arrow((3.35, 0.75), (3.58, 1.4))
arrow((4.14, 1.18), (4.14, 0.94))

fig.savefig("figs/fig3_arch.png", bbox_inches="tight", pad_inches=0.02)
