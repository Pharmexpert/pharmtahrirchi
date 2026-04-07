"""
Morphology analysis endpoints (Phase 2).

Provides morphological decomposition of Uzbek words via Hunspell + heuristic.
"""
import re
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
import morphology

logger = logging.getLogger("morph_routes")
router = APIRouter(prefix="/api/morph", tags=["morphology"])


@router.post("/analyze")
async def analyze_word(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """
    Analyze a single Uzbek word.

    Request: { "word": "ишламоқдамасанми" }
    Response: {
        word, stem, pos, morphemes[], tense, person, number, case, mood, negation,
        breakdown, source
    }
    """
    word = (payload.get("word") or "").strip()
    if not word:
        raise HTTPException(status_code=400, detail="word is required")
    if len(word) > 60:
        raise HTTPException(status_code=400, detail="word too long (max 60 chars)")

    analyzer = morphology.get_analyzer()
    result = analyzer.analyze(word)

    if result is None:
        return {
            "word": word,
            "valid": False,
            "message": "Морфологик таҳлил қилиб бўлмади — сўз танилмади",
            "source": "none",
        }

    data = result.to_dict()
    data["valid"] = True
    return data


@router.post("/analyze-text")
async def analyze_text(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """
    Analyze every word in a text. Returns list of analyses + list of unknowns.

    Request: { "text": "..." }
    Response: {
        "analyses": [...],
        "unknowns": ["word1", "word2"],
        "total_words": N,
        "recognized": M,
        "unknown": K
    }
    """
    text = payload.get("text") or ""
    if not text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    if len(text) > 50000:
        raise HTTPException(status_code=400, detail="text too long (max 50000 chars)")

    analyzer = morphology.get_analyzer()

    # Tokenize
    words = re.findall(r"\w+", text, re.UNICODE)
    seen = set()
    analyses: List[Dict[str, Any]] = []
    unknowns: List[str] = []

    for word in words:
        if len(word) < 2:
            continue
        if word.lower() in seen:
            continue
        seen.add(word.lower())

        result = analyzer.analyze(word)
        if result:
            analyses.append(result.to_dict())
        else:
            unknowns.append(word)

    return {
        "analyses": analyses,
        "unknowns": unknowns,
        "total_words": len(words),
        "unique_words": len(seen),
        "recognized": len(analyses),
        "unknown": len(unknowns),
    }


@router.post("/validate")
async def validate_words(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """
    Quick validation: check which words are morphologically valid.

    Request: { "words": ["word1", "word2", ...] }
    Response: { "results": { "word1": true, "word2": false, ... } }
    """
    words = payload.get("words") or []
    if not isinstance(words, list):
        raise HTTPException(status_code=400, detail="words must be a list")
    if len(words) > 500:
        raise HTTPException(status_code=400, detail="too many words (max 500)")

    analyzer = morphology.get_analyzer()
    results = {}
    for w in words:
        if not isinstance(w, str) or len(w) < 2:
            continue
        results[w] = analyzer.is_valid_form(w)

    return {"results": results, "total": len(results)}


@router.get("/flags")
async def get_affix_flags(current_user: Dict = Depends(get_current_user)):
    """Return semantic mapping of Hunspell affix flags used by the analyzer."""
    return {
        "flags": morphology.FLAG_SEMANTICS,
        "total": len(morphology.FLAG_SEMANTICS),
    }
