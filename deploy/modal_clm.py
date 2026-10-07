"""Serve the real CLM-8B (Qwen3-8B encoder + CLM head) on a Modal L4 GPU.

Modal's free Starter plan includes $30/month of compute (an L4 costs about $0.80/hr),
and this container scales to zero when idle.

    pip install modal && modal setup
    modal secret create clm-api-key CLM_API_KEY=<pick-a-random-string>
    modal deploy deploy/modal_clm.py
    # -> https://<you>--clm-voice-serve.modal.run   (put it in backend/.env as CLM_BASE_URL)

The first request after idle cold-starts the GPU (~1-3 min while vLLM loads).
Hit /health once before a demo to warm it.
"""
import subprocess
import time
import urllib.request

import modal

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
    .pip_install("vllm", "huggingface_hub[hf_transfer]",
                 "git+https://github.com/Contrastive-LM/CLM")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": "/cache/hf", "CLM_CKPT_DIR": "/cache/clm"})
)
cache = modal.Volume.from_name("clm-cache", create_if_missing=True)  # HF weights + CLM head
app = modal.App("clm-voice")

VLLM = ("vllm serve Qwen/Qwen3-8B --served-model-name qwen3-8b --runner pooling "
        "--enable-prefix-caching --max-model-len 2048 --gpu-memory-utilization 0.85 --port 8090")


def _wait(url: str, timeout: float = 900) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if urllib.request.urlopen(url, timeout=5).status == 200:
                return
        except Exception:  # noqa: BLE001
            time.sleep(3)
    raise RuntimeError(f"{url} did not come up")


@app.function(image=image, gpu=["L4", "A10G", "L40S"], volumes={"/cache": cache},
              secrets=[modal.Secret.from_name("clm-api-key")],
              timeout=24 * 3600, scaledown_window=2 * 60)  # GPU bills while idle; keep this short
@modal.concurrent(max_inputs=32)
@modal.web_server(port=8700, startup_timeout=900)
def serve():
    subprocess.Popen(VLLM, shell=True)
    _wait("http://127.0.0.1:8090/v1/models")
    subprocess.Popen("clm-serve --port 8700", shell=True)  # reads CLM_API_KEY from the secret
