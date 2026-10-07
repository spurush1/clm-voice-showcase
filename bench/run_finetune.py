"""Iteration 2: fine-tune CLM's head on bench/train_set.json via Modal.

Each training row asks exactly the questions the eval asks (backend/app.py make_questions),
with 8 or 64 tools so the head also learns to ignore distractor tools. Rare intents are
repeated so every class has roughly the same weight. 10% of the training rows are held
out as the trainer's own test split; bench/eval_set.json is never used here.

    python bench/run_finetune.py [extra finetune.py args, e.g. --epochs 30]
"""
import json
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "deploy"))
import app as backend  # noqa: E402
from catalog import build_tools  # noqa: E402

GREETING = "Thanks for calling Maple Street Clinic, how can I help you today?"
TARGET_PER_CLASS = 40


def to_row(i, r, n_tools):
    state = backend.make_state([backend.Turn(role="agent", text=GREETING), backend.Turn(role="caller", text=r["caller"])])
    qs = backend.make_questions(build_tools(n_tools))
    del qs["frustration"]  # no gold label for it
    g = r["gold"]
    gold = {"escalate": {"label": g["escalate"]}, "end_of_turn": {"label": g["end_of_turn"]}}
    if g["tool"]:
        gold["tool"] = {"label": g["tool"]}
    else:
        del qs["tool"]
    return {"id": f"r{i}", "workflow": "voice", "state": json.dumps(state), "questions": json.dumps(qs),
            "gold": json.dumps(gold)}


def main():
    rows = json.load(open(os.path.join(ROOT, "bench", "train_set.json"), encoding="utf-8"))["rows"]
    rng = random.Random(11)
    rng.shuffle(rows)
    n_test = len(rows) // 10
    test, train = rows[:n_test], rows[n_test:]

    by = {}
    for r in train:
        by.setdefault(r["gold"]["tool"] or ("esc" if r["gold"]["escalate"] else "trail"), []).append(r)
    balanced = []
    for k, rs in by.items():
        balanced += [rs[j % len(rs)] for j in range(max(len(rs), TARGET_PER_CLASS))]
    print("train classes:", {k: max(len(v), TARGET_PER_CLASS) for k, v in by.items()}, "| test rows:", len(test))

    train_rows = [to_row(i, r, 8 if i % 2 else 64) for i, r in enumerate(balanced)]
    test_rows = [to_row(10_000 + i, r, 8) for i, r in enumerate(test)]

    import modal
    ft = modal.Function.from_name("clm-voice", "finetune")
    log = ft.remote(train_rows, test_rows, sys.argv[1:])
    out = os.path.join(ROOT, "bench", "results", "iter2_finetune.log")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(log)
    print(log[-3000:])


if __name__ == "__main__":
    main()
