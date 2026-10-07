# Voice-agent eval: Normal LLM vs Jev vs CLM

Run 2026-10-07T13:11:12 · 40 labeled caller turns · models: {'llm': 'openai/gpt-4.1-mini', 'jev': 'jev-latest', 'clm': 'clm-voice'}

| Tools | Lane | Tool acc | Escalate acc | End-of-turn acc | p50 ms | p95 ms | Under 300 ms | CLM server p50 ms |
|---|---|---|---|---|---|---|---|---|
| 8 | Jev | 100% | 100% | 98% | 382 | 573 | 0% | — |
| 8 | CLM-8B | 87% | 92% | 100% | 505 | 553 | 0% | 152 |
| 64 | Jev | 100% | 100% | 98% | 392 | 497 | 0% | — |
| 64 | CLM-8B | 87% | 92% | 100% | 346 | 359 | 0% | 2 |
| 250 | Jev | 100% | 100% | 98% | 428 | 543 | 0% | — |
| 250 | CLM-8B | 87% | 92% | 100% | 352 | 608 | 0% | 2 |
