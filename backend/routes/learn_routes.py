"""
Phase 5: Self-learning loop endpoints.

Receives user accept/reject events and updates:
  - sayqallash_rules (frequency, BERT vector)
  - FAISS index (live add)
  - tahrirchi.db lexicon (new correct words)
  - learning_log (for analytics)
"""
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
import db

logger = logging.getLogger("learn_routes")
router = APIRouter(prefix="/api/learn", tags=["learning"])


@router.post("/correction")
async def learn_from_correction(
    payload: Dict[str, Any],
    current_user: Dict = Depends(get_current_user),
):
    """
    Learn from a single user-accepted correction.

    Request:
    {
        "wrong": "ишлатмоқдадиган",
        "correct": "ишлатиладиган",
        "context": "Ушбу дори касал ишлатмоқдадиган...",
        "error_type": "G/Morphology",
        "lang": "uz"
    }

    Response:
    {
        "success": bool,
        "rule_id": int,
        "rule_action": "inserted"|"updated",
        "bert_indexed": bool,
        "faiss_added": bool,
        "lexicon_added": bool,
        "activity_logged": bool
    }
    """
    wrong = (payload.get("wrong") or "").strip()
    correct = (payload.get("correct") or "").strip()
    if not wrong or not correct:
        raise HTTPException(status_code=400, detail="wrong and correct are required")

    result = db.learn_from_correction(
        wrong=wrong,
        correct=correct,
        user_id=current_user.get("id", ""),
        user_name=current_user.get("name", ""),
        context=payload.get("context", ""),
        error_type=payload.get("error_type", "S/Spelling"),
        lang=payload.get("lang", "uz"),
        source="learned",
    )
    return result


@router.post("/batch")
async def learn_from_batch(
    payload: Dict[str, Any],
    current_user: Dict = Depends(get_current_user),
):
    """
    Learn from multiple corrections at once (e.g. after user accepts all in Sayqallash).

    Request:
    {
        "corrections": [
            { "wrong": "...", "correct": "...", "error_type": "...", "context": "..." },
            ...
        ],
        "lang": "uz"
    }
    """
    corrections: List[Dict[str, Any]] = payload.get("corrections") or []
    lang = payload.get("lang", "uz")
    if not isinstance(corrections, list):
        raise HTTPException(status_code=400, detail="corrections must be a list")
    if len(corrections) > 200:
        raise HTTPException(status_code=400, detail="too many corrections (max 200 per batch)")

    results = []
    for c in corrections:
        wrong = (c.get("wrong") or "").strip()
        correct = (c.get("correct") or "").strip()
        if not wrong or not correct:
            continue
        r = db.learn_from_correction(
            wrong=wrong,
            correct=correct,
            user_id=current_user.get("id", ""),
            user_name=current_user.get("name", ""),
            context=c.get("context", ""),
            error_type=c.get("error_type", "S/Spelling"),
            lang=c.get("lang", lang),
            source="learned",
        )
        results.append(r)

    return {
        "success": True,
        "total": len(results),
        "inserted": sum(1 for r in results if r.get("rule_action") == "inserted"),
        "updated": sum(1 for r in results if r.get("rule_action") == "updated"),
        "bert_indexed": sum(1 for r in results if r.get("bert_indexed")),
        "lexicon_added": sum(1 for r in results if r.get("lexicon_added")),
        "results": results,
    }


@router.get("/stats")
async def learning_stats(
    since_days: int = 7,
    current_user: Dict = Depends(get_current_user),
):
    """
    Return analytics about how much the system has learned recently.

    Query params:
      since_days: window for "recent actions" (default 7)

    Response:
    {
        "since_days": 7,
        "total_recent_actions": N,
        "by_error_type": { "G/Morphology": X, ... },
        "top_users": [{"user": "Akmal", "count": N}, ...],
        "total_learned_rules": M,
        "total_rules": K,
        "learning_ratio": 0.0-100.0
    }
    """
    if since_days < 1:
        since_days = 1
    if since_days > 365:
        since_days = 365
    return db.get_learning_stats(since_days=since_days)
