"""
Phase 7: QA Lab endpoints — translation quality checking.

POST /api/qa/check  — run QA checks on source/target pair
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends

from auth import get_current_user

router = APIRouter(prefix="/api/qa", tags=["qa"])


@router.post("/check")
async def qa_check(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Run QA checks on a translation pair.
    Input: { source_text, target_text, source_lang?, target_lang?, back_translate? }
    """
    source_text = (payload.get("source_text") or "").strip()
    target_text = (payload.get("target_text") or "").strip()
    source_lang = payload.get("source_lang", "en")
    target_lang = payload.get("target_lang", "uz")
    back_translate = payload.get("back_translate", False)

    if not source_text or not target_text:
        return {"checks": {}, "score": 0, "passed": 0, "total": 0, "grade": "N/A", "error": "Both source and target text required"}

    import qa_engine
    result = await qa_engine.run_qa_check(
        source_text, target_text,
        source_lang, target_lang,
        include_back_translation=back_translate,
    )
    return result
