"""
Startup script for Railway deployment.
Downloads BERT model from HuggingFace and rebuilds tahrirchi.db from compressed data.
Run once on first deployment, then data persists in Railway volume.
"""
import os
import sys
import gzip
import sqlite3
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("startup")

# Paths — use environment variables for Railway, fallback for local dev
DATA_DIR = os.getenv("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
TAHRIRCHI_DB_PATH = os.path.join(DATA_DIR, "tahrirchi.db")
PHARMA_DB_PATH = os.path.join(DATA_DIR, "pharma_editor.db")
DICT_COMPRESSED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dictionary_data.csv.gz")

def setup_tahrirchi_db():
    """Rebuild tahrirchi.db from compressed dictionary data."""
    if os.path.exists(TAHRIRCHI_DB_PATH):
        conn = sqlite3.connect(TAHRIRCHI_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dictionary")
        count = cursor.fetchone()[0]
        conn.close()
        if count > 1000:
            logger.info(f"[+] tahrirchi.db already exists with {count:,} words. Skipping rebuild.")
            return True
    
    if not os.path.exists(DICT_COMPRESSED):
        logger.warning(f"[!] dictionary_data.csv.gz not found at {DICT_COMPRESSED}")
        logger.info("[*] Creating empty tahrirchi.db with basic schema...")
        create_empty_tahrirchi_db()
        return True
    
    logger.info(f"[*] Rebuilding tahrirchi.db from {DICT_COMPRESSED}...")
    start = time.time()
    
    conn = sqlite3.connect(TAHRIRCHI_DB_PATH)
    cursor = conn.cursor()
    
    # Create all tables matching original schema
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE,
            frequency INTEGER DEFAULT 1,
            source TEXT DEFAULT 'corpus',
            is_confirmed INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT, category TEXT, description TEXT,
            added_by TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_word TEXT, corrected_word TEXT, sentence_context TEXT,
            correction_type TEXT, accepted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text_length INTEGER, word_count INTEGER, error_count INTEGER,
            score REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS confirmed_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT, context TEXT, frequency INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_dictionary_word ON dictionary(word);
    """)
    conn.commit()
    
    # Import from compressed CSV
    batch = []
    batch_size = 50000
    total = 0
    
    with gzip.open(DICT_COMPRESSED, 'rt', encoding='utf-8') as f:
        header = f.readline()  # Skip header
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 4:
                word, freq, source, confirmed = parts[0], int(parts[1]), parts[2], int(parts[3])
                batch.append((word, freq, source, confirmed))
                
                if len(batch) >= batch_size:
                    cursor.executemany(
                        "INSERT OR IGNORE INTO dictionary (word, frequency, source, is_confirmed) VALUES (?, ?, ?, ?)",
                        batch
                    )
                    conn.commit()
                    total += len(batch)
                    batch = []
                    if total % 500000 == 0:
                        logger.info(f"    ...imported {total:,} words")
    
    if batch:
        cursor.executemany(
            "INSERT OR IGNORE INTO dictionary (word, frequency, source, is_confirmed) VALUES (?, ?, ?, ?)",
            batch
        )
        conn.commit()
        total += len(batch)
    
    # Analyze for performance
    cursor.execute("ANALYZE dictionary")
    conn.commit()
    conn.close()
    
    elapsed = time.time() - start
    logger.info(f"[+] tahrirchi.db rebuilt: {total:,} words in {elapsed:.1f}s")
    return True

def create_empty_tahrirchi_db():
    """Create empty tahrirchi.db with correct schema."""
    conn = sqlite3.connect(TAHRIRCHI_DB_PATH)
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE,
            frequency INTEGER DEFAULT 1,
            source TEXT DEFAULT 'corpus',
            is_confirmed INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT, category TEXT, description TEXT,
            added_by TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_word TEXT, corrected_word TEXT, sentence_context TEXT,
            correction_type TEXT, accepted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text_length INTEGER, word_count INTEGER, error_count INTEGER,
            score REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS confirmed_words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT, context TEXT, frequency INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_dictionary_word ON dictionary(word);
    """)
    conn.commit()
    conn.close()
    logger.info("[+] Empty tahrirchi.db created with schema.")

def setup_bert_model():
    """Download BERT model from HuggingFace if not present locally."""
    model_name = os.getenv("BERT_MODEL", "tahrirchi/tahrirchi-bert-base")
    
    # If it's a HuggingFace model ID, transformers will auto-download
    if "/" in model_name:
        logger.info(f"[*] BERT model '{model_name}' will be auto-downloaded from HuggingFace on first use.")
        return True
    
    # If it's a local path, check existence
    if os.path.exists(model_name):
        logger.info(f"[+] BERT model found at {model_name}")
        return True
    
    logger.warning(f"[!] Local BERT model not found: {model_name}. Falling back to HuggingFace download.")
    os.environ["BERT_MODEL"] = "tahrirchi/tahrirchi-bert-base"
    return True

def copy_pharma_db():
    """Ensure pharma_editor.db exists in DATA_DIR."""
    local_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pharma_editor.db")
    if DATA_DIR != os.path.dirname(os.path.abspath(__file__)):
        if os.path.exists(local_db) and not os.path.exists(PHARMA_DB_PATH):
            import shutil
            shutil.copy2(local_db, PHARMA_DB_PATH)
            logger.info(f"[+] Copied pharma_editor.db to {PHARMA_DB_PATH}")
    return True


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("PHARMA EXPERT — STARTUP INITIALIZATION")
    logger.info("=" * 50)
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    setup_bert_model()
    setup_tahrirchi_db()
    copy_pharma_db()
    
    logger.info("[+] All systems initialized. Ready to start.")
