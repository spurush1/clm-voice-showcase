# Free alternative: run CLM on Kaggle (2× T4, 30 GPU-hours/week, no card)

Qwen3-8B does not fit on one 16 GB T4, so this splits it across Kaggle's two T4s. T4s don't support bf16, so it runs in fp16. Scores can differ very slightly from the bf16 reference; Modal (L4, bf16) is the faithful setup.

1. Kaggle → New Notebook → Settings: **Accelerator = GPU T4 x2**, **Internet = On** (Internet requires a phone-verified account).
2. Cell 1:
   ```bash
   !pip install -q vllm git+https://github.com/Contrastive-LM/CLM
   !wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared && chmod +x cloudflared
   ```
3. Cell 2 (start the encoder + CLM, then tunnel):
   ```bash
   !nohup vllm serve Qwen/Qwen3-8B --served-model-name qwen3-8b --runner pooling --dtype half \
       --tensor-parallel-size 2 --enable-prefix-caching --max-model-len 2048 --port 8090 > vllm.log 2>&1 &
   !until curl -s localhost:8090/v1/models >/dev/null; do sleep 5; done; echo encoder up
   !CLM_API_KEY=change-me nohup clm-serve --port 8700 > clm.log 2>&1 &
   !sleep 20; nohup ./cloudflared tunnel --url http://localhost:8700 > cf.log 2>&1 &
   !sleep 10; grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' cf.log
   ```
4. Put the printed URL in `backend/.env` as `CLM_BASE_URL` and set `CLM_API_KEY=change-me`.

Keep the notebook running during the demo. The URL changes every session.
