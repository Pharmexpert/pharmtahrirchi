"""
Sayqallash DB cleanup — weekly cron task.

Removes exact duplicates and low-confidence rules.
Run: python scripts/sayqallash_cleanup.py
"""
import os
import sys
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[sayqallash_cleanup] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))


def cleanup():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Count before
    cur.execute("SELECT COUNT(*) FROM sayqallash_rules")
    before = cur.fetchone()[0]
    log.info(f"Before: {before} rules")

    # 1. Remove EXACT duplicates (keep highest frequency)
    cur.execute("""
        DELETE FROM sayqallash_rules
        WHERE id NOT IN (
            SELECT MAX(id) FROM sayqallash_rules
            GROUP BY LOWER(wrong_form), LOWER(correct_form), lang
        )
    """)
    dupes_removed = cur.rowcount
    log.info(f"Duplicates removed: {dupes_removed}")

    # 2. Remove rules where wrong_form == correct_form (no-op rules)
    cur.execute("DELETE FROM sayqallash_rules WHERE LOWER(wrong_form) = LOWER(correct_form)")
    noop_removed = cur.rowcount
    log.info(f"No-op rules removed: {noop_removed}")

    # 3. Remove empty rules
    cur.execute("DELETE FROM sayqallash_rules WHERE wrong_form IS NULL OR wrong_form = '' OR correct_form IS NULL OR correct_form = ''")
    empty_removed = cur.rowcount
    log.info(f"Empty rules removed: {empty_removed}")

    # 4. Remove very short wrong forms (< 2 chars)
    cur.execute("DELETE FROM sayqallash_rules WHERE LENGTH(wrong_form) < 2")
    short_removed = cur.rowcount
    log.info(f"Too-short rules removed: {short_removed}")

    # Compact
    cur.execute("VACUUM")

    cur.execute("SELECT COUNT(*) FROM sayqallash_rules")
    after = cur.fetchone()[0]
    log.info(f"After: {after} rules (removed {before - after})")

    conn.commit()
    conn.close()

    return {
        "before": before,
        "after": after,
        "removed": before - after,
        "duplicates": dupes_removed,
        "noop": noop_removed,
        "empty": empty_removed,
        "short": short_removed,
    }


if __name__ == "__main__":
    try:
        result = cleanup()
        print(result)
        sys.exit(0)
    except Exception as e:
        log.error(f"Cleanup failed: {e}")
        sys.exit(1)
