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

# Limits (control memory + time) — small defaults to avoid download bottleneck
UZ_CRAWL_SAMPLES = int(os.getenv("UZ_CRAWL_SAMPLES", "500"))
DILMASH_SAMPLES = int(os.getenv("DILMASH_SAMPLES", "2000"))
LUTFIY_SAMPLES = int(os.getenv("LUTFIY_SAMPLES", "1000"))
UZLIB_SAMPLES = int(os.getenv("UZLIB_SAMPLES", "500"))


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
        # uz-crawl has splits: 'news', 'telegram_blogs' (no 'train')
        total_inserted = 0
        for split_name in ["news", "telegram_blogs"]:
            try:
                per_split = limit // 2
                ds = load_dataset("tahrirchi/uz-crawl", split=f"{split_name}[:{per_split}]", token=HF_TOKEN)
                log.info(f"Dataset {split_name}: {len(ds)} examples, fields: {ds.column_names if hasattr(ds, 'column_names') else '?'}")
                for example in ds:
                    text = ""
                    if isinstance(example, dict):
                        text = example.get("text") or example.get("content") or example.get("body") or example.get("sentence") or ""
                        if not text:
                            for k, v in example.items():
                                if isinstance(v, str) and len(v) > 20:
                                    text = v
                                    break
                    if not text or len(text) < 20:
                        continue
                    try:
                        cur.execute("INSERT INTO uz_crawl_corpus (text, metadata) VALUES (?, ?)",
                                    (str(text)[:10000], f"{split_name}"))
                        total_inserted += 1
                    except Exception:
                        pass
            except Exception as ee:
                log.warning(f"uz-crawl split {split_name} failed: {ee}")
        log.info(f"uz-crawl: +{total_inserted}")
        return total_inserted
    except Exception as e:
        log.warning(f"uz-crawl import failed: {e}")
        return 0

def _unused_old_uz_crawl(cur, limit):
    try:
        ds = None
        inserted = 0
        for i, example in enumerate([]):
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
    """Import dilmash translation pairs (non-streaming)."""
    try:
        from datasets import load_dataset
    except ImportError:
        return 0
    try:
        # dilmash has multiple configs: kaa_eng, kaa_rus, kaa_uzb, eng_uzb, eng_rus, uzb_rus etc.
        # Each is a parquet file — we load them directly
        all_inserted = 0
        configs = ["eng_uzb", "kaa_uzb", "eng_rus", "uzb_rus", "kaa_rus", "kaa_eng"]
        for conf in configs:
            try:
                ds = load_dataset("tahrirchi/dilmash", name=conf, split=f"train[:{limit // len(configs)}]", token=HF_TOKEN)
                log.info(f"dilmash {conf}: {len(ds)}, fields={ds.column_names}")
                # Config name tells us src/tgt languages
                parts = conf.split("_")
                src_lang = parts[0][:3] if len(parts) >= 2 else "en"
                tgt_lang = parts[1][:3] if len(parts) >= 2 else "uz"
                for example in ds:
                    if not isinstance(example, dict):
                        continue
                    str_fields = [(k, v) for k, v in example.items() if isinstance(v, str) and v.strip()]
                    if len(str_fields) >= 2:
                        src = str_fields[0][1]
                        tgt = str_fields[1][1]
                        try:
                            cur.execute("""
                                INSERT INTO translation_memory (source_lang, target_lang, source_text, target_text, source_db, quality_score)
                                VALUES (?, ?, ?, ?, 'tahrirchi_dilmash', 1.0)
                            """, (src_lang, tgt_lang, str(src)[:2000], str(tgt)[:2000]))
                            all_inserted += 1
                        except Exception:
                            pass
            except Exception as ee:
                log.warning(f"dilmash {conf} failed: {ee}")
        log.info(f"dilmash: +{all_inserted}")
        return all_inserted

    except Exception as e:
        log.warning(f"dilmash outer failed: {e}")
        return 0

