"""
Tahrirchi engine — Uzbek-native NLP services via HuggingFace models.

Services (all local, no API needed):
  - Translation: tahrirchi/dilmash (en/ru/uz/kaa)
  - Transliteration: tahrirchi/dilmash-til
  - Spell correction: tahrirchi/tahrirchi-bert-base (already in bert_engine)

Modes:
  - TAHRIRCHI_LOCAL=1: load m2m100 locally (~500MB RAM per model)
  - Otherwise: use HF Inference API (HF_TOKEN)

Provides:
  - translate(text, src, tgt)
  - transliterate(text, target)
  - is_available()
  - get_mode()
"""
import os
import logging
import asyncio
from typing import Optional

import requests

logger = logging.getLogger("tahrirchi_engine")

MODEL_DILMASH = os.getenv("TAHRIRCHI_DILMASH", "tahrirchi/dilmash")
MODEL_TIL = os.getenv("TAHRIRCHI_TIL", "tahrirchi/dilmash-til")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
LOCAL_MODE = os.getenv("TAHRIRCHI_LOCAL") == "1"

_dilmash_model = None
_dilmash_tokenizer = None
_til_model = None
_til_tokenizer = None
_lock = None


def _get_lock():
    global _lock
    if _lock is None:
        import threading
        _lock = threading.Lock()
    return _lock


# Language code mapping for m2m100
LANG_MAP = {
    "en": "en",
    "ru": "ru",
    "uz": "uz",
    "uz-lat": "uz",
    "uz-cyr": "uz",
    "kaa": "kaa",  # Karakalpak
}


def _load_dilmash():
    global _dilmash_model, _dilmash_tokenizer
    if _dilmash_model is not None:
        return _dilmash_model, _dilmash_tokenizer
    if not LOCAL_MODE:
        return None, None
    try:
        with _get_lock():
            if _dilmash_model is None:
                from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
                logger.info(f"[tahrirchi] Loading {MODEL_DILMASH} (~500MB)")
                _dilmash_tokenizer = M2M100Tokenizer.from_pretrained(MODEL_DILMASH, token=HF_TOKEN)
                _dilmash_model = M2M100ForConditionalGeneration.from_pretrained(MODEL_DILMASH, token=HF_TOKEN)
                _dilmash_model.eval()
                logger.info("[tahrirchi] dilmash READY")
    except Exception as e:
        logger.error(f"[tahrirchi] dilmash load failed: {e}")
    return _dilmash_model, _dilmash_tokenizer


def _load_til():
    global _til_model, _til_tokenizer
    if _til_model is not None:
        return _til_model, _til_tokenizer
    if not LOCAL_MODE:
        return None, None
    try:
        with _get_lock():
            if _til_model is None:
                from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
                logger.info(f"[tahrirchi] Loading {MODEL_TIL}")
                _til_tokenizer = M2M100Tokenizer.from_pretrained(MODEL_TIL, token=HF_TOKEN)
                _til_model = M2M100ForConditionalGeneration.from_pretrained(MODEL_TIL, token=HF_TOKEN)
                _til_model.eval()
                logger.info("[tahrirchi] dilmash-til READY")
    except Exception as e:
        logger.error(f"[tahrirchi] til load failed: {e}")
    return _til_model, _til_tokenizer


def is_available() -> bool:
    if LOCAL_MODE:
        return True
    return bool(HF_TOKEN)


def get_mode() -> str:
    if LOCAL_MODE:
        return "local_dilmash"
    if HF_TOKEN:
        return "hf_inference"
    return "unavailable"


def _translate_local(text: str, src: str, tgt: str) -> str:
    model, tok = _load_dilmash()
    if not model or not tok:
        return ""
    try:
        import torch
        src_code = LANG_MAP.get(src, "en")
        tgt_code = LANG_MAP.get(tgt, "uz")
        tok.src_lang = src_code
        inputs = tok(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                forced_bos_token_id=tok.get_lang_id(tgt_code),
                max_length=512,
                num_beams=4,
                early_stopping=True,
            )
        return tok.decode(outputs[0], skip_special_tokens=True)
    except Exception as e:
        logger.error(f"[tahrirchi translate] {e}")
        return ""


def _translate_hf(text: str, src: str, tgt: str) -> str:
    if not HF_TOKEN:
        return ""
    try:
        url = f"https://api-inference.huggingface.co/models/{MODEL_DILMASH}"
        src_code = LANG_MAP.get(src, "en")
        tgt_code = LANG_MAP.get(tgt, "uz")
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={
                "inputs": text,
                "parameters": {"src_lang": src_code, "tgt_lang": tgt_code, "max_length": 512},
            },
            timeout=120,
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                return data[0].get("translation_text", data[0].get("generated_text", ""))
            if isinstance(data, dict):
                return data.get("translation_text", data.get("generated_text", ""))
    except Exception as e:
        logger.error(f"[tahrirchi HF] {e}")
    return ""


def translate(text: str, source_lang: str = "en", target_lang: str = "uz") -> str:
    """Translate between en/ru/uz/kaa via Tahrirchi dilmash."""
    if not text or not text.strip():
        return ""
    mode = get_mode()
    if mode == "local_dilmash":
        return _translate_local(text, source_lang, target_lang)
    if mode == "hf_inference":
        return _translate_hf(text, source_lang, target_lang)
    return ""


async def translate_async(text: str, source_lang: str = "en", target_lang: str = "uz") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, translate, text, source_lang, target_lang)


def transliterate(text: str, target: str = "latin") -> str:
    """
    Transliterate between Latin/Cyrillic Uzbek using Tahrirchi dilmash-til.
    Falls back to existing `transliterate.py` if model unavailable.
    """
    if not text or not text.strip():
        return text
    # Check if already in target script — skip
    try:
        has_cyr = any("\u0400" <= ch <= "\u04FF" for ch in text)
        if (target == "latin" and not has_cyr) or (target == "cyrillic" and has_cyr):
            return text  # already in target
    except Exception:
        pass

    # Try model-based transliteration
    if LOCAL_MODE:
        model, tok = _load_til()
        if model and tok:
            try:
                import torch
                tok.src_lang = "uz"
                inputs = tok(text, return_tensors="pt", truncation=True, max_length=512)
                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        forced_bos_token_id=tok.get_lang_id("uz"),
                        max_length=512,
                        num_beams=4,
                    )
                return tok.decode(outputs[0], skip_special_tokens=True)
            except Exception as e:
                logger.warning(f"[tahrirchi transliterate model] {e}")

    # Fallback: use local transliterate.py
    try:
        import transliterate as tl
        if target == "latin":
            return tl.to_latin(text)
        return tl.to_cyrillic(text)
    except Exception:
        return text


async def transliterate_async(text: str, target: str = "latin") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, transliterate, text, target)
