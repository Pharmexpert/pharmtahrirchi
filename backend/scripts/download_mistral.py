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
# Community-quantized GGUF (mradermacher is most reliable, 248+ downloads)
REPO = os.getenv("MISTRAL_GGUF_REPO", "mradermacher/Mistral-7B-Instruct-Uz-GGUF")
# Default Q8_0 for Pro plan (best quality, ~7.7GB) — change to Q4_K_M for 4.4GB
FILE = os.getenv("MISTRAL_GGUF_FILE", "Mistral-7B-Instruct-Uz.Q8_0.gguf")
TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")


def main():
    # Skip entirely if local mode is not enabled — saves boot time
    if os.getenv("MISTRAL_LOCAL") != "1":
        log.info("MISTRAL_LOCAL != 1 — skipping local GGUF download (using cloud/HF API instead)")
        return 0

    if os.path.exists(DEST):
        size_mb = os.path.getsize(DEST) / (1024 * 1024)
        if size_mb > 100:  # sanity check — full file should be GBs
            log.info(f"✓ Model already exists at {DEST} ({size_mb:.1f} MB)")
            return 0
        else:
            log.warning(f"Existing file at {DEST} is too small ({size_mb:.1f} MB) — re-downloading")
            os.remove(DEST)

    if not TOKEN:
        log.error("HF_TOKEN not set — cannot download gated model. Set HF_TOKEN env var.")
        return 1

    os.makedirs(os.path.dirname(DEST), exist_ok=True)

    # Clean up any partial downloads from previous failed attempts to free disk space
    cache_dir = os.path.join(os.path.dirname(DEST), ".cache")
    if os.path.exists(cache_dir):
        try:
            import shutil
            shutil.rmtree(cache_dir)
            log.info(f"Cleaned partial download cache: {cache_dir}")
        except Exception as e:
            log.warning(f"Failed to clean cache: {e}")
    # Also clean any orphan .gguf.tmp files
    try:
        for f in os.listdir(os.path.dirname(DEST)):
            if f.endswith(".tmp") or f.endswith(".incomplete") or f.endswith(".partial"):
                try:
                    os.remove(os.path.join(os.path.dirname(DEST), f))
                    log.info(f"Removed partial: {f}")
                except Exception:
                    pass
    except Exception:
        pass

    # Check available disk space before attempting download
    try:
        import shutil as _sh
        total, used, free = _sh.disk_usage(os.path.dirname(DEST))
        free_mb = free // (1024 * 1024)
        log.info(f"Disk: {free_mb} MB free at {os.path.dirname(DEST)}")
        # Estimated GGUF sizes (MB)
        size_estimates = {
            "Q8_0": 7700, "Q6_K": 6000, "Q5_K_M": 5100, "Q5_K_S": 4900,
            "Q4_K_M": 4400, "Q4_K_S": 4100, "Q3_K_M": 3300, "Q3_K_S": 2900,
            "Q2_K": 2700, "f16": 14000,
        }
        wanted_mb = next((mb for tag, mb in size_estimates.items() if tag in FILE), 5000)
        if free_mb < wanted_mb + 200:
            log.error(f"Not enough disk space: need ~{wanted_mb} MB, have {free_mb} MB free")
            log.error(f"Please resize Railway volume to at least {(wanted_mb + 2000) // 1024 + 1} GB")
            return 1
    except Exception:
        pass

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
