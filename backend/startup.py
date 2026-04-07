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

# Paths — use environment variables for Railway volume, fallback for local dev
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
IS_RAILWAY = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.path.exists("/app/data"))
DATA_DIR = os.getenv("DATA_DIR", "/app/data" if IS_RAILWAY else BACKEND_DIR)
os.makedirs(DATA_DIR, exist_ok=True)

TAHRIRCHI_DB_PATH = os.getenv("TAHRIRCHI_DB_PATH", os.path.join(DATA_DIR, "tahrirchi.db"))
PHARMA_DB_PATH = os.getenv("DB_PATH", os.path.join(DATA_DIR, "pharma_editor.db"))
DICT_COMPRESSED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dictionary_data.csv.gz")

# Phase 1: Remote download URL for tahrirchi.db (GitHub Release)
# Set TAHRIRCHI_DOWNLOAD_URL env var to override
TAHRIRCHI_DOWNLOAD_URL = os.getenv(
    "TAHRIRCHI_DOWNLOAD_URL",
    "https://github.com/Pharmexpert/pharmtahrirchi/releases/download/v1-tahrirchi-lexicon/tahrirchi.db"
)

# Phase 3: Remote download URLs for pre-built FAISS lexicon index
TAHRIRCHI_FAISS_INDEX_URL = os.getenv(
    "TAHRIRCHI_FAISS_INDEX_URL",
    "https://github.com/Pharmexpert/pharmtahrirchi/releases/download/v1-tahrirchi-faiss/tahrirchi_lexicon.index"
)
TAHRIRCHI_FAISS_IDS_URL = os.getenv(
    "TAHRIRCHI_FAISS_IDS_URL",
    "https://github.com/Pharmexpert/pharmtahrirchi/releases/download/v1-tahrirchi-faiss/tahrirchi_lexicon.ids"
)


def _download_file(url: str, dest: str, min_size_mb: float = 0.0) -> bool:
    """Download file from URL to dest path with progress logging. Skip if dest already exists."""
    if os.path.exists(dest):
        size_mb = os.path.getsize(dest) / (1024 * 1024)
        if size_mb >= min_size_mb:
            logger.info(f"[+] {os.path.basename(dest)} already exists ({size_mb:.1f} MB). Skipping download.")
            return True
        else:
            logger.info(f"[*] {os.path.basename(dest)} exists but too small ({size_mb:.1f} MB < {min_size_mb}). Re-downloading.")

    logger.info(f"[*] Downloading {url} → {dest}")
    start = time.time()
    try:
        import urllib.request
        import urllib.error

        os.makedirs(os.path.dirname(dest), exist_ok=True)

        # Stream download with progress
        with urllib.request.urlopen(url, timeout=600) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            chunk_size = 8 * 1024 * 1024  # 8 MB chunks
            downloaded = 0
            last_log = 0

            with open(dest + ".tmp", "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Log every 50 MB
                    if downloaded - last_log >= 50 * 1024 * 1024:
                        pct = (downloaded / total_size * 100) if total_size else 0
                        logger.info(
                            f"    ...{downloaded/(1024*1024):.0f} MB / "
                            f"{total_size/(1024*1024):.0f} MB ({pct:.0f}%)"
                        )
                        last_log = downloaded

        # Atomic rename
        os.replace(dest + ".tmp", dest)
        elapsed = time.time() - start
        final_size_mb = os.path.getsize(dest) / (1024 * 1024)
        logger.info(f"[+] Downloaded {final_size_mb:.1f} MB in {elapsed:.1f}s → {dest}")
        return True
    except urllib.error.HTTPError as e:
        logger.warning(f"[!] HTTP error downloading {url}: {e.code} {e.reason}")
        if os.path.exists(dest + ".tmp"):
            os.remove(dest + ".tmp")
        return False
    except Exception as e:
        logger.error(f"[!] Download failed for {url}: {e}")
        if os.path.exists(dest + ".tmp"):
            os.remove(dest + ".tmp")
        return False


def setup_tahrirchi_db():
    """Set up tahrirchi.db: check existing → download from GitHub Release → fallback to empty."""
    if os.path.exists(TAHRIRCHI_DB_PATH):
        try:
            conn = sqlite3.connect(TAHRIRCHI_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM dictionary")
            count = cursor.fetchone()[0]
            conn.close()
            if count > 1000:
                logger.info(f"[+] tahrirchi.db already exists with {count:,} words. Skipping download.")
                # Also try to download FAISS index if missing
                _try_download_faiss_lexicon()
                return True
            else:
                logger.info(f"[*] tahrirchi.db exists but only has {count} words. Re-downloading.")
                os.remove(TAHRIRCHI_DB_PATH)
        except Exception as e:
            logger.warning(f"[!] Error reading tahrirchi.db: {e}. Re-downloading.")
            try:
                os.remove(TAHRIRCHI_DB_PATH)
            except Exception:
                pass

    # Try to download from GitHub Release (primary source)
    if TAHRIRCHI_DOWNLOAD_URL:
        logger.info("[*] Attempting to download tahrirchi.db from GitHub Release...")
        if _download_file(TAHRIRCHI_DOWNLOAD_URL, TAHRIRCHI_DB_PATH, min_size_mb=100.0):
            # Verify
            try:
                conn = sqlite3.connect(TAHRIRCHI_DB_PATH)
                count = conn.execute("SELECT COUNT(*) FROM dictionary").fetchone()[0]
                conn.close()
                logger.info(f"[+] tahrirchi.db downloaded successfully: {count:,} words")
                _try_download_faiss_lexicon()
                return True
            except Exception as e:
                logger.error(f"[!] Downloaded tahrirchi.db is invalid: {e}")

    # Fallback: rebuild from local CSV (legacy)
    if os.path.exists(DICT_COMPRESSED):
        logger.info(f"[*] Fallback: rebuilding tahrirchi.db from {DICT_COMPRESSED}...")
        return _rebuild_from_csv()

    # Last fallback: create empty
    logger.warning("[!] No source available for tahrirchi.db. Creating empty schema.")
    create_empty_tahrirchi_db()
    return True


def _try_download_faiss_lexicon():
    """Download pre-built FAISS lexicon index if missing (Phase 3)."""
    index_path = os.path.join(DATA_DIR, "tahrirchi_lexicon.index")
    ids_path = os.path.join(DATA_DIR, "tahrirchi_lexicon.ids")

    if os.path.exists(index_path) and os.path.exists(ids_path):
        logger.info("[+] FAISS lexicon already present. Skipping.")
        return

    if TAHRIRCHI_FAISS_INDEX_URL:
        logger.info("[*] Attempting to download pre-built FAISS lexicon index...")
        idx_ok = _download_file(TAHRIRCHI_FAISS_INDEX_URL, index_path, min_size_mb=10.0)
        ids_ok = _download_file(TAHRIRCHI_FAISS_IDS_URL, ids_path, min_size_mb=1.0)
        if idx_ok and ids_ok:
            logger.info("[+] FAISS lexicon downloaded successfully.")
        else:
            logger.warning("[!] FAISS lexicon download failed — semantic search will be unavailable.")
            # Clean up partial files
            for p in [index_path, ids_path]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass


def _rebuild_from_csv():
    """Legacy: rebuild tahrirchi.db from compressed CSV."""
    
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
