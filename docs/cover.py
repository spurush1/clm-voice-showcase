"""Cover image for the LinkedIn article (1920x1080). Run: python docs/cover.py"""
import math
import os

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cover.png")
BG, INK, MUTED, GREEN, LIGHT, PURPLE, RED = "#0b1020", "#f3f4f6", "#9ca3af", "#34d399", "#1f6f57", "#a78bfa", "#f87171"

fig = plt.figure(figsize=(12, 6.75), dpi=160, facecolor=BG)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1920)
ax.set_ylim(0, 1080)
ax.axis("off")
ax.set_facecolor(BG)

# dotted grid
for x in range(40, 1920, 48):
    for y in range(40, 1080, 48):
        ax.plot(x, y, ".", color="#1a2236", ms=1.6, zorder=0)

# voice waveform along the bottom
xs = list(range(0, 1920, 4))
ys = [150 + 46 * math.sin(x / 37) * math.exp(-((x - 960) / 620) ** 2) * math.sin(x / 9.5) for x in xs]
ax.plot(xs, ys, color=GREEN, lw=2.2, alpha=0.55)

# left: words
ax.text(110, 905, "A LONG-WEEKEND BUILD  ·  VOICE AI  ·  OPEN SOURCE", color=GREEN, fontsize=15, weight="bold")
ax.text(105, 770, "Reading is", color=INK, fontsize=58, weight="bold")
ax.text(105, 655, "not believing.", color=INK, fontsize=58, weight="bold")
ax.text(110, 545, "I put an open-source rival to Jev to the test", color=MUTED, fontsize=21)
ax.text(110, 492, "on a real voice agent. Here's what I found.", color=MUTED, fontsize=21)
ax.text(110, 395, "Builder hat on.", color=GREEN, fontsize=22, weight="bold", style="italic")

# right: claim vs reality card
card = FancyBboxPatch((1250, 300), 580, 590, boxstyle="round,pad=0,rounding_size=28",
                      fc="#121a2e", ec="#26314d", lw=2, zorder=1)
ax.add_patch(card)
ax.text(1290, 835, "THE PAPER SAID", color=MUTED, fontsize=13, weight="bold")
ax.text(1290, 805, "“On par with Jev,\nup to 9x faster”", color=INK, fontsize=21, style="italic", linespacing=1.3, va="top")
ax.plot([1290, 1790], [668, 668], color="#26314d", lw=1.5)
ax.text(1290, 625, "MY CALLS SAID  ·  right tool", color=MUTED, fontsize=13, weight="bold")

bars = [("CLM out of the box", 13, LIGHT, RED), ("CLM fine-tuned (27 s)", 87, GREEN, GREEN), ("Jev", 100, PURPLE, PURPLE)]
for i, (label, v, col, txt) in enumerate(bars):
    y = 550 - i * 92
    ax.text(1290, y + 22, label, color=INK, fontsize=14)
    ax.add_patch(FancyBboxPatch((1290, y - 30), 390, 30, boxstyle="round,pad=0,rounding_size=15", fc="#1c2640", ec="none", zorder=2))
    ax.add_patch(FancyBboxPatch((1290, y - 30), max(30, 390 * v / 100), 30, boxstyle="round,pad=0,rounding_size=15",
                                fc=col, ec="none", zorder=3))
    ax.text(1695, y - 16, f"{v}%", color=txt, fontsize=17, weight="bold", va="center")

ax.text(110, 60, "github.com/spurush1/clm-voice-showcase", color="#6b7280", fontsize=13)
fig.savefig(OUT, facecolor=BG)
print("wrote", OUT)
