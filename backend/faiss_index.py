# -*- coding: utf-8 -*-
"""
faiss_index.py — B-6: FAISS lexicon similarity index.

Builds a FAISS index from the dictionary table (88K words).
Lazy-loads on first use, caches to disk as data/lexicon.faiss.
Does NOT block startup.

Usage:
    from faiss_index import search_similar
    results = search_similar("дори", k=5)
"""
import os
import logging
import threading
import sqlite3
import numpy as np
from pathlib import Path

logger = logging.getLogger("faiss_index")

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FAISS_PATH = os.path.join(DATA_DIR, "lexicon.faiss")
WORDS_PATH = os.path.join(DATA_DIR, "lexicon_words.npy")

_index = None
_words = None
_lock = threading.Lock()
_building = False


def _char_vector(word: str, dim: int = 64) -> np.ndarray:
    """Simple character n-gram vector for a word (no ML model needed).
    Uses character trigram hashing into a fixed-size vector."""
    vec = np.zeros(dim, dtype=np.float32)
    w = word.lower()
    for i in range(len(w)):
        # unigram
        vec[ord(w[i]) % dim] += 1.0
        # bigram
        if i + 1 < len(w):
            h = (ord(w[i]) * 31 + ord(w[i+1])) % dim
            vec[h] += 1.0
        # trigram
        if i + 2 < len(w):
            h = (ord(w[i]) * 961 + ord(w[i+1]) * 31 + ord(w[i+2])) % dim
            vec[h] += 1.0
    # L2 normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def build_lexicon_index() -> bool:
    """Build FAISS index from dictionary table. Returns True on success."""
    global _index, _words, _building
    _building = True
    try:
        import faiss
    except ImportError:
        logger.warning("[FAISS] faiss-cpu not installed — lexicon index disabled")
        _building = False
        return False

    try:
        # Load words from dictionary
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT word FROM dictionary WHERE word IS NOT NULL AND LENGTH(word) > 1 ORDER BY word")
        rows = cur.fetchall()
        conn.close()

        if not rows:
            logger.warning("[FAISS] No words in dictionary table")
            _building = False
            return False

        words_list = [r[0] for r in rows]
        logger.info(f"[FAISS] Building index for {len(words_list)} words...")

        dim = 64
        vectors = np.array([_char_vector(w, dim) for w in words_list], dtype=np.float32)

        index = faiss.IndexFlatIP(dim)  # Inner product (cosine on normalized vecs)
        index.add(vectors)

        # Cache to disk
        os.makedirs(DATA_DIR, exist_ok=True)
        faiss.write_index(index, FAISS_PATH)
        np.save(WORDS_PATH, np.array(words_list, dtype=object))

        _index = index
        _words = words_list
        logger.info(f"[FAISS] Lexicon index ready: {len(words_list)} words, dim={dim}")
        _building = False
        return True

    except Exception as e:
        logger.error(f"[FAISS] Build failed: {e}")
        _building = False
        return False


def _ensure_index():
    """Lazy-load: build or load from cache on first use."""
    global _index, _words
    if _index is not None:
        return True
    if _building:
        return False

    with _lock:
        if _index is not None:
            return True

        # Try loading from cache
        if os.path.exists(FAISS_PATH) and os.path.exists(WORDS_PATH):
            try:
                import faiss
                _index = faiss.read_index(FAISS_PATH)
                _words = list(np.load(WORDS_PATH, allow_pickle=True))
                logger.info(f"[FAISS] Loaded cached index: {len(_words)} words")
                return True
            except Exception as e:
                logger.warning(f"[FAISS] Cache load failed: {e}")

        # Build in background thread (don't block)
        t = threading.Thread(target=build_lexicon_index, daemon=True)
        t.start()
        return False


def search_similar(word: str, k: int = 5) -> list:
    """Search for k most similar words in the lexicon.
    Returns: [{"word": str, "score": float}, ...]
    """
    if not _ensure_index():
        return []
    if _index is None or _words is None:
        return []

    try:
        vec = _char_vector(word, 64).reshape(1, -1)
        scores, indices = _index.search(vec, min(k + 1, len(_words)))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(_words):
                continue
            w = _words[idx]
            if w.lower() == word.lower():
                continue
            results.append({"word": w, "score": round(float(score), 4)})
        return results[:k]
    except Exception as e:
        logger.error(f"[FAISS] Search failed: {e}")
        return []


def is_available() -> bool:
    """Check if FAISS is installed."""
    try:
        import faiss  # noqa
        return True
    except ImportError:
        return False


def get_stats() -> dict:
    """Return index statistics."""
    return {
        "available": is_available(),
        "loaded": _index is not None,
        "words": len(_words) if _words else 0,
        "building": _building,
        "cache_path": FAISS_PATH,
    }
