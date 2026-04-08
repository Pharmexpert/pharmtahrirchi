"""
Import MUNIS soros dictionary + QuvonchbekBobojonov uzwords into Pharma Expert.

Sources:
    1. uzbek-spell/spellchecker (MUNIS REP-2/6) — official government-funded Uzbek Hunspell
    2. QuvonchbekBobojonov/Uzbek-language — Python package with 646 KB + 395 KB wordlists
"""
import os
import sys
import sqlite3
import logging
import urllib.request
import re

logging.basicConfig(level=logging.INFO, format="[extra_dicts] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))
HUNSPELL_DIR = os.getenv("HUNSPELL_V2_PATH", "/app/data/hunspell")


def fetch_raw(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pharma-expert/1.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        log.warning(f"Fetch failed {url}: {e}")
        return ""


def fetch_binary(url: str, dest: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pharma-expert/1.0"})
        with urllib.request.urlopen(req, timeout=120) as response:
            data = response.read()
        with open(dest, "wb") as f:
            f.write(data)
        log.info(f"Downloaded {os.path.basename(dest)} ({len(data)//1024} KB)")
        return True
    except Exception as e:
        log.warning(f"Failed download {url}: {e}")
        return False


# ─────────────────────────────────────────────
# 1. MUNIS soros dictionary
# ─────────────────────────────────────────────
def import_munis():
    """Download MUNIS soros .dic/.aff files if present."""
    os.makedirs(HUNSPELL_DIR, exist_ok=True)
    base = "https://raw.githubusercontent.com/uzbek-spell/spellchecker/master/soros"
    # Try common filenames
    candidates = [
        ("uz_UZ.dic", "munis_uz_UZ.dic"),
        ("uz_UZ.aff", "munis_uz_UZ.aff"),
        ("uz.dic", "munis_uz.dic"),
        ("uz.aff", "munis_uz.aff"),
        ("dictionary.dic", "munis_dict.dic"),
        ("dictionary.aff", "munis_dict.aff"),
    ]
    downloaded = 0
    for remote, local_name in candidates:
        url = f"{base}/{remote}"
        dest = os.path.join(HUNSPELL_DIR, local_name)
        if os.path.exists(dest):
            continue
        if fetch_binary(url, dest):
            downloaded += 1
    return {"munis_files_downloaded": downloaded}


def load_munis_words() -> list:
    """Parse any MUNIS .dic file and return word list."""
    words = []
    for fname in os.listdir(HUNSPELL_DIR) if os.path.exists(HUNSPELL_DIR) else []:
        if fname.startswith("munis_") and fname.endswith(".dic"):
            try:
                with open(os.path.join(HUNSPELL_DIR, fname), encoding="utf-8", errors="ignore") as f:
                    lines = f.read().splitlines()
                # First line is count; rest are "word[/FLAGS]"
                for line in lines[1:]:
                    w = line.split("/")[0].strip()
                    if w and len(w) > 1:
                        words.append(w)
            except Exception:
                pass
    return words


# ─────────────────────────────────────────────
# 2. QuvonchbekBobojonov uzwords extraction
# ─────────────────────────────────────────────
def import_quvonchbek():
    """
    Extract word lists from QuvonchbekBobojonov Python package.
    uzwords.py and uzwords_latin.py contain words = [...] format.
    """
    urls = [
        ("uzwords.py", "uzbek_language/uzwords.py"),
        ("uzwords_latin.py", "uzbek_language/uzwords_latin.py"),
    ]
    base = "https://raw.githubusercontent.com/QuvonchbekBobojonov/Uzbek-language/main"

    all_words = []
    # Simple pattern: match any quoted string with 1+ characters
    pattern = re.compile(r'"([^"]{1,60})"')

    for name, path in urls:
        url = f"{base}/{path}"
        content = fetch_raw(url)
        if not content:
            continue
        matches = pattern.findall(content)
        # Filter: valid Uzbek words (Cyrillic or Latin)
        valid = [m for m in matches if len(m) >= 2 and not any(c in m for c in ['=', '(', ')', '[', ']', '\\', '\n'])]
        log.info(f"  {name}: extracted {len(valid)} words (from {len(matches)} strings)")
        all_words.extend(valid)

    return all_words


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
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
    # Migrate: add source column if missing
    try:
        cur.execute("ALTER TABLE user_dictionary ADD COLUMN source TEXT")
    except Exception:
        pass

    result = {}

    # MUNIS
    log.info("=== MUNIS soros ===")
    munis_dl = import_munis()
    result.update(munis_dl)
    munis_words = load_munis_words()
    munis_inserted = 0
    for w in munis_words:
        try:
            cur.execute("INSERT OR IGNORE INTO user_dictionary (word, lang, source) VALUES (?, 'uz', 'munis_soros')", (w,))
            if cur.rowcount > 0:
                munis_inserted += 1
        except Exception:
            pass
    result["munis_words_inserted"] = munis_inserted
    log.info(f"MUNIS: +{munis_inserted} words")

    # QuvonchbekBobojonov
    log.info("=== QuvonchbekBobojonov ===")
    qb_words = import_quvonchbek()
    qb_inserted = 0
    for w in qb_words:
        if len(w) < 2 or len(w) > 40:
            continue
        try:
            cur.execute("INSERT OR IGNORE INTO user_dictionary (word, lang, source) VALUES (?, 'uz', 'quvonchbek_bobojonov')", (w,))
            if cur.rowcount > 0:
                qb_inserted += 1
        except Exception:
            pass
    result["quvonchbek_words_inserted"] = qb_inserted
    log.info(f"QuvonchbekBobojonov: +{qb_inserted} words")

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM user_dictionary")
    result["user_dictionary_total"] = cur.fetchone()[0]
    conn.close()

    log.info(f"Final: {result}")
    return result


if __name__ == "__main__":
    print(main())
