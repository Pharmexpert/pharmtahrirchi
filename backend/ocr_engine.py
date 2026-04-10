"""
OCR Engine — Tesseract wrapper for PDF/image → text extraction.
Phase 6: Supports eng, rus, uzb traineddata.

Usage:
    from ocr_engine import extract_text
    text = extract_text("/path/to/image.png", lang="uzb+rus+eng")
"""
import os
import logging
from typing import Optional

logger = logging.getLogger("ocr_engine")

TESSDATA_DIR = os.getenv("TESSDATA_PREFIX", "/usr/share/tesseract-ocr/5/tessdata")


def is_available() -> bool:
    """Check if pytesseract + Tesseract binary are available."""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def extract_text(image_path: str, lang: str = "uzb+rus+eng") -> str:
    """Extract text from an image file using Tesseract OCR.
    Args:
        image_path: Path to image (PNG, JPG, TIFF) or PDF
        lang: Tesseract language codes (e.g. "uzb+rus+eng")
    Returns:
        Extracted text string
    """
    import pytesseract
    from PIL import Image

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    ext = os.path.splitext(image_path)[1].lower()

    if ext == ".pdf":
        return extract_from_pdf(image_path, lang)

    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
    return text.strip()


def extract_from_pdf(pdf_path: str, lang: str = "uzb+rus+eng") -> str:
    """Extract text from PDF by converting pages to images first."""
    try:
        from pdf2image import convert_from_path
        import pytesseract

        images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=20)
        pages = []
        for i, img in enumerate(images):
            text = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
            if text.strip():
                pages.append(f"--- Page {i+1} ---\n{text.strip()}")
        return "\n\n".join(pages)
    except ImportError:
        raise RuntimeError("pdf2image not installed. Install: pip install pdf2image")
    except Exception as e:
        raise RuntimeError(f"PDF OCR failed: {e}")


def extract_from_bytes(image_bytes: bytes, lang: str = "uzb+rus+eng", filename: str = "image.png") -> str:
    """Extract text from image bytes (for API uploads)."""
    import pytesseract
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
    return text.strip()


def get_available_languages() -> list:
    """Return list of installed Tesseract languages."""
    try:
        import pytesseract
        return pytesseract.get_languages()
    except Exception:
        return []


def info() -> dict:
    """Return OCR engine status."""
    available = is_available()
    langs = get_available_languages() if available else []
    return {
        "available": available,
        "languages": langs,
        "tessdata_dir": TESSDATA_DIR,
    }
