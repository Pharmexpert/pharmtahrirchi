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

    # 8. BERTbek POS engine (Phase 4)
    try:
        import bertbek_engine
        binfo = bertbek_engine.info()
        health["bertbek"] = {
            "status": "ready" if binfo.get("pos_loaded") else ("available" if binfo.get("available") else "disabled"),
            "enabled": binfo.get("enabled", False),
            "pos_loaded": binfo.get("pos_loaded", False),
            "pos_model": binfo.get("pos_model", ""),
        }
    except Exception as e:
        health["bertbek"] = {"status": "error", "error": str(e)}

    # 9. Mistral LLM engine (Phase 8)
    try:
        import mistral_engine
        health["mistral"] = {
            "status": "ready" if mistral_engine.is_available() else "unavailable",
            "mode": mistral_engine.get_mode(),
            "model": mistral_engine.MODEL_ID,
            "has_hf_token": bool(mistral_engine.HF_TOKEN),
        }
    except Exception as e:
        health["mistral"] = {"status": "error", "error": str(e)}

    # Overall status
    statuses = [v.get("status") for v in health.values() if isinstance(v, dict)]
    if all(s in ("ready", "active") for s in statuses):
        overall = "healthy"
    elif any(s == "error" for s in statuses):
        overall = "degraded"
    else:
        overall = "partial"

    return {"overall": overall, "components": health}


