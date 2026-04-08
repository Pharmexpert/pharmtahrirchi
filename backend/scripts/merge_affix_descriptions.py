"""
Merge uzhungen .qoida descriptions into affix_flags table.

Strategy:
  - affix_flags table (Hunspell SFX flags) has flag letters (A, B, C, ...)
  - hunspell_affix_descriptions (from .qoida) has semantic names (EGALIK, KELISHIK, ...)
  - Our FLAG_DESCRIPTIONS mapping in hunspell_data.py links them

This script:
  1. Reads hunspell_affix_descriptions
  2. For each flag, builds a rich description from rule_name + suffix + condition
  3. Updates affix_flags.description field OR creates mapping table

The result: each Hunspell flag in our DB has a human-readable description
from the uzhungen .qoida source.
"""
import os
import sqlite3
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="[merge_affix] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))

# Semantic flag names → Hunspell flag letters (from u2b3k naming convention)
# These are heuristic — real mapping depends on the actual .qoida definitions
SEMANTIC_TO_FLAG = {
    "EGALIK": "B",      # 1-шахс эгалик
    "KELISHIK": "H",    # Ҳол/келишик
    "KOPLIK": "N",      # Кўплик
    "OZLIK": "J",       # Ўзлик (reflexive)
    "SIFAT": "A",       # Сифат
    "FEL": "F",         # Феъл
    "ORTTIRMA": "R",    # Орттирма даража
}


def ensure_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # affix_flag_mapping: semantic name ↔ flag letter(s)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS affix_flag_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            semantic_name TEXT NOT NULL,
            flag_letter TEXT,
            description_uz TEXT,
            rule_count INTEGER DEFAULT 0,
            examples TEXT,
            source TEXT DEFAULT 'uzhungen',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(semantic_name)
        )
    """)
    conn.commit()
    conn.close()


def main():
    ensure_schema()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Check source table exists
    try:
        cur.execute("SELECT COUNT(*) FROM hunspell_affix_descriptions")
        total = cur.fetchone()[0]
    except Exception:
        log.warning("hunspell_affix_descriptions not populated — run import_uzhungen_qoida first")
        conn.close()
        return {"error": "no source data"}

    if total == 0:
        log.warning("hunspell_affix_descriptions is empty")
        conn.close()
        return {"error": "empty source"}

    log.info(f"Source has {total} rule descriptions")

    # Group by semantic flag name
    cur.execute("""
        SELECT flag, rule_name, suffix, condition
        FROM hunspell_affix_descriptions
        ORDER BY flag, rule_name
    """)
    grouped = defaultdict(list)
    for flag, rule_name, suffix, condition in cur.fetchall():
        grouped[flag].append((rule_name, suffix, condition))

    # Build descriptions
    inserted = 0
    for semantic_name, rules in grouped.items():
        # Description: concatenate sample rules
        examples = []
        for rule_name, suffix, condition in rules[:5]:
            examples.append(f"{rule_name}={suffix}" + (f" ({condition})" if condition else ""))
        desc = f"Ўзбек тили {semantic_name.lower()} қўшимчалари. Намуналар: " + ", ".join(examples)

        flag_letter = SEMANTIC_TO_FLAG.get(semantic_name, "")
        try:
            cur.execute("""
                INSERT OR REPLACE INTO affix_flag_mapping
                (semantic_name, flag_letter, description_uz, rule_count, examples, source)
                VALUES (?, ?, ?, ?, ?, 'uzhungen')
            """, (semantic_name, flag_letter, desc, len(rules), "; ".join(examples)))
            inserted += 1
        except Exception as e:
            log.warning(f"insert fail {semantic_name}: {e}")

    conn.commit()
    conn.close()

    result = {
        "source_rules": total,
        "semantic_flags_found": len(grouped),
        "mappings_created": inserted,
        "flags": list(grouped.keys()),
    }
    log.info(f"Done: {result}")
    return result


if __name__ == "__main__":
    print(main())
