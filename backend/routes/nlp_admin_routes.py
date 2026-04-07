"""
Phase 6/7: NLP admin endpoints — manual trigger + metrics dashboard.
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from auth import get_admin_user, get_current_user
import db

logger = logging.getLogger("nlp_admin_routes")
router = APIRouter(prefix="/api/nlp", tags=["nlp-admin"])


@router.post("/grow-now")
async def trigger_growth(current_user: Dict = Depends(get_admin_user)):
    """
    Manually trigger the nightly dictionary growth job (admin only).
    Runs synchronously and returns the summary.
    """
    try:
        from scripts.nightly_dictionary_grow import grow_dictionary
        summary = grow_dictionary(window_hours=24)
        return {"success": True, "summary": summary}
    except Exception as e:
        logger.error(f"[grow-now] Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/growth-history")
async def growth_history(limit: int = 30, current_user: Dict = Depends(get_current_user)):
    """Return last N nightly run summaries."""
    if limit < 1:
        limit = 1
    if limit > 365:
        limit = 365
    try:
        from scripts.nightly_dictionary_grow import get_recent_runs
        return {"runs": get_recent_runs(limit), "limit": limit}
    except Exception as e:
        logger.error(f"[growth-history] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def nlp_health(current_user: Dict = Depends(get_current_user)):
    """
    Return health status of NLP subsystems:
      - Morphology Analyzer (Phase 2)
      - tahrirchi.db dictionary (Phase 1)
      - BERT engine (Phase 1)
      - FAISS rule index (existing)
      - FAISS lexicon index (Phase 3)
      - Self-learning loop (Phase 5)
    """
    import os
    import sqlite3

    health: Dict[str, Any] = {}

    # 1. Morphology Analyzer
    try:
        import morphology
        analyzer = morphology.get_analyzer()
        analyzer._ensure_loaded()
        health["morphology"] = {
            "status": "ready" if (analyzer._hunspell or analyzer._hunspell_lat) else "degraded",
            "cyrillic_loaded": analyzer._hunspell is not None,
            "latin_loaded": analyzer._hunspell_lat is not None,
        }
    except Exception as e:
        health["morphology"] = {"status": "error", "error": str(e)}

    # 2. tahrirchi.db
    try:
        if os.path.exists(db.TAHRIRCHI_DB_PATH):
            conn = sqlite3.connect(db.TAHRIRCHI_DB_PATH)
            cnt = conn.execute("SELECT COUNT(*) FROM dictionary").fetchone()[0]
            conn.close()
            health["tahrirchi_db"] = {
                "status": "ready" if cnt > 1000 else "empty",
                "word_count": cnt,
                "size_mb": round(os.path.getsize(db.TAHRIRCHI_DB_PATH) / (1024 * 1024), 1),
                "path": db.TAHRIRCHI_DB_PATH,
            }
        else:
            health["tahrirchi_db"] = {"status": "missing", "path": db.TAHRIRCHI_DB_PATH}
    except Exception as e:
        health["tahrirchi_db"] = {"status": "error", "error": str(e)}

    # 3. BERT engine
    try:
        import bert_engine
        health["bert"] = {
            "status": "ready" if bert_engine.engine.initialized else "loading",
            "model": bert_engine.MODEL_NAME,
        }
    except Exception as e:
        health["bert"] = {"status": "error", "error": str(e)}

    # 4. FAISS rule index
    try:
        rules_count = db.faiss_manager.index.ntotal if db.faiss_manager.is_ready() else 0
        health["faiss_rules"] = {
            "status": "ready" if db.faiss_manager.is_ready() else "empty",
            "vectors": rules_count,
            "dimension": db.faiss_manager.dimension,
        }
    except Exception as e:
        health["faiss_rules"] = {"status": "error", "error": str(e)}

    # 5. FAISS lexicon (Phase 3)
    try:
        lex = db.tahrirchi_lexicon
        if not lex.loaded:
            lex.load()
        if lex.is_ready():
            health["faiss_lexicon"] = {
                "status": "ready",
                "vectors": lex.index.ntotal,
                "dimension": lex.dimension,
            }
        else:
            health["faiss_lexicon"] = {
                "status": "missing",
                "note": "Run scripts/build_tahrirchi_faiss_index.py to build",
            }
    except Exception as e:
        health["faiss_lexicon"] = {"status": "error", "error": str(e)}

    # 6. Self-learning stats
    try:
        stats = db.get_learning_stats(since_days=7)
        health["self_learning"] = {
            "status": "active",
            "total_rules": stats.get("total_rules"),
            "learned_rules": stats.get("total_learned_rules"),
            "learning_ratio_pct": round(stats.get("learning_ratio", 0), 2),
            "actions_last_7d": stats.get("total_recent_actions"),
        }
    except Exception as e:
        health["self_learning"] = {"status": "error", "error": str(e)}

    # 7. Grammar checker (just a sanity ping)
    try:
        import grammar_checker
        gc = grammar_checker.get_checker()
        health["grammar_checker"] = {"status": "ready"}
    except Exception as e:
        health["grammar_checker"] = {"status": "error", "error": str(e)}

    # Overall status
    statuses = [v.get("status") for v in health.values() if isinstance(v, dict)]
    if all(s in ("ready", "active") for s in statuses):
        overall = "healthy"
    elif any(s == "error" for s in statuses):
        overall = "degraded"
    else:
        overall = "partial"

    return {"overall": overall, "components": health}


@router.get("/dashboard-summary")
async def dashboard_summary(current_user: Dict = Depends(get_current_user)):
    """
    Compact summary for the learning metrics dashboard widget (Phase 7).
    """
    try:
        stats_7d = db.get_learning_stats(since_days=7)
        stats_30d = db.get_learning_stats(since_days=30)

        # Recent nightly runs
        try:
            from scripts.nightly_dictionary_grow import get_recent_runs
            recent_runs = get_recent_runs(7)
        except Exception:
            recent_runs = []

        return {
            "last_7_days": stats_7d,
            "last_30_days": stats_30d,
            "recent_nightly_runs": recent_runs,
        }
    except Exception as e:
        logger.error(f"[dashboard-summary] {e}")
        raise HTTPException(status_code=500, detail=str(e))
