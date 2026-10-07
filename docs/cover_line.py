"""Line-diagram cover for the LinkedIn article (1920x1080). Run: python docs/cover_line.py

Points: the CLM paper's tool-calling score (BFCL v4, 95.2%), then our measured tool-routing
accuracy on 40 clinic calls: 13% out of the box, 87% after fine-tuning. Jev = 100% on our test.
"""
import math
import os

import matplotlib.pyplot as plt
from matplotlib.patheffects import withStroke

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cover_line.png")
BG, INK, MUTED, GREEN, RED, PURPLE, AMBER = "#0b1020", "#f3f4f6", "#8b93a7", "#34d399", "#f87171", "#a78bfa", "#fbbf24"

fig = plt.figure(figsize=(12, 6.75), dpi=160, facecolor=BG)
ax = fig.add_axes((0, 0, 1, 1))
ax.set_xlim(0, 1920)
ax.set_ylim(0, 1080)
ax.axis("off")

for x in range(40, 1920, 48):
    for y in range(40, 1080, 48):
        ax.plot(x, y, ".", color="#161e33", ms=1.5, zorder=0)

# plot area mapping: accuracy 0..100 -> y 200..760
def Y(v):
    return 200 + v * 5.6

XS = [260, 760, 1200, 1640]
# Jev reference
ax.plot([180, 1760], [Y(100)] * 2, color=PURPLE, lw=1.4, ls=(0, (6, 6)), alpha=0.7)
ax.text(1770, Y(100), "Jev", color=PURPLE, fontsize=14, va="center", weight="bold")

# the journey line: smooth curve through the points, with a glow
pts = [(XS[0], Y(95.2)), (XS[1], Y(13)), (XS[2], Y(87))]
def smooth(p0, p1, n=60):
    out = []
    for i in range(n + 1):
        t = i / n
        s = (1 - math.cos(math.pi * t)) / 2
        out.append((p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * s))
    return out
curve = smooth(pts[0], pts[1]) + smooth(pts[1], pts[2])[1:]
cx, cy = zip(*curve)
for lw, a in ((14, 0.06), (8, 0.12)):
    ax.plot(cx[:61], cy[:61], color=RED, lw=lw, alpha=a, solid_capstyle="round")
    ax.plot(cx[60:], cy[60:], color=GREEN, lw=lw, alpha=a, solid_capstyle="round")
ax.plot(cx[:61], cy[:61], color=RED, lw=3.2, alpha=0.9)
ax.plot(cx[60:], cy[60:], color=GREEN, lw=3.2)
# where next?
nx = [XS[2] + (XS[3] - XS[2]) * t / 20 for t in range(21)]
ny = [Y(87) + (Y(91) - Y(87)) * (1 - math.cos(math.pi * t / 20)) / 2 for t in range(21)]
ax.plot(nx, ny, color=GREEN, lw=2.4, ls=(0, (2, 5)), alpha=0.8)

def dot(x, y, col, ring):
    ax.plot(x, y, "o", ms=26, color=col, alpha=0.18, zorder=4)
    ax.plot(x, y, "o", ms=13, color=col, mec=ring, mew=2.5, zorder=5)

dot(*pts[0], MUTED, BG)
dot(*pts[1], RED, BG)
dot(*pts[2], GREEN, BG)
ax.text(XS[3] + 14, Y(91), "?", color=GREEN, fontsize=54, weight="bold", va="center", ha="center",
        path_effects=[withStroke(linewidth=8, foreground=BG)])

glow = [withStroke(linewidth=6, foreground=BG)]
ax.text(pts[0][0], pts[0][1] + 48, "95%", color=INK, fontsize=26, weight="bold", ha="center", path_effects=glow)
ax.text(pts[1][0], pts[1][1] - 70, "13%", color=RED, fontsize=26, weight="bold", ha="center", path_effects=glow)
ax.text(pts[2][0] + 10, pts[2][1] - 78, "87%", color=GREEN, fontsize=26, weight="bold", ha="center", path_effects=glow)

for x, lbl in zip(XS, ["What the paper said\n(tool-calling benchmark)", "My voice agent, day one", "27 seconds of fine-tuning", "What's next"]):
    ax.text(x, 132, lbl, color=MUTED, fontsize=14, ha="center", va="top", linespacing=1.4)
ax.plot([180, 1760], [160, 160], color="#26314d", lw=1.2)
ax.text(510, 182, "READING", color="#4b5573", fontsize=11, ha="center", va="bottom", weight="bold")
ax.text(1420, 182, "BUILDING", color="#4b5573", fontsize=11, ha="center", va="bottom", weight="bold")
ax.plot([980, 980], [160, 200], color="#26314d", lw=1.2)

ax.text(110, 975, "Reading is not believing.", color=INK, fontsize=40, weight="bold")
ax.text(112, 915, "I put an open-source rival to Jev to the test on a real voice agent.", color=MUTED, fontsize=18)
ax.text(112, 860, "Picked the right tool, %", color="#4b5573", fontsize=13)

fig.savefig(OUT, facecolor=BG)
print("wrote", OUT)
