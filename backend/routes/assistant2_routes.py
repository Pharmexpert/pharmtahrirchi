"""
Assistant2 — AI-powered translation, scientific editing, and quality checking.

Endpoints:
  POST /api/assistant2/translate       — translate text between UZ/RU/EN
  POST /api/assistant2/edit            — scientific editing of pharma text
  POST /api/assistant2/check-translation — evaluate translation quality (0-100)
  POST /api/assistant2/check-edit      — evaluate edit quality (0-100)
  POST /api/assistant2/upload          — extract text from .txt/.docx files
"""
import io
import logging
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from auth import get_current_user
from routes.ai_helpers import generate_ai_content

logger = logging.getLogger("assistant2")
router = APIRouter(prefix="/api/assistant2", tags=["assistant2"])

LANG_NAMES = {"uz": "o'zbek", "ru": "rus", "en": "ingliz"}

# ═══════════════════════════════════════════════════
# System prompts
# ═══════════════════════════════════════════════════

TRANSLATE_SYSTEM = """Siz farmatsevtika sohasidagi mutaxassis tarjimonisiz, farmakopeya va dori vositalarini standartlashtirish bo'yicha chuqur ilmga egasiz.
Berilgan matnni ko'rsatilgan tillarga tarjima qiling.
Farmatsevtik terminologiyaga qat'iy rioya qiling.
Faqat tarjima matnini qaytaring, izoh yozmang."""

EDIT_SYSTEM = """Siz farmatsevtika sohasidagi ilmiy muharrirsiz, farmakopeya va dori vositalarini standartlashtirish bo'yicha chuqur ilmga egasiz.
Berilgan matnni ilmiy tahrir qiling:
- Terminologik aniqlik
- Uslubiy izchillik
- Grammatik to'g'rilik
- Farmatsevtik standartlarga moslik
Faqat tahrirlangan matnni qaytaring, izoh yoki tushuntirish yozmang."""

CHECK_TRANSLATION_SYSTEM = """Siz farmatsevtika tarjimasi sifatini baholovchi ekspertsiz, farmakopeya va dori vositalarini standartlashtirish bo'yicha chuqur ilmga egasiz.
Faqat JSON qaytaring, boshqa hech narsa yozmang:
{
  "umumiy_ball": 0-100,
  "terminologiya": {"ball": 0-100, "muammolar": [], "tavsiyalar": []},
  "toliqligi": {"ball": 0-100, "muammolar": []},
  "grammatika": {"ball": 0-100, "muammolar": []},
  "uslub": {"ball": 0-100, "muammolar": []},
  "xulosa": "",
  "ijobiy_jihatlar": []
}"""

CHECK_EDIT_SYSTEM = """Siz farmatsevtika ilmiy tahrir sifatini baholovchi ekspertsiz, farmakopeya va dori vositalarini standartlashtirish bo'yicha chuqur ilmga egasiz.
Faqat JSON qaytaring, boshqa hech narsa yozmang:
{
  "umumiy_ball": 0-100,
  "ilmiy_aniqlik": {"ball": 0-100, "izohlar": []},
  "ravonlik": {"ball": 0-100, "izohlar": []},
  "izchillik": {"ball": 0-100, "izohlar": []},
  "farmatsevtik_standart": {"ball": 0-100, "izohlar": []},
  "xulosa": "",
  "yaxshilanishlar": []
}"""


# ═══════════════════════════════════════════════════
# Request models
# ═══════════════════════════════════════════════════

class TranslateRequest(BaseModel):
    text: str
    source_lang: str  # uz, ru, en
    target_langs: List[str]  # ["uz", "ru"] etc.

class EditRequest(BaseModel):
    text: str
    lang: str  # uz, ru, en

class CheckTranslationRequest(BaseModel):
    original: str
    translation: str
    source_lang: str
    target_lang: str

class CheckEditRequest(BaseModel):
    original: str
    edited: str
    lang: str


# ═══════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════

