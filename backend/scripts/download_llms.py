"""
Auto-download BOTH Llama 3.1 + Mistral 7B GGUF Q4_K_M on Railway startup.

Env vars:
    HF_TOKEN              — HF token (required)
    LLAMA_LOCAL=1         — enable Llama GGUF
    MISTRAL_LOCAL=1       — enable Mistral GGUF
    LLAMA_GGUF_PATH       — dest (default: /tmp/llama-q4.gguf)
    MISTRAL_GGUF_PATH     — dest (default: /tmp/mistral-q4.gguf)

Both models Q4_K_M:
    Llama 3.1 8B: ~4.7 GB
    Mistral 7B:   ~4.4 GB
    Total:        ~9 GB disk, ~10 GB RAM at inference
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="[download_llms] %(message)s")
log = logging.getLogger()

HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")


def download_one(name: str, env_flag: str, dest_env: str, default_dest: str, repo: str, filename: str) -> bool:
    """Download one GGUF file if env flag is set."""
    if os.getenv(env_flag) != "1":
        log.info(f"[{name}] {env_flag} != 1 — skipping")
        return True

    dest = os.getenv(dest_env, default_dest)

    if os.path.exists(dest):
        size_mb = os.path.getsize(dest) / (1024 * 1024)
        if size_mb > 1000:  # sanity: GGUF Q4 should be 3-5 GB
            log.info(f"[{name}] ✓ Already exists at {dest} ({size_mb:.0f} MB)")
            return True
        else:
            log.warning(f"[{name}] Existing file too small ({size_mb:.0f} MB) — redownloading")
            try:
                os.remove(dest)
            except Exception:
                pass

    if not HF_TOKEN:
        log.error(f"[{name}] HF_TOKEN not set")
        return False

    os.makedirs(os.path.dirname(dest), exist_ok=True)

    # Clean partial downloads
    try:
        for f in os.listdir(os.path.dirname(dest)):
            if (f.endswith(".tmp") or f.endswith(".incomplete") or f.endswith(".partial")) and name.lower() in f.lower():
                os.remove(os.path.join(os.path.dirname(dest), f))
    except Exception:
        pass

    # Check disk space
    try:
        import shutil
        _, _, free = shutil.disk_usage(os.path.dirname(dest))
        free_gb = free // (1024 ** 3)
        log.info(f"[{name}] Disk: {free_gb} GB free")
        if free_gb < 6:
            log.error(f"[{name}] Not enough disk ({free_gb} GB < 6 GB needed)")
            return False
    except Exception:
        pass

    log.info(f"[{name}] Downloading {repo}/{filename} → {dest}")
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(
            repo_id=repo,
            filename=filename,
            local_dir=os.path.dirname(dest),
            token=HF_TOKEN,
        )
        if path != dest and os.path.exists(path):
            os.rename(path, dest)
        size_mb = os.path.getsize(dest) / (1024 * 1024)
        log.info(f"[{name}] ✓ Downloaded {size_mb:.0f} MB to {dest}")
        return True
    except Exception as e:
        log.error(f"[{name}] Download failed: {e}")
        return False


def main():
    log.info("=" * 60)
    log.info("GGUF Auto-Downloader (Llama + Mistral)")
    log.info("=" * 60)

    ok1 = download_one(
        "Llama",
        env_flag="LLAMA_LOCAL",
        dest_env="LLAMA_GGUF_PATH",
        default_dest="/tmp/llama-q4.gguf",
        repo="mradermacher/Llama-3.1-8B-Instruct-Uz-GGUF",
        filename="Llama-3.1-8B-Instruct-Uz.Q4_K_M.gguf",
    )
    ok2 = download_one(
        "Mistral",
        env_flag="MISTRAL_LOCAL",
        dest_env="MISTRAL_GGUF_PATH",
        default_dest="/tmp/mistral-q4.gguf",
        repo="mradermacher/Mistral-7B-Instruct-Uz-GGUF",
        filename="Mistral-7B-Instruct-Uz.Q4_K_M.gguf",
    )
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    sys.exit(main())
