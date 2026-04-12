"""
OCR Engine — Tesseract wrapper for PDF/image -> text extraction.
Phase 6: Supports eng, rus, uzb traineddata.
Provides confidence scores and language auto-detection.

Usage:
    from ocr_engine import extract_text, extract_with_confidence
    text = extract_text("/path/to/image.png", lang="uzb+rus+eng")
    result = extract_with_confidence(image_bytes, lang="uzb+rus+eng")
"""
import os
import io
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger("ocr_engine")

def _find_tessdata():
    """Find tessdata directory from multiple possible locations."""
    candidates = [
        os.getenv("TESSDATA_PREFIX", ""),
        "/usr/share/tesseract-ocr/5/tessdata",
        "/usr/share/tesseract-ocr/4.00/tessdata",
        "/usr/share/tessdata",
        os.path.join(os.path.dirname(__file__), "tessdata"),
    ]
    for d in candidates:
        if d and os.path.isdir(d):
            return d
    return "/usr/share/tesseract-ocr/5/tessdata"

TESSDATA_DIR = _find_tessdata()

# Language code mapping: ISO 639-1 -> Tesseract lang code
LANG_MAP = {
    "en": "eng", "ru": "rus", "uz": "uzb",
    "eng": "eng", "rus": "rus", "uzb": "uzb",
}


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

    img = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
    return text.strip()


def extract_with_confidence(image_bytes: bytes, lang: str = "uzb+rus+eng") -> Dict[str, Any]:
    """Extract text with per-word confidence scores.
    Returns:
        {
            "text": str,
            "mean_confidence": float,
            "words": [{"text": str, "confidence": int, "left": int, "top": int, ...}],
            "page_confidences": [float]  # per-page average for multi-page
        }
    """
    import pytesseract
    from PIL import Image
    import csv

    img = Image.open(io.BytesIO(image_bytes))
    # image_to_data returns TSV with word-level confidence
    tsv_data = pytesseract.image_to_data(img, lang=lang, config="--psm 6")

    words = []
    confidences = []
    reader = csv.DictReader(io.StringIO(tsv_data), delimiter="\t")
    for row in reader:
        conf = int(row.get("conf", -1))
        text = (row.get("text") or "").strip()
        if conf >= 0 and text:
            words.append({
                "text": text,
                "confidence": conf,
                "left": int(row.get("left", 0)),
                "top": int(row.get("top", 0)),
                "width": int(row.get("width", 0)),
                "height": int(row.get("height", 0)),
                "block_num": int(row.get("block_num", 0)),
                "line_num": int(row.get("line_num", 0)),
            })
            confidences.append(conf)

    full_text = " ".join(w["text"] for w in words)
    mean_conf = round(sum(confidences) / max(len(confidences), 1), 1)

    return {
        "text": full_text,
        "mean_confidence": mean_conf,
        "word_count": len(words),
        "words": words,
    }


def extract_pdf_with_confidence(pdf_path: str, lang: str = "uzb+rus+eng") -> Dict[str, Any]:
    """Extract text from PDF with per-page confidence scores."""
    from pdf2image import convert_from_path

    images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=20)
    pages = []
    all_words = []
    all_confidences = []

    for i, img in enumerate(images):
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        page_result = extract_with_confidence(img_bytes.getvalue(), lang=lang)
        pages.append({
            "page": i + 1,
            "text": page_result["text"],
            "mean_confidence": page_result["mean_confidence"],
            "word_count": page_result["word_count"],
        })
        all_words.extend(page_result["words"])
        if page_result["words"]:
            all_confidences.append(page_result["mean_confidence"])

    full_text = "\n\n".join(f"--- Page {p['page']} ---\n{p['text']}" for p in pages if p["text"])
    overall_conf = round(sum(all_confidences) / max(len(all_confidences), 1), 1) if all_confidences else 0

    return {
        "text": full_text,
        "mean_confidence": overall_conf,
        "word_count": len(all_words),
        "pages": pages,
        "page_count": len(pages),
    }


def detect_language(text: str) -> Dict[str, Any]:
    """Auto-detect the language of extracted text.
    Uses langdetect for reliable detection across eng/rus/uzb.
    """
    if not text or len(text.strip()) < 10:
        return {"detected": "unknown", "confidence": 0, "details": {}}

    try:
        from langdetect import detect_langs
        results = detect_langs(text)
        # langdetect returns ISO 639-1 codes
        detected = []
        for r in results:
            detected.append({"lang": str(r.lang), "probability": round(r.prob, 3)})
        primary = detected[0] if detected else {"lang": "unknown", "probability": 0}
        return {
            "detected": primary["lang"],
            "confidence": primary["probability"],
            "details": detected,
        }
    except Exception as e:
        logger.warning(f"Language detection failed: {e}")
        return {"detected": "unknown", "confidence": 0, "error": str(e)}


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