@router.post("/discover-terms")
async def discover_terms(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Phase 4: BERTbek POS → discover new NOUN/ADJ terms not yet in DB.
    Input: { text: string, lang?: string }
    Returns: { new_terms: [{term, pos, confidence}], known_count, new_count }
    """
    text = (payload.get("text") or "").strip()
    lang = payload.get("lang", "uz")
    if not text:
        return {"new_terms": [], "known_count": 0, "new_count": 0}

    # 1. POS-tag with BERTbek (or fallback to basic regex)
    tagged = []
    try:
        import bertbek_engine
        if bertbek_engine.is_available():
            tagged = bertbek_engine.tag_pos(text)
        else:
            # Fallback: extract words as NOUN candidates
            import re
            words = re.findall(r"[А-ЯЁЎҒҚҲа-яёўғқҳA-Za-z\u2018\u2019']+", text)
            tagged = [(w, "NOUN") for w in words if len(w) > 3]
    except Exception as e:
        logger.warning(f"[discover-terms] POS failed: {e}")
        import re
        words = re.findall(r"[А-ЯЁЎҒҚҲа-яёўғқҳA-Za-z\u2018\u2019']+", text)
        tagged = [(w, "NOUN") for w in words if len(w) > 3]

    # 2. Filter: only NOUN and ADJ
    candidates = [(token, pos) for token, pos in tagged if pos in ("NOUN", "ADJ", "PROPN") and len(token) > 2]

    # 3. Check against existing DB
    import sqlite3, os
    DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))
    known = set()
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for q in [
            "SELECT LOWER(term_uz) FROM annotated_words WHERE term_uz IS NOT NULL",
            "SELECT LOWER(trade_name) FROM drug_registry WHERE trade_name IS NOT NULL",
            "SELECT LOWER(inn) FROM drug_registry WHERE inn IS NOT NULL",
            "SELECT LOWER(wrong_form) FROM sayqallash_rules",
            "SELECT LOWER(correct_form) FROM sayqallash_rules",
        ]:
            try:
                cur.execute(q)
                for row in cur.fetchall():
                    if row[0]:
                        known.add(row[0].strip())
            except Exception:
                pass
        conn.close()
    except Exception:
        pass

    # 4. Separate new vs known
    new_terms = []
    known_count = 0
    seen = set()
    for token, pos in candidates:
        key = token.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        if key in known:
            known_count += 1
        else:
            new_terms.append({"term": token, "pos": pos, "confidence": 0.8})

    return {"new_terms": new_terms[:50], "known_count": known_count, "new_count": len(new_terms)}


@router.post("/approve-term")
async def approve_term(payload: Dict[str, Any], current_user: Dict = Depends(get_admin_user)):
    """Phase 4: Admin approves a new term → insert into annotated_words.
    Input: { term: string, pos?: string, category?: string, lang?: string }
    """
    term = (payload.get("term") or "").strip()
    if not term:
        raise HTTPException(status_code=400, detail="Term is required")

    category = payload.get("category", "auto-discovered")
    lang = payload.get("lang", "uz")

    import sqlite3, os
    DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT OR IGNORE INTO annotated_words (term_uz, category, source, status) VALUES (?, ?, ?, ?)",
            (term, category, "bertbek_auto", "new")
        )
        conn.commit()
        conn.close()
        return {"success": True, "term": term, "category": category}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mistral-status")
async def mistral_status(current_user: Dict = Depends(get_current_user)):
    """Phase 8: Mistral engine health check with optional connectivity probe."""
    try:
        import mistral_engine
        basic = mistral_engine.info()
        # Quick probe only if available (avoids timeout on cold start)
        if basic.get("available"):
            try:
                probe = await mistral_engine.health_check()
                return {**basic, **probe}
            except Exception as e:
                return {**basic, "status": "error", "probe_error": str(e)[:200]}
        return {**basic, "status": "unavailable"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/auto-enrich")
async def auto_enrich(payload: Dict[str, Any] = None, current_user: Dict = Depends(get_admin_user)):
    """
    Phase 4: BERTbek POS auto-enrichment of dictionary table.
    Input (optional): { words: ["word1", "word2", ...], limit: 200 }
    If no words provided, fetches words from dictionary that lack POS tags.
    Returns: { enriched: int, skipped: int, errors: int, bertbek_available: bool }
    """
    import os
    import sqlite3

    payload = payload or {}
    words = payload.get("words", [])
    limit = min(payload.get("limit", 200), 500)  # cap at 500

    # Check BERTbek availability
    try:
        import bertbek_engine
        bertbek_ok = bertbek_engine.is_available()
    except Exception:
        bertbek_ok = False

    if not bertbek_ok:
        return {
            "enriched": 0, "skipped": 0, "errors": 0,
            "bertbek_available": False,
            "message": "BERTbek not available (BERTBEK_ENABLED=0 or transformers missing)"
        }

    DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))

    # If no words provided, fetch from dictionary where pos is NULL or empty
    if not words:
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                "SELECT word FROM dictionary WHERE (pos IS NULL OR pos = '' OR pos = 'unknown') AND word IS NOT NULL LIMIT ?",
                (limit,)
            )
            words = [row[0] for row in cur.fetchall() if row[0] and row[0].strip()]
            conn.close()
        except Exception as e:
            logger.error(f"[auto-enrich] Failed to fetch words: {e}")
            raise HTTPException(status_code=500, detail=f"DB fetch failed: {e}")

    if not words:
        return {"enriched": 0, "skipped": 0, "errors": 0, "bertbek_available": True, "message": "No words need enrichment"}

    # POS-tag in batches (group words into short sentences for efficiency)
    enriched = 0
    skipped = 0
    errors = 0
    pos_results: Dict[str, str] = {}

    BATCH_SIZE = 20
    for i in range(0, len(words), BATCH_SIZE):
        batch = words[i:i + BATCH_SIZE]
        text = " ".join(batch)
        try:
            tagged = bertbek_engine.tag_pos(text)
            for token, pos in tagged:
                key = token.lower().strip()
                if pos and pos != "X" and key:
                    pos_results[key] = pos
        except Exception as e:
            logger.warning(f"[auto-enrich] Batch {i} failed: {e}")
            errors += len(batch)

    # Update dictionary table
    if pos_results:
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            for word_key, pos in pos_results.items():
                try:
                    cur.execute(
                        "UPDATE dictionary SET pos = ? WHERE LOWER(word) = ? AND (pos IS NULL OR pos = '' OR pos = 'unknown')",
                        (pos, word_key)
                    )
                    if cur.rowcount > 0:
                        enriched += cur.rowcount
                    else:
                        skipped += 1
                except Exception:
                    errors += 1
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[auto-enrich] DB update failed: {e}")
            raise HTTPException(status_code=500, detail=f"DB update failed: {e}")

    logger.info(f"[auto-enrich] Done: enriched={enriched}, skipped={skipped}, errors={errors}")
    return {
        "enriched": enriched,
        "skipped": skipped,
        "errors": errors,
        "bertbek_available": True,
        "words_processed": len(words),
    }


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
