#!/usr/bin/env bash
# Serve the real CLM-8B on a Lightning AI Studio (free tier, L4 GPU) and expose it
# through a Cloudflare quick tunnel.
#
# In the Studio terminal:
#   export CLM_API_KEY=<the CLM_API_KEY value from your local backend/.env>
#   bash lightning_clm.sh
# It prints a https://....trycloudflare.com URL: put it in backend/.env as CLM_BASE_URL.
set -euo pipefail
: "${CLM_API_KEY:?export CLM_API_KEY first (copy it from backend/.env)}"
nvidia-smi --query-gpu=name,memory.total --format=csv

pip install -q vllm "git+https://github.com/Contrastive-LM/CLM"
[ -x ./cloudflared ] || { curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared; chmod +x cloudflared; }

# Qwen3-8B encoder, last-token pooling, bf16: the setup the CLM head was trained on
nohup vllm serve Qwen/Qwen3-8B --served-model-name qwen3-8b --runner pooling \
  --enable-prefix-caching --max-model-len 2048 --gpu-memory-utilization 0.85 --port 8090 > vllm.log 2>&1 &
echo "loading Qwen3-8B (first run downloads ~16 GB)..."
until curl -s localhost:8090/v1/models >/dev/null; do sleep 5; tail -n 1 vllm.log; done
echo "encoder up"

nohup clm-serve --port 8700 > clm.log 2>&1 &
until curl -s localhost:8700/health >/dev/null; do sleep 3; done
curl -s localhost:8700/health; echo

nohup ./cloudflared tunnel --url http://localhost:8700 > cf.log 2>&1 &
for _ in $(seq 1 30); do
  URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' cf.log | head -1 || true)
  [ -n "$URL" ] && break; sleep 2
done
echo
echo "CLM_BASE_URL=$URL"
echo "Keep this Studio running while the evaluation runs. Stop the Studio afterwards to save credits."
