"""Share-ready charts for the article, from our own eval runs.

Iteration 1 numbers are copied from bench/results/iter1_clm_zero_shot/:
  LLM  -> llm_jev_2026-10-06.log (8 tools)        Jev, CLM -> results.json (8 tools, 2026-10-07)
Run: python bench/story_charts.py
"""
import os

import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
INK, MUTED, RED = "#1f2430", "#6b7280", "#ef4444"
COLORS = {"Normal LLM": "#d97706", "Jev": "#7c5cd6", "CLM-8B": "#0f9f6e"}
SRC = "Our eval: 40 labeled clinic caller turns, 8 tools, end-to-end latency from the app backend (India to US). github.com/spurush1/clm-voice-showcase"

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#d1d5db"})


def iteration_chart(fname, title, subtitle, acc, lat, compute):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 6.75), dpi=150)
    fig.subplots_adjust(top=0.78, bottom=0.14, left=0.07, right=0.97, wspace=0.3)
    fig.text(0.07, 0.93, title, fontsize=20, weight="bold", color=INK)
    fig.text(0.07, 0.875, subtitle, fontsize=12, color=MUTED)
    fig.text(0.07, 0.03, SRC, fontsize=8.5, color=MUTED)
    names = list(acc)
    cols = [COLORS[n.split(" (")[0]] for n in names]

    a1.bar(names, [acc[n] for n in names], color=cols, width=0.6)
    for i, n in enumerate(names):
        a1.text(i, acc[n] + 2, f"{acc[n]:.0f}%", ha="center", weight="bold", color=cols[i], fontsize=13)
    a1.set_ylim(0, 115)
    a1.set_title("Picked the right tool", loc="left", color=INK, fontsize=13)
    a1.set_yticks([])

    a2.bar(names, [lat[n] for n in names], color=cols, width=0.6)
    for i, n in enumerate(names):
        a2.text(i, lat[n] + 40, f"{lat[n]:,.0f} ms", ha="center", weight="bold", color=cols[i], fontsize=13)
        if n in compute:
            a2.bar(i, compute[n], color="white", alpha=0.45, width=0.6, hatch="//", edgecolor="white")
            a2.annotate(f"model compute only:\n{compute[n]:.0f} ms (hatched)", (i, compute[n] / 2),
                        xytext=(i - 0.9, max(lat.values()) * 0.5), fontsize=10, color=INK, ha="left",
                        arrowprops=dict(arrowstyle="->", color=MUTED))
    a2.axhline(300, color=RED, ls="--", lw=1.2)
    a2.set_ylim(0, max(lat.values()) * 1.18)
    a2.set_title("Median time to decide  (red line: 300 ms voice budget)", loc="left", color=INK, fontsize=13)
    a2.set_yticks([])
    for ax in (a1, a2):
        ax.tick_params(axis="x", labelsize=12)
    fig.savefig(os.path.join(OUT, fname))
    print("wrote", fname)


iteration_chart(
    "iter1_out_of_the_box.png",
    "Iteration 1: CLM out of the box",
    "Same 40 caller turns, same questions, all models called at the same moment.",
    acc={"Normal LLM": 100, "Jev": 100, "CLM-8B": 13},
    lat={"Normal LLM": 1857, "Jev": 328, "CLM-8B": 436},
    compute={"CLM-8B": 102},
)
