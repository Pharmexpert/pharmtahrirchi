"""
Phase 6: Nightly dictionary growth job.

Runs every night at 03:00 (Tashkent time) and:
  1. Aggregates new "learned" rules from sayqallash_rules
  2. Adds their correct_form into tahrirchi.db dictionary if missing
  3. Computes BERT embeddings for any rules still missing them
  4. Adds them to the in-memory FAISS index
  5. Records growth statistics in dictionary_stats table
  6. Logs the run to learning_log

Designed to be triggered by:
    - Railway cron job (recommended)
    - Or in-process APScheduler (when WORKER_MODE=app)
    - Or manual: `python scripts/nightly_dictionary_grow.py`
"""
from __future__ import annotations

import os
import sqlite3
import logging
import time
import sys
from datetime import datetime, timedelta

# Make backend root importable when run as standalone script
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import db  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("nightly_grow")


def ensure_stats_table():
    """Create dictionary_stats table if missing."""
    conn = db.connect_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS dictionary_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_date TEXT,                       -- YYYY-MM-DD
            tahrirchi_total INTEGER DEFAULT 0,   -- total words after run
            tahrirchi_added INTEGER DEFAULT 0,   -- new words added
            rules_total INTEGER DEFAULT 0,
            rules_indexed INTEGER DEFAULT 0,     -- rules that got BERT vectors this run
            rules_learned INTEGER DEFAULT 0,
            learning_actions_24h INTEGER DEFAULT 0,
            duration_sec REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def grow_dictionary(window_hours: int = 24) -> dict:
    """
    Main growth routine. Returns a dict with the run summary.

    window_hours: Look at rules / learning events from last N hours.
    """
    start = time.time()
    logger.info("=" * 60)
    logger.info(f"[NIGHTLY] Starting dictionary growth run (window={window_hours}h)")
    logger.info("=" * 60)

    ensure_stats_table()
    summary = {
        "started_at": datetime.utcnow().isoformat(),
        "window_hours": window_hours,
        "tahrirchi_added": 0,
        "tahrirchi_total": 0,
        "rules_indexed_with_bert": 0,
        "rules_total": 0,
        "rules_learned": 0,
        "learning_actions_24h": 0,
        "errors": [],
    }

    conn = db.connect_db()
    cur = conn.cursor()

    # ───────────── Step 1: Recent learned rules ─────────────
    since = (datetime.utcnow() - timedelta(hours=window_hours)).isoformat()
    cur.execute(
        """
        SELECT id, wrong_form, correct_form, lang
        FROM sayqallash_rules
        WHERE source = 'learned' AND updated_at > ?
        """,
        (since,),
    )
    recent_rules = cur.fetchall()
    summary["rules_learned"] = len(recent_rules)
    logger.info(f"[NIGHTLY] Found {len(recent_rules)} learned rules in last {window_hours}h")

    # ───────────── Step 2: Add correct forms to tahrirchi.db ─────────────
    if os.path.exists(db.TAHRIRCHI_DB_PATH) and recent_rules:
        try:
            dict_conn = sqlite3.connect(db.TAHRIRCHI_DB_PATH)
            dict_cur = dict_conn.cursor()
            added = 0
            for _, wrong, correct, lang in recent_rules:
                if not correct or lang != "uz":
                    continue
                cf = correct.strip().lower()
                if not cf:
                    continue
                dict_cur.execute("SELECT 1 FROM dictionary WHERE word = ? LIMIT 1", (cf,))
                if not dict_cur.fetchone():
                    dict_cur.execute(
                        """
                        INSERT OR IGNORE INTO dictionary (word, frequency, source, is_confirmed)
                        VALUES (?, 1, 'pharma_learned', 1)
                        """,
                        (cf,),
                    )
                    added += 1
            dict_conn.commit()

            dict_cur.execute("SELECT COUNT(*) FROM dictionary")
            total = dict_cur.fetchone()[0]
            dict_conn.close()

            summary["tahrirchi_added"] = added
            summary["tahrirchi_total"] = total
            logger.info(f"[NIGHTLY] tahrirchi.db: +{added} words (total now {total:,})")
        except Exception as e:
            logger.error(f"[NIGHTLY] tahrirchi update failed: {e}")
            summary["errors"].append(f"tahrirchi: {e}")
    else:
        logger.warning("[NIGHTLY] tahrirchi.db not available — skipping lexicon update")

    # ───────────── Step 3: Compute BERT vectors for rules missing them ─────────────
    try:
        import bert_engine
        if not bert_engine.engine.initialized:
            logger.warning("[NIGHTLY] BERT engine not yet initialized — skipping vector indexing")
        else:
            cur.execute(
                "SELECT id, wrong_form FROM sayqallash_rules WHERE vector IS NULL"
            )
            missing = cur.fetchall()
            indexed = 0
            for rid, wrong in missing:
                if not wrong:
                    continue
                emb = bert_engine.engine.get_embedding(wrong.strip().lower(), as_numpy=True)
                if emb is None:
                    continue
                import pickle  # noqa
                emb_bytes = pickle.dumps(emb)
                cur.execute(
                    "UPDATE sayqallash_rules SET vector = ? WHERE id = ?",
                    (emb_bytes, rid),
                )
                # Add to FAISS in-memory index
                try:
                    db.faiss_manager.add_rule(rid, emb_bytes)
                except Exception as e:
                    logger.debug(f"FAISS add error: {e}")
                indexed += 1
                if indexed % 50 == 0:
                    logger.info(f"[NIGHTLY] BERT-indexed {indexed}/{len(missing)} rules...")
            conn.commit()
            summary["rules_indexed_with_bert"] = indexed
            logger.info(f"[NIGHTLY] BERT-indexed {indexed} new rule vectors")
    except Exception as e:
        logger.error(f"[NIGHTLY] BERT indexing failed: {e}")
        summary["errors"].append(f"bert: {e}")

    # ───────────── Step 4: Snapshot stats ─────────────
    cur.execute("SELECT COUNT(*) FROM sayqallash_rules")
    summary["rules_total"] = cur.fetchone()[0]

    try:
        cur.execute(
            f"SELECT COUNT(*) FROM learning_log WHERE created_at > datetime('now', '-{int(window_hours)} hours')"
        )
        summary["learning_actions_24h"] = cur.fetchone()[0]
    except Exception:
        summary["learning_actions_24h"] = 0

    duration = time.time() - start

    # ───────────── Step 5: Save run summary ─────────────
    try:
        cur.execute(
            """
            INSERT INTO dictionary_stats (
                run_date, tahrirchi_total, tahrirchi_added,
                rules_total, rules_indexed, rules_learned,
                learning_actions_24h, duration_sec
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().strftime("%Y-%m-%d"),
                summary["tahrirchi_total"],
                summary["tahrirchi_added"],
                summary["rules_total"],
                summary["rules_indexed_with_bert"],
                summary["rules_learned"],
                summary["learning_actions_24h"],
                duration,
            ),
        )
        conn.commit()
    except Exception as e:
        logger.error(f"[NIGHTLY] Failed to save run summary: {e}")
        summary["errors"].append(f"stats_save: {e}")

    conn.close()

    summary["duration_sec"] = duration
    summary["finished_at"] = datetime.utcnow().isoformat()

    logger.info("=" * 60)
    logger.info(f"[NIGHTLY] Run complete in {duration:.1f}s")
    logger.info(f"    +{summary['tahrirchi_added']} words to tahrirchi.db (total {summary['tahrirchi_total']:,})")
    logger.info(f"    +{summary['rules_indexed_with_bert']} rule vectors BERT-indexed")
    logger.info(f"    {summary['rules_learned']} rules learned in last {window_hours}h")
    logger.info(f"    {summary['learning_actions_24h']} learning actions logged")
    logger.info(f"    Errors: {len(summary['errors'])}")
    logger.info("=" * 60)

    return summary


def get_recent_runs(limit: int = 30) -> list:
    """Return last N nightly runs for dashboard charts."""
    ensure_stats_table()
    conn = db.connect_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM dictionary_stats ORDER BY id DESC LIMIT ?",
        (int(limit),),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    grow_dictionary(window_hours=24)
