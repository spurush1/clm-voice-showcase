"""Render the published CLM vs Jev benchmarks as share-ready PNGs.

Numbers are transcribed from the CLM authors' figures (zero-shot.png, agentic.png in
github.com/Contrastive-LM/CLM). Run: python docs/make_charts.py
"""
import os

import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))
CLM, JEV, INK, MUTED = "#0f9f6e", "#7c5cd6", "#1f2430", "#6b7280"
SOURCE = "Source: Kwok et al., Contrastive Language Models (2026), github.com/Contrastive-LM/CLM"

TASKS = ["T-Rex game", "Tool calling\n(BFCL v4)", "WikiRacing", "Super Mario", "DeepSWE\n(verifier)", "Terminal-Bench 2.1\n(verifier)"]
LAT_CLM = [16.5, 76.8, 79.8, 33.5, 79, 32]
LAT_JEV = [149.8, 125.5, 225, 132.6, 449, 131]
ACC_CLM = [100, 95.2, 86.7, 100, 81.6, 87.6]
ACC_JEV = [100, 99.2, 100, 100, 71.1, 83.1]

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#d1d5db", "xtick.color": INK, "ytick.color": MUTED})


def frame(title, subtitle):
    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=150)
    fig.subplots_adjust(top=0.80, bottom=0.17, left=0.07, right=0.98)
    fig.text(0.07, 0.93, title, fontsize=20, weight="bold", color=INK)
    fig.text(0.07, 0.875, subtitle, fontsize=12, color=MUTED)
    fig.text(0.07, 0.03, SOURCE, fontsize=9, color=MUTED)
    ax.grid(axis="y", color="#eef0f3")
    ax.set_axisbelow(True)
    return fig, ax


def bars(ax, a, b, fmt):
    x = range(len(TASKS))
    w = 0.38
    ra = ax.bar([i - w / 2 for i in x], a, w, color=CLM, label="CLM-8B")
    rb = ax.bar([i + w / 2 for i in x], b, w, color=JEV, label="Jev (TypeSafe)")
    for rects, vals, col in ((ra, a, CLM), (rb, b, JEV)):
        for r, v in zip(rects, vals):
            ax.text(r.get_x() + r.get_width() / 2, r.get_height(), fmt(v), ha="center", va="bottom",
                    fontsize=10, color=col, weight="bold", zorder=5,
                    bbox=dict(fc="white", ec="none", pad=1))
    ax.set_xticks(list(x), TASKS, fontsize=11)
    ax.legend(frameon=False, fontsize=11, loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2)


# 1. latency
fig, ax = frame("CLM answers 1.6x to 9.1x faster than Jev",
                "Decision latency per step, milliseconds (lower is better). Measured by the CLM authors.")
bars(ax, LAT_CLM, LAT_JEV, lambda v: f"{v:g}")
for i, (c, j) in enumerate(zip(LAT_CLM, LAT_JEV)):
    ax.text(i, j + 38, f"{j / c:.1f}x faster", ha="center", fontsize=11, color=INK, weight="bold")
ax.set_ylim(0, 520)
ax.set_ylabel("ms", color=MUTED)
fig.savefig(os.path.join(OUT, "latency.png"))

# 2. accuracy
fig, ax = frame("Same league on accuracy, ahead as a verifier",
                "Success rate, % (higher is better). Zero-shot tasks, then fine-tuned best-of-N verification.")
bars(ax, ACC_CLM, ACC_JEV, lambda v: f"{v:g}%")
ax.set_ylim(60, 110)
ax.axvline(3.5, color="#d1d5db", lw=1, ls="--")
ax.text(1.5, 106.5, "zero-shot", ha="center", color=MUTED, fontsize=11)
ax.text(4.5, 106.5, "verifier (fine-tuned)", ha="center", color=MUTED, fontsize=11)
for x, base in ((4, 73.7), (5, 84.0)):
    ax.hlines(base, x - 0.42, x + 0.42, colors=INK, linestyles="--", lw=1.5)
    ax.text(x + 0.44, base, f"Pass@1\n{base}%", va="center", fontsize=8.5, color=INK)
ax.set_ylabel("%", color=MUTED)
fig.savefig(os.path.join(OUT, "accuracy.png"))
print("wrote", OUT)
