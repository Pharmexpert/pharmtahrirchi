"""
Dict2Vec engine scaffold — elmurod1202/dict2vec-uzbek.

Dict2Vec: Word2Vec fine-tuned on dictionary definitions.
Better than standard Word2Vec for **synonym detection** because it learns
from structured semantic definitions (izohli lug'at) not just context windows.

Usage:
  engine = Dict2VecEngine()
  synonyms = engine.find_synonyms("дори", top_n=5)
  similarity = engine.similarity("дори", "препарат")

Activation:
  export DICT2VEC_ENABLED=1

Model files (gensim KeyedVectors format):
  - downloaded on first call from HuggingFace
  - cached to /tmp/dict2vec_uzbek.kv
"""
import os
import logging
import urllib.request

logger = logging.getLogger("dict2vec_engine")

DICT2VEC_ENABLED = os.getenv("DICT2VEC_ENABLED", "0") == "1"
MODEL_URL = "https://huggingface.co/elmurod1202/dict2vec-uzbek/resolve/main/dict2vec_uzbek.kv"
CACHE_PATH = "/tmp/dict2vec_uzbek.kv"

_model = None
_loaded = False
_load_attempted = False


def is_available() -> bool:
    if not DICT2VEC_ENABLED:
        return False
    try:
        import gensim  # noqa
        return True
    except ImportError:
        return False


def _download_model() -> bool:
    """Download model if not cached."""
    if os.path.exists(CACHE_PATH):
        return True
    try:
        logger.info(f"[dict2vec] Downloading model from {MODEL_URL}")
        urllib.request.urlretrieve(MODEL_URL, CACHE_PATH)
        logger.info("[dict2vec] Model downloaded")
        return True
    except Exception as e:
        logger.error(f"[dict2vec] Download failed: {e}")
        return False


def _load():
    """Lazy-load the model."""
    global _model, _loaded, _load_attempted
    if _loaded or _load_attempted:
        return _model
    _load_attempted = True
    if not is_available():
        return None
    try:
        if not _download_model():
            return None
        from gensim.models import KeyedVectors
        _model = KeyedVectors.load(CACHE_PATH)
        _loaded = True
        logger.info("[dict2vec] Model loaded successfully")
        return _model
    except Exception as e:
        logger.error(f"[dict2vec] Load failed: {e}")
        return None


def find_synonyms(word: str, top_n: int = 5) -> list:
    """Return top N most similar words via dict2vec embedding."""
    if not word:
        return []
    m = _load()
    if m is None:
        return []
    try:
        word_l = word.lower().strip()
        if word_l not in m:
            return []
        results = m.most_similar(word_l, topn=top_n)
        return [{"word": w, "similarity": float(s)} for w, s in results]
    except Exception as e:
        logger.debug(f"[dict2vec] find_synonyms error: {e}")
        return []


def similarity(word1: str, word2: str) -> float:
    """Compute cosine similarity between two words."""
    if not word1 or not word2:
        return 0.0
    m = _load()
    if m is None:
        return 0.0
    try:
        w1, w2 = word1.lower().strip(), word2.lower().strip()
        if w1 not in m or w2 not in m:
            return 0.0
        return float(m.similarity(w1, w2))
    except Exception:
        return 0.0


def info() -> dict:
    return {
        "enabled": DICT2VEC_ENABLED,
        "available": is_available(),
        "loaded": _loaded,
        "cached": os.path.exists(CACHE_PATH),
        "model_url": MODEL_URL,
    }
