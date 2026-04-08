"""
Mistral-7B-Instruct-Uz integration.

Three execution modes (auto-detected by env vars):

1. **HF_INFERENCE** — HuggingFace Inference API (free tier, recommended for Railway)
   ENV: HF_TOKEN=hf_xxx (must accept model license at huggingface.co/behbudiy/Mistral-7B-Instruct-Uz)

2. **HF_ENDPOINT** — Self-hosted inference endpoint (HF Inference Endpoints / Together / Replicate)
   ENV: MISTRAL_ENDPOINT=https://your-endpoint.com/v1/completions
        MISTRAL_API_KEY=...

3. **LOCAL_GGUF** — Local llama.cpp + GGUF quantized model (for self-hosted Railway with >=8GB RAM)
   ENV: MISTRAL_LOCAL=1
        MISTRAL_GGUF_PATH=/app/data/mistral-7b-instruct-uz-q4_K_M.gguf

The module exposes:
    - is_available() → bool
    - generate(prompt, system=None, max_tokens=512, temperature=0.3) → str
    - chat(messages, ...) → str
    - improve_text(text, lang) → improved text (Uzbek-aware editing)
    - translate(text, src, tgt) → translation
    - score_translation(src, tgt) → 0..1 quality score
    - learn_record(prompt, response) → log to learning DB

Designed to be drop-in replacement / supplement for ai_helpers.generate_ai_content().
"""
import os
import json
import logging
import time
import asyncio
from typing import List, Dict, Optional, Any

import requests

logger = logging.getLogger("mistral_engine")

MODEL_ID = os.getenv("MISTRAL_MODEL_ID", "behbudiy/Mistral-7B-Instruct-Uz")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
HF_INFERENCE_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"
ENDPOINT_URL = os.getenv("MISTRAL_ENDPOINT")
ENDPOINT_KEY = os.getenv("MISTRAL_API_KEY") or HF_TOKEN
LOCAL_MODE = os.getenv("MISTRAL_LOCAL") == "1"
GGUF_PATH = os.getenv("MISTRAL_GGUF_PATH", "/app/data/mistral-7b-instruct-uz.gguf")

FULL_HF_MODE = os.getenv("MISTRAL_FULL_HF") == "1"  # Use transformers + full HF model (no GGUF)

_local_llm = None
_local_lock = None
_hf_model = None
_hf_tokenizer = None
_hf_lock = None


def _get_local_llm():
    """Lazy-load llama-cpp model if local mode enabled."""
    global _local_llm, _local_lock
    if not LOCAL_MODE:
        return None
    if _local_llm is not None:
        return _local_llm
    try:
        import threading
        if _local_lock is None:
            _local_lock = threading.Lock()
        with _local_lock:
            if _local_llm is None:
                from llama_cpp import Llama  # type: ignore
                logger.info(f"[Mistral] Loading local GGUF: {GGUF_PATH}")
                _local_llm = Llama(
                    model_path=GGUF_PATH,
                    n_ctx=4096,
                    n_threads=int(os.getenv("LLAMA_THREADS", "4")),
                    n_gpu_layers=int(os.getenv("LLAMA_GPU_LAYERS", "0")),
                    verbose=False,
                )
                logger.info("[Mistral] Local GGUF model READY")
    except Exception as e:
        logger.error(f"[Mistral] Local GGUF load failed: {e}")
        return None
    return _local_llm


def _get_hf_model():
    """Lazy-load full HF transformers model (~14GB RAM)."""
    global _hf_model, _hf_tokenizer, _hf_lock
    if not FULL_HF_MODE:
        return None, None
    if _hf_model is not None:
        return _hf_model, _hf_tokenizer
    try:
        import threading
        if _hf_lock is None:
            _hf_lock = threading.Lock()
        with _hf_lock:
            if _hf_model is None:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer
                logger.info(f"[Mistral] Loading {MODEL_ID} (CPU bf16, ~14GB RAM, 3-5 min)")
                _hf_tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=HF_TOKEN)
                load_kwargs = {"token": HF_TOKEN, "low_cpu_mem_usage": True}
                if torch.cuda.is_available():
                    load_kwargs["torch_dtype"] = torch.float16
                    load_kwargs["device_map"] = "auto"
                else:
                    load_kwargs["torch_dtype"] = torch.bfloat16
                _hf_model = AutoModelForCausalLM.from_pretrained(MODEL_ID, **load_kwargs)
                _hf_model.eval()
                logger.info("[Mistral] Full HF model READY (bf16 CPU)")
    except Exception as e:
        logger.error(f"[Mistral] Full HF model load failed: {e}")
        return None, None
    return _hf_model, _hf_tokenizer


