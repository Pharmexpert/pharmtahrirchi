"""
Multilingual translation engine — facebook/nllb-200-distilled-1.3B.

Supports translation between 200 languages including:
  - English (eng_Latn)
  - Russian (rus_Cyrl)
  - Uzbek Latin (uzn_Latn)

Used in Tilshunos translate panel and Dashboard for cross-language translation
when target/source involves Russian.

Modes (env vars):
1. HF Inference API (default, free, HF_TOKEN required)
2. NLLB_LOCAL=1 — local transformers (~5GB RAM)
3. NLLB_ENDPOINT — dedicated endpoint
"""
import os
import logging
import asyncio
from typing import Optional

import requests

logger = logging.getLogger("translator_engine")

MODEL_ID = os.getenv("NLLB_MODEL_ID", "facebook/nllb-200-distilled-1.3B")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
ENDPOINT_URL = os.getenv("NLLB_ENDPOINT")
ENDPOINT_KEY = os.getenv("NLLB_API_KEY") or HF_TOKEN
LOCAL_MODE = os.getenv("NLLB_LOCAL") == "1"

HF_INFERENCE_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"

# Language code mapping (project lang → NLLB Flores-200 code)
LANG_MAP = {
    "en": "eng_Latn",
    "ru": "rus_Cyrl",
    "uz": "uzn_Latn",
    "uz-lat": "uzn_Latn",
    "uz-cyr": "uzn_Latn",  # NLLB uses Latin for Uzbek; we transliterate before
}

_local_model = None
_local_tokenizer = None
_local_lock = None


def _get_local():
    global _local_model, _local_tokenizer, _local_lock
    if not LOCAL_MODE:
        return None, None
    if _local_model is not None:
        return _local_model, _local_tokenizer
    try:
        import threading
        if _local_lock is None:
            _local_lock = threading.Lock()
        with _local_lock:
            if _local_model is None:
                from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
                logger.info(f"[NLLB] Loading {MODEL_ID} (~5GB RAM)")
                _local_tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=HF_TOKEN)
                _local_model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_ID, token=HF_TOKEN)
                _local_model.eval()
                logger.info("[NLLB] Model READY")
    except Exception as e:
        logger.error(f"[NLLB] local load failed: {e}")
        return None, None
    return _local_model, _local_tokenizer


def is_available() -> bool:
    if LOCAL_MODE:
        return True
    if ENDPOINT_URL and ENDPOINT_KEY:
        return True
    return bool(HF_TOKEN)


def get_mode() -> str:
    if LOCAL_MODE:
        return "local"
    if ENDPOINT_URL:
        return "endpoint"
    if HF_TOKEN:
        return "hf_inference"
    return "unavailable"


def _normalize_input(text: str, src_lang: str) -> str:
    """If source is Uzbek Cyrillic, transliterate to Latin (NLLB uses uzn_Latn)."""
    if src_lang == "uz-cyr":
        try:
            import transliterate as tl
            return tl.to_latin(text)
        except Exception:
            pass
    return text


def _normalize_output(text: str, tgt_lang: str) -> str:
    """If target is Uzbek Cyrillic, transliterate output back to Cyrillic."""
    if tgt_lang == "uz-cyr":
        try:
            import transliterate as tl
            return tl.to_cyrillic(text)
        except Exception:
            pass
    return text


def _translate_local(text: str, src: str, tgt: str) -> str:
    model, tok = _get_local()
    if not model or not tok:
        return ""
    try:
        import torch
        src_code = LANG_MAP.get(src, "eng_Latn")
        tgt_code = LANG_MAP.get(tgt, "uzn_Latn")
        tok.src_lang = src_code
        inputs = tok(text, return_tensors="pt", max_length=512, truncation=True)
        with torch.no_grad():
            forced_bos = tok.convert_tokens_to_ids(tgt_code)
            outputs = model.generate(
                **inputs,
                forced_bos_token_id=forced_bos,
                max_length=512,
                num_beams=5,
                early_stopping=True,
            )
        return tok.decode(outputs[0], skip_special_tokens=True)
    except Exception as e:
        logger.error(f"[NLLB local] {e}")
        return ""


def _translate_hf(text: str, src: str, tgt: str) -> str:
    if not HF_TOKEN:
        return ""
    try:
        import time
        src_code = LANG_MAP.get(src, "eng_Latn")
        tgt_code = LANG_MAP.get(tgt, "uzn_Latn")
        r = requests.post(
            HF_INFERENCE_URL,
            headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"},
            json={
                "inputs": text,
                "parameters": {"src_lang": src_code, "tgt_lang": tgt_code, "max_length": 512},
            },
            timeout=120,
        )
        if r.status_code == 503:
            time.sleep(5)
            r = requests.post(HF_INFERENCE_URL, headers={"Authorization": f"Bearer {HF_TOKEN}"}, json={"inputs": text, "parameters": {"src_lang": src_code, "tgt_lang": tgt_code}}, timeout=120)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                return data[0].get("translation_text", data[0].get("generated_text", ""))
            if isinstance(data, dict):
                return data.get("translation_text", data.get("generated_text", ""))
    except Exception as e:
        logger.error(f"[NLLB HF] {e}")
    return ""


def translate(text: str, source_lang: str, target_lang: str) -> str:
    if not text or not text.strip():
        return ""
    text = _normalize_input(text, source_lang)
    mode = get_mode()
    if mode == "local":
        result = _translate_local(text, source_lang, target_lang)
    else:
        result = _translate_hf(text, source_lang, target_lang)
    return _normalize_output(result, target_lang)


async def translate_async(text: str, source_lang: str, target_lang: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, translate, text, source_lang, target_lang)


def supports(src_lang: str, tgt_lang: str) -> bool:
    """Check if NLLB supports this language pair (currently any combo of en/ru/uz)."""
    return src_lang in LANG_MAP and tgt_lang in LANG_MAP
