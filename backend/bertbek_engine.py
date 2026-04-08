"""
BERTbek engine — elmurod1202/BERTbek models wrapper.

Provides:
  - POS tagging via bertbek-pos-tagger (17 POS tags)
  - Base embeddings via BERTbek-news-big-cased
  - Lazy loading (model only loads when first called)
  - Opt-in via BERTBEK_ENABLED env var (default OFF due to RAM cost)

Activation:
  export BERTBEK_ENABLED=1
  Railway: add BERTBEK_ENABLED=1 env var

Models (downloaded from HuggingFace on first call):
  - elmurod1202/bertbek-pos-tagger (~500 MB)
  - elmurod1202/bertbek-news-big-cased (~450 MB)

Total RAM footprint when loaded: ~1 GB.
"""
import os
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger("bertbek_engine")

BERTBEK_ENABLED = os.getenv("BERTBEK_ENABLED", "0") == "1"
POS_MODEL_ID = "elmurod1202/bertbek-pos-tagger"
BASE_MODEL_ID = "elmurod1202/bertbek-news-big-cased"

_pos_model = None
_pos_tokenizer = None
_base_model = None
_base_tokenizer = None


def is_available() -> bool:
    """Return True if BERTbek is enabled AND transformers lib is installed."""
    if not BERTBEK_ENABLED:
        return False
    try:
        import transformers  # noqa
        import torch  # noqa
        return True
    except ImportError:
        return False


def _load_pos():
    """Lazy-load POS tagger model. Returns (model, tokenizer) or (None, None)."""
    global _pos_model, _pos_tokenizer
    if not is_available():
        return None, None
    if _pos_model is not None:
        return _pos_model, _pos_tokenizer
    try:
        from transformers import AutoTokenizer, AutoModelForTokenClassification
        logger.info(f"[bertbek] Loading POS model: {POS_MODEL_ID}")
        _pos_tokenizer = AutoTokenizer.from_pretrained(POS_MODEL_ID)
        _pos_model = AutoModelForTokenClassification.from_pretrained(POS_MODEL_ID)
        _pos_model.eval()
        logger.info(f"[bertbek] POS model loaded successfully")
        return _pos_model, _pos_tokenizer
    except Exception as e:
        logger.error(f"[bertbek] POS load failed: {e}")
        return None, None


def _load_base():
    """Lazy-load BERTbek base model for embeddings."""
    global _base_model, _base_tokenizer
    if not is_available():
        return None, None
    if _base_model is not None:
        return _base_model, _base_tokenizer
    try:
        from transformers import AutoTokenizer, AutoModel
        logger.info(f"[bertbek] Loading base model: {BASE_MODEL_ID}")
        _base_tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)
        _base_model = AutoModel.from_pretrained(BASE_MODEL_ID)
        _base_model.eval()
        logger.info(f"[bertbek] Base model loaded successfully")
        return _base_model, _base_tokenizer
    except Exception as e:
        logger.error(f"[bertbek] Base load failed: {e}")
        return None, None


def tag_pos(text: str) -> List[Tuple[str, str]]:
    """
    Tag text with POS labels.
    Returns list of (token, pos_label) tuples.

    POS labels (17): NOUN, VERB, ADJ, ADV, PRON, NUM, PROPN, DET,
                     CCONJ, SCONJ, ADP, AUX, INTJ, PART, PUNCT, SYM, X
    """
    if not text or not text.strip():
        return []
    model, tok = _load_pos()
    if model is None or tok is None:
        return []
    try:
        import torch
        inputs = tok(text, return_tensors="pt", truncation=True, max_length=512, return_offsets_mapping=True)
        offsets = inputs.pop("offset_mapping")[0].tolist()
        with torch.no_grad():
            logits = model(**inputs).logits
            predictions = logits.argmax(-1)[0].tolist()

        id2label = model.config.id2label
        input_ids = inputs["input_ids"][0].tolist()
        tokens = tok.convert_ids_to_tokens(input_ids)

        # Merge subwords into words
        result: List[Tuple[str, str]] = []
        current_word = ""
        current_tag = ""
        for i, (token, tag_id, (start, end)) in enumerate(zip(tokens, predictions, offsets)):
            if token in (tok.cls_token, tok.sep_token, tok.pad_token):
                continue
            if token.startswith("##"):
                current_word += token[2:]
            else:
                if current_word:
                    result.append((current_word, current_tag))
                current_word = token
                current_tag = id2label.get(tag_id, "X")
        if current_word:
            result.append((current_word, current_tag))
        return result
    except Exception as e:
        logger.error(f"[bertbek] tag_pos error: {e}")
        return []


def embed(text: str):
    """Get sentence embedding using BERTbek base model. Returns tensor or None."""
    if not text or not text.strip():
        return None
    model, tok = _load_base()
    if model is None or tok is None:
        return None
    try:
        import torch
        inputs = tok(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = model(**inputs)
            # Mean pooling over tokens
            embedding = outputs.last_hidden_state.mean(dim=1).squeeze()
        return embedding.numpy()
    except Exception as e:
        logger.error(f"[bertbek] embed error: {e}")
        return None


def similarity(text1: str, text2: str) -> float:
    """Cosine similarity between two texts using BERTbek embeddings."""
    e1 = embed(text1)
    e2 = embed(text2)
    if e1 is None or e2 is None:
        return 0.0
    try:
        import numpy as np
        cos = float(np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2) + 1e-8))
        return max(0.0, min(1.0, cos))
    except Exception:
        return 0.0


def info() -> dict:
    """Return engine status info."""
    return {
        "enabled": BERTBEK_ENABLED,
        "available": is_available(),
        "pos_loaded": _pos_model is not None,
        "base_loaded": _base_model is not None,
        "pos_model": POS_MODEL_ID,
        "base_model": BASE_MODEL_ID,
    }