def is_available() -> bool:
    if FULL_HF_MODE and HF_TOKEN:
        return True
    if LOCAL_MODE:
        return os.path.exists(GGUF_PATH)
    if ENDPOINT_URL and ENDPOINT_KEY:
        return True
    if HF_TOKEN:
        return True
    return False


def get_mode() -> str:
    if FULL_HF_MODE and HF_TOKEN:
        return "full_hf"
    if LOCAL_MODE and os.path.exists(GGUF_PATH):
        return "local_gguf"
    if ENDPOINT_URL and ENDPOINT_KEY:
        return "hf_endpoint"
    if HF_TOKEN:
        return "hf_inference"
    return "unavailable"


def _build_prompt(messages: List[Dict[str, str]]) -> str:
    """Build Mistral instruction format from messages list."""
    parts = []
    system = None
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        elif m["role"] == "user":
            content = m["content"]
            if system:
                parts.append(f"<s>[INST] {system}\n\n{content} [/INST]")
                system = None
            else:
                parts.append(f"<s>[INST] {content} [/INST]")
        elif m["role"] == "assistant":
            parts.append(f" {m['content']}</s>")
    return "".join(parts)


def chat(messages: List[Dict[str, str]], max_tokens: int = 512, temperature: float = 0.3) -> str:
    """Universal chat → returns assistant text."""
    mode = get_mode()
    prompt = _build_prompt(messages)

    if mode == "full_hf":
        model, tokenizer = _get_hf_model()
        if not model or not tokenizer:
            return ""
        try:
            import torch
            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=4096)
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=temperature > 0,
                    pad_token_id=tokenizer.eos_token_id,
                )
            full = tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Extract response (after last [/INST])
            if "[/INST]" in full:
                return full.split("[/INST]")[-1].strip()
            return full[len(prompt):].strip()
        except Exception as e:
            logger.error(f"[Mistral full HF] {e}")
            return ""

    if mode == "local_gguf":
        llm = _get_local_llm()
        if not llm:
            return ""
        try:
            out = llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["</s>", "[INST]"],
            )
            return out["choices"][0]["text"].strip()
        except Exception as e:
            logger.error(f"[Mistral local] {e}")
            return ""

    if mode == "hf_endpoint":
        try:
            r = requests.post(
                ENDPOINT_URL,
                headers={"Authorization": f"Bearer {ENDPOINT_KEY}", "Content-Type": "application/json"},
                json={"inputs": prompt, "parameters": {"max_new_tokens": max_tokens, "temperature": temperature, "return_full_text": False}},
                timeout=120,
            )
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and data:
                    return data[0].get("generated_text", "").strip()
                return data.get("generated_text", "").strip() if isinstance(data, dict) else ""
        except Exception as e:
            logger.error(f"[Mistral endpoint] {e}")
        return ""

    if mode == "hf_inference":
        try:
            r = requests.post(
                HF_INFERENCE_URL,
                headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"},
                json={"inputs": prompt, "parameters": {"max_new_tokens": max_tokens, "temperature": temperature, "return_full_text": False}},
                timeout=120,
            )
            if r.status_code == 503:
                # model loading — retry once after wait
                time.sleep(5)
                r = requests.post(HF_INFERENCE_URL, headers={"Authorization": f"Bearer {HF_TOKEN}"}, json={"inputs": prompt, "parameters": {"max_new_tokens": max_tokens, "temperature": temperature, "return_full_text": False}}, timeout=120)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and data:
                    return data[0].get("generated_text", "").strip()
                if isinstance(data, dict):
                    return data.get("generated_text", "").strip()
        except Exception as e:
            logger.error(f"[Mistral HF] {e}")
        return ""

    return ""


