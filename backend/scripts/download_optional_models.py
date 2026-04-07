"""
Download optional models on Railway startup if env vars enable them:
  - FastText Uzbek (.bin) — for fast synonyms
  - Whisper (small/base) — for audio transcription

Skipped if env vars not set, or if models already exist.
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="[optional_models] %(message)s")
log = logging.getLogger()


def download_fasttext():
    """Download fastText Uzbek model from HF."""
    if os.getenv("FASTTEXT_LOCAL") != "1":
        return
    dest = os.getenv("FASTTEXT_PATH", "/tmp/uz_fasttext.bin")
    if os.path.exists(dest):
        log.info(f"fasttext already exists at {dest}")
        return
    try:
        from huggingface_hub import hf_hub_download
        token = os.getenv("HF_TOKEN")
        # Try multiple known fastText repos for Uzbek
        attempts = [
            ("facebook/fasttext-uz-vectors", "model.bin"),
            ("elmurod1202/uztext-fasttext", "uz.bin"),
        ]
        for repo, fn in attempts:
            try:
                log.info(f"Trying {repo}/{fn}...")
                path = hf_hub_download(repo_id=repo, filename=fn, token=token, local_dir=os.path.dirname(dest), local_dir_use_symlinks=False)
                if path != dest:
                    os.rename(path, dest)
                log.info(f"✓ fasttext at {dest}")
                return
            except Exception as e:
                log.warning(f"  {repo} failed: {e}")
    except ImportError:
        log.warning("huggingface_hub not installed")


def download_whisper():
    """Pre-download whisper model so first request is fast."""
    if os.getenv("WHISPER_LOCAL") != "1":
        return
    model_name = os.getenv("WHISPER_MODEL", "base")
    try:
        # Try faster-whisper first (smaller, CPU-friendly)
        try:
            from faster_whisper import WhisperModel
            log.info(f"Pre-loading faster-whisper {model_name}...")
            _ = WhisperModel(model_name, device="cpu", compute_type="int8")
            log.info(f"✓ faster-whisper {model_name} ready")
            return
        except ImportError:
            pass
        # Fall back to openai-whisper
        try:
            import whisper
            log.info(f"Pre-loading openai-whisper {model_name}...")
            _ = whisper.load_model(model_name)
            log.info(f"✓ openai-whisper {model_name} ready")
        except ImportError:
            log.warning("Neither faster-whisper nor whisper installed — skipping")
    except Exception as e:
        log.warning(f"Whisper preload failed: {e}")


def main():
    download_fasttext()
    download_whisper()
    return 0


if __name__ == "__main__":
    sys.exit(main())
