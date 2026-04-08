"""
Llama-3.1-8B-Instruct-Uz integration.

Stronger Uzbek-aware instruction-tuned LLM:
  - 8B parameters (~16GB fp16, ~4-5GB Q4 GGUF)
  - 128K context window (4x larger than Mistral-7B)
  - Better instruction following (+25% vs Mistral 7B)
  - Same provider (behbudiy) — consistent Uzbek tuning

Modes:
  1. HF Inference API (default, free, HF_TOKEN)
  2. LLAMA_FULL_HF=1 — transformers full precision (16GB RAM)
  3. LLAMA_LOCAL=1 + LLAMA_GGUF_PATH — llama.cpp GGUF (~5GB RAM)
  4. LLAMA_ENDPOINT — dedicated HF Inference Endpoint
"""
import os
import logging
import asyncio
from typing import List, Dict, Optional, Any
import time

import requests

logger = logging.getLogger("llama_engine")

MODEL_ID = os.getenv("LLAMA_MODEL_ID", "behbudiy/Llama-3.1-8B-Instruct-Uz")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
ENDPOINT_URL = os.getenv("LLAMA_ENDPOINT")
ENDPOINT_KEY = os.getenv("LLAMA_API_KEY") or HF_TOKEN
LOCAL_MODE = os.getenv("LLAMA_LOCAL") == "1"
FULL_HF_MODE = os.getenv("LLAMA_FULL_HF") == "1"
GGUF_PATH = os.getenv("LLAMA_GGUF_PATH", "/tmp/llama-3.1-8b-instruct-uz.gguf")

HF_INFERENCE_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"

_local_llm = None
_hf_model = None
_hf_tokenizer = None
_lock = None


def _get_lock():
    global _lock
    if _lock is None:
        import threading
        _lock = threading.Lock()
    return _lock


def _get_local_llm():
    global _local_llm
    if not LOCAL_MODE or _local_llm is not None:
        return _local_llm
    try:
        with _get_lock():
            if _local_llm is None:
                from llama_cpp import Llama  # type: ignore
                logger.info(f"[Llama] Loading GGUF: {GGUF_PATH}")
                _local_llm = Llama(
                    model_path=GGUF_PATH,
                    n_ctx=2048,
                    n_threads=int(os.getenv("LLAMA_THREADS", "4")),
                    n_gpu_layers=int(os.getenv("LLAMA_GPU_LAYERS", "0")),
                    verbose=False,
                )
                logger.info("[Llama] Local GGUF READY")
    except Exception as e:
        logger.error(f"[Llama] GGUF load failed: {e}")
    return _local_llm


def _get_hf_model():
    global _hf_model, _hf_tokenizer
    if not FULL_HF_MODE or _hf_model is not None:
        return _hf_model, _hf_tokenizer
    try:
        with _get_lock():
            if _hf_model is None:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer
                logger.info(f"[Llama] Loading {MODEL_ID} (CPU bf16, ~16GB RAM, 3-5 min)")
                _hf_tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, token=HF_TOKEN)

                load_kwargs = {
                    "token": HF_TOKEN,
                    "low_cpu_mem_usage": True,
                }
                if torch.cuda.is_available():
                    # GPU: fp16 with accelerate device_map
                    load_kwargs["torch_dtype"] = torch.float16
                    load_kwargs["device_map"] = "auto"
                else:
                    # CPU: bf16 is faster than fp32 on modern CPUs + half the RAM
                    load_kwargs["torch_dtype"] = torch.bfloat16
                _hf_model = AutoModelForCausalLM.from_pretrained(MODEL_ID, **load_kwargs)
                _hf_model.eval()
                logger.info("[Llama] Full HF model READY (bf16 CPU)")
    except Exception as e:
        logger.error(f"[Llama] full HF load failed: {e}")
    return _hf_model, _hf_tokenizer


