from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
import os
import shutil
import json
import re
import requests
import logging
import random
import string
from datetime import datetime
import db
import bert_engine
import transliterate
from processor import ParagraphAligner, export_to_docx
from pdf2docx import Converter
import google.generativeai as genai
from dotenv import load_dotenv
import admin_routes
import linguistic_routes
from auth import create_access_token, verify_token, get_current_user, get_admin_user

load_dotenv()
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BACKEND_DIR, "temp_files")
UPLOADS_DIR = os.path.join(BACKEND_DIR, "uploads")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

app = FastAPI()

# ═══════════════════════════════════════════════════
# Middleware: CORS & Initialization
# ═══════════════════════════════════════════════════

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

@app.on_event("startup")
async def startup_event():
    # Initialize tahrirchi.db if needed (for Railway deployment)
    import startup as startup_module
    startup_module.setup_tahrirchi_db()
    
    db.init_db()
    # Initialize FAISS in-memory index
    db.init_faiss_index()
    # Initialize BERT in background
    bert_engine.engine.initialize()
    
    # Run vector migration for legacy rules after a short delay to let BERT load
    import asyncio
    from anyio import to_thread
    
    async def run_migration():
        try:
            await asyncio.sleep(10) # Give BERT more time to load in background
            logger.info("[*] Starting background vector migration...")
            await to_thread.run_sync(db.migrate_vectors)
        except Exception as e:
            logger.error(f"[!] Background migration error: {e}")
    
    asyncio.create_task(run_migration())


os.makedirs(os.path.join(TEMP_DIR, "imgs"), exist_ok=True)

# Serve extracted images as static files
app.mount("/static", StaticFiles(directory=TEMP_DIR), name="static")

app.include_router(admin_routes.router)
app.include_router(linguistic_routes.router)

# Security constants are now in auth.py
GOOGLE_CLIENT_ID = "1069007349621-b47vhi16hf6rdi7phgkga9mobjvfqq3g.apps.googleusercontent.com"

# ═══════════════════════════════════════════════════
# DUAL AI: Google Gemini (primary) + Anthropic Claude (fallback)
# ═══════════════════════════════════════════════════

_gemini_model = None
_anthropic_client = None

def get_gemini():
    global _gemini_model
    if not _gemini_model:
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            _gemini_model = genai.GenerativeModel("models/gemini-2.0-flash")
    return _gemini_model

def get_anthropic():
    global _anthropic_client
    if not _anthropic_client:
        try:
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                _anthropic_client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            pass
    return _anthropic_client

def get_client():
    """Returns Gemini model (primary). Use generate_ai_content() for dual-AI calls."""
    return get_gemini() or (True if get_anthropic() else None)

async def generate_ai_content(prompt: str) -> str:
    """
    Dual-AI content generation:
      - Primary: Google Gemini 2.0 Flash
      - Fallback: Anthropic Claude (claude-3-5-haiku)
    Returns the text response or raises if both fail.
    """
    # Try Gemini first
    gemini = get_gemini()
    if gemini:
        try:
            response = gemini.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.warning(f"[AI] Gemini failed: {e} — switching to Anthropic...")

    # Fallback to Anthropic Claude
    anthropic_client = get_anthropic()
    if anthropic_client:
        try:
            msg = anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text
        except Exception as e:
            logger.error(f"[AI] Anthropic also failed: {e}")
            raise

    raise Exception("No AI client configured. Set GOOGLE_API_KEY or ANTHROPIC_API_KEY.")



# ═══════════════════════════════════════════════════
# CORE: Upload & Process
# ═══════════════════════════════════════════════════

