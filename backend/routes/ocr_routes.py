"""
Phase 6: OCR endpoints — image/PDF -> text extraction with confidence + lang detection.

POST /api/ocr/extract   — upload image/PDF -> get text + confidence scores
GET  /api/ocr/status    — check Tesseract availability
"""
import os
import logging
import tempfile
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query

from auth import get_current_user

logger = logging.getLogger("ocr_routes")
router = APIRouter(prefix="/api/ocr", tags=["ocr"])

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp", ".pdf"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.get("/status")
async def ocr_status():
    """Check OCR engine availability and installed languages."""
    try:
        import ocr_engine
        return ocr_engine.info()
    except ImportError:
        return {"available": False, "error": "pytesseract not installed"}
    except Exception as e:
        return {"available": False, "error": str(e)}


@router.post("/extract")
async def ocr_extract(
    file: UploadFile = File(...),
    lang: str = Query("uzb+rus+eng", description="Tesseract language codes"),
    auto_detect_lang: bool = Query(False, description="Auto-detect language of extracted text"),
    include_confidence: bool = Query(True, description="Include per-word confidence scores"),
    auto_sayqallash: bool = Query(False, description="Run spellcheck on extracted text"),
    current_user: Dict = Depends(get_current_user),
):
    """Extract text from uploaded image/PDF using Tesseract OCR.

    Returns extracted text with confidence scores and optional language detection.
    """
    # Validate extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max: {MAX_FILE_SIZE // (1024*1024)} MB",
        )

    # Extract text
    try:
        import ocr_engine

        if not ocr_engine.is_available():
            raise HTTPException(status_code=503, detail="Tesseract OCR not available on this server")

        if ext == ".pdf":
            # PDF requires temp file for pdf2image conversion
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            try:
                if include_confidence:
                    extraction = ocr_engine.extract_pdf_with_confidence(tmp_path, lang=lang)
                else:
                    text = ocr_engine.extract_from_pdf(tmp_path, lang=lang)
                    extraction = {"text": text}
            finally:
                os.unlink(tmp_path)
        else:
            # Image file — extract from bytes
            if include_confidence:
                extraction = ocr_engine.extract_with_confidence(content, lang=lang)
            else:
                text = ocr_engine.extract_from_bytes(content, lang=lang, filename=file.filename or "image")
                extraction = {"text": text}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[OCR] extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")

    text = extraction.get("text", "")

    result = {
        "text": text,
        "filename": file.filename,
        "lang": lang,
        "char_count": len(text),
        "word_count": len(text.split()) if text else 0,
    }

    # Confidence scores
    if include_confidence:
        result["mean_confidence"] = extraction.get("mean_confidence", 0)
        if "pages" in extraction:
            result["pages"] = extraction["pages"]
            result["page_count"] = extraction.get("page_count", 0)
        # Only include word-level details if not PDF (too large for multi-page)
        if ext != ".pdf" and "words" in extraction:
            result["words"] = extraction["words"]

    # Language auto-detection
    if auto_detect_lang and text.strip():
        try:
            import ocr_engine as _ocr
            lang_result = _ocr.detect_language(text)
            result["detected_language"] = lang_result
        except Exception as e:
            logger.warning(f"[OCR] language detection failed: {e}")
            result["detected_language"] = {"detected": "unknown", "error": str(e)}

    # Optional: run sayqallash on extracted text
    if auto_sayqallash and text.strip():
        try:
            from routes.sayqallash_routes import sayqallash
            say_result = await sayqallash({"text": text, "lang": "uz"})
            result["sayqallash"] = {
                "corrected_text": say_result.get("corrected_text", text),
                "annotations": say_result.get("annotations", []),
                "error_count": len(say_result.get("annotations", [])),
            }
        except Exception as e:
            logger.warning(f"[OCR] auto-sayqallash failed: {e}")

    return result