async def chat_async(messages: List[Dict[str, str]], max_tokens: int = 512, temperature: float = 0.3) -> str:
    """Async wrapper to keep FastAPI handlers non-blocking."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: chat(messages, max_tokens, temperature))


def generate(prompt: str, system: Optional[str] = None, max_tokens: int = 512, temperature: float = 0.3) -> str:
    msgs: List[Dict[str, str]] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return chat(msgs, max_tokens=max_tokens, temperature=temperature)


async def generate_async(prompt: str, system: Optional[str] = None, max_tokens: int = 512, temperature: float = 0.3) -> str:
    msgs: List[Dict[str, str]] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return await chat_async(msgs, max_tokens=max_tokens, temperature=temperature)


# ─────────────────────────────────────────────
# Pharma-specific high-level helpers
# ─────────────────────────────────────────────

async def improve_text(text: str, lang: str = "uz") -> str:
    """Илмий таҳрир: грамматика, имло, услуб тузатилади. Структурани сақлайди."""
    system = (
        "Сен ўзбек тилини мукаммал биладиган илмий муҳаррирсан. "
        "Берилган матнни илмий-тиббий услубда тузат: имло, грамматика, синтаксис, тиниш белгиларини тўғрила. "
        "МАТН СТРУКТУРАСИНИ САҚЛА (абзацлар, рўйхатлар, формулалар, рақамлар). "
        "Фақат тузатилган матнни қайтар, изоҳсиз."
    )
    return await generate_async(text, system=system, max_tokens=2048, temperature=0.2)


async def translate(text: str, source_lang: str, target_lang: str) -> str:
    """Илмий таржима: фарма терминлар сақланган ҳолда таржима."""
    label = {"en": "ингилизча", "ru": "русча", "uz": "ўзбекча", "uz-lat": "ўзбекча (лотин)", "uz-cyr": "ўзбекча (кирилл)"}
    src = label.get(source_lang, source_lang)
    tgt = label.get(target_lang, target_lang)
    system = (
        f"Сен профессионал илмий таржимонсан. {src}дан {tgt}га таржима қиласан. "
        "Тиббий ва фарма терминларини тўғри ишлат, асл маънони сақла, услубни илмий тутиб тур. "
        "Фақат таржимани қайтар, изоҳсиз."
    )
    return await generate_async(text, system=system, max_tokens=2048, temperature=0.3)


async def score_translation(src: str, tgt: str) -> Dict[str, Any]:
    """Таржима сифатини баҳолаш — BERT sentence similarity + LLM фикри."""
    score = 0.0
    try:
        import bert_engine
        if bert_engine.engine.initialized:
            score = float(bert_engine.engine.sentence_similarity(src, tgt))
    except Exception:
        pass

    note = ""
    try:
        prompt = f"АСЛ:\n{src}\n\nТАРЖИМА:\n{tgt}\n\nТаржимани 1-10 баҳола (фақат рақам) ва 1 жумлада камчилигини айт."
        note = await generate_async(prompt, max_tokens=120, temperature=0.0)
    except Exception:
        pass

    return {"semantic_score": round(score, 3), "llm_note": note, "source": src[:200], "target": tgt[:200]}


async def explain_term(word: str, lang: str = "uz") -> str:
    """Луғат тушунтирмаси (тиббий контекстда)."""
    prompt = f'"{word}" сўзининг тиббий-фарма соҳасидаги маъносини 2-3 жумлада тушунтир.'
    return await generate_async(prompt, max_tokens=200, temperature=0.2)


def learn_record(prompt: str, response: str, kind: str = "edit") -> None:
    """Пайдо бўлган AI самарасини self-learning логига ёзиш — кейинчалик fine-tune учун."""
    try:
        import db
        conn = db.connect_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS llm_training_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT,
                prompt TEXT,
                response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("INSERT INTO llm_training_log (kind, prompt, response) VALUES (?, ?, ?)", (kind, prompt[:5000], response[:5000]))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"[Mistral] learn_record failed: {e}")
