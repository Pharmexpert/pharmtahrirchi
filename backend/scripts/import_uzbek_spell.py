"""
Import uzbek-spell/spellchecker v1.0 (Latin .aff + .dic) to our DB.

Source: https://github.com/uzbek-spell/spellchecker/releases/tag/v1.0
Files:
  - uz_Latn_UZ.aff  (Hunspell affix file, Latin)
  - uz_Latn_UZ.dic  (Hunspell dictionary, Latin)

Strategy:
  1. Download raw files from GitHub
  2. Parse .dic (word/flags format)
  3. Insert into user_dictionary with source='uzbek_spell_latn'
  4. Skip existing (idempotent)
"""
import os
import sys
import sqlite3
import urllib.request
import logging

logging.basicConfig(level=logging.INFO, format="[uzbek_spell] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))

BASE = "https://raw.githubusercontent.com/uzbek-spell/spellchecker/main"
FILES = {
    "dic": f"{BASE}/uz_Latn_UZ.dic",
    "aff": f"{BASE}/uz_Latn_UZ.aff",
}


def fetch(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pharma-expert/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        log.warning(f"Fetch failed {url}: {e}")
        return ""


def parse_dic(text: str) -> list:
    """Hunspell .dic format: first line is count, rest are 'word' or 'word/flags'."""
    lines = text.splitlines()
    if not lines:
        return []
    words = []
    for line in lines[1:]:  # skip count header
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # split "word/flags" or just "word"
        if "/" in line:
            word, flags = line.split("/", 1)
        else:
            word, flags = line, ""
        word = word.strip()
        if word and len(word) >= 2:
            words.append((word, flags))
    return words


def import_to_db(words: list, lang: str = "uz-lat") -> int:
    """Insert into user_dictionary, skipping duplicates."""
    if not words:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Ensure schema
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_dictionary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                lang TEXT DEFAULT 'uz',
                source TEXT DEFAULT 'user',
                hunspell_flags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(word, lang)
            )
        """)
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE user_dictionary ADD COLUMN hunspell_flags TEXT")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE user_dictionary ADD COLUMN source TEXT DEFAULT 'user'")
    except Exception:
        pass

    inserted = 0
    for word, flags in words:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO user_dictionary (word, lang, source, hunspell_flags)
                VALUES (?, ?, 'uzbek_spell_latn', ?)
            """, (word, lang, flags))
            if cur.rowcount > 0:
                inserted += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    return inserted


def main():
    log.info("Fetching uzbek-spell/spellchecker v1.0...")
    dic_text = fetch(FILES["dic"])
    if not dic_text:
        log.warning("Could not fetch .dic file")
        return {"inserted": 0, "error": "fetch failed"}

    words = parse_dic(dic_text)
    log.info(f"Parsed {len(words)} words")

    inserted = import_to_db(words)
    log.info(f"Inserted {inserted} new words")

    return {"parsed": len(words), "inserted": inserted, "source": "uzbek_spell_latn"}


if __name__ == "__main__":
    print(main())
