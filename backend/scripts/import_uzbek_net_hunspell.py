"""
Import uzbek-net/uz-hunspell (updated fork of u2b3k with LibreOffice + tests).

Source: https://github.com/uzbek-net/uz-hunspell
Files:
  - uz_UZ.dic        (Latin, expanded)
  - uz_UZ.aff        (Latin)
  - uz_UZ_Cyrl.dic   (Cyrillic)
  - uz_UZ_Cyrl.aff   (Cyrillic)

Strategy:
  1. Download both Latin and Cyrillic dictionaries
  2. Import to user_dictionary with proper lang tags (uz-lat / uz-cyr)
  3. source='uzbek_net_hunspell'
"""
import os
import sqlite3
import urllib.request
import logging

logging.basicConfig(level=logging.INFO, format="[uzbek_net] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))

BASE = "https://raw.githubusercontent.com/uzbek-net/uz-hunspell/master"
CANDIDATES = [
    ("uz_UZ.dic", "uz-lat"),
    ("uz_UZ_Cyrl.dic", "uz-cyr"),
    # Fallback branch names
]
BRANCHES = ["master", "main"]


def fetch(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pharma-expert/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def fetch_with_fallback(filename: str) -> str:
    for branch in BRANCHES:
        url = f"https://raw.githubusercontent.com/uzbek-net/uz-hunspell/{branch}/{filename}"
        text = fetch(url)
        if text:
            log.info(f"Fetched {filename} from {branch}")
            return text
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


def import_to_db(words: list, lang: str) -> int:
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
                VALUES (?, ?, 'uzbek_net_hunspell', ?)
            """, (word, lang, flags))
            if cur.rowcount > 0:
                inserted += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return inserted


def main():
    total = {}
    for fname, lang in CANDIDATES:
        text = fetch_with_fallback(fname)
        if not text:
            log.warning(f"Skip {fname} — not found")
            continue
        words = parse_dic(text)
        inserted = import_to_db(words, lang)
        total[fname] = {"parsed": len(words), "inserted": inserted, "lang": lang}
        log.info(f"{fname}: parsed={len(words)} inserted={inserted}")
    return total


if __name__ == "__main__":
    print(main())
