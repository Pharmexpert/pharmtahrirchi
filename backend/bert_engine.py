import threading
import time
import os
import logging

# Configure logging
logger = logging.getLogger("bert_engine")

# ═══════════════════════════════════════════════════
# PHASE 1: Persistent HuggingFace cache on Railway volume
# Before importing torch/transformers — otherwise cache env is ignored
# ═══════════════════════════════════════════════════
_IS_RAILWAY = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.path.exists("/app/data"))
if _IS_RAILWAY:
    _HF_CACHE = "/app/data/hf_cache"
    os.makedirs(_HF_CACHE, exist_ok=True)
    os.environ.setdefault("HF_HOME", _HF_CACHE)
    os.environ.setdefault("TRANSFORMERS_CACHE", _HF_CACHE)
    os.environ.setdefault("HF_HUB_CACHE", _HF_CACHE)
    logger.info(f"[BERT] Using persistent HF cache at {_HF_CACHE}")

# HF_TOKEN for higher rate limits (optional)
if os.getenv("HF_TOKEN"):
    os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", os.getenv("HF_TOKEN"))
    logger.info("[BERT] HF_TOKEN detected — using authenticated requests")

import torch
from transformers import pipeline, AutoTokenizer, AutoModelForMaskedLM

# Uzbek BERT model — uses env var, falls back to HuggingFace auto-download
_default_local = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tahrirchi-bert-base")
MODEL_NAME = os.getenv("BERT_MODEL", _default_local if os.path.exists(_default_local) else "tahrirchi/tahrirchi-bert-base")

class BertEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BertEngine, cls).__new__(cls)
                cls._instance.initialized = False
                cls._instance.nlp = None
                cls._instance.tokenizer = None
                cls._instance.model = None
        return cls._instance

    def initialize(self):
        """Initialize BERT in a background thread."""
        if self.initialized:
            return
        
        thread = threading.Thread(target=self._load_model)
        thread.daemon = True
        thread.start()
        logger.info(f"[*] BERT Engine ({MODEL_NAME}) initialization started in background...")

    def _load_model(self):
        try:
            # Using CPU by default for stability (Mac/Windows)
            device = 0 if torch.cuda.is_available() else -1
            
            logger.info(f"[*] Loading tokenizer for {MODEL_NAME}...")
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            
            logger.info(f"[*] Loading model for {MODEL_NAME}...")
            # Load floating-point model first
            fp32_model = AutoModelForMaskedLM.from_pretrained(MODEL_NAME)
            
            # Apply 8-bit dynamic quantization to Linear layers
            logger.info(f"[*] Quantizing model (8-bit)...")
            self.model = torch.quantization.quantize_dynamic(
                fp32_model, {torch.nn.Linear}, dtype=torch.qint8
            )
            
            logger.info(f"[*] Setting up pipeline...")
            self.nlp = pipeline("fill-mask", model=self.model, tokenizer=self.tokenizer, device=device)
            
            self.initialized = True
            logger.info(f"[+] BERT Engine ({MODEL_NAME}) is READY.")
        except Exception as e:
            logger.error(f"[!] Error loading BERT model: {e}")

    def predict_mask(self, text: str, top_k: int = 5):
        """Predict the masked word in a sentence using BERT."""
        if not self.initialized or not self.nlp:
            return []
        
        try:
            # Ensure text contains [MASK]
            if "[MASK]" not in text:
                return []
                
            results = self.nlp(text, top_k=top_k)
            return [res['token_str'] for res in results]
        except Exception as e:
            logger.error(f"[!] BERT Prediction Error: {e}")
            return []

    def get_embedding(self, text: str, as_numpy: bool = False):
        """Get vector embedding for a text snippet."""
        if not self.initialized or not self.model or not self.tokenizer:
            return None
        try:
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=128)
            with torch.no_grad():
                # For quantized models, we need to handle the output slightly differently if needed
                outputs = self.model.base_model(**inputs)
                # Use [CLS] token embedding
                embeddings = outputs.last_hidden_state[:, 0, :].squeeze()
            
            if as_numpy:
                return embeddings.cpu().numpy()
            return embeddings
        except Exception as e:
            logger.error(f"[!] Embedding Error: {e}")
            return None

    def cosine_similarity(self, a, b):
        """Compute cosine similarity between two vectors."""
        if a is None or b is None: return 0.0
        # Use torch's functional cosine similarity
        return torch.nn.functional.cosine_similarity(a.unsqueeze(0), b.unsqueeze(0)).item()

    def get_context_suggestion(self, text: str, wrong_word: str):
        """Suggest a correction for a word based on context."""
        if not self.initialized or not self.nlp:
            return None
            
        # Replace word with [MASK]
        masked_text = text.replace(wrong_word, "[MASK]")
        if "[MASK]" not in masked_text:
            return None
            
        suggestions = self.predict_mask(masked_text)
        return suggestions[0] if suggestions else None

# Global instance
engine = BertEngine()
