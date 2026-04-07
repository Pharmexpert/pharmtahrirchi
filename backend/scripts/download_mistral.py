"""
Auto-download Mistral-7B-Instruct-Uz GGUF model on Railway first start.

Run via:
    python scripts/download_mistral.py

Requires:
    pip install huggingface-hub

Env vars:
    HF_TOKEN              — HuggingFace token (must accept model license)
    MISTRAL_GGUF_PATH     — destination path (default: /app/data/mistral-7b-instruct-uz.gguf)
    MISTRAL_GGUF_REPO     — GGUF repo (default: behbudiy/Mistral-7B-Instruct-Uz-GGUF)
    MISTRAL_GGUF_FILE     — file name (default: mistral-7b-instruct-uz.Q4_K_M.gguf — ~4.4GB)

Quantization options (Q4_K_M ~4.4GB recommended for Railway Pro 8GB):
    Q3_K_M  — 3.5 GB (faster, lower quality)
    Q4_K_M  — 4.4 GB (recommended, best balance)
    Q5_K_M  — 5.1 GB (higher quality)
    Q8_0    — 7.7 GB (near-original quality, needs Railway 16GB+)
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="[download_mistral] %(message)s")
log = logging.getLogger()

DEST = os.getenv("MISTRAL_GGUF_PATH", "/app/data/mistral-7b-instruct-uz.gguf")
REPO = os.getenv("MISTRAL_GGUF_REPO", "behbudiy/Mistral-7B-Instruct-Uz-GGUF")
FILE = os.getenv("MISTRAL_GGUF_FILE", "mistral-7b-instruct-uz.Q4_K_M.gguf")
TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")


def main():
    if os.path.exists(DEST):
        size_mb = os.path.getsize(DEST) / (1024 * 1024)
        log.info(f"✓ Model already exists at {DEST} ({size_mb:.1f} MB)")
        return 0

    os.makedirs(os.path.dirname(DEST), exist_ok=True)

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        log.error("huggingface-hub not installed. Run: pip install huggingface-hub")
        return 1

    log.info(f"Downloading {REPO}/{FILE} → {DEST}")
    try:
        path = hf_hub_download(
            repo_id=REPO,
            filename=FILE,
            local_dir=os.path.dirname(DEST),
            token=TOKEN,
            local_dir_use_symlinks=False,
        )
        # Move/rename if needed
        if path != DEST and os.path.exists(path):
            os.rename(path, DEST)
        log.info(f"✓ Downloaded to {DEST}")
        return 0
    except Exception as e:
        log.error(f"Download failed: {e}")
        log.error("Make sure you've accepted the model license at:")
        log.error(f"  https://huggingface.co/{REPO}")
        log.error("And set HF_TOKEN env var.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
