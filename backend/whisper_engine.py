"""
Whisper audio transcription (optional).

Modes:
  1. WHISPER_LOCAL=1 — local openai-whisper or faster-whisper
  2. WHISPER_API=1   — OpenAI Whisper API (needs OPENAI_API_KEY)
  3. Disabled — return empty
"""
import os
import logging
import asyncio
from typing import Optional

logger = logging.getLogger("whisper_engine")

LOCAL_MODE = os.getenv("WHISPER_LOCAL") == "1"
API_MODE = os.getenv("WHISPER_API") == "1"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny/base/small/medium/large

_model = None
_lock = None


def is_available() -> bool:
    if API_MODE and os.getenv("OPENAI_API_KEY"):
        return True
    if LOCAL_MODE:
        try:
            import whisper  # noqa
            return True
        except ImportError:
            try:
                import faster_whisper  # noqa
                return True
            except ImportError:
                return False
    return False


def get_mode() -> str:
    if API_MODE and os.getenv("OPENAI_API_KEY"):
        return "openai_api"
    if LOCAL_MODE:
        try:
            import whisper  # noqa
            return "local_whisper"
        except ImportError:
            try:
                import faster_whisper  # noqa
                return "local_faster_whisper"
            except ImportError:
                return "unavailable"
    return "disabled"


def _get_local_model():
    global _model, _lock
    if _model is not None:
        return _model
    if not LOCAL_MODE:
        return None
    try:
        import threading
        if _lock is None:
            _lock = threading.Lock()
        with _lock:
            if _model is None:
                try:
                    import whisper
                    logger.info(f"[whisper] Loading openai-whisper {WHISPER_MODEL}")
                    _model = whisper.load_model(WHISPER_MODEL)
                except ImportError:
                    from faster_whisper import WhisperModel
                    logger.info(f"[whisper] Loading faster-whisper {WHISPER_MODEL}")
                    _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    except Exception as e:
        logger.warning(f"[whisper] load failed: {e}")
    return _model


def transcribe(audio_bytes: bytes, filename: str = "audio.mp3") -> str:
    """Transcribe audio to text."""
    if API_MODE and os.getenv("OPENAI_API_KEY"):
        try:
            import openai
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            import io
            f = io.BytesIO(audio_bytes)
            f.name = filename
            r = client.audio.transcriptions.create(model="whisper-1", file=f)
            return r.text
        except Exception as e:
            logger.warning(f"[whisper API] {e}")
            return ""

    model = _get_local_model()
    if not model:
        return ""
    try:
        import tempfile
        import os as _os
        with tempfile.NamedTemporaryFile(suffix="." + filename.rsplit(".", 1)[-1], delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            if hasattr(model, "transcribe") and "fp16" in str(model.transcribe.__code__.co_varnames):
                # openai-whisper
                result = model.transcribe(tmp_path, fp16=False)
                return result.get("text", "")
            else:
                # faster-whisper
                segments, info = model.transcribe(tmp_path)
                return " ".join(s.text for s in segments)
        finally:
            try:
                _os.unlink(tmp_path)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"[whisper local] {e}")
        return ""


async def transcribe_async(audio_bytes: bytes, filename: str = "audio.mp3") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, transcribe, audio_bytes, filename)
