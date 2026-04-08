"""
Syntax routes — Phase 3.
Endpoints:
  POST /api/syntax/analyze   — full analysis of one sentence
  POST /api/syntax/check     — multi-sentence text → list of errors (for editor)
  POST /api/syntax/reorder   — auto-reorder to canonical S-O-V
  POST /api/syntax/save-rule — user saves a corrected rule
  GET  /api/syntax/templates — list of sentence templates
  GET  /api/syntax/stats     — DB statistics
"""
import os
import sqlite3
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user

import syntax_engine

router = APIRouter(prefix="/api/syntax", tags=["syntax"])

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))


@router.post("/analyze")
async def analyze_sentence(payload: Dict[str, Any]):
    """Analyze a single sentence — return tokens, roles, errors, suggestions."""
    sentence = (payload.get("text") or payload.get("sentence") or "").strip()
    if not sentence:
        raise HTTPException(status_code=400, detail="text is required")
    return syntax_engine.analyze(sentence)


@router.post("/check")
async def check_text(payload: Dict[str, Any]):
    """Check multi-sentence text and return all errors (for editor integration)."""
    text = (payload.get("text") or "").strip()
    if not text:
        return {"errors": []}
    errors = syntax_engine.check_text(text)
    return {"errors": errors, "count": len(errors)}


@router.post("/reorder")
async def reorder(payload: Dict[str, Any]):
    """Reorder words to canonical S-O-V order."""
    sentence = (payload.get("text") or "").strip()
    if not sentence:
        raise HTTPException(status_code=400, detail="text is required")
    return {"original": sentence, "canonical": syntax_engine.reorder_canonical(sentence)}


@router.post("/save-rule")
async def save_rule(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """User saves a corrected word order rule."""
    wrong = (payload.get("wrong") or "").strip()
    correct = (payload.get("correct") or "").strip()
    explanation = payload.get("explanation", "")
    if not wrong or not correct:
        raise HTTPException(status_code=400, detail="wrong and correct required")
    return syntax_engine.save_user_rule(wrong, correct, explanation, user_id=current_user.get("id"))


@router.get("/templates")
async def list_templates(limit: int = 50):
    """List sentence templates from DB."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT id, template, sentence_type, semantic_type, example_uz, formula, frequency
            FROM syntax_sentence_templates
            ORDER BY frequency DESC LIMIT ?
        """, (limit,))
        templates = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def syntax_stats():
    """Database statistics for syntax module."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        stats = {}
        for table in ["syntax_sentence_parts", "syntax_phrases", "syntax_sentence_templates",
                      "syntax_word_order_rules", "syntax_parsed_sentences"]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cur.fetchone()[0]
            except Exception:
                stats[table] = 0
        conn.close()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────
# GECTurk-style endpoints (Phases A, B, C)
# ─────────────────────────────────────────────

@router.post("/verify-rules")
async def verify_rules(payload: Dict[str, Any] = None, current_user: Dict = Depends(get_current_user)):
    """Phase A: Bidirectional verification of sayqallash_rules. Flags noisy rules."""
    import syntax_verifier
    limit = (payload or {}).get("limit", 5000)
    return syntax_verifier.verify_all_rules(limit=limit)


@router.get("/noisy-rules")
async def list_noisy_rules(limit: int = 100, current_user: Dict = Depends(get_current_user)):
    """List rules flagged as noisy after verification."""
    import syntax_verifier
    return {"rules": syntax_verifier.get_noisy_rules(limit=limit)}


@router.post("/delete-noisy")
async def delete_noisy(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Delete all noisy rules (requires confirm=true)."""
    import syntax_verifier
    confirm = payload.get("confirm", False)
    deleted = syntax_verifier.delete_noisy_rules(confirm=confirm)
    return {"deleted": deleted}


@router.post("/generate-synth")
async def generate_synth(payload: Dict[str, Any] = None, current_user: Dict = Depends(get_current_user)):
    """Phase B: Generate synthetic parallel pairs from UD sentences via 10 transformations."""
    import syntax_synth_generator
    p = payload or {}
    return syntax_synth_generator.generate_all(
        limit_sentences=p.get("limit_sentences", 1000),
        transforms_per_sent=p.get("transforms_per_sent", 5),
    )


@router.post("/export-training")
async def export_training(current_user: Dict = Depends(get_current_user)):
    """Phase C: Export training dataset (JSONL) for mBART fine-tuning."""
    import syntax_train_mbart
    path = "/tmp/syntax_train.jsonl"
    count = syntax_train_mbart.export_training_dataset(path)
    return {"exported": count, "path": path}


@router.get("/parts/{word}")
async def get_word_roles(word: str):
    """Get all known roles for a word."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT role, COUNT(*) as freq, MAX(example_uz) as example
            FROM syntax_sentence_parts
            WHERE word = ? OR lemma = ?
            GROUP BY role
            ORDER BY freq DESC
        """, (word.lower(), word.lower()))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"word": word, "roles": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
