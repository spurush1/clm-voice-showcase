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
import os
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
    extra = f" --model clm-voice={FT_HEAD}" if os.path.exists(FT_HEAD) else ""  # Iteration 2 head, once trained
    subprocess.Popen("clm-serve --port 8700" + extra, shell=True)  # reads CLM_API_KEY from the secret


# --------------------------------------------------------------------------- Iteration 2: fine-tuning
FT_DIR = "/cache/ft/voice"
FT_HEAD = f"{FT_DIR}/best_head.pt"
ft_image = (image.run_commands("git clone --depth 1 https://github.com/Contrastive-LM/CLM /opt/CLM")
            .pip_install("pyarrow", "transformers"))


@app.function(image=ft_image, gpu=["L4", "A10G", "L40S"], volumes={"/cache": cache}, timeout=2 * 3600)
def finetune(train_rows: list[dict], test_rows: list[dict], extra_args: list[str]) -> str:
    """Warm-start CLM's published head and fine-tune it on our typed voice-agent questions
    with the authors' own train/finetune.py (--task choice). Returns the training log tail."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    data = "/cache/voice_data"
    os.makedirs(f"{data}/voice", exist_ok=True)
    for split, rows in (("train", train_rows), ("test", test_rows)):
        pq.write_table(pa.Table.from_pylist(rows), f"{data}/voice/{split}.parquet")

    subprocess.run("clm-download", shell=True, check=True)  # reference head -> /cache/clm
    subprocess.Popen(VLLM, shell=True)
    _wait("http://127.0.0.1:8090/v1/models")
    cmd = ["python", "/opt/CLM/train/finetune.py", "--task", "choice", "--data", data, "--workflow", "voice",
           "--embed-url", "http://127.0.0.1:8090/v1/embeddings", "--served-model-name", "qwen3-8b",
           "--init-ckpt", "/cache/clm/CLM_v0.1-8B.pt", "--out-dir", FT_DIR, "--targets", "hard", *extra_args]
    r = subprocess.run(cmd, capture_output=True, text=True)
    cache.commit()
    log = (r.stdout + "\n" + r.stderr)[-6000:]
    if r.returncode:
        raise RuntimeError(f"finetune failed ({r.returncode}):\n{log}")
    return log
