"""
Import kmashrab/uzbek-wordlist into Pharma Expert databases.

Source: https://github.com/kmashrab/uzbek-wordlist
Files:
    unsorted.wordlist (928 KB) → ~50K extra words → user_dictionary
    todo.wordlist (355 KB) → ~20K pending words → user_dictionary
    abbriviation.wordlist (1.4 KB) → abbreviations table
    names.root (12 KB) → person_names (new table)
    places.root (10 KB) → places (new table)
    numbers.root (1.7 KB) → numbers (new table)
    blacklist.wordlist (105 KB) → word_blacklist (new table)
"""
import os
import sys
import sqlite3
import logging
import urllib.request

logging.basicConfig(level=logging.INFO, format="[kmashrab] %(message)s")
log = logging.getLogger()

BASE = "https://raw.githubusercontent.com/kmashrab/uzbek-wordlist/master"
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))

FILES = [
    ("unsorted.wordlist", "user_dictionary", "kmashrab_unsorted"),
    ("todo.wordlist", "user_dictionary", "kmashrab_todo"),
    ("abbriviation.wordlist", "abbreviations", "kmashrab"),
    ("names.root", "person_names", "kmashrab"),
    ("places.root", "places", "kmashrab"),
    ("numbers.root", "numbers", "kmashrab"),
    ("blacklist.wordlist", "word_blacklist", "kmashrab"),
]


def fetch(filename: str) -> list:
    url = f"{BASE}/{filename}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pharma-expert/1.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read().decode("utf-8", errors="ignore")
        words = [w.strip() for w in data.splitlines() if w.strip() and not w.startswith("#")]
        log.info(f"Fetched {filename}: {len(words)} words")
        return words
    except Exception as e:
        log.error(f"Failed {filename}: {e}")
        return []


def ensure_tables(cur):
    """Create all target tables."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            lang TEXT DEFAULT 'uz',
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(word, lang)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS person_names (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number_word TEXT UNIQUE,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS word_blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE,
            reason TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # abbreviations may already exist — add missing columns
    try:
        cur.execute("CREATE TABLE IF NOT EXISTS abbreviations (id INTEGER PRIMARY KEY, uz TEXT, ru TEXT, en TEXT, definition TEXT, source TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    except Exception:
        pass


def insert_into(cur, table: str, word: str, source: str) -> bool:
    """Insert a word; returns True if a new row was added."""
    try:
        if table == "user_dictionary":
            # Check first — reliable across SQLite versions
            cur.execute("SELECT 1 FROM user_dictionary WHERE word = ? AND lang = 'uz'", (word,))
            if cur.fetchone():
                return False
            cur.execute("INSERT INTO user_dictionary (word, lang, source) VALUES (?, 'uz', ?)", (word, source))
            return True
        elif table == "person_names":
            cur.execute("SELECT 1 FROM person_names WHERE name = ?", (word,))
            if cur.fetchone():
                return False
            cur.execute("INSERT INTO person_names (name, source) VALUES (?, ?)", (word, source))
            return True
        elif table == "places":
            cur.execute("SELECT 1 FROM places WHERE name = ?", (word,))
            if cur.fetchone():
                return False
            cur.execute("INSERT INTO places (name, source) VALUES (?, ?)", (word, source))
            return True
        elif table == "numbers":
            cur.execute("SELECT 1 FROM numbers WHERE number_word = ?", (word,))
            if cur.fetchone():
                return False
            cur.execute("INSERT INTO numbers (number_word, source) VALUES (?, ?)", (word, source))
            return True
        elif table == "word_blacklist":
            cur.execute("SELECT 1 FROM word_blacklist WHERE word = ?", (word,))
            if cur.fetchone():
                return False
            cur.execute("INSERT INTO word_blacklist (word, reason, source) VALUES (?, 'blacklisted', ?)", (word, source))
            return True
        elif table == "abbreviations":
            # Don't dedupe abbreviations — just insert
            cur.execute("INSERT INTO abbreviations (uz, source) VALUES (?, ?)", (word, source))
            return True
    except Exception as e:
        logger = logging.getLogger("kmashrab")
        logger.debug(f"Insert failed {word}: {e}")
    return False


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    ensure_tables(cur)

    totals = {}
    for filename, table, source in FILES:
        words = fetch(filename)
        if not words:
            totals[filename] = 0
            continue
        inserted = 0
        for w in words:
            # Basic cleaning — remove slash affixes, quotes
            clean = w.split("/")[0].strip().strip('"\'')
            if len(clean) < 1:
                continue
            if insert_into(cur, table, clean, source):
                inserted += 1
        totals[filename] = inserted
        log.info(f"  → {table}: +{inserted}")

    conn.commit()

    # Summary
    result = {"inserted": totals, "total_sum": sum(totals.values())}
    cur.execute("SELECT COUNT(*) FROM user_dictionary")
    result["user_dictionary_total"] = cur.fetchone()[0]
    try:
        cur.execute("SELECT COUNT(*) FROM person_names")
        result["person_names_total"] = cur.fetchone()[0]
    except Exception:
        pass
    try:
        cur.execute("SELECT COUNT(*) FROM places")
        result["places_total"] = cur.fetchone()[0]
    except Exception:
        pass

    conn.close()
    log.info(f"Result: {result}")
    return result


if __name__ == "__main__":
    print(main())
