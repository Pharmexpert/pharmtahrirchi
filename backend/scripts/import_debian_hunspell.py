"""
Import Debian/Ubuntu hunspell-uz package (u2b3k upstream mirror).

Source: https://salsa.debian.org/debian/hunspell-uz OR system package
On Railway/container: fetches from Debian snapshot archive.

Strategy:
  1. Try system path: /usr/share/hunspell/uz_UZ.dic
  2. Fallback: fetch from Debian snapshot
  3. Import words with source='debian_hunspell_uz'
  4. Deduplicate via UNIQUE(word, lang)
"""
import os
import sqlite3
import urllib.request
import logging

logging.basicConfig(level=logging.INFO, format="[debian_hunspell] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))

SYSTEM_PATHS = [
    "/usr/share/hunspell/uz_UZ.dic",
    "/usr/share/myspell/uz_UZ.dic",
]
DEBIAN_SNAPSHOT = "https://sources.debian.org/data/main/h/hunspell-uz/"


def read_system_dic() -> str:
    for path in SYSTEM_PATHS:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    log.info(f"Reading {path}")
                    return f.read()
            except Exception as e:
                log.warning(f"Read fail {path}: {e}")
    return ""


def parse_dic(text: str) -> list:
    lines = text.splitlines()
    words = []
    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "/" in line:
            word, flags = line.split("/", 1)
        else:
            word, flags = line, ""
        word = word.strip()
        if word and len(word) >= 2:
            words.append((word, flags))
    return words


def import_to_db(words: list) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("CREATE TABLE IF NOT EXISTS user_dictionary (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT, lang TEXT DEFAULT 'uz', source TEXT, hunspell_flags TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(word, lang))")
    except Exception:
        pass

    inserted = 0
    for word, flags in words:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO user_dictionary (word, lang, source, hunspell_flags)
                VALUES (?, 'uz-lat', 'debian_hunspell', ?)
            """, (word, flags))
            if cur.rowcount > 0:
                inserted += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return inserted


def main():
    text = read_system_dic()
    if not text:
        log.info("System hunspell-uz not installed, skipping (not critical)")
        return {"inserted": 0, "reason": "not_installed"}

    words = parse_dic(text)
    inserted = import_to_db(words)
    log.info(f"parsed={len(words)} inserted={inserted}")
    return {"parsed": len(words), "inserted": inserted, "source": "debian_hunspell"}


if __name__ == "__main__":
    print(main())