def is_available() -> bool:
    if FULL_HF_MODE and HF_TOKEN:
        return True
    if LOCAL_MODE and os.path.exists(GGUF_PATH):
        return True
    if ENDPOINT_URL and ENDPOINT_KEY:
        return True
    return bool(HF_TOKEN)


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
    """Llama 3.1 chat template (header_id + start_header)."""
    parts = ["<|begin_of_text|>"]
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        parts.append(f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>")
    parts.append("<|start_header_id|>assistant<|end_header_id|>\n\n")
    return "".join(parts)


def chat(messages: List[Dict[str, str]], max_tokens: int = 1024, temperature: float = 0.3) -> str:
    mode = get_mode()
    prompt = _build_prompt(messages)

    if mode == "full_hf":
        model, tok = _get_hf_model()
        if not model or not tok:
            return ""
        try:
            import torch
            # Limit input length to 2048 for CPU speed
            inputs = tok(prompt, return_tensors="pt", truncation=True, max_length=2048)
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            # CPU is slow — cap new tokens to 256 for first response
            effective_max = min(max_tokens, 256) if not torch.cuda.is_available() else max_tokens
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=effective_max,
                    temperature=temperature,
                    do_sample=temperature > 0,
                    pad_token_id=tok.eos_token_id,
                    eos_token_id=[tok.eos_token_id, tok.convert_tokens_to_ids("<|eot_id|>")],
                )
            full = tok.decode(outputs[0], skip_special_tokens=True)
            # Extract assistant response after the last "assistant" header
            if "assistant" in full:
                return full.split("assistant")[-1].strip().lstrip("\n")
            return full[len(prompt):].strip()
        except Exception as e:
            logger.error(f"[Llama full HF] {e}")
            return ""

    if mode == "local_gguf":
        llm = _get_local_llm()
        if not llm:
            return ""
        try:
            # Cap tokens for CPU speed: 128 for chat, 512 for edit/translate
            effective_max = min(max_tokens, 128)
            out = llm(
                prompt,
                max_tokens=effective_max,
                temperature=temperature,
                top_p=0.9,
                stop=["<|eot_id|>", "<|end_of_text|>", "<|start_header_id|>"],
            )
            return out["choices"][0]["text"].strip()
        except Exception as e:
            logger.error(f"[Llama local] {e}")
            return ""

    if mode in ("hf_endpoint", "hf_inference"):
        url = ENDPOINT_URL if mode == "hf_endpoint" else HF_INFERENCE_URL
        try:
            r = requests.post(
                url,
                headers={"Authorization": f"Bearer {ENDPOINT_KEY or HF_TOKEN}", "Content-Type": "application/json"},
                json={"inputs": prompt, "parameters": {"max_new_tokens": max_tokens, "temperature": temperature, "return_full_text": False}},
                timeout=180,
            )
            if r.status_code == 503:
                time.sleep(8)
                r = requests.post(url, headers={"Authorization": f"Bearer {ENDPOINT_KEY or HF_TOKEN}"}, json={"inputs": prompt, "parameters": {"max_new_tokens": max_tokens, "temperature": temperature, "return_full_text": False}}, timeout=180)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and data:
                    return data[0].get("generated_text", "").strip()
                if isinstance(data, dict):
                    return data.get("generated_text", "").strip()
        except Exception as e:
            logger.error(f"[Llama HF inference] {e}")

    return ""


async def chat_async(messages: List[Dict[str, str]], max_tokens: int = 1024, temperature: float = 0.3) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: chat(messages, max_tokens, temperature))


async def generate_async(prompt: str, system: Optional[str] = None, max_tokens: int = 1024, temperature: float = 0.3) -> str:
    msgs: List[Dict[str, str]] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return await chat_async(msgs, max_tokens=max_tokens, temperature=temperature)


# ─────────────────────────────────────────────────
# Pharma-specific helpers
# ─────────────────────────────────────────────────

async def improve_text(text: str, lang: str = "uz") -> str:
    """Илмий таҳрир — Llama 3.1 8B with stronger instruction following."""
    system = (
        "Сен ўзбек тилини мукаммал биладиган профессионал илмий-фарма муҳарририсан. "
        "Берилган матнни илмий-тиббий услубда тузат: имло, грамматика, синтаксис, тиниш белгилари, услуб. "
        "ҚАТЪИЙ ҚОИДАЛАР: "
        "1) Структурани сақла (абзацлар, рўйхатлар, формулалар, рақамлар, ATC кодлар) "
        "2) Тиббий терминларни ўзгартирма (фақат имло хатоларини туза) "
        "3) INN, бренд номлар, дозаларни сақла "
        "4) Фақат тузатилган матнни қайтар, изоҳсиз."
    )
    return await generate_async(text, system=system, max_tokens=4096, temperature=0.15)


async def translate(text: str, source_lang: str, target_lang: str) -> str:
    """Илмий таржима — Llama 3.1 with terminology preservation."""
    label = {"en": "English", "ru": "Russian", "uz": "Uzbek (Latin)", "uz-lat": "Uzbek (Latin)", "uz-cyr": "Uzbek (Cyrillic)"}
    src = label.get(source_lang, source_lang)
    tgt = label.get(target_lang, target_lang)
    system = (
        f"You are a professional pharmaceutical and medical translator. Translate from {src} to {tgt}. "
        "Critical rules: "
        "1) Preserve INN (International Non-proprietary Names) exactly as in source "
        "2) Preserve brand names, dosages, ATC codes "
        "3) Use formal scientific style "
        "4) Preserve document structure (paragraphs, lists, tables) "
        "5) Output ONLY the translation, no commentary."
    )
    return await generate_async(text, system=system, max_tokens=4096, temperature=0.2)


def learn_record(prompt: str, response: str, kind: str = "llama_generate") -> None:
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
                    (kind, prompt[:5000], response[:5000]))
        conn.commit()
        conn.close()
    except Exception:
        pass