@router.post("/translate")
async def translate_text(req: TranslateRequest, current_user: Dict = Depends(get_current_user)):
    """Translate pharma text to one or two target languages."""
    if not req.text.strip():
        raise HTTPException(400, "Matn bo'sh")
    if len(req.text) > 50000:
        raise HTTPException(400, "Matn juda uzun (max 50000 belgi)")

    results = {}
    source_name = LANG_NAMES.get(req.source_lang, req.source_lang)

    for target in req.target_langs:
        if target == req.source_lang:
            continue
        target_name = LANG_NAMES.get(target, target)
        prompt = f"""{TRANSLATE_SYSTEM}

Manba til: {source_name}
Maqsad til: {target_name}

Matn:
{req.text}"""
        try:
            result = await generate_ai_content(prompt, prefer="cloud")
            results[target] = result.strip() if result else ""
        except Exception as e:
            logger.error(f"[translate] {req.source_lang}->{target} failed: {e}")
            results[target] = f"Xatolik: {str(e)[:200]}"

    return {"translations": results, "source_lang": req.source_lang}


@router.post("/edit")
async def edit_text(req: EditRequest, current_user: Dict = Depends(get_current_user)):
    """Scientific editing of pharma text."""
    if not req.text.strip():
        raise HTTPException(400, "Matn bo'sh")
    if len(req.text) > 50000:
        raise HTTPException(400, "Matn juda uzun (max 50000 belgi)")

    lang_name = LANG_NAMES.get(req.lang, req.lang)
    prompt = f"""{EDIT_SYSTEM}

Til: {lang_name}

Matn:
{req.text}"""

    try:
        result = await generate_ai_content(prompt, prefer="cloud")
        return {"edited": result.strip() if result else "", "lang": req.lang}
    except Exception as e:
        logger.error(f"[edit] failed: {e}")
        raise HTTPException(500, f"Tahrir xatoligi: {str(e)[:200]}")


@router.post("/check-translation")
async def check_translation(req: CheckTranslationRequest, current_user: Dict = Depends(get_current_user)):
    """Evaluate translation quality with detailed scoring."""
    if not req.original.strip() or not req.translation.strip():
        raise HTTPException(400, "Original va tarjima matni kerak")

    source_name = LANG_NAMES.get(req.source_lang, req.source_lang)
    target_name = LANG_NAMES.get(req.target_lang, req.target_lang)

    prompt = f"""{CHECK_TRANSLATION_SYSTEM}

Manba til: {source_name}
Maqsad til: {target_name}

Original matn:
{req.original}

Tarjima:
{req.translation}"""

    try:
        result = await generate_ai_content(prompt, prefer="cloud")
        # Try to parse JSON from result
        import json, re
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return {"result": data}
        return {"result": {"umumiy_ball": 0, "xulosa": result, "raw": True}}
    except Exception as e:
        logger.error(f"[check-translation] failed: {e}")
        raise HTTPException(500, f"Tekshirish xatoligi: {str(e)[:200]}")


@router.post("/check-edit")
async def check_edit(req: CheckEditRequest, current_user: Dict = Depends(get_current_user)):
    """Evaluate edit quality with detailed scoring."""
    if not req.original.strip() or not req.edited.strip():
        raise HTTPException(400, "Dastlabki va tahrirlangan matn kerak")

    lang_name = LANG_NAMES.get(req.lang, req.lang)

    prompt = f"""{CHECK_EDIT_SYSTEM}

Til: {lang_name}

Dastlabki matn:
{req.original}

Tahrirlangan matn:
{req.edited}"""

    try:
        result = await generate_ai_content(prompt, prefer="cloud")
        import json, re
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return {"result": data}
        return {"result": {"umumiy_ball": 0, "xulosa": result, "raw": True}}
    except Exception as e:
        logger.error(f"[check-edit] failed: {e}")
        raise HTTPException(500, f"Tekshirish xatoligi: {str(e)[:200]}")


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), current_user: Dict = Depends(get_current_user)):
    """Extract text from .txt or .docx file."""
    if not file.filename:
        raise HTTPException(400, "Fayl nomi yo'q")

    name = file.filename.lower()
    raw = await file.read()

    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(400, "Fayl hajmi 10MB dan oshmasligi kerak")

    if name.endswith('.txt'):
        # Try UTF-8, fallback to cp1251
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            text = raw.decode('cp1251', errors='replace')
        return {"filename": file.filename, "text": text}

    elif name.endswith('.docx'):
        try:
            from docx import Document
            doc = Document(io.BytesIO(raw))
            paragraphs = [p.text for p in doc.paragraphs]
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        paragraphs.append(cell.text)
            text = "\n".join(paragraphs)
            return {"filename": file.filename, "text": text}
        except Exception as e:
            raise HTTPException(400, f"DOCX o'qishda xatolik: {str(e)[:200]}")

    else:
        raise HTTPException(400, "Faqat .txt va .docx fayllar qo'llab-quvvatlanadi")
