# CLM vs Jev vs LLM: Voice Agent Showcase (Plan)

## Goal
A single-page React app that shows a real-time **voice agent** making the same decisions three ways, and makes the case for **CLM**:
1. **Normal LLM** (generates JSON / a function call)
2. **Jev** (TypeSafe System One, typed answers)
3. **CLM-8B** (contrastive state/action encoders, cached action embeddings)

Core message: **voice has a latency budget of about 300 ms per turn.** The LLM misses it, Jev is close, and CLM stays inside it while matching Jev's accuracy, even as the action set grows.

## Source facts (from the CLM blog and repo)
- CLM-8B matches Jev on computer-use, gaming and tool calling (BFCL v4) with **up to 9× lower latency**, and **13× at ~1k candidates**.
- Action embeddings are **precomputed once**. Each turn, only the new state is encoded, so cost stays flat as the number of tools grows.
- Used as a verifier: DeepSWE **81.6%**, Terminal-Bench 2.1 **87.6%**, **4–6× faster** than Jev. Jev falls below the Pass@1 baseline as a long-horizon verifier.
- The API is **TypeSafe-compatible** (`Noul` / `Choice` / `Score`), so the same request can go to both. It self-hosts via `clm-serve` (vLLM + Qwen3-8B, port 8700). Weights are open and you can fine-tune it.

## Voice agent scenario
A scripted phone call (e.g., a clinic/restaurant booking plus support) with about 6 caller turns. Each turn needs **4 parallel judgments**:
| Judgment | Primitive | Why it matters in voice |
|---|---|---|
| End-of-turn: has the caller finished speaking? | Noul | Stops the agent from interrupting or leaving dead air |
| Tool routing: which of N tools to call | Choice (N = 8 → 1000) | This is where CLM's action caching wins |
| Frustration level | Score | Tone adaptation |
| Escalate to a human? | Noul | Safety |

## Page sections
1. **Hero**: "System One for Voice: decisions in milliseconds." Includes a one-line comparison.
2. **The latency budget**: an animated bar showing ASR + decision + TTS against the ~300 ms "feels human" line.
3. **Three-lane live race (the centerpiece)**: the same call plays in three columns. Each lane shows a waveform, a transcript, the decision it made, and latency in ms. Slow lanes show a **dead-air / "uh…" indicator**. Includes a play/pause button, a turn stepper, and TTS playback through the Web Speech API. (This replaces the "Dino Run GIF" idea with a voice-native race.)
4. **Scaling slider**: moving the tool count from 8 to 1000 re-renders a latency chart. The LLM and Jev grow with the tool count; CLM stays flat. It links to the action-caching explanation.
5. **Under the hood**: an animated diagram comparing Jev's N forward passes with CLM's single state pass scored against cached action vectors (cosine similarity).
6. **Accuracy parity**: a chart of the blog's benchmarks (BFCL, T-Rex, WikiRacing, Mario, DeepSWE, TB 2.1).
7. **Why CLM**: a decision matrix covering latency, cost per 1k turns, self-hosting/data residency, fine-tunability, verifier ability, output always valid, and API compatibility with Jev (zero migration cost).
8. **CTA / next steps**: a pilot plan for the voice stack.

## Data
Live only: no simulation. A FastAPI backend fans each turn out to OpenAI, Jev (api.typesafe.ai) and CLM (self-hosted on a free Modal/Kaggle GPU) and streams measured latencies to the UI. See README.md.

## Stack
Vite + React + Tailwind + Framer Motion (race and diagram animation) + Recharts (charts) + Web Speech API (TTS, optional mic). Scenario, questions and benchmark numbers live in a single `src/data/` JSON file.

## Deliverables (one commit each)
1. Scaffold + scenario/benchmark data + layout shell
2. Three-lane race (simulated)
3. Scaling slider + chart
4. Architecture diagram + accuracy charts + "Why CLM" matrix
5. (Optional) FastAPI live proxy + mode toggle
6. Polish: dark theme, responsive layout, TTS