def _dilmash_legacy_skip(cur, limit):
    try:
        ds = None
        if ds is None:
            log.warning("dilmash: no valid split found")
            return 0
        inserted = 0
        for example in ds:
            if inserted >= limit:
                break
            if not isinstance(example, dict):
                continue
            # Auto-detect: first 2 string fields as src/tgt
            str_fields = [(k, v) for k, v in example.items() if isinstance(v, str) and v.strip()]
            if len(str_fields) >= 2:
                src_key, src = str_fields[0]
                tgt_key, tgt = str_fields[1]
                src_lang = src_key[:3] if len(src_key) <= 5 else "en"
                tgt_lang = tgt_key[:3] if len(tgt_key) <= 5 else "uz"
            else:
                continue
            # Legacy fallback if auto-detect gave empty
            if not src:
                src = example.get("source", example.get("src", example.get("en", "")))
            if not tgt:
                tgt = example.get("target", example.get("tgt", example.get("uz", "")))
            if 'src_lang' not in locals():
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
    """Import lutfiy literary pairs (non-streaming + field auto-detection)."""
    try:
        from datasets import load_dataset
    except ImportError:
        return 0
    try:
        ds = None
        for split_attempt in ["train", "validation", "test"]:
            try:
                ds = load_dataset("tahrirchi/lutfiy", split=f"{split_attempt}[:{limit}]", token=HF_TOKEN)
                log.info(f"lutfiy loaded: {len(ds)}, fields={ds.column_names}")
                break
            except Exception:
                continue
        if ds is None:
            log.warning("lutfiy: no split found")
            return 0
        inserted = 0
        for example in ds:
            if inserted >= limit:
                break
            if not isinstance(example, dict):
                continue
            # Auto-detect fields: first 2 string fields are src/tgt
            str_fields = [(k, v) for k, v in example.items() if isinstance(v, str) and v.strip()]
            if len(str_fields) < 2:
                continue
            src_key, src = str_fields[0]
            tgt_key, tgt = str_fields[1]
            try:
                cur.execute("""
                    INSERT INTO translation_memory (source_lang, target_lang, source_text, target_text, source_db, quality_score)
                    VALUES (?, ?, ?, ?, 'tahrirchi_lutfiy', 0.95)
                """, (src_key[:3], tgt_key[:3], str(src)[:2000], str(tgt)[:2000]))
                inserted += 1
            except Exception:
                pass
        log.info(f"lutfiy: +{inserted}")
        return inserted
    except Exception as e:
        log.warning(f"lutfiy import failed: {e}")
        return 0


def import_uzlib(cur, limit: int) -> int:
    """Import uzlib (splits: correct_word, meaning, meaning_in_context, fill_in)."""
    try:
        from datasets import load_dataset
    except ImportError:
        return 0
    try:
        total_inserted = 0
        for split_name in ["correct_word", "meaning", "meaning_in_context", "fill_in"]:
            try:
                ds = load_dataset("tahrirchi/uzlib", split=f"{split_name}[:{limit // 4}]", token=HF_TOKEN)
                log.info(f"uzlib {split_name}: {len(ds)}, fields={ds.column_names}")
                for example in ds:
                    if not isinstance(example, dict):
                        continue
                    # Concatenate all string fields as text
                    parts = [f"{k}: {v}" for k, v in example.items() if isinstance(v, str) and v.strip()]
                    if not parts:
                        continue
                    text = " | ".join(parts)
                    try:
                        cur.execute("INSERT INTO uzbek_literature (text, source, metadata) VALUES (?, 'tahrirchi_uzlib', ?)",
                                    (text[:5000], split_name))
                        total_inserted += 1
                    except Exception:
                        pass
            except Exception as ee:
                log.warning(f"uzlib split {split_name} failed: {ee}")
        log.info(f"uzlib: +{total_inserted}")
        return total_inserted
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
