"""
Russian text correction engine — ai-forever/sage-fredt5-large.

Used for: scientific Russian text editing, spell/punctuation correction.
Integrated with Tilshunos (Russian column) and Dashboard (Russian source text).

Modes (auto-selected by env vars):
1. HF Inference API — default (free, requires HF_TOKEN)
2. Local transformers — RUSSIAN_LOCAL=1 + ~3GB RAM
3. HF Endpoint — RUSSIAN_ENDPOINT=https://...

Self-improvement: corrections logged to llm_training_log table.
"""
import os
import logging
import asyncio
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger("russian_engine")

MODEL_ID = os.getenv("RUSSIAN_MODEL_ID", "ai-forever/sage-fredt5-large")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
ENDPOINT_URL = os.getenv("RUSSIAN_ENDPOINT")
ENDPOINT_KEY = os.getenv("RUSSIAN_API_KEY") or HF_TOKEN
LOCAL_MODE = os.getenv("RUSSIAN_LOCAL") == "1"

HF_INFERENCE_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"

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
                from transformers import T5ForConditionalGeneration, AutoTokenizer
                logger.info(f"[Russian] Loading {MODEL_ID} (~3GB RAM)")
                _local_tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=HF_TOKEN)
                _local_model = T5ForConditionalGeneration.from_pretrained(MODEL_ID, token=HF_TOKEN)
                _local_model.eval()
                logger.info("[Russian] Model READY")
    except Exception as e:
        logger.error(f"[Russian] local load failed: {e}")
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


def _correct_local(text: str) -> str:
    model, tok = _get_local()
    if not model or not tok:
        return text
    try:
        import torch
        inputs = tok(text, return_tensors="pt", max_length=512, truncation=True)
        with torch.no_grad():
            outputs = model.generate(
                **inputs, max_length=512, num_beams=4, early_stopping=True
            )
        return tok.decode(outputs[0], skip_special_tokens=True)
    except Exception as e:
        logger.error(f"[Russian local] {e}")
        return text


def _correct_hf(text: str) -> str:
    if not HF_TOKEN:
        return text
    try:
        import time
        r = requests.post(
            HF_INFERENCE_URL,
            headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"},
            json={"inputs": text, "parameters": {"max_length": 512, "num_beams": 4}},
            timeout=120,
        )
        if r.status_code == 503:
            time.sleep(5)
            r = requests.post(HF_INFERENCE_URL, headers={"Authorization": f"Bearer {HF_TOKEN}"}, json={"inputs": text}, timeout=120)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                return data[0].get("generated_text", text)
            if isinstance(data, dict):
                return data.get("generated_text", text)
    except Exception as e:
        logger.error(f"[Russian HF] {e}")
    return text


def correct(text: str) -> str:
    """Synchronous Russian text correction."""
    if not text or not text.strip():
        return text
    mode = get_mode()
    if mode == "local":
        return _correct_local(text)
    if mode in ("endpoint", "hf_inference"):
        return _correct_hf(text)
    return text


async def correct_async(text: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, correct, text)


async def improve(text: str) -> str:
    """High-level: scientific Russian editing with self-learning logging."""
    corrected = await correct_async(text)
    if corrected and corrected != text:
        try:
            import db
            conn = db.connect_db()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS llm_training_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT, prompt TEXT, response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("INSERT INTO llm_training_log (kind, prompt, response) VALUES (?, ?, ?)",
                        ("russian_correct", text[:5000], corrected[:5000]))
            conn.commit()
            conn.close()
        except Exception:
            pass
    return corrected
