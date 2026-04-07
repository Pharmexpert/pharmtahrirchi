"""
FastText synonym engine for fast lexical similarity.

Uses pre-computed FastText embeddings (Uzbek) to find similar words in milliseconds.
Optional integration — gracefully degrades if fasttext model unavailable.

Source: https://huggingface.co/elmurod1202/uztext-fasttext (or fasttext.cc)

Modes:
  1. FASTTEXT_LOCAL=1 + FASTTEXT_PATH=/tmp/uz.bin — load .bin file
  2. Disabled — fall through to BERT-based synonym discovery
"""
import os
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger("fasttext_engine")

LOCAL_MODE = os.getenv("FASTTEXT_LOCAL") == "1"
MODEL_PATH = os.getenv("FASTTEXT_PATH", "/tmp/uz_fasttext.bin")

_model = None
_lock = None


def _get_model():
    global _model, _lock
    if _model is not None:
        return _model
    if not LOCAL_MODE:
        return None
    if not os.path.exists(MODEL_PATH):
        return None
    try:
        import threading
        if _lock is None:
            _lock = threading.Lock()
        with _lock:
            if _model is None:
                import fasttext  # type: ignore
                logger.info(f"[fasttext] Loading {MODEL_PATH}")
                _model = fasttext.load_model(MODEL_PATH)
                logger.info(f"[fasttext] READY")
    except Exception as e:
        logger.warning(f"[fasttext] load failed: {e}")
    return _model


def is_available() -> bool:
    return _get_model() is not None


def get_mode() -> str:
    if LOCAL_MODE and os.path.exists(MODEL_PATH):
        return "local_bin"
    return "unavailable"


def find_synonyms(word: str, top_k: int = 10) -> List[Tuple[str, float]]:
    """Return list of (similar_word, score) pairs."""
    model = _get_model()
    if not model:
        return []
    try:
        results = model.get_nearest_neighbors(word, k=top_k)
        return [(w, float(s)) for s, w in results]
    except Exception as e:
        logger.warning(f"[fasttext] neighbors failed: {e}")
        return []


def word_similarity(a: str, b: str) -> float:
    """Cosine similarity между двумя словами."""
    model = _get_model()
    if not model:
        return 0.0
    try:
        import numpy as np
        va = model.get_word_vector(a)
        vb = model.get_word_vector(b)
        return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb) + 1e-9))
    except Exception:
        return 0.0
