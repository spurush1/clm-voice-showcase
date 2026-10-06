"""Evaluate Normal LLM vs Jev vs CLM on a labeled voice-agent test set.

For every case and tool-set size, all lanes get the same conversation and the same
four questions at the same moment (via backend/app.py). We score:
  - tool accuracy     (cases with a gold tool)
  - escalate accuracy (p >= 0.5 vs gold)
  - end-of-turn accuracy (p >= 0.5 vs gold)
  - latency: end-to-end round trip from this machine, p50 / p95 / share under 300 ms
    (+ CLM server-side compute time, from its X-CLM-Latency-Ms header)

Keys and the CLM URL are read from backend/.env, which is git-ignored.

    python bench/run_eval.py                       # all lanes, sizes 8 64 250
    python bench/run_eval.py --sizes 8 250 --limit 10
"""
import argparse
import asyncio
import datetime as dt
import json
import os
import platform
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(ROOT, "backend", ".env"))
import app  # noqa: E402
from catalog import build_tools  # noqa: E402

OUT = os.path.join(ROOT, "bench", "results")
GREETING = "Thanks for calling Maple Street Clinic, how can I help you today?"
BUDGET_MS = 300
LANES = ["llm", "jev", "clm"]
NAMES = {"llm": "Normal LLM", "jev": "Jev", "clm": "CLM-8B"}


def state_for(case):
    return app.make_state([app.Turn(role="agent", text=GREETING), app.Turn(role="caller", text=case["caller"])])


def pct(xs, q):
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))] if s else None


async def run(sizes, lanes, cases, warmup):
    rows = []
    for n in sizes:
        tools = build_tools(n)
        print(f"\n== {len(tools)} tools ==")
        for _ in range(warmup):  # first calls pay connection setup and CLM's one-time action embedding
            await asyncio.gather(*(app.run_lane(l, state_for(cases[0]), tools) for l in lanes))
        for i, case in enumerate(cases, 1):
            results = await asyncio.gather(*(app.run_lane(l, state_for(case), tools) for l in lanes))
            for r in results:
                rows.append({"n_tools": len(tools), "case": case["id"], "gold": case["gold"], **r})
            line = "  ".join(f"{r['lane']}={r['latency_ms']:.0f}ms" if r.get("ok") else f"{r['lane']}=ERR"
                             for r in results)
            print(f"[{i:>2}/{len(cases)}] {case['id']:<10} {line}")
    return rows


def summarize(rows, sizes, lanes):
    summary = []
    for n in sorted({r["n_tools"] for r in rows}):
        for l in lanes:
            rs = [r for r in rows if r["n_tools"] == n and r["lane"] == l]
            ok = [r for r in rs if r.get("ok")]
            if not ok:
                summary.append({"n_tools": n, "lane": l, "ok": 0, "errors": len(rs),
                                "error": rs[0].get("error") if rs else "no rows"})
                continue
            tool_cases = [r for r in ok if r["gold"]["tool"]]
            lat = [r["latency_ms"] for r in ok]
            srv = [r["server_ms"] for r in ok if r.get("server_ms") is not None]
            summary.append({
                "n_tools": n, "lane": l, "ok": len(ok), "errors": len(rs) - len(ok),
                "tool_acc": sum(r["tool"] == r["gold"]["tool"] for r in tool_cases) / len(tool_cases) if tool_cases else None,
                "escalate_acc": sum((r["escalate"] >= 0.5) == r["gold"]["escalate"] for r in ok) / len(ok),
                "eot_acc": sum((r["end_of_turn"] >= 0.5) == r["gold"]["end_of_turn"] for r in ok) / len(ok),
                "p50_ms": statistics.median(lat), "p95_ms": pct(lat, 0.95), "mean_ms": statistics.mean(lat),
                "under_budget": sum(x <= BUDGET_MS for x in lat) / len(lat),
                "server_p50_ms": statistics.median(srv) if srv else None,
            })
    return summary


