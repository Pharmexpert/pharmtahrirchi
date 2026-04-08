"""
Advanced Uzbek NLP engines — niche models for higher-than-competitor quality.

Integrated models (all from HuggingFace):
  1. jmshd/whisper-uz — best Uzbek ASR (48K+ downloads)
  2. MaksudSharipov/Uzbek-POS-Tagger-TahrirchiBERT — POS tagging
  3. islomov/rubai-corrector-ocr-books-uz — OCR text correction
  4. tahrirchi/tahrirchi-bert-small — fast BERT for quick tasks
  5. Arofat/uzbek-dependency-parser — dependency parsing

Goal: Surpass tilmoch.ai and savodxon.uz quality by combining:
  - Native Uzbek models (instead of multilingual compromises)
  - Specialized correctors (OCR, transcript) fused into sayqallash
  - POS-aware morphology validator for BERT predict_mask
  - Audio transcription for voice input
"""
import os
import logging
import asyncio
from typing import Optional, List, Dict, Any

logger = logging.getLogger("uzbek_engines")

HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")

# Feature flags — load on demand, not at boot
UZBEK_POS_ENABLED = os.getenv("UZBEK_POS_ENABLED", "1") == "1"
UZBEK_CORRECTOR_ENABLED = os.getenv("UZBEK_CORRECTOR_ENABLED", "1") == "1"
UZBEK_WHISPER_ENABLED = os.getenv("UZBEK_WHISPER_ENABLED", "0") == "1"  # Large, opt-in

_pos_pipe = None
_corrector_pipe = None
_whisper_pipe = None
_lock = None


def _get_lock():
    global _lock
    if _lock is None:
        import threading
        _lock = threading.Lock()
    return _lock


# ─────────────────────────────────────────────
# 1. POS Tagger
# ─────────────────────────────────────────────
def _get_pos():
    global _pos_pipe
    if not UZBEK_POS_ENABLED or _pos_pipe is not None:
        return _pos_pipe
    try:
        with _get_lock():
            if _pos_pipe is None:
                from transformers import pipeline
                logger.info("[uzbek_pos] Loading MaksudSharipov/Uzbek-POS-Tagger-TahrirchiBERT")
                _pos_pipe = pipeline(
                    "token-classification",
                    model="MaksudSharipov/Uzbek-POS-Tagger-TahrirchiBERT",
                    token=HF_TOKEN,
                    aggregation_strategy="simple",
                )
                logger.info("[uzbek_pos] READY")
    except Exception as e:
        logger.warning(f"[uzbek_pos] load failed: {e}")
    return _pos_pipe


def pos_tag(text: str) -> List[Dict[str, Any]]:
    """Return list of {word, pos, start, end} for Uzbek text."""
    if not text:
        return []
    pipe = _get_pos()
    if not pipe:
        return []
    try:
        results = pipe(text)
        out = []
        for r in results:
            out.append({
                "word": r.get("word", "").strip(),
                "pos": r.get("entity_group", "UNK"),
                "start": int(r.get("start", 0)),
                "end": int(r.get("end", 0)),
                "score": float(r.get("score", 0.0)),
            })
        return out
    except Exception as e:
        logger.warning(f"[pos_tag] {e}")
        return []


async def pos_tag_async(text: str) -> List[Dict[str, Any]]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, pos_tag, text)


# ─────────────────────────────────────────────
# 2. Text Corrector (OCR/transcript)
# ─────────────────────────────────────────────
def _get_corrector():
    global _corrector_pipe
    if not UZBEK_CORRECTOR_ENABLED or _corrector_pipe is not None:
        return _corrector_pipe
    try:
        with _get_lock():
            if _corrector_pipe is None:
                from transformers import pipeline
                logger.info("[uzbek_corrector] Loading islomov/rubai-corrector-ocr-books-uz")
                _corrector_pipe = pipeline(
                    "text2text-generation",
                    model="islomov/rubai-corrector-ocr-books-uz",
                    token=HF_TOKEN,
                )
                logger.info("[uzbek_corrector] READY")
    except Exception as e:
        logger.warning(f"[uzbek_corrector] load failed: {e}")
    return _corrector_pipe


def correct_text(text: str) -> str:
    """Uzbek text correction (OCR/transcript quality)."""
    if not text or len(text) < 5:
        return text
    pipe = _get_corrector()
    if not pipe:
        return text
    try:
        result = pipe(text, max_length=512, num_beams=4, early_stopping=True)
        if result and isinstance(result, list):
            return result[0].get("generated_text", text)
    except Exception as e:
        logger.warning(f"[correct_text] {e}")
    return text


async def correct_text_async(text: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, correct_text, text)


# ─────────────────────────────────────────────
# 3. Whisper Uzbek ASR
# ─────────────────────────────────────────────
def _get_whisper():
    global _whisper_pipe
    if not UZBEK_WHISPER_ENABLED or _whisper_pipe is not None:
        return _whisper_pipe
    try:
        with _get_lock():
            if _whisper_pipe is None:
                from transformers import pipeline
                logger.info("[whisper_uz] Loading jmshd/whisper-uz")
                _whisper_pipe = pipeline(
                    "automatic-speech-recognition",
                    model="jmshd/whisper-uz",
                    token=HF_TOKEN,
                )
                logger.info("[whisper_uz] READY")
    except Exception as e:
        logger.warning(f"[whisper_uz] load failed: {e}")
    return _whisper_pipe


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.mp3") -> str:
    """Uzbek audio transcription."""
    pipe = _get_whisper()
    if not pipe:
        return ""
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix="." + filename.rsplit(".", 1)[-1], delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            result = pipe(tmp_path)
            return result.get("text", "") if isinstance(result, dict) else ""
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"[transcribe_audio] {e}")
        return ""


async def transcribe_audio_async(audio_bytes: bytes, filename: str = "audio.mp3") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, transcribe_audio, audio_bytes, filename)


# ─────────────────────────────────────────────
# Status
# ─────────────────────────────────────────────
def get_status() -> Dict[str, Any]:
    return {
        "pos_tagger": {
            "available": UZBEK_POS_ENABLED,
            "loaded": _pos_pipe is not None,
            "model": "MaksudSharipov/Uzbek-POS-Tagger-TahrirchiBERT",
        },
        "corrector": {
            "available": UZBEK_CORRECTOR_ENABLED,
            "loaded": _corrector_pipe is not None,
            "model": "islomov/rubai-corrector-ocr-books-uz",
        },
        "whisper_uz": {
            "available": UZBEK_WHISPER_ENABLED,
            "loaded": _whisper_pipe is not None,
            "model": "jmshd/whisper-uz",
        },
    }


def is_available() -> bool:
    return UZBEK_POS_ENABLED or UZBEK_CORRECTOR_ENABLED or UZBEK_WHISPER_ENABLED


def get_mode() -> str:
    return "local"
