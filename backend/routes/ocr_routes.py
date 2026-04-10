"""
Phase 6: OCR endpoints — image/PDF → text extraction + auto-sayqallash.

POST /api/ocr/extract   — upload image/PDF → get text
GET  /api/ocr/status     — check Tesseract availability
"""
import os
import logging
import tempfile
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

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
    lang: str = "uzb+rus+eng",
    auto_sayqallash: bool = False,
    current_user: Dict = Depends(get_current_user),
):
    """Extract text from uploaded image/PDF using Tesseract OCR.

    Args:
        file: Image or PDF file
        lang: Tesseract language codes (default: uzb+rus+eng)
        auto_sayqallash: If true, run sayqallash on extracted text
    """
    # Validate extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    # Read file
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max: {MAX_FILE_SIZE // (1024*1024)} MB")

    # Extract text
    try:
        import ocr_engine
        if not ocr_engine.is_available():
            raise HTTPException(status_code=503, detail="Tesseract OCR not available on this server")

        if ext == ".pdf":
            # Save to temp file for PDF processing
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            try:
                text = ocr_engine.extract_text(tmp_path, lang=lang)
            finally:
                os.unlink(tmp_path)
        else:
            text = ocr_engine.extract_from_bytes(content, lang=lang, filename=file.filename or "image")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[OCR] extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")

    result = {
        "text": text,
        "filename": file.filename,
        "lang": lang,
        "char_count": len(text),
        "word_count": len(text.split()),
    }

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
