"""
Build word frequency rankings from corpus data.

Sources:
  1. uz_crawl_corpus (Tahrirchi news + telegram blogs)
  2. translation_memory (source_text + target_text)
  3. syntax_parsed_sentences
  4. dashboard (confirmed_uz_text)

Output:
  - Adds `frequency` column to user_dictionary (if missing)
  - Updates frequency counts for each word
  - Creates word_frequency_corpus table for raw counts per source
"""
import os
import sqlite3
import re
import logging
from collections import Counter

logging.basicConfig(level=logging.INFO, format="[freq_rankings] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))

WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁўЎқҚғҒҳҲ'ʻ]+", re.UNICODE)


def tokenize(text: str) -> list:
    if not text:
        return []
    return [w.lower() for w in WORD_RE.findall(text) if len(w) >= 2]


def ensure_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE user_dictionary ADD COLUMN frequency INTEGER DEFAULT 0")
    except Exception:
        pass
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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_wfc_word ON word_frequency_corpus(word)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_wfc_source ON word_frequency_corpus(source)")
    conn.commit()
    conn.close()


def collect_from_table(cur, table: str, columns: list, source_label: str) -> Counter:
    counter = Counter()
    for col in columns:
        try:
            cur.execute(f"SELECT {col} FROM {table} WHERE {col} IS NOT NULL")
            for row in cur.fetchall():
                text = row[0] or ""
                for w in tokenize(text):
                    counter[w] += 1
        except Exception as e:
            log.debug(f"{table}.{col}: {e}")
    log.info(f"{source_label}: {len(counter)} uniq words, total tokens {sum(counter.values())}")
    return counter


def main(min_count: int = 2):
    ensure_schema()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Collect from all corpus sources
    counters = {}
    counters["uz_crawl"] = collect_from_table(cur, "uz_crawl_corpus", ["text"], "uz_crawl_corpus")
    counters["translation_memory"] = collect_from_table(cur, "translation_memory", ["source_text", "target_text"], "translation_memory")
    counters["syntax_parsed"] = collect_from_table(cur, "syntax_parsed_sentences", ["text"], "syntax_parsed_sentences")
    counters["dashboard"] = collect_from_table(cur, "dashboard", ["confirmed_uz_text", "uz_v1"], "dashboard")

    # 2. Global merge
    global_counter = Counter()
    for c in counters.values():
        global_counter.update(c)

    # 3. Write per-source to word_frequency_corpus
    inserted_corpus = 0
    for source, counter in counters.items():
        for word, count in counter.items():
            if count < min_count:
                continue
            try:
                cur.execute("""
                    INSERT OR REPLACE INTO word_frequency_corpus (word, source, count)
                    VALUES (?, ?, ?)
                """, (word, source, count))
                inserted_corpus += 1
            except Exception:
                pass

    # 4. Update user_dictionary.frequency with global counts
    updated = 0
    for word, count in global_counter.items():
        if count < min_count:
            continue
        try:
            cur.execute("""
                UPDATE user_dictionary SET frequency = ? WHERE word = ?
            """, (count, word))
            updated += cur.rowcount
        except Exception:
            pass

    conn.commit()
    conn.close()

    result = {
        "total_unique_words": len(global_counter),
        "total_tokens": sum(global_counter.values()),
        "corpus_rows_inserted": inserted_corpus,
        "user_dict_rows_updated": updated,
        "per_source": {k: len(v) for k, v in counters.items()},
    }
    log.info(f"Done: {result}")
    return result


if __name__ == "__main__":
    print(main())
