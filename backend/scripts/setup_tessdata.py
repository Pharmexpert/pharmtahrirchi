"""
Download Tesseract traineddata files for OCR (eng, rus, uzb).
Runs at Railway startup — idempotent, skips if already present.
"""
import os
import urllib.request
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("setup_tessdata")

# Tesseract tessdata directory — check multiple possible paths
TESSDATA_CANDIDATES = [
    os.getenv("TESSDATA_PREFIX", ""),
    "/usr/share/tesseract-ocr/5/tessdata",
    "/usr/share/tesseract-ocr/4.00/tessdata",
    "/usr/share/tessdata",
    "/usr/local/share/tessdata",
    "/nix/store",  # nixpacks
]

GITHUB_TESSDATA = "https://github.com/tesseract-ocr/tessdata_fast/raw/main"

LANGUAGES = {
    "eng": "English",
    "rus": "Russian",
    "uzb": "Uzbek (Cyrillic)",
}


def find_tessdata_dir():
    """Find existing tessdata directory or create one."""
    for candidate in TESSDATA_CANDIDATES:
        if candidate and os.path.isdir(candidate):
            # Check if it contains any .traineddata files
            if any(f.endswith(".traineddata") for f in os.listdir(candidate)):
                return candidate
            # Directory exists but empty — try to use it
            if os.access(candidate, os.W_OK):
                return candidate

    # Fallback: create local tessdata
    local_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tessdata")
    os.makedirs(local_dir, exist_ok=True)
    os.environ["TESSDATA_PREFIX"] = local_dir
    return local_dir


def download_traineddata(tessdata_dir, lang_code):
    """Download a traineddata file if not already present."""
    filepath = os.path.join(tessdata_dir, f"{lang_code}.traineddata")
    if os.path.exists(filepath) and os.path.getsize(filepath) > 100_000:
        log.info(f"[tessdata] {lang_code}.traineddata already exists ({os.path.getsize(filepath) // 1024} KB)")
        return True

    url = f"{GITHUB_TESSDATA}/{lang_code}.traineddata"
    log.info(f"[tessdata] Downloading {lang_code}.traineddata from {url}...")
    try:
        urllib.request.urlretrieve(url, filepath)
        size_kb = os.path.getsize(filepath) // 1024
        log.info(f"[tessdata] {lang_code}.traineddata downloaded ({size_kb} KB)")
        return True
    except Exception as e:
        log.warning(f"[tessdata] Failed to download {lang_code}: {e}")
        return False


def main():
    tessdata_dir = find_tessdata_dir()
    log.info(f"[tessdata] Using directory: {tessdata_dir}")

    success = 0
    for lang_code, lang_name in LANGUAGES.items():
        if download_traineddata(tessdata_dir, lang_code):
            success += 1

    log.info(f"[tessdata] {success}/{len(LANGUAGES)} languages ready in {tessdata_dir}")

    # Set env for pytesseract
    os.environ["TESSDATA_PREFIX"] = tessdata_dir
    log.info(f"[tessdata] TESSDATA_PREFIX={tessdata_dir}")


if __name__ == "__main__":
    main()
