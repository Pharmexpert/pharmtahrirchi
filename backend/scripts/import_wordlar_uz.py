"""
Import elmurod1202/wordlar-uz — Uzbek word frequency list.
Adds ~100K words with frequencies to word_frequency_corpus + user_dictionary.

Source: https://huggingface.co/datasets/elmurod1202/wordlar-uz
(public dataset, tsv format: word\tfrequency)
"""
import os
import sys
import sqlite3
import logging
import urllib.request

logging.basicConfig(level=logging.INFO, format="[wordlar_uz] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))

# Fallback: use raw GitHub if HF datasets unavailable
HF_URLS = [
    "https://huggingface.co/datasets/elmurod1202/wordlar-uz/resolve/main/wordlar.txt",
    "https://huggingface.co/datasets/elmurod1202/wordlar-uz/resolve/main/wordlist.txt",
]


def ensure_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS word_frequency_corpus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            source TEXT NOT NULL,
            count INTEGER DEFAULT 1,
            lang TEXT DEFAULT 'uz',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(word, source)
        )
    """)
    try:
        cur.execute("CREATE TABLE IF NOT EXISTS user_dictionary (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT, lang TEXT DEFAULT 'uz', source TEXT, frequency INTEGER DEFAULT 0, hunspell_flags TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(word, lang))")
    except Exception:
        pass
    conn.commit()
    conn.close()


def fetch_dataset():
    """Try multiple URLs to download wordlar-uz."""
    try:
        from datasets import load_dataset
        ds = load_dataset("elmurod1202/wordlar-uz")
        return ds
    except Exception as e:
        log.warning(f"HF datasets lib failed: {e}, trying raw HTTP")

    for url in HF_URLS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pharma-expert/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                text = resp.read().decode("utf-8", errors="ignore")
                if len(text) > 1000:
                    return text
        except Exception as e:
            log.debug(f"fetch {url}: {e}")
    return None


def parse_text(text: str) -> list:
    """Parse TSV/CSV lines — word\\tfrequency or just word per line."""
    pairs = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t") if "\t" in line else line.split(",") if "," in line else line.split()
        if len(parts) >= 2:
            try:
                word = parts[0].strip()
                freq = int(float(parts[1]))
                if word and 2 <= len(word) <= 50:
                    pairs.append((word, freq))
            except Exception:
                continue
        elif len(parts) == 1:
            word = parts[0].strip()
            if word and 2 <= len(word) <= 50:
                pairs.append((word, 1))
    return pairs


def main():
    ensure_schema()

    ds = fetch_dataset()
    if ds is None:
        return {"error": "dataset unavailable — both HF datasets and raw URLs failed"}

    pairs = []
    if isinstance(ds, str):
        pairs = parse_text(ds)
    else:
        # HF dataset dict
        try:
            for split_name in ds.keys():
                for row in ds[split_name]:
                    word = row.get("word") or row.get("text") or next(iter(row.values()), None)
                    freq = row.get("frequency", 1) or row.get("count", 1) or 1
                    if word and isinstance(word, str) and 2 <= len(word) <= 50:
                        pairs.append((word, int(freq)))
        except Exception as e:
            log.warning(f"HF dataset parse failed: {e}")

    if not pairs:
        return {"error": "no pairs parsed"}

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Cap at 200K to avoid huge imports
    pairs = pairs[:200000]

    corpus_added = 0
    dict_updated = 0
    for word, freq in pairs:
        try:
            cur.execute("""
                INSERT OR REPLACE INTO word_frequency_corpus (word, source, count, lang)
                VALUES (?, 'wordlar_uz', ?, 'uz')
            """, (word, freq))
            corpus_added += 1
        except Exception:
            pass
        # Update user_dictionary frequency if word exists
        try:
            cur.execute("""
                UPDATE user_dictionary SET frequency = MAX(COALESCE(frequency, 0), ?)
                WHERE LOWER(word) = LOWER(?)
            """, (freq, word))
            if cur.rowcount > 0:
                dict_updated += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    result = {
        "corpus_added": corpus_added,
        "user_dict_updated": dict_updated,
        "total_pairs_parsed": len(pairs),
    }
    log.info(result)
    return result


if __name__ == "__main__":
    print(main())
