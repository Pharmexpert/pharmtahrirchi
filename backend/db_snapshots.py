"""
Lightweight time-series snapshots for DB tables — enables sparkline charts.

Storage: db_size_snapshots (table_name, count, created_at)
Snapshots are throttled to 1 per hour per table.
"""
import os
import sqlite3
import logging
from datetime import datetime, timedelta

log = logging.getLogger("db_snapshots")

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))

TRACKED_TABLES = [
    "user_dictionary",
    "sayqallash_rules",
    "syntax_phrases",
    "syntax_parsed_sentences",
    "syntax_sentence_templates",
    "syntax_word_order_rules",
    "translation_memory",
    "word_frequency_corpus",
    "hunspell_affix_descriptions",
    "projects",
    "dashboard",
]


def ensure_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS db_size_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            count INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_dss_table ON db_size_snapshots(table_name, created_at)")
    conn.commit()
    conn.close()


def take_snapshot(throttle_hours: int = 1) -> dict:
    """Snapshot current counts. Throttled: skip if last snapshot is newer than throttle_hours."""
    ensure_schema()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cutoff = (datetime.utcnow() - timedelta(hours=throttle_hours)).isoformat(" ")
    cur.execute("SELECT MAX(created_at) FROM db_size_snapshots")
    last = cur.fetchone()[0]
    if last and last >= cutoff:
        conn.close()
        return {"skipped": True, "reason": "throttled", "last": last}

    taken = {}
    for table in TRACKED_TABLES:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
        except Exception:
            continue
        try:
            cur.execute("""
                INSERT INTO db_size_snapshots (table_name, count)
                VALUES (?, ?)
            """, (table, count))
            taken[table] = count
        except Exception:
            pass

    conn.commit()
    conn.close()
    return {"snapshotted": taken, "count": len(taken)}


def get_history(limit_per_table: int = 20) -> dict:
    """Get last N snapshots per table for sparkline display."""
    ensure_schema()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    result: dict = {}
    for table in TRACKED_TABLES:
        try:
            cur.execute("""
                SELECT count, created_at FROM db_size_snapshots
                WHERE table_name = ?
                ORDER BY created_at DESC LIMIT ?
            """, (table, limit_per_table))
            rows = list(reversed(cur.fetchall()))  # chronological
            result[table] = [{"count": r[0], "at": r[1]} for r in rows]
        except Exception:
            result[table] = []
    conn.close()
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(take_snapshot(throttle_hours=0))
    print(get_history())