def write_markdown(summary, meta, path):
    f = lambda v, p=False: "—" if v is None else (f"{v * 100:.0f}%" if p else f"{v:.0f}")
    lines = [f"# Voice-agent eval: Normal LLM vs Jev vs CLM", "",
             f"Run {meta['run_at']} · {meta['cases']} labeled caller turns · models: {meta['models']}", "",
             "| Tools | Lane | Tool acc | Escalate acc | End-of-turn acc | p50 ms | p95 ms | Under 300 ms | CLM server p50 ms |",
             "|---|---|---|---|---|---|---|---|---|"]
    for s in summary:
        if not s["ok"]:
            lines.append(f"| {s['n_tools']} | {NAMES[s['lane']]} | error: {s['error'][:60]} |||||||")
            continue
        lines.append(f"| {s['n_tools']} | {NAMES[s['lane']]} | {f(s['tool_acc'], True)} | {f(s['escalate_acc'], True)} | "
                     f"{f(s['eot_acc'], True)} | {f(s['p50_ms'])} | {f(s['p95_ms'])} | {f(s['under_budget'], True)} | "
                     f"{f(s['server_p50_ms'])} |")
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def charts(summary, lanes, meta):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: skipping charts (pip install matplotlib)")
        return
    colors = {"llm": "#d97706", "jev": "#7c5cd6", "clm": "#0f9f6e"}
    ink, muted = "#1f2430", "#6b7280"
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})
    src = f"Our run, {meta['run_at'][:10]}: {meta['cases']} labeled caller turns, end-to-end latency from the app backend. github.com/spurush1/clm-voice-showcase"

    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=150)
    fig.subplots_adjust(top=0.80, bottom=0.14, left=0.08, right=0.97)
    fig.text(0.08, 0.93, "Decision latency as the agent's toolbox grows", fontsize=20, weight="bold", color=ink)
    fig.text(0.08, 0.875, "Median end-to-end latency per caller turn, ms (lower is better)", fontsize=12, color=muted)
    fig.text(0.08, 0.03, src, fontsize=8.5, color=muted)
    for l in lanes:
        pts = [(s["n_tools"], s["p50_ms"]) for s in summary if s["lane"] == l and s["ok"]]
        if not pts:
            continue
        xs, ys = zip(*pts)
        ax.plot(xs, ys, marker="o", lw=3, color=colors[l], label=NAMES[l])
        ax.annotate(f"{ys[-1]:.0f} ms", (xs[-1], ys[-1]), textcoords="offset points", xytext=(8, 0),
                    va="center", color=colors[l], weight="bold")
    ax.axhline(BUDGET_MS, color="#ef4444", ls="--", lw=1.2)
    ax.text(ax.get_xlim()[0], BUDGET_MS, " 300 ms voice budget", va="bottom", color="#ef4444", fontsize=10)
    ax.set_xlabel("tools available to the agent", color=muted)
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", color="#eef0f3")
    ax.legend(frameon=False, loc="lower right", bbox_to_anchor=(1, 1.0), ncol=3)
    fig.savefig(os.path.join(OUT, "ours_latency.png"))

    n_max = max(s["n_tools"] for s in summary)
    metrics = [("tool_acc", "Tool routing"), ("escalate_acc", "Escalation"), ("eot_acc", "End of turn")]
    fig, ax = plt.subplots(figsize=(12, 6.75), dpi=150)
    fig.subplots_adjust(top=0.80, bottom=0.14, left=0.08, right=0.97)
    fig.text(0.08, 0.93, f"Decision accuracy with {n_max} tools", fontsize=20, weight="bold", color=ink)
    fig.text(0.08, 0.875, "Share of labeled caller turns decided correctly, % (higher is better)", fontsize=12, color=muted)
    fig.text(0.08, 0.03, src, fontsize=8.5, color=muted)
    w = 0.26
    for k, l in enumerate(lanes):
        s = next((s for s in summary if s["lane"] == l and s["n_tools"] == n_max and s["ok"]), None)
        if not s:
            continue
        vals = [(s[m] or 0) * 100 for m, _ in metrics]
        xs = [i + (k - 1) * w for i in range(len(metrics))]
        ax.bar(xs, vals, w, color=colors[l], label=NAMES[l])
        for x, v in zip(xs, vals):
            ax.text(x, v + 1, f"{v:.0f}%", ha="center", color=colors[l], weight="bold", fontsize=10)
    ax.set_xticks(range(len(metrics)), [t for _, t in metrics], fontsize=12)
    ax.set_ylim(0, 110)
    ax.grid(axis="y", color="#eef0f3")
    ax.legend(frameon=False, loc="lower right", bbox_to_anchor=(1, 1.0), ncol=3)
    fig.savefig(os.path.join(OUT, "ours_accuracy.png"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[8, 64, 250])
    ap.add_argument("--lanes", nargs="+", default=LANES, choices=LANES)
    ap.add_argument("--limit", type=int, default=None, help="only the first N cases")
    ap.add_argument("--warmup", type=int, default=2)
    a = ap.parse_args()

    cases = json.load(open(os.path.join(ROOT, "bench", "eval_set.json"), encoding="utf-8"))["cases"][: a.limit]
    lanes = [l for l in a.lanes if app.configured(l)]
    for l in set(a.lanes) - set(lanes):
        print(f"skipping {l}: not configured in backend/.env")
    if not lanes:
        sys.exit("no lanes configured: fill backend/.env first")

    rows = asyncio.run(run(a.sizes, lanes, cases, a.warmup))
    os.makedirs(OUT, exist_ok=True)
    meta = {"run_at": dt.datetime.now().isoformat(timespec="seconds"), "cases": len(cases), "sizes": a.sizes,
            "models": {"llm": app.OPENAI_MODEL, "jev": app.JEV_MODEL, "clm": app.CLM_MODEL},
            "client": platform.platform()}
    summary = summarize(rows, a.sizes, lanes)
    json.dump({"meta": meta, "summary": summary, "rows": rows}, open(os.path.join(OUT, "results.json"), "w"), indent=1)
    write_markdown(summary, meta, os.path.join(OUT, "summary.md"))
    charts(summary, lanes, meta)
    print("\n" + open(os.path.join(OUT, "summary.md"), encoding="utf-8").read())


if __name__ == "__main__":
    main()
