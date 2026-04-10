"""
Translation Memory (TM) search module.

Provides fuzzy lookup against the translation_memory table.
Used by translate endpoints to check for existing translations
before calling AI — saves tokens and improves consistency.

Usage:
    from tm_search import search_tm
    match = search_tm("Салом, қандайсиз?", src_lang="uz", tgt_lang="en")
    if match and match["score"] >= 0.85:
        return match["tgt_text"]  # exact or near-exact match
"""
import os
import sqlite3
import logging
from difflib import SequenceMatcher

log = logging.getLogger("tm_search")

DB_PATH = os.getenv("DB_PATH", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "pharma_editor.db"
))

# Minimum similarity score (0-1) to consider a TM match usable
MIN_SCORE_EXACT = 0.95    # use directly without AI
MIN_SCORE_FUZZY = 0.70    # show as suggestion alongside AI result


def _similarity(a: str, b: str) -> float:
    """Normalized similarity between two strings (0-1)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def search_tm(
    text: str,
    src_lang: str = "uz",
    tgt_lang: str = "en",
    limit: int = 5,
    min_score: float = 0.60,
) -> list:
    """Search translation_memory for matches.

    Returns list of {src_text, tgt_text, score, source} sorted by score desc.
    """
    if not text or not text.strip():
        return []

    text_clean = text.strip()
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Strategy: fetch all TM entries for this lang pair, compute similarity
        # For small TM (<10K) this is fine; for larger, switch to trigram index
        cur.execute(
            """SELECT src_text, tgt_text, source, quality_score
               FROM translation_memory
               WHERE src_lang = ? AND tgt_lang = ?""",
            (src_lang, tgt_lang),
        )
        rows = cur.fetchall()
        conn.close()

        results = []
        for row in rows:
            score = _similarity(text_clean, row["src_text"])
            if score >= min_score:
                results.append({
                    "src_text": row["src_text"],
                    "tgt_text": row["tgt_text"],
                    "score": round(score, 3),
                    "source": row["source"],
                    "quality": row["quality_score"],
                })

        results.sort(key=lambda x: -x["score"])
        return results[:limit]

    except Exception as e:
        log.error(f"TM search error: {e}")
        return []


def best_match(
    text: str,
    src_lang: str = "uz",
    tgt_lang: str = "en",
) -> dict | None:
    """Return single best TM match if score >= MIN_SCORE_FUZZY, else None."""
    matches = search_tm(text, src_lang, tgt_lang, limit=1, min_score=MIN_SCORE_FUZZY)
    return matches[0] if matches else None


def save_to_tm(
    src_text: str,
    tgt_text: str,
    src_lang: str = "uz",
    tgt_lang: str = "en",
    domain: str = "pharma",
    source: str = "user",
):
    """Save a new translation pair to TM (learn from user edits)."""
    if not src_text or not tgt_text:
        return
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """INSERT OR IGNORE INTO translation_memory
               (src_lang, src_text, tgt_lang, tgt_text, domain, source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (src_lang, src_text.strip(), tgt_lang, tgt_text.strip(), domain, source),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.error(f"TM save error: {e}")
