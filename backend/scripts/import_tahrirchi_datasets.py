"""
Import Tahrirchi HuggingFace datasets:
  - tahrirchi/uz-crawl (1.62M entries, web corpus) → sayqallash_rules growth
  - tahrirchi/dilmash (300K pairs) → translation_memory
  - tahrirchi/lutfiy (40K pairs) → translation_memory (literary)
  - tahrirchi/uzlib (1.86K literary) → uzbek_literature corpus

Usage: Streaming-mode, takes first N samples (configurable).
"""
import os
import sys
import sqlite3
import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format="[tahrirchi_ds] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")

# Limits (control memory + time)
UZ_CRAWL_SAMPLES = int(os.getenv("UZ_CRAWL_SAMPLES", "5000"))
DILMASH_SAMPLES = int(os.getenv("DILMASH_SAMPLES", "10000"))
LUTFIY_SAMPLES = int(os.getenv("LUTFIY_SAMPLES", "5000"))
UZLIB_SAMPLES = int(os.getenv("UZLIB_SAMPLES", "2000"))


def ensure_tables(cur):
    """Create tables for imported data."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS translation_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_lang TEXT,
            target_lang TEXT,
            source_text TEXT,
            target_text TEXT,
            source_db TEXT,
            quality_score REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tm_src ON translation_memory(source_text)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tm_langs ON translation_memory(source_lang, target_lang)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS uzbek_literature (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            source TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS uz_crawl_corpus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def import_uz_crawl(cur, limit: int) -> int:
    """Import uz-crawl corpus via non-streaming (streaming returns IterableDataset)."""
    try:
        from datasets import load_dataset
    except ImportError:
        log.error("datasets library not installed")
        return 0
    try:
        log.info(f"Loading tahrirchi/uz-crawl (split='train', first {limit})...")
        # Non-streaming — small sample
        ds = load_dataset("tahrirchi/uz-crawl", split=f"train[:{limit}]", token=HF_TOKEN)
        log.info(f"Dataset loaded: {len(ds)} examples, fields: {ds.column_names if hasattr(ds, 'column_names') else '?'}")
        inserted = 0
        for i, example in enumerate(ds):
            if i >= limit:
                break
            # Try multiple possible field names
            text = ""
            if isinstance(example, dict):
                text = example.get("text") or example.get("content") or example.get("sentence") or ""
                if not text:
                    # Take first string field
                    for k, v in example.items():
                        if isinstance(v, str) and len(v) > 20:
                            text = v
                            break
            if not text or len(text) < 20:
                continue
            try:
                cur.execute("INSERT INTO uz_crawl_corpus (text, metadata) VALUES (?, ?)",
                            (str(text)[:10000], f"example_{i}"))
                inserted += 1
            except Exception as e:
                log.debug(f"  insert fail: {e}")
        log.info(f"uz-crawl: +{inserted}")
        return inserted
    except Exception as e:
        log.warning(f"uz-crawl import failed: {e}")
        return 0


def import_dilmash(cur, limit: int) -> int:
    """Import dilmash translation pairs."""
    try:
        from datasets import load_dataset
    except ImportError:
        return 0
    try:
        ds = load_dataset("tahrirchi/dilmash", split="train", streaming=True, token=HF_TOKEN)
        inserted = 0
        for i, example in enumerate(ds):
            if i >= limit:
                break
            if not isinstance(example, dict):
                continue
            # Common field names: src_lang/tgt_lang OR language pairs
            src = example.get("source", example.get("src", example.get("en", "")))
            tgt = example.get("target", example.get("tgt", example.get("uz", "")))
            src_lang = example.get("source_lang", "en")
            tgt_lang = example.get("target_lang", "uz")
            # Try other common structures
            if not src and "translation" in example:
                t = example["translation"]
                if isinstance(t, dict):
                    keys = list(t.keys())
                    if len(keys) >= 2:
                        src_lang, tgt_lang = keys[0], keys[1]
                        src = t[src_lang]
                        tgt = t[tgt_lang]
            if not src or not tgt:
                continue
            try:
                cur.execute("""
                    INSERT INTO translation_memory (source_lang, target_lang, source_text, target_text, source_db, quality_score)
                    VALUES (?, ?, ?, ?, 'tahrirchi_dilmash', 1.0)
                """, (src_lang, tgt_lang, str(src)[:2000], str(tgt)[:2000]))
                inserted += 1
            except Exception:
                pass
        log.info(f"dilmash: +{inserted}")
        return inserted
    except Exception as e:
        log.warning(f"dilmash import failed: {e}")
        return 0


def import_lutfiy(cur, limit: int) -> int:
    """Import lutfiy literary pairs."""
    try:
        from datasets import load_dataset
    except ImportError:
        return 0
    try:
        ds = load_dataset("tahrirchi/lutfiy", split="train", streaming=True, token=HF_TOKEN)
        inserted = 0
        for i, example in enumerate(ds):
            if i >= limit:
                break
            if not isinstance(example, dict):
                continue
            src = example.get("source", example.get("en", ""))
            tgt = example.get("target", example.get("uz", ""))
            if not src or not tgt:
                continue
            try:
                cur.execute("""
                    INSERT INTO translation_memory (source_lang, target_lang, source_text, target_text, source_db, quality_score)
                    VALUES ('en', 'uz', ?, ?, 'tahrirchi_lutfiy', 0.95)
                """, (str(src)[:2000], str(tgt)[:2000]))
                inserted += 1
            except Exception:
                pass
        log.info(f"lutfiy: +{inserted}")
        return inserted
    except Exception as e:
        log.warning(f"lutfiy import failed: {e}")
        return 0


def import_uzlib(cur, limit: int) -> int:
    """Import uzlib literary corpus."""
    try:
        from datasets import load_dataset
    except ImportError:
        return 0
    try:
        ds = load_dataset("tahrirchi/uzlib", split="train", streaming=True, token=HF_TOKEN)
        inserted = 0
        for i, example in enumerate(ds):
            if i >= limit:
                break
            text = example.get("text", "") if isinstance(example, dict) else ""
            if not text or len(text) < 20:
                continue
            try:
                cur.execute("INSERT INTO uzbek_literature (text, source, metadata) VALUES (?, 'tahrirchi_uzlib', ?)",
                            (text[:5000], f"sample_{i}"))
                inserted += 1
            except Exception:
                pass
        log.info(f"uzlib: +{inserted}")
        return inserted
    except Exception as e:
        log.warning(f"uzlib import failed: {e}")
        return 0


def main():
    if not HF_TOKEN:
        log.error("HF_TOKEN not set — cannot access datasets")
        return {"error": "no_hf_token"}

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    ensure_tables(cur)
    conn.commit()

    result = {}
    result["uz_crawl"] = import_uz_crawl(cur, UZ_CRAWL_SAMPLES)
    conn.commit()
    result["dilmash"] = import_dilmash(cur, DILMASH_SAMPLES)
    conn.commit()
    result["lutfiy"] = import_lutfiy(cur, LUTFIY_SAMPLES)
    conn.commit()
    result["uzlib"] = import_uzlib(cur, UZLIB_SAMPLES)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM translation_memory")
    result["translation_memory_total"] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM uz_crawl_corpus")
    result["uz_crawl_total"] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM uzbek_literature")
    result["uzbek_literature_total"] = cur.fetchone()[0]

    conn.close()
    log.info(f"Result: {result}")
    return result


if __name__ == "__main__":
    print(main())
