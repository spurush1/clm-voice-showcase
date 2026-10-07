# Voice-agent eval: Normal LLM vs Jev vs CLM

Run 2026-10-07T12:52:24 · 40 labeled caller turns · models: {'llm': 'openai/gpt-4.1-mini', 'jev': 'jev-latest', 'clm': 'clm-latest'}

| Tools | Lane | Tool acc | Escalate acc | End-of-turn acc | p50 ms | p95 ms | Under 300 ms | CLM server p50 ms |
|---|---|---|---|---|---|---|---|---|
| 8 | Normal LLM | error: HTTP 402: {"error":{"message":"This request requires more cr |||||||
| 8 | Jev | 100% | 100% | 98% | 328 | 421 | 2% | — |
| 8 | CLM-8B | 13% | 88% | 85% | 436 | 672 | 0% | 102 |
| 64 | Normal LLM | error: HTTP 402: {"error":{"message":"This request requires more cr |||||||
| 64 | Jev | 100% | 100% | 98% | 353 | 419 | 0% | — |
| 64 | CLM-8B | 13% | 88% | 85% | 341 | 372 | 0% | 2 |
| 250 | Normal LLM | error: HTTP 402: {"error":{"message":"This request requires more cr |||||||
| 250 | Jev | 100% | 100% | 98% | 382 | 445 | 0% | — |
| 250 | CLM-8B | 13% | 88% | 85% | 338 | 597 | 0% | 2 |
