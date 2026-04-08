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

# Primary Uzbek BERT — Tahrirchi (8.7M corpus, 2024)
_default_local = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tahrirchi-bert-base")
MODEL_NAME = os.getenv("BERT_MODEL", _default_local if os.path.exists(_default_local) else "tahrirchi/tahrirchi-bert-base")

# Secondary Uzbek BERT — UzBERT (CopperCity Labs, 142GB corpus, 2020)
# Used as ENSEMBLE complement: lowercase Latin script, BPE-tokenized
UZBERT_MODEL = os.getenv("UZBERT_MODEL", "coppercitylabs/uzbert-base-uncased")
ENSEMBLE_MODE = os.getenv("BERT_ENSEMBLE", "1") == "1"  # Default ON


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
                # Ensemble (UzBERT) — secondary model
                cls._instance.uzbert_initialized = False
                cls._instance.uzbert_nlp = None
                cls._instance.uzbert_tokenizer = None
                cls._instance.uzbert_model = None
        return cls._instance

    def initialize(self):
        """Initialize Tahrirchi BERT (and UzBERT if ensemble enabled) in background threads."""
        if self.initialized:
            return
        thread = threading.Thread(target=self._load_model)
        thread.daemon = True
        thread.start()
        logger.info(f"[*] BERT Engine ({MODEL_NAME}) initialization started in background...")

        if ENSEMBLE_MODE:
            uzbert_thread = threading.Thread(target=self._load_uzbert)
            uzbert_thread.daemon = True
            uzbert_thread.start()
            logger.info(f"[*] UzBERT ensemble ({UZBERT_MODEL}) initialization started in background...")

    def _load_model(self):
        try:
            device = 0 if torch.cuda.is_available() else -1
            logger.info(f"[*] Loading tokenizer for {MODEL_NAME}...")
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            logger.info(f"[*] Loading model for {MODEL_NAME}...")
            fp32_model = AutoModelForMaskedLM.from_pretrained(MODEL_NAME)
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

    def _load_uzbert(self):
        """Load secondary UzBERT model for ensemble predictions."""
        try:
            device = 0 if torch.cuda.is_available() else -1
            logger.info(f"[*] [UzBERT] Loading tokenizer for {UZBERT_MODEL}...")
            self.uzbert_tokenizer = AutoTokenizer.from_pretrained(UZBERT_MODEL)
            logger.info(f"[*] [UzBERT] Loading model {UZBERT_MODEL}...")
            # Skip quantization (causes meta tensor issue on newer transformers)
            self.uzbert_model = AutoModelForMaskedLM.from_pretrained(UZBERT_MODEL)
            self.uzbert_model.eval()
            self.uzbert_nlp = pipeline("fill-mask", model=self.uzbert_model, tokenizer=self.uzbert_tokenizer, device=device)
            self.uzbert_initialized = True
            logger.info(f"[+] UzBERT ({UZBERT_MODEL}) is READY (ensemble enabled).")
        except Exception as e:
            logger.warning(f"[!] UzBERT load failed (non-fatal, ensemble disabled): {e}")
            self.uzbert_initialized = False

    # ───────────────────────────────────────────────────
    # Helpers
    # ───────────────────────────────────────────────────
    def _normalize_to_latin(self, text: str) -> str:
        """Tahrirchi BERT тренировкаси лотин ёзувида — Cyrillic'ни автоматик ўгирамиз."""
        if not text:
            return text
        try:
            import transliterate as tl
            if any("\u0400" <= ch <= "\u04FF" for ch in text):
                return tl.to_latin(text)
        except Exception:
            pass
        return text

    def _context_window(self, text: str, target_word: str, half_tokens: int = 64) -> str:
        """Хато сўз атрофидан ±half_tokens ойнача ажратиш — BERT 512 чегарасига тушмайди."""
        if not target_word:
            return text
        idx = text.find(target_word)
        if idx < 0:
            return text
        # Approx by chars (1 token ≈ 4 chars). Take ±half_tokens*4 around the word
        char_radius = half_tokens * 4
        start = max(0, idx - char_radius)
        end = min(len(text), idx + len(target_word) + char_radius)
        return text[start:end]

    # ───────────────────────────────────────────────────
    # Mask prediction (with cross-script + window + Hunspell filter)
    # ───────────────────────────────────────────────────
    def _query_single_model(self, nlp, tokenizer, text: str, top_k: int):
        """Query a single fill-mask model and return list of (token, score) pairs."""
        try:
            mask_token = tokenizer.mask_token if tokenizer else "[MASK]"
            # Replace generic [MASK] with the specific mask token of this tokenizer
            t = text.replace("[MASK]", mask_token) if mask_token != "[MASK]" else text
            if mask_token not in t:
                return []
            results = nlp(t, top_k=top_k)
            out = []
            for r in results:
                tok = r.get('token_str', '').strip().lstrip('##').strip()
                score = float(r.get('score', 0.0))
                if tok and tok not in ('[UNK]', '[PAD]', '[SEP]', '[CLS]', '<s>', '</s>', '<pad>', '<unk>', '<mask>'):
                    out.append((tok.lower(), score))
            return out
        except Exception as e:
            logger.warning(f"[BERT single query] {e}")
            return []

    def predict_mask(self, text: str, top_k: int = 15, hunspell_filter: bool = True, lang: str = "uz", final_k: int = 5):
        """
        Ensemble prediction: Tahrirchi BERT + UzBERT.

        Combines results from both models with weighted scoring:
            final_score = (tahrirchi_score * 0.6) + (uzbert_score * 0.4)
        Tokens predicted by BOTH models get a 1.5x boost.
        """
        if not self.initialized or not self.nlp:
            return []
        try:
            normalized = self._normalize_to_latin(text)
            if "[MASK]" not in normalized:
                return []

            # 1. Primary model (Tahrirchi)
            primary = self._query_single_model(self.nlp, self.tokenizer, normalized, top_k)

            # 2. Secondary model (UzBERT) if ensemble enabled
            secondary = []
            if ENSEMBLE_MODE and self.uzbert_initialized and self.uzbert_nlp:
                secondary = self._query_single_model(self.uzbert_nlp, self.uzbert_tokenizer, normalized, top_k)

            # 3. Combine — weighted ensemble with agreement boost
            score_map = {}
            for tok, sc in primary:
                score_map[tok] = score_map.get(tok, 0) + sc * 0.6
            for tok, sc in secondary:
                if tok in score_map:
                    score_map[tok] = score_map[tok] + sc * 0.4
                    score_map[tok] *= 1.5  # agreement boost
                else:
                    score_map[tok] = sc * 0.4

            # 4. Sort by combined score
            ranked = sorted(score_map.items(), key=lambda x: -x[1])
            tokens = [t for t, _ in ranked]

            # 5. Hunspell filter (only keep tokens that exist in dict)
            if hunspell_filter:
                try:
                    import spellcheck
                    filtered = [t for t in tokens if spellcheck.is_correct(t, is_cyrillic=False)]
                    if filtered:
                        tokens = filtered
                except Exception:
                    pass

            return tokens[:final_k]
        except Exception as e:
            logger.error(f"[!] BERT Ensemble Prediction Error: {e}")
            return []

    def predict_in_context(self, full_text: str, wrong_word: str, top_k: int = 10, hunspell_filter: bool = True):
        """Wrong word ўрнига [MASK] қўйиб, контекст ойначадан BERT'дан таклиф олиш."""
        if not wrong_word:
            return []
        window = self._context_window(full_text, wrong_word, half_tokens=64)
        masked = window.replace(wrong_word, "[MASK]", 1)
        return self.predict_mask(masked, top_k=top_k, hunspell_filter=hunspell_filter)

    # ───────────────────────────────────────────────────
    # Embeddings (token + sentence)
    # ───────────────────────────────────────────────────
    def get_embedding(self, text: str, as_numpy: bool = False):
        """Get [CLS] token embedding (cross-script normalized)."""
        if not self.initialized or not self.model or not self.tokenizer:
            return None
        try:
            normalized = self._normalize_to_latin(text)
            inputs = self.tokenizer(normalized, return_tensors="pt", padding=True, truncation=True, max_length=128)
            with torch.no_grad():
                outputs = self.model.base_model(**inputs)
                embeddings = outputs.last_hidden_state[:, 0, :].squeeze()
            return embeddings.cpu().numpy() if as_numpy else embeddings
        except Exception as e:
            logger.error(f"[!] Embedding Error: {e}")
            return None

    def get_sentence_embedding(self, text: str, as_numpy: bool = False):
        """Mean-pooled sentence embedding (better for sentence similarity / translation scoring)."""
        if not self.initialized or not self.model or not self.tokenizer:
            return None
        try:
            normalized = self._normalize_to_latin(text)
            inputs = self.tokenizer(normalized, return_tensors="pt", padding=True, truncation=True, max_length=512)
            with torch.no_grad():
                outputs = self.model.base_model(**inputs)
                last_hidden = outputs.last_hidden_state  # (1, seq, dim)
                mask = inputs["attention_mask"].unsqueeze(-1).float()
                summed = (last_hidden * mask).sum(dim=1)
                counts = mask.sum(dim=1).clamp(min=1)
                mean_pooled = (summed / counts).squeeze()
            return mean_pooled.cpu().numpy() if as_numpy else mean_pooled
        except Exception as e:
            logger.error(f"[!] Sentence Embedding Error: {e}")
            return None

    def sentence_similarity(self, a: str, b: str) -> float:
        """Cosine similarity между двумя предложениями (mean-pooled embeddings)."""
        ea = self.get_sentence_embedding(a)
        eb = self.get_sentence_embedding(b)
        if ea is None or eb is None:
            return 0.0
        return torch.nn.functional.cosine_similarity(ea.unsqueeze(0), eb.unsqueeze(0)).item()

    def cosine_similarity(self, a, b):
        if a is None or b is None: return 0.0
        try:
            return torch.nn.functional.cosine_similarity(a.unsqueeze(0), b.unsqueeze(0)).item()
        except Exception:
            try:
                import numpy as np
                an, bn = np.array(a), np.array(b)
                return float(np.dot(an, bn) / (np.linalg.norm(an) * np.linalg.norm(bn) + 1e-9))
            except Exception:
                return 0.0

    # ───────────────────────────────────────────────────
    # Pseudo-perplexity (sentence well-formedness scorer)
    # ───────────────────────────────────────────────────
    def pseudo_perplexity(self, text: str, max_tokens: int = 64) -> float:
        """
        BERT pseudo-perplexity. Pастроқ — гап табиийроқ.
        Ҳар бир токенни алоҳида MASK қилиб, тўғри эҳтимолини олиб, ўртача -log хисобланади.
        """
        if not self.initialized or not self.model or not self.tokenizer:
            return float('inf')
        try:
            import math
            normalized = self._normalize_to_latin(text)
            ids = self.tokenizer.encode(normalized, add_special_tokens=True)
            if len(ids) > max_tokens:
                ids = ids[:max_tokens]
            mask_id = self.tokenizer.mask_token_id
            if mask_id is None:
                return float('inf')
            log_probs = []
            for i in range(1, len(ids) - 1):  # skip [CLS]/[SEP]
                masked = ids.copy()
                orig = masked[i]
                masked[i] = mask_id
                input_ids = torch.tensor([masked])
                with torch.no_grad():
                    out = self.model(input_ids=input_ids).logits
                probs = torch.softmax(out[0, i], dim=-1)
                p = float(probs[orig].item())
                log_probs.append(math.log(max(p, 1e-12)))
            if not log_probs:
                return float('inf')
            avg_neg_log = -sum(log_probs) / len(log_probs)
            return math.exp(avg_neg_log)
        except Exception as e:
            logger.warning(f"[BERT] perplexity failed: {e}")
            return float('inf')

    def grammar_score(self, text: str) -> float:
        """0.0–1.0: қанчалик гап табиий. 1.0 = идеал."""
        ppl = self.pseudo_perplexity(text)
        if ppl == float('inf'):
            return 0.0
        # Normalize: ppl ~10 → 0.95, ppl ~100 → 0.5, ppl ~1000 → 0.05
        import math
        return float(1.0 / (1.0 + math.log10(max(ppl, 1.0))))

    def get_context_suggestion(self, text: str, wrong_word: str):
        suggestions = self.predict_in_context(text, wrong_word, top_k=10, hunspell_filter=True)
        return suggestions[0] if suggestions else None

    # ───────────────────────────────────────────────────
    # Semantic clustering (synonyms grouping)
    # ───────────────────────────────────────────────────
    def cluster_words(self, words: list, threshold: float = 0.78) -> list:
        """
        Сўзларни эмбединг ўхшашлиги бўйича кластерлаш (greedy).
        Қайтаради: list[list[str]] — ҳар кластер ўз гуруҳи.
        """
        if not self.initialized or not words:
            return [[w] for w in words]
        try:
            embs = []
            for w in words:
                e = self.get_embedding(w)
                if e is not None:
                    embs.append((w, e))
            clusters: list = []
            for w, e in embs:
                placed = False
                for c in clusters:
                    sim = self.cosine_similarity(e, c['centroid'])
                    if sim >= threshold:
                        c['words'].append(w)
                        # update centroid (running mean)
                        c['centroid'] = (c['centroid'] * (len(c['words']) - 1) + e) / len(c['words'])
                        placed = True
                        break
                if not placed:
                    clusters.append({'centroid': e, 'words': [w]})
            return [c['words'] for c in clusters]
        except Exception as e:
            logger.warning(f"[BERT] clustering failed: {e}")
            return [[w] for w in words]

# Global instance
engine = BertEngine()