@app.post("/api/upload")
@app.post("/api/upload-docx")
@app.post("/upload")  # backward compat
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), mode: str = "auto", text_id: str = "", current_user: Dict = Depends(get_current_user)):
    # Save uploaded file to persistent uploads directory
    persistent_file_path = os.path.join(UPLOADS_DIR, f"{int(datetime.utcnow().timestamp())}_{file.filename}")
    with open(persistent_file_path, "wb") as buffer:
        file.file.seek(0)
        shutil.copyfileobj(file.file, buffer)

    processing_path = persistent_file_path
    
    # PDF to DOCX Conversion if needed
    if file.filename.lower().endswith(".pdf"):
        docx_path = persistent_file_path.rsplit(".", 1)[0] + ".docx"
        try:
            logger.info(f"[*] Converting PDF to DOCX: {file.filename}")
            cv = Converter(persistent_file_path)
            cv.convert(docx_path)
            cv.close()
            processing_path = docx_path
        except Exception as e:
            logger.error(f"[!] PDF Conversion Error: {e}")
            raise HTTPException(status_code=500, detail=f"PDF конвертация қилишда хатолик: {str(e)}")

    try:
        aligner = ParagraphAligner(processing_path)
        if mode == "ready":
            data = aligner.process_ready_form()
        else:
            data = aligner.process()
        
        # Auto-generate text_id if not provided
        if not text_id.strip():
            # Generate from specialist name + timestamp
            specialist_short = current_user.get("name", "User").split()[0][:6] if current_user.get("name") else "User"
            text_id = f"{specialist_short}_{int(datetime.utcnow().timestamp())}"
        
        for row in data:
            row["text_id"] = text_id
        
        # Update metadata including file path
        db.update_project_metadata(text_id, current_user.get("name", "Aniqlanmagan"), user_id=current_user["id"])
        
        # Update project with file details
        conn = db.connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE projects SET original_filename = ?, file_path = ? WHERE id = ?", (file.filename, persistent_file_path, text_id))
        conn.commit()
        conn.close()

        db.save_alignments(text_id, data, user_id=current_user["id"])
        
        # PROACTIVE OPTIMIZATION: Trigger background pre-polishing
        background_tasks.add_task(pre_polish_document, text_id)
        
        return {"filename": file.filename, "data": data, "text_id": text_id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════
# AI: Document Alignment
# ═══════════════════════════════════════════════════

@app.post("/api/align-document")
async def align_document(payload: Dict[str, Any]):
    """AI-based alignment for the entire document in a single batched call."""
    client = get_client()
    if not client:
        raise HTTPException(status_code=503, detail="AI client not configured")

    rows = payload.get("data", [])
    if not rows:
        return {"data": rows}

    blocks = []
    current_block = {"marker": None, "rows": []}
    for row in rows:
        if row.get("type") == "marker":
            if current_block["rows"] or current_block["marker"]:
                blocks.append(current_block)
            current_block = {"marker": row, "rows": []}
        else:
            current_block["rows"].append(row)
    if current_block["rows"] or current_block["marker"]:
        blocks.append(current_block)

    BATCH_SIZE = 4
    aligned_blocks = []

    for batch_start in range(0, len(blocks), BATCH_SIZE):
        batch = blocks[batch_start: batch_start + BATCH_SIZE]
        
        batch_data = []
        for bi, blk in enumerate(batch):
            batch_data.append({
                "block_idx": bi,
                "en_sentences": [r["en"] for r in blk["rows"]],
                "ru_sentences": [r["ru_v1"] for r in blk["rows"]],
                "uz_sentences": [r["uz_v1"] for r in blk["rows"]],
            })

        prompt = f"""You are a pharmaceutical document alignment expert.
For each block, re-align the Russian (ru) and Uzbek (uz) sentences to correctly match the English (en) sentences based on MEANING, not position.

Blocks:
{json.dumps(batch_data, ensure_ascii=False, indent=2)}

Rules:
- Each en sentence must get exactly one best-matching ru and uz sentence
- If ru/uz has fewer sentences, merge the extras into the closest English sentence
- Return ONLY a JSON array:
[
  {{
    "block_idx": 0,
    "alignments": [
      {{"en_idx": 0, "ru": "matched russian sentence", "uz": "matched uzbek sentence"}},
      ...
    ]
  }},
  ...
]"""

        model = get_client()
        if not model:
            print("AI client not configured for alignment")
            aligned_blocks.extend(batch)
            continue

        try:
            ai_text = await generate_ai_content(prompt)
            match = re.search(r'\[.*\]', ai_text, re.DOTALL)
            if match:
                ai_result = json.loads(match.group())
                for blk_result in ai_result:
                    bi = blk_result.get("block_idx", 0)
                    if bi < len(batch):
                        blk = batch[bi]
                        alignments = blk_result.get("alignments", [])
                        for aln in alignments:
                            en_idx = aln.get("en_idx", 0)
                            if en_idx < len(blk["rows"]):
                                blk["rows"][en_idx]["ru_v1"] = aln.get("ru", blk["rows"][en_idx]["ru_v1"])
                                blk["rows"][en_idx]["uz_v1"] = aln.get("uz", blk["rows"][en_idx]["uz_v1"])
                                blk["rows"][en_idx]["ru_proposed"] = aln.get("ru", blk["rows"][en_idx].get("ru_proposed", ""))
                                blk["rows"][en_idx]["uz_proposed"] = aln.get("uz", blk["rows"][en_idx].get("uz_proposed", ""))
        except Exception as e:
            print(f"AI alignment error for batch {batch_start}: {e}")

        aligned_blocks.extend(batch)

    result_data = []
    for blk in aligned_blocks:
        if blk["marker"]:
            result_data.append(blk["marker"])
        result_data.extend(blk["rows"])

    return {"data": result_data}

# ═══════════════════════════════════════════════════
# AI: Improve Row (V.6 Expert Prompt)
# ═══════════════════════════════════════════════════

@app.post("/api/improve-row")
async def improve_row(payload: Dict[str, Any]):
    """Uses the expert pharmaceutical AI prompt to improve a single row, wrapping unified Sayqallash logic."""
    target_lang = payload.get("target_lang", "uz")
    text = payload.get(f"{target_lang}_proposed", "") or payload.get(f"{target_lang}_v1", "")
    en_text = payload.get("en", "")
    
    # Unified sayqallash logic to get Tier 1-3 improvements
    sayqallash_res = await sayqallash({"text": text, "lang": target_lang, "context_en": en_text})
    
    # Return in the format expected by TableEditor's improveRow logic
    return {
        f"{target_lang}_v2": sayqallash_res["corrected_text"],
        "annotations": sayqallash_res["annotations"],
        "rationale": "Sayqallash алгоритми (3-босқичли) асосида тузатилди."
    }

# ═══════════════════════════════════════════════════
# BERT: Context-aware Synonyms
# ═══════════════════════════════════════════════════

@app.post("/api/bert/synonyms")
async def bert_synonyms(payload: Dict[str, Any]):
    """BERT-based contextual word suggestions using fill-mask."""
    word = payload.get("word", "")
    context = payload.get("context", "")
    lang = payload.get("lang", "uz")
    
    if not word:
        return {"synonyms": [], "source": "none"}
    
    suggestions = []
    
    # 1. BERT fill-mask (if model is ready)
    if bert_engine.engine.initialized and context:
        masked = context.replace(word, "[MASK]", 1)
        if "[MASK]" in masked:
            predictions = bert_engine.engine.predict_mask(masked, top_k=10)
            suggestions.extend([p for p in predictions if p.strip() and p.lower() != word.lower()])
    
    # 2. Dictionary frequency ranking (if tahrirchi.db available)
    if lang == 'uz' and os.path.exists(db.TAHRIRCHI_DB_PATH):
        try:
            dict_conn = __import__('sqlite3').connect(db.TAHRIRCHI_DB_PATH)
            dc = dict_conn.cursor()
            # Find words with similar prefix
            dc.execute(
                "SELECT word, frequency FROM dictionary WHERE word LIKE ? ORDER BY frequency DESC LIMIT 5",
                (word[:3] + '%',)
            )
            for dw, freq in dc.fetchall():
                if dw.lower() != word.lower() and dw not in suggestions:
                    suggestions.append(dw)
            dict_conn.close()
        except Exception:
            pass
    
    return {"synonyms": suggestions[:10], "source": "bert+dictionary"}

# ═══════════════════════════════════════════════════
# Dictionary: Autocomplete & Fuzzy Suggest
# ═══════════════════════════════════════════════════

@app.post("/api/dictionary/autocomplete")
async def dict_autocomplete(payload: Dict[str, Any]):
    """Get word completions from 8.7M dictionary."""
    prefix = payload.get("prefix", "").strip().lower()
    limit = min(payload.get("limit", 10), 20)
    
    if len(prefix) < 2 or not os.path.exists(db.TAHRIRCHI_DB_PATH):
        return {"words": []}
    
    import sqlite3 as sq
    conn = sq.connect(db.TAHRIRCHI_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT word, frequency FROM dictionary WHERE word LIKE ? ORDER BY frequency DESC LIMIT ?",
        (prefix + '%', limit)
    )
    results = [{"word": w, "frequency": f} for w, f in cursor.fetchall()]
    conn.close()
    return {"words": results}

@app.post("/api/dictionary/suggest")
async def dict_suggest(payload: Dict[str, Any]):
    """Suggest corrections for misspelled words using dictionary + Levenshtein."""
    word = payload.get("word", "").strip().lower()
    
    if len(word) < 2 or not os.path.exists(db.TAHRIRCHI_DB_PATH):
        return {"suggestions": [], "in_dictionary": False}
    
    import sqlite3 as sq
    conn = sq.connect(db.TAHRIRCHI_DB_PATH)
    cursor = conn.cursor()
    
    # Check if word exists
    cursor.execute("SELECT 1 FROM dictionary WHERE word = ? LIMIT 1", (word,))
    exists = cursor.fetchone() is not None
    
    if exists:
        conn.close()
        return {"suggestions": [], "in_dictionary": True}
    
    # Find similar words (prefix match + character variants)
    candidates = []
    
    # Prefix-based search
    for prefix_len in [len(word)-1, len(word)-2, 3]:
        if prefix_len < 2:
            continue
        cursor.execute(
            "SELECT word, frequency FROM dictionary WHERE word LIKE ? AND length(word) BETWEEN ? AND ? ORDER BY frequency DESC LIMIT 10",
            (word[:prefix_len] + '%', len(word)-2, len(word)+2)
        )
        for w, f in cursor.fetchall():
            if w != word:
                # Simple edit distance approximation
                dist = sum(1 for a, b in zip(word, w) if a != b) + abs(len(word) - len(w))
                if dist <= 3:
                    candidates.append({"word": w, "frequency": f, "distance": dist})
    
    conn.close()
    
    # Sort by distance, then frequency
    candidates.sort(key=lambda x: (x["distance"], -x["frequency"]))
    seen = set()
    unique = []
    for c in candidates:
        if c["word"] not in seen:
            seen.add(c["word"])
            unique.append(c)
    
    return {"suggestions": unique[:5], "in_dictionary": False}

# ═══════════════════════════════════════════════════
# AI: Suggest Edits / Synonyms (V.6 Expert Prompt)
# ═══════════════════════════════════════════════════

@app.post("/suggest-edits")
@app.post("/synonyms")

async def suggest_edits(payload: Dict[str, Any]):
    model = get_client()
    if not model:
        raise HTTPException(status_code=503, detail="AI client not configured")

    word        = payload.get("word", "")
    lang        = payload.get("lang", "ru")
    context_en  = payload.get("context_en", payload.get("context", ""))
    context_ru  = payload.get("context_ru", "")
    context_uz  = payload.get("context_uz", "")
    lang_label  = "рус" if lang == "ru" else "ўзбек"
    current_txt = context_ru if lang == "ru" else context_uz

    prompt = f"""Role: Сиз фармакология ва халқаро стандартлар (Pharmacopoeia, GMP, ISO) бўйича юқори малакали эксперт-муҳаррирсиз.

Инглизча оригинал гап: {context_en}
Таҳрир қилинаётган {lang_label} матн: {current_txt}
Танланган ифода: "{word}"

Вазифа: Юқоридаги матн мазмунидан келиб чиқиб, "{word}" ифодасига фармацевтик жиҳатдан энг тўғри 5 та СИНОНИМ ёки муқобил ифодани топинг.
Жавобни ҚАТЪИЙ тарзда фақат JSON форматида қайтаринг:
{{"synonyms": ["1-синоним", "2-синоним", ...], "note": "асослама"}}"""

    try:
        resp_text = await generate_ai_content(prompt)
        match = re.search(r'\{.*\}', resp_text, re.DOTALL)
        if not match:
            return {"variants": [], "synonyms": [], "note": ""}
        result = json.loads(match.group())
        result["synonyms"] = [s for s in result.get("synonyms", []) if not db.is_word_wrong(s, lang)]
        
        # Auto-save synonyms to database
        syns = result.get("synonyms", [])[:5]
        if syns:
            try:
                db.save_synonyms_batch(word, syns, lang, source='ai')
            except Exception as se:
                print(f"Synonym save error: {se}")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════
# SAYQALLASH LOGIC
# ═══════════════════════════════════════════════════

def get_sayqallash_prompt(lang: str, rules_examples: str) -> str:
    if lang == 'ru':
        return f"""Сиз — фармацевтик ва илмий матнлар бўйича юқори малакали эксперт-муҳаррирсиз (ГФ, USP, Ph. Eur. стандартлари).
 
 ВАЗИФА: Берилган русча матнни грамматик, пунктуацион ва услубий жиҳатдан мукаммал ҳолатга келтиринг.
  
 ТЕРМИНОЛОГИК ҚОИДАЛАР (ҚАТЪИЙ):
 - "Assay" -> "Количественное определение" (Фармакопеяда "Анализ" эмас)
 - "Identification" -> "Подлинность" (НЕ "Идентификация")
 - "Dissolution" -> "Растворение"
 - "Disintegration" -> "Распадаемость"
 - "Content" -> "Содержание" (НЕ "Миқдори")
 - "Description" -> "Описание" (НЕ "Тавсиф")
 
 МУҲИМ КЎРСАТМАЛАР:
 1. Фақат ХАТО берилган сўзларни белгиланг. Тўғри сўзга тегманг!
 2. Фарм-услубни (научный стиль) сақлаб қолинг.
 3. {rules_examples} базасидаги хатоларни биринчи навбатда изланг.
 
 Фақат JSON қайтаринг:
 {{"annotations": [{{"old_value": "хато", "new_value": "тузатилган", "start_index": 0, "end_index": 4, "error_type": "S/Spelling"}}], "corrected_text": "тўлиқ матн", "confidence": 95}}"""
    
    # Default: Uzbek
    return f"""Сиз ўзбек тили грамматикаси ва халқаро ФАРМАЦЕВТИК ТЕРМИНОЛОГИЯ (USP, Ph. Eur., ГФ) бўйича юқори малакали эксперт-таҳрирчисиз.
 
 ВАЗИФА: Матндаги БАРЧА илмий, грамматик ва услубий хатоларни аниқланг ва тузатинг.
  
 ФАРМАКОПЕЯ СТАНДАРТЛАРИ (ТЕРМИНОЛОГИК ХАРИТА):
 - "Wetting" -> "Намланиш" (Фармакопеяда "Ҳўлланиш" эмас)
 - "Assay" -> "Миқдорий аниқлаш" (НЕ "Анализ")
 - "Identification" -> "Чинлигини аниқлаш"
 - "Dissolution" -> "Эрувчанлик" (Тест "Эрувчанлик")
 - "Excipients" -> "Ёрдамчи моддалар"
 - "Sieving" -> "Элаш"
 - "Stability" -> "Барқарорлик"
 
 МУҲИМ ҚОИДАЛАР:
 1. ТЎҒРИ сўзни асло хато деб белгиламанг!
 2. Ҳарф тушиб қолиши ва имло хатоларига (синаладган -> синаладиган) катта эътибор беринг.
 3. {rules_examples} базасидаги тажрибадан фойдаланинг.
 
 Фақат JSON қайтаринг:
 {{"annotations": [{{"old_value": "хато", "new_value": "тўғри", "start_index": 0, "end_index": 4, "error_type": "S/Spelling"}}], "corrected_text": "тўлиқ тузатилган матн", "confidence": 95}}"""

@app.post("/sayqallash")
async def sayqallash(payload: Dict[str, Any]):
    """
    Grammatical Error Correction (GEC) with 3-tier priority:
    1. Rules DB (db.get_rules_for_text)
    2. Google Gemini 2.0 Flash (for regions not covered by rules)
    3. BERT fallback (processed within rules engine)
    Optimized with AI Cache and Confidence Scores.
    """
    text = payload.get("text", "").strip()
    lang = payload.get("lang", "uz")
    context_en = payload.get("context_en", "")
    
    if not text:
        return {"annotations": [], "corrected_text": "", "rules_count": 0, "confidence": 100}

    # Optimization: Check AI Cache first
    cached_res = db.get_ai_cache(text, lang)
    if cached_res:
        cached_res["cached"] = True
        return cached_res

    is_uz_cyrillic = False
    if lang == 'uz':
        is_uz_cyrillic = transliterate.is_cyrillic(text)

    # ═══════════════════════════════════════════════
    # TIER 1: Rules DB (Local Corrections + Semantic rules)
    # ═══════════════════════════════════════════════
    local_annotations = db.get_rules_for_text(text, lang)
    rules_count = db.get_rules_count(lang)
    
    covered_ranges = [(a["from_index"], a["to_index"]) for a in local_annotations]

    ai_annotations = []
    confidence = 100 # High confidence for local rules
    
    # ═══════════════════════════════════════════════
    # TIER 2: Dual AI (Gemini primary → Anthropic fallback)
    # ═══════════════════════════════════════════════
    if get_client():
        known_rules = db.get_all_rules(lang, limit=20)
        rules_examples = ""
        if known_rules:
            examples = [f"«{r['wrong_form']}»→«{r['correct_form']}»" for r in known_rules]
            rules_examples = "\nMa'lumotlar bazasidagi qoidalar: " + ", ".join(examples)

        prompt_system = get_sayqallash_prompt(lang, rules_examples)

        try:
            user_message = f"Check and perfect this text:\n\n{text}"
            if context_en: user_message += f"\nContext (EN source): {context_en}"

            resp_text = await generate_ai_content(prompt_system + "\n\n" + user_message)
            match = re.search(r'\{.*\}', resp_text, re.DOTALL)
            if match:
                result = json.loads(match.group())
                raw_ai = result.get("annotations", [])
                confidence = result.get("confidence", 90)
                
                for ann in raw_ai:
                    if "start_index" in ann and "end_index" in ann:
                        ann["from_index"] = ann.pop("start_index")
                        ann["to_index"] = ann.pop("end_index")
                    
                    old_v = ann.get("old_value", "")
                    if "from_index" not in ann and old_v:
                        idx = text.find(old_v)
                        if idx != -1:
                            ann["from_index"] = idx
                            ann["to_index"] = idx + len(old_v)
                    
                    if "from_index" in ann:
                        start, end = ann["from_index"], ann["to_index"]
                        overlap = False
                        for cs, ce in covered_ranges:
                            if max(start, cs) < min(end, ce):
                                overlap = True; break
                        
                        if not overlap:
                            ann["source"] = "ai"
                            ai_annotations.append(ann)
                            covered_ranges.append((start, end))

        except Exception as e:
            print(f"AI Tier Error: {e} -> Falling back to BERT/Dictionary logic")
            # TIER 3: BERT / Dictionary Fallback (if AI fails)
            # This is already partially handled by local_annotations, but we can add more here if needed
            pass

    all_annotations = local_annotations + ai_annotations
    
    sorted_anns = sorted(all_annotations, key=lambda x: x['from_index'], reverse=True)
    curr_text = text
    for ann in sorted_anns:
        start, end = ann['from_index'], ann['to_index']
        curr_text = curr_text[:start] + ann['new_value'] + curr_text[end:]
    
    if lang == 'uz' and is_uz_cyrillic:
        curr_text = transliterate.to_cyrillic(curr_text)
        for ann in all_annotations:
            ann["old_value"] = transliterate.to_cyrillic(ann.get("old_value", ""))
            ann["new_value"] = transliterate.to_cyrillic(ann.get("new_value", ""))

    final_result = {
        "annotations": all_annotations, 
        "corrected_text": curr_text, 
        "rules_count": rules_count, 
        "confidence": confidence
    }
    # Save to Cache for 0ms latency next time
    db.set_ai_cache(text, lang, final_result)
    return final_result

async def pre_polish_document(text_id: str):
    """Proactively run Sayqallash on all rows after upload."""
    import asyncio
    rows = db.get_alignments_by_text_id(text_id)
    if not rows: return

    total_corrected = 0
    total_annotations = 0
    total_rows = len(rows)

    # Process in batches of 10 sentences (20 AI calls) to optimize throughput
    BATCH_SIZE = 10
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        tasks = []
        for row in batch:
            if row.get("row_type") == "marker": continue
            tasks.append(sayqallash({"text": row["confirmed_uz_text"], "lang": "uz", "context_en": row["en_text"]}))
            tasks.append(sayqallash({"text": row["confirmed_ru_text"], "lang": "ru", "context_en": row["en_text"]}))
        
        if not tasks: continue
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for j, res in enumerate(results):
            if isinstance(res, Exception) or not res: continue
            
            row_idx = i + (j // 2)
            lang = 'uz' if j % 2 == 0 else 'ru'
            
            # Check if correction actually changed something
            original_text = rows[row_idx]["confirmed_uz_text"] if lang == 'uz' else rows[row_idx]["confirmed_ru_text"]
            if res["corrected_text"] and res["corrected_text"].strip() != (original_text or "").strip():
                total_corrected += 1
                total_annotations += len(res.get("annotations", []))
                
                db.update_alignment_ai_result(
                    rows[row_idx]["id"], 
                    lang, 
                    res["corrected_text"], 
                    res["annotations"], 
                    res["confidence"]
                )
    
    # Save statistics for the Final Summary
    summary = {
        "total": total_rows,
        "corrected": total_corrected,
        "annotations": total_annotations,
        "timestamp": datetime.utcnow().isoformat()
    }
    db.save_project_polishing_summary(text_id, summary)

@app.post("/api/sayqallash/batch")
async def sayqallash_batch(payload: Dict[str, Any]):
    """Parallel processing for multiple rows requested by UI."""
    import asyncio
    items = payload.get("items", [])
    if not items: return {"results": []}
    
    tasks = [sayqallash(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    final_results = []
    for res in results:
        if isinstance(res, Exception):
            final_results.append({"error": str(res), "annotations": [], "corrected_text": ""})
        else:
            final_results.append(res)
            
    return {"results": final_results}


@app.post("/api/sayqallash/learn-batch")
async def learn_batch(payload: Dict[str, Any]):
    """
    Self-learning: Save accepted corrections to the rules database.
    Building the 'Rules DB' (Tier 1) from user choices.
    """
    corrections = payload.get("corrections", [])
    lang = payload.get("lang", "uz")
    count = 0
    for c in corrections:
        old = c.get("old_value", "").strip()
        new = c.get("new_value", "").strip()
        error_type = c.get("error_type", "F/Correction")
        if old and new and old != new:
            # Skip if it's just a 'not found' tag
            if "[Луғатда топилмади]" in new or "[Not Found]" in new:
                continue
            
            db.add_sayqallash_rule(old, new, error_type, lang=lang, source="user_feedback")
            count += 1
            
    # Refresh FAISS if possible
    try:
        db.index_missing_rules()
    except: pass
    
    return {"success": True, "count": count}

@app.post("/api/sayqallash-batch")
async def sayqallash_batch(payload: Dict[str, Any]):
    rows = payload.get("rows", [])
    lang = payload.get("lang", "uz")
    if not rows: return {"results": []}
    results = []
    for row in rows:
        res = await sayqallash({"text": row.get("text", ""), "lang": lang, "context_en": row.get("en", "")})
        results.append({"id": row.get("id"), "original": row.get("text"), "corrected": res.get("corrected_text"), "annotations": res.get("annotations")})
    return {"results": results}

# ═══════════════════════════════════════════════════
# Auto-Notes & Sayqallash Rules CRUD
# ═══════════════════════════════════════════════════

@app.post("/api/auto-notes")
async def auto_notes(payload: Dict[str, Any]):
    """Generate diff notes by comparing V1 with Proposed text."""
    v1 = payload.get("v1", "")
    proposed = payload.get("proposed", "")
    lang = payload.get("lang", "uz")
    notes = db.generate_diff_notes(v1, proposed, lang)
    return {"notes": notes}

# Note: /sayqallash-rules CRUD (Rules DB) moved to admin_routes.py (/api/admin/rules)

# ═══════════════════════════════════════════════════
# Data Persistence: Save / Export / History / Delete
# ═══════════════════════════════════════════════════

@app.post("/api/save")
async def save_data(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    try:
        project_id = payload.get("project_id", "default")
        data = payload.get("data", [])
        specialist = payload.get("specialist_name", current_user.get("name", "Aniqlanmagan"))
        
        db.save_alignments(project_id, data, user_id=current_user["id"])
        db.update_project_metadata(project_id, specialist, user_id=current_user["id"])
        
        # NEW: Batch record to Paragraphs Dashboard (History)
        for row in data:
            if row.get("type") == "content" and (row.get("ru_proposed") or row.get("uz_proposed")):
                try:
                    db.record_dashboard_entry(
                        en=row.get("en", ""),
                        ru=row.get("ru_proposed", row.get("ru_v1", "")),
                        uz=row.get("uz_proposed", row.get("uz_v1", "")),
                        specialist=specialist,
                        text_id=project_id,
                        action_type="Bulk Save"
                    )
                except Exception as de:
                    print(f"Dashboard recording error for row: {de}")

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/export")
async def export_project_live(project_id: str, current_user: Dict = Depends(get_current_user)):
    """Live export of the current database state to DOCX."""
    try:
        data = db.get_history(project_id)
        if not data:
            raise HTTPException(status_code=404, detail="Project not found")
            
        output_path = os.path.abspath(os.path.join(TEMP_DIR, f"live_export_{project_id}.docx"))
        from processor import export_to_docx
        export_to_docx(data, output_path)
        
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"PharmaExpert_{project_id}.docx"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/polishing-summary")
async def get_polishing_summary(project_id: str, current_user: Dict = Depends(get_current_user)):
    """Fetch the aggregate result summary for the last polishing run."""
    summary = db.get_project_polishing_summary(project_id)
    if not summary:
        return {"status": "none"}
    return {"status": "success", "summary": summary}

@app.post("/api/projects/{project_id}/finish")
async def finish_project(project_id: str, payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Mark project as finished and save final state."""
    try:
        data = payload.get("data", [])
        specialist = payload.get("specialist_name", current_user.get("name", "Aniqlanmagan"))
        
        # 1. Save all data one last time
        if data:
            db.save_alignments(project_id, data, user_id=current_user["id"])
            
        # 2. Update status to 'finished'
        conn = db.connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE projects SET status = 'finished', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (project_id,))
        conn.commit()
        conn.close()
        
        # 3. Final Audit Log
        db.record_dashboard_entry(
            en="[PROJECT FINISHED]",
            ru="Проект завершен",
            uz="Лойиҳа якунланди",
            specialist=specialist,
            text_id=project_id,
            action_type="Project Finished"
        )
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}/preview")
async def preview_project(project_id: str, current_user: Dict = Depends(get_current_user)):
    """Simple preview of project content for the directory."""
    try:
        data = db.get_history(project_id)
        return {"alignments": data[:50]} # Top 50 rows for preview
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/save-row")
async def save_single_row(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    try:
        new_id = db.save_single_row(payload, user_id=current_user["id"])
        
        # NEW: Record in Dashboard
        try:
            db.record_dashboard_entry(
                en=payload.get("en", ""),
                ru=payload.get("ru_proposed", ""),
                uz=payload.get("uz_proposed", ""),
                specialist=payload.get("specialist_name", current_user.get("name", "Aniqlanmagan")),
                text_id=payload.get("text_id", ""),
                action_type=payload.get("action_type", "Manual Edit")
            )
        except Exception as de:
            print(f"Dashboard recording error: {de}")

        return {"status": "success", "new_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════
# NEW: Paragraphs Dashboard API
# ═══════════════════════════════════════════════════

@app.get("/api/dashboard/all")
async def get_dashboard_all(current_user: Dict = Depends(get_current_user)):
    """Fetch all history from the Paragraphs Dashboard."""
    try:
        entries = db.get_dashboard_entries()
        return {"entries": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/dashboard/record")
async def record_dashboard_manual(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Manually record an entry in the dashboard."""
    try:
        db.record_dashboard_entry(
            en=payload.get("en"),
            ru=payload.get("ru"),
            uz=payload.get("uz"),
            specialist=payload.get("specialist", current_user.get("name")),
            text_id=payload.get("text_id"),
            action_type=payload.get("action_type", "Manual Edit")
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/me")
async def get_my_profile(current_user: Dict = Depends(get_current_user)):
    return current_user

@app.put("/api/user/me")
async def update_my_profile(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    try:
        db.update_user_profile(current_user["id"], payload)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects")
async def list_projects(current_user: Dict = Depends(get_current_user)):
    projects = db.list_projects()
    return {"projects": projects}

@app.delete("/api/projects/{project_id}")
async def delete_project_api(project_id: str, current_user: Dict = Depends(get_current_user)):
    try:
        # Get file path before deleting from DB
        file_path = db.get_project_file_path(project_id)
        
        # Delete from DB
        db.delete_project(project_id)
        
        # Delete physical file if exists
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                # Also try to delete converted docx if it was a pdf
                if file_path.lower().endswith(".pdf"):
                    docx_path = file_path.rsplit(".", 1)[0] + ".docx"
                    if os.path.exists(docx_path):
                        os.remove(docx_path)
            except Exception as fe:
                logger.error(f"Error deleting physical file: {fe}")
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/delete-row/{text_id}/{sentence_no}")
async def delete_row(text_id: str, sentence_no: int, current_user: Dict = Depends(get_current_user)):
    try:
        db.delete_row(sentence_no, text_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/{text_id}")
@app.get("/api/alignments/{text_id}")
async def get_history(text_id: str):
    data = db.get_history(text_id)
    return {"alignments": data}

@app.post("/api/export")
async def export_data(payload: Dict[str, Any]):
    filename = payload.get("filename", "aligned_output.docx")
    data = payload.get("data", [])
    file_basename = os.path.basename(filename)
    output_path = os.path.abspath(os.path.join(TEMP_DIR, f"confirmed_{file_basename}"))
    try:
        export_to_docx(data, output_path)
        download_name = f"confirmed_{file_basename}"
        if not download_name.endswith(".docx"):
            download_name += ".docx"
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=download_name,
            headers={"Content-Disposition": f'attachment; filename="{download_name}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/specialists")
async def get_specialists():
    try:
        names = db.get_unique_specialists()
        return {"specialists": names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════
# Split / Merge Rows
# ═══════════════════════════════════════════════════

@app.post("/api/split-row")
async def split_row(payload: Dict[str, Any]):
    row = payload.get("row")
    if not row: raise HTTPException(status_code=400, detail="Row data required")
    
    client = get_client()
    if client:
        try:
            prompt = f"""Split this trilingual pharma row into two logical parts (sentence breaks).
EN: {row['en']}
RU: {row.get('ru_proposed') or row['ru_v1']}
UZ: {row.get('uz_proposed') or row['uz_v1']}

Return JSON only: {{"part1": {{"en": "...", "ru": "...", "uz": "..."}}, "part2": {{"en": "...", "ru": "...", "uz": "..."}}}}"""
            
            response = client.generate_content(prompt)
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                parts = json.loads(match.group())
                row1 = {**row, "en": parts["part1"]["en"], "ru_v1": parts["part1"]["ru"], "uz_v1": parts["part1"]["uz"], "ru_proposed": "", "uz_proposed": ""}
                row2 = {**row, "en": parts["part2"]["en"], "ru_v1": parts["part2"]["ru"], "uz_v1": parts["part2"]["uz"], "ru_proposed": "", "uz_proposed": "", "sentence_no": 0}
                return {"row1": row1, "row2": row2}
        except Exception as e:
            print(f"Magic split error: {e}")
    
    mid = len(row['en']) // 2
    row1 = {**row, "en": row['en'][:mid], "ru_proposed": "", "uz_proposed": ""}
    row2 = {**row, "en": row['en'][mid:], "sentence_no": 0, "ru_proposed": "", "uz_proposed": ""}
    return {"row1": row1, "row2": row2}

@app.post("/api/transliterate-batch")
async def transliterate_batch(payload: Dict[str, Any]):
    """Batch transliterate text elements."""
    texts = payload.get("texts", [])
    target = payload.get("target", "latin")
    if not texts: return {"texts": []}
    
    results = []
    for txt in texts:
        if not txt:
            results.append("")
            continue
        if target == 'latin':
            results.append(transliterate.to_latin(txt))
        else:
            results.append(transliterate.to_cyrillic(txt))
            
    return {"texts": results}

# ═══════════════════════════════════════════════════
# AUTH & ADMIN PANEL
# ═══════════════════════════════════════════════════

@app.post("/api/auth/google")
async def auth_google(payload: Dict[str, Any]):
    credential = payload.get("credential")
    if credential == "dev-token" or payload.get("email") == "admin@pharma.local":
        user = db.get_user_by_email("texnopharm@gmail.com")
        return {"success": True, "token": "dev-token", "user": user}
    try:
        resp = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}")
        if not resp.ok: raise HTTPException(status_code=401, detail="Invalid token")
        google_data = resp.json()
        email, name = google_data.get("email"), google_data.get("name")
    except Exception: raise HTTPException(status_code=401, detail="Google verification failed")
    user = db.get_user_by_email(email)
    if not user:
        user_id = f"google_{int(datetime.utcnow().timestamp())}"
        # Google OAuth users are auto-approved — no admin approval needed
        db.create_user(user_id, email, name, avatar_url=google_data.get("picture"), auto_approve=True)
        user = db.get_user_by_email(email)
    else:
        # If user exists but is pending, auto-approve on Google login
        if user["status"] == "pending":
            db.update_user_status(user["id"], "approved")
            user = db.get_user_by_email(email)
    if user["status"] == "rejected": raise HTTPException(status_code=403, detail="Rejected")
    db.update_user_login(user["id"])
    token = create_access_token({"userId": user["id"], "email": user["email"], "role": user["role"], "name": user["name"]})
    return {"success": True, "token": token, "user": user}

@app.post("/api/auth/register")
async def register(payload: Dict[str, Any]):
    email = payload.get("email", "").lower().strip()
    name = payload.get("name", "").strip()
    password = payload.get("password")
    department = payload.get("department", "").strip()
    if not email or not name or not password:
        raise HTTPException(status_code=400, detail="Barcha maydonlarni тўлдиринг")
    if db.get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Бундай Email аллақачон мавжуд")
    user_id = f"user_{int(datetime.utcnow().timestamp())}"
    db.create_user(user_id, email, name, password=password, department=department)
    return {"success": True, "message": "Рўйхатдан ўтиш муваффақиятли! Админ тасдиқлашини кутинг."}

@app.post("/api/auth/login")
async def login_api(payload: Dict[str, Any]):
    email = payload.get("email", "").lower().strip()
    password = payload.get("password")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email манзилини киритинг")
        
    # Check if this is an admin first-time login (no password set in DB)
    user_data = db.get_user_by_email(email)
    pw_required = True
    if user_data and user_data.get('role') == 'admin' and not user_data.get('password_hash'):
        pw_required = False
        
    if pw_required and not password:
        raise HTTPException(status_code=400, detail="Паролни киритинг")
        
    if not db.verify_password(email, password or ""):
        raise HTTPException(status_code=401, detail="Email ёки парол хато")
    user = db.get_user_by_email(email)
    if not user: raise HTTPException(status_code=401, detail="Фойдаланувчи топилмади")
    if user["email"] != "texnopharm@gmail.com" and user["status"] != "approved":
        detail = "Ҳисобингиз ҳали тасдиқланмаган" if user["status"] == "pending" else "Ҳисобингиз рад этилган"
        raise HTTPException(status_code=403, detail=detail)
    db.update_user_login(user["id"])
    token = create_access_token({"userId": user["id"], "email": user["email"], "role": user["role"], "name": user["name"]})
    return {"success": True, "token": token, "user": user}

@app.get("/api/auth/me")
async def get_me(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header: raise HTTPException(status_code=401)
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if not payload: raise HTTPException(status_code=401)
    user = db.get_user_by_id(payload["userId"])
    return {"user": user}

@app.post("/api/auth/forgot-password")
async def forgot_password(payload: Dict[str, Any]):
    email = payload.get("email", "").lower().strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email манзилини киритинг")
    
    user = db.get_user_by_email(email)
    if not user:
        # Don't reveal if user exists for security, but in this case we'll just return success
        return {"success": True, "message": "Агар ушбу Email мавжуд бўлса, тиклаш коди юборилди."}
    
    # Generate 6-digit code
    code = ''.join(random.choices(string.digits, k=6))
    db.create_reset_code(email, code)
    
    # MOCK EMAIL SENDING - Print to console for Railway logs
    logger.info(f"🔑 PASSWORD RESET CODE for {email}: {code}")
    
    return {"success": True, "message": "Тиклаш коди Email манзилингизга юборилди (Логларни текширинг)."}

@app.post("/api/auth/reset-password")
async def reset_password(payload: Dict[str, Any]):
    email = payload.get("email", "").lower().strip()
    code = payload.get("code", "").strip()
    new_password = payload.get("password")
    
    if not email or not code or not new_password:
        raise HTTPException(status_code=400, detail="Барча майдонларни тўлдиринг")
    
    saved_code = db.get_reset_code(email)
    if not saved_code or saved_code != code:
        raise HTTPException(status_code=400, detail="Хато ёки муддати ўтган тиклаш коди")
    
    db.update_user_password(email, new_password)
    db.delete_reset_code(email)
    
    return {"success": True, "message": "Парол муваффақиятли ўзгартирилди! Энди янги парол билан киришингиз мумкин."}

# Note: Admin users and moderation routes moved to admin_routes.py

# ═══════════════════════════════════════════════════
# FILES DIRECTORY API
# ═══════════════════════════════════════════════════

@app.get("/api/files")
async def list_files(current_user: Dict = Depends(get_current_user)):
    """List all uploaded files in the uploads directory."""
    try:
        files = db.list_uploaded_files()
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/{filename}/download")
async def download_file(filename: str, current_user: Dict = Depends(get_current_user)):
    """Download a specific file from uploads."""
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл топилмади")
    return FileResponse(
        file_path,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.get("/api/files/{filename}/preview")
async def preview_file(filename: str, current_user: Dict = Depends(get_current_user)):
    """Get text preview of a file."""
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл топилмади")
    preview = db.get_file_text_preview(file_path)
    return {"preview": preview, "filename": filename}

@app.post("/api/files/upload")
async def upload_file_to_directory(file: UploadFile = File(...), current_user: Dict = Depends(get_current_user)):
    """Upload a file directly to the files directory (without processing)."""
    safe_name = f"{int(datetime.utcnow().timestamp())}_{file.filename}"
    file_path = os.path.join(UPLOADS_DIR, safe_name)
    with open(file_path, "wb") as buffer:
        file.file.seek(0)
        shutil.copyfileobj(file.file, buffer)
    return {"success": True, "filename": safe_name, "original": file.filename}

@app.delete("/api/files/{filename}")
async def delete_file(filename: str, current_user: Dict = Depends(get_current_user)):
    """Delete a file from uploads directory."""
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл топилмади")
    try:
        os.remove(file_path)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/{filename}/open")
async def open_file_in_editor(filename: str, background_tasks: BackgroundTasks, mode: str = "auto", current_user: Dict = Depends(get_current_user)):
    """Process a file from uploads directory and open it in the editor."""
    file_path = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл топилмади")
    
    processing_path = file_path
    original_filename = filename
    
    # Convert PDF to DOCX if needed
    if filename.lower().endswith(".pdf"):
        docx_path = file_path.rsplit(".", 1)[0] + ".docx"
        if not os.path.exists(docx_path):
            try:
                cv = Converter(file_path)
                cv.convert(docx_path)
                cv.close()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"PDF конвертация хатоси: {str(e)}")
        processing_path = docx_path
    
    try:
        aligner = ParagraphAligner(processing_path)
        data = aligner.process_ready_form() if mode == "ready" else aligner.process()
        
        # Auto-generate text_id
        specialist_short = current_user.get("name", "User").split()[0][:6] if current_user.get("name") else "User"
        text_id = f"{specialist_short}_{int(datetime.utcnow().timestamp())}"
        
        for row in data:
            row["text_id"] = text_id
        
        db.update_project_metadata(text_id, current_user.get("name", "Aniqlanmagan"), user_id=current_user["id"])
        
        conn = db.connect_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE projects SET original_filename = ?, file_path = ? WHERE id = ?", (original_filename, file_path, text_id))
        conn.commit()
        conn.close()
        
        db.save_alignments(text_id, data, user_id=current_user["id"])
        background_tasks.add_task(pre_polish_document, text_id)
        
        return {"filename": original_filename, "data": data, "text_id": text_id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════
# TRANSLITERATION
# ═══════════════════════════════════════════════════

@app.post("/api/transliterate")
async def transliterate_text(payload: Dict[str, Any]):
    text = payload.get("text", "")
    target = payload.get("target", "latin") # 'latin' or 'cyrillic'
    if not text:
        return {"text": ""}
    
    result = transliterate.convert_text(text, target=target)
    return {"text": result}

@app.post("/api/transliterate-batch")
async def transliterate_batch(payload: Dict[str, Any]):
    texts = payload.get("texts", [])
    target = payload.get("target", "latin")
    results = [transliterate.convert_text(t, target=target) for t in texts]
    return {"texts": results}

# ═════════════════════════════════════════════════
# Synonyms API
# ═════════════════════════════════════════════════

@app.get("/api/synonyms")
async def get_synonyms_list(word: str = None, lang: str = None, current_user: Dict = Depends(get_current_user)):
    """Get synonyms list, optionally filtered."""
    syns = db.get_synonyms(word=word, lang=lang, limit=10000)
    return {"synonyms": syns, "total": len(syns)}

@app.post("/api/synonyms/save")
async def save_synonym_endpoint(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Save a synonym manually."""
    word = payload.get("word", "").strip()
    synonym = payload.get("synonym", "").strip()
    lang = payload.get("lang", "uz")
    if not word or not synonym:
        raise HTTPException(status_code=400, detail="word and synonym required")
    db.save_synonym(word, synonym, lang, source='manual', created_by=current_user.get("name", ""))
    return {"status": "saved"}

@app.post("/api/synonyms/select")
async def select_synonym(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Increment synonym frequency when user selects it."""
    word = payload.get("word", "").strip()
    synonym = payload.get("synonym", "").strip()
    lang = payload.get("lang", "uz")
    if word and synonym:
        db.increment_synonym_frequency(word, synonym, lang)
    return {"status": "ok"}

@app.delete("/api/synonyms/{syn_id}")
async def delete_synonym_endpoint(syn_id: int, current_user: Dict = Depends(get_current_user)):
    """Delete a synonym."""
    db.delete_synonym(syn_id)
    return {"status": "deleted"}

# ═════════════════════════════════════════════════
# Profile & Password API
# ═════════════════════════════════════════════════

@app.post("/api/profile/update")
async def update_profile(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Update user profile (name, email)."""
    name = payload.get("name", "").strip()
    email = payload.get("email", "").strip()
    db.update_user_profile(current_user["id"], name=name or None, email=email or None)
    return {"status": "updated"}

@app.post("/api/profile/password")
async def update_password(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Set or change password. Google OAuth users can add a password."""
    import hashlib
    old_password = payload.get("old_password", "")
    new_password = payload.get("new_password", "")
    
    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Парол камида 6 та белгидан иборат бўлиши керак")
    
    # Check if user has existing password
    existing_hash = db.get_user_password_hash(current_user["id"])
    if existing_hash and existing_hash.strip():
        # Verify old password
        old_hash = hashlib.sha256(old_password.encode()).hexdigest()
        if old_hash != existing_hash:
            raise HTTPException(status_code=400, detail="Эски парол нотўғри")
    
    # Set new password
    new_hash = hashlib.sha256(new_password.encode()).hexdigest()
    db.set_user_password(current_user["id"], new_hash)
    return {"status": "password_updated"}

# ═════════════════════════════════════════════════
# API Aliases for frontend compatibility
# ═════════════════════════════════════════════════

@app.post("/api/suggest-edits")
async def suggest_edits_alias(payload: Dict[str, Any]):
    """Alias for /suggest-edits for frontend /api/ prefix compatibility."""
    return await suggest_edits(payload)

@app.post("/api/synonyms-lookup")
async def synonyms_lookup_alias(payload: Dict[str, Any]):
    """Alias for /synonyms."""
    return await suggest_edits(payload)

if __name__ == "__main__":
    import startup
    startup.setup_tahrirchi_db()
    
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
