"""
Phase 4: Grammar check endpoints.
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
import grammar_checker

logger = logging.getLogger("grammar_routes")
router = APIRouter(prefix="/api/grammar", tags=["grammar"])


@router.post("/check")
async def check_grammar(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """
    Check Uzbek text for grammar issues.

    Request: { "text": "...", "lang": "uz" }
    Response: {
        "issues": [
            {
                "word": "...",
                "from_index": N,
                "to_index": M,
                "issue_type": "G/Morphology|G/Agreement|...",
                "message": "...",
                "suggestions": [...],
                "source": "morph|bert|tahrirchi_faiss",
                "confidence": 0.0-1.0
            }
        ],
        "total": N,
        "by_type": { "G/Morphology": X, ... }
    }
    """
    text = payload.get("text") or ""
    lang = payload.get("lang") or "uz"
    if not text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    if len(text) > 50000:
        raise HTTPException(status_code=400, detail="text too long (max 50000)")

    checker = grammar_checker.get_checker()
    issues = checker.check(text, lang=lang)

    # Group by type
    by_type: Dict[str, int] = {}
    for i in issues:
        by_type[i.issue_type] = by_type.get(i.issue_type, 0) + 1

    return {
        "issues": [i.to_dict() for i in issues],
        "total": len(issues),
        "by_type": by_type,
        "lang": lang,
    }


@router.post("/lexicon-search")
async def lexicon_search(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """
    Semantic search over 8.7M word tahrirchi lexicon.

    Request: { "word": "...", "k": 10 }
    Response: { "results": [{"word", "frequency", "similarity"}, ...] }
    """
    word = (payload.get("word") or "").strip()
    k = int(payload.get("k") or 10)
    if not word:
        raise HTTPException(status_code=400, detail="word is required")
    if k > 50:
        raise HTTPException(status_code=400, detail="k too large (max 50)")

    import db
    lex = db.tahrirchi_lexicon
    if not lex.is_ready():
        lex.load()
    if not lex.is_ready():
        return {"results": [], "note": "FAISS lexicon index not loaded"}

    results = lex.search_similar(word, k=k)
    return {"results": results, "total": len(results)}
