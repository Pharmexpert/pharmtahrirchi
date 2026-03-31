from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
import os
import shutil
import json
import re
import db
from processor import ParagraphAligner, export_to_docx
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Database initialization
db.init_db()

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(os.path.join(TEMP_DIR, "imgs"), exist_ok=True)

# Serve extracted images as static files
app.mount("/static", StaticFiles(directory=TEMP_DIR), name="static")

# Initialize Anthropic client
_anthropic_client = None
def get_client():
    global _anthropic_client
    if not _anthropic_client:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            _anthropic_client = Anthropic(api_key=api_key)
    return _anthropic_client

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), mode: str = "auto"):
    file_path = os.path.join(TEMP_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        aligner = ParagraphAligner(file_path)
        if mode == "ready":
            data = aligner.process_ready_form()
        else:
            data = aligner.process()
        return {"filename": file.filename, "data": data}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/align-document")
async def align_document(payload: Dict[str, Any]):
    """AI-based alignment for the entire document in a single batched call."""
    client = get_client()
    if not client:
        raise HTTPException(status_code=503, detail="AI client not configured")

    rows = payload.get("data", [])
    if not rows:
        return {"data": rows}

    # Split rows into blocks (each block starts with a marker row)
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

    # Process blocks in batches of 4 to minimize API calls
    BATCH_SIZE = 4
    aligned_blocks = []

    for batch_start in range(0, len(blocks), BATCH_SIZE):
        batch = blocks[batch_start: batch_start + BATCH_SIZE]
        
        # Build a compact prompt with all blocks in this batch
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

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=6000,
                temperature=0,
                system="You are a trilingual pharmaceutical document alignment engine. Output valid JSON only.",
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                ai_result = json.loads(match.group())
                # Apply AI alignment to blocks
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
            print(f"AI alignment error for batch {batch_start}: {e} — keeping proportional alignment")

        aligned_blocks.extend(batch)

    # Reassemble flat data
    result_data = []
    for blk in aligned_blocks:
        if blk["marker"]:
            result_data.append(blk["marker"])
        result_data.extend(blk["rows"])

    return {"data": result_data}

@app.post("/improve-row")
async def improve_row(payload: Dict[str, Any]):
    """Uses the expert pharmaceutical AI prompt to improve a single row.
    If target_lang is specified, only that language is improved."""
    client = get_client()
    if not client:
        raise HTTPException(status_code=503, detail="AI client not configured")
    
    en_text = payload.get("en", "")
    ru_text = payload.get("ru_proposed", "") or payload.get("ru_v1", "")
    uz_text = payload.get("uz_proposed", "") or payload.get("uz_v1", "")
    target_lang = payload.get("target_lang", "")  # 'ru', 'uz', or '' for both
    
    EXPERT_SYSTEM_PROMPT = """Role: Сиз фармакология ва халқаро стандартлар (Pharmacopoeia, GMP, ISO) бўйича юқори малакали эксперт-муҳаррир ва таржимонсиз.

Task: Сизга берилган инглиз тилидаги ОРИГИНАЛ (Ground Truth) матн ҳамда унинг таржимасини ўзаро солиштириб, илмий таҳрир қилинг.

Илмий таҳрир мезонлари:
1. Инглизча матн - асосий манба. Таржима унинг маъносини ва фармацевтик терминологиясини 100% аниқликда ифодалаши шарт.
2. Услуб - матн қатъий равишда фармакопея мақолалари услубида, илмий ва терминологик жиҳатдан бенуқсон бўлиши керак.
3. Агар таржимада инглизча асл матнга зид ёки ноаниқ жойлар бўлса, уларни инглизча матнга мувофиқлаштириб тузатинг.

Ўзгартирилган сўз ёки иборалар КИРИЛЛЧА ёзувида <b>...тегларда</b> ажратиб кўрсатилсин."""
    
    if target_lang == 'ru':
        user_prompt = f"""Инглизча матн (АСОСИЙ МАНБА): {en_text}
Русча матн (таҳрир учун лойиҳа): {ru_text}

ФАҚАТ рус тилидаги матнни инглизча асл матнга асосланиб, илмий жиҳатдан таҳрир қилинг ва JSON форматида қайтаринг:
{{"ru_v2": "инглизча матнга мос тўғриланган рус матн", "rationale": "нега айнан шундай тузатилди (терминга асос)"}}"""
    elif target_lang == 'uz':
        user_prompt = f"""Инглизча матн (АСОСИЙ МАНБА): {en_text}
Ўзбекча матн (таҳрир учун лойиҳа): {uz_text}

ФАҚАТ ўзбек тилидаги матнни инглизча асл матнга асосланиб, илмий жиҳатдан таҳрир қилинг ва JSON форматида қайтаринг:
{{"uz_v2": "инглизча матнга мос тўғриланган ўзбек матн", "rationale": "нега айнан шундай тузатилди (терминга асос)"}}"""
    else:
        user_prompt = f"""Инглизча матн (АСОСИЙ МАНБА): {en_text}
Русча матн: {ru_text}
Ўзбекча матн: {uz_text}

Иккала тилдаги матнни ҳам инглизча асл матнга асосланиб, таҳрир қилинг ва JSON форматида қайтаринг:
{{"ru_v2": "тўғриланган рус матн", "uz_v2": "тўғриланган ўзбек матн", "rationale": "тузатишлар изоҳи"}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0,
            system=EXPERT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        text = response.content[0].text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            raise HTTPException(status_code=500, detail="AI response format error")
        result = json.loads(match.group())
        return result
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse AI response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/suggest-edits")
@app.post("/synonyms")  # keep alias for compatibility
async def suggest_edits(payload: Dict[str, Any]):
    """
    Returns 5 optimal edit variants for the selected phrase,
    ranked by probability (highest → lowest),
    using the pharmaceutical expert prompt context.
    """
    client = get_client()
    if not client:
        raise HTTPException(status_code=503, detail="AI client not configured")

    word        = payload.get("word", "")
    lang        = payload.get("lang", "ru")
    context_en  = payload.get("context_en", payload.get("context", ""))
    context_ru  = payload.get("context_ru", "")
    context_uz  = payload.get("context_uz", "")
    lang_label  = "рус" if lang == "ru" else "ўзбек"
    current_txt = context_ru if lang == "ru" else context_uz

    prompt = f"""Role: Сиз фармакология ва халқаро стандартлар (Pharmacopoeia, GMP, ISO) бўйича юқори малакали эксперт-муҳаррир сизсиз.

Инглизча оригинал гап: {context_en}
Таҳрир қилинаётган {lang_label} матн: {current_txt}
Танланган ифода: "{word}"

Task: Ушbu танланган ифода учун матннинг тўлиқ контекстидан ва инглизча оригиналдан келиб чиқиб, фармакология стандартларига мос, илмий жиҳатдан оптимал таҳрир вариантларини эҳтимоллик юқоридан пастга қараб 5 та беринг.

Мезонлар (промт йўриқномасига амал қилинг):
1. Фармакопея терминологиясига мослик
2. Инглизча оригинал билан маъновий мувофиқлик  
3. {lang_label} илмий услуб ва стилистика
4. Грамматик аниқлик

Фақат JSON форматида жавоб беринг:
{{"variants": ["энг эҳтимолли", "2-вариант", "3-вариант", "4-вариант", "5-вариант"], "note": "қисқача асослама"}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            temperature=0,
            system="You are a pharmaceutical expert editor. Return only valid JSON, no extra text.",
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            return {"variants": [], "synonyms": [], "note": ""}
        result = json.loads(match.group())
        # Normalize: support both 'variants' and 'synonyms' keys in frontend
        result["synonyms"] = result.get("variants", [])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sayqallash")
async def sayqallash(payload: Dict[str, Any]):
    """
    Grammatical Error Correction (GEC) for Uzbek text.
    HYBRID: Local rules DB + AI (Claude).
    """
    text = payload.get("text", "").strip()
    lang = payload.get("lang", "uz")
    if not text:
        return {"annotations": [], "corrected_text": "", "rules_count": 0}

    # ── Step 1: Check local rules database first ──
    local_annotations = db.get_rules_for_text(text, lang)
    rules_count = db.get_rules_count(lang)

    # ── Step 2: Call AI for comprehensive check ──
    client = get_client()
    ai_annotations = []
    corrected_text = text

    if client:
        # Build rules context for AI (teach it our learned patterns)
        known_rules = db.get_all_rules(lang, limit=50)
        rules_examples = ""
        if known_rules:
            examples = [f"  «{r['wrong_form']}» → «{r['correct_form']}» [{r['error_type']}]" 
                       for r in known_rules[:20]]
            rules_examples = f"\n\nОлдинги тузатишлар базасидан намуналар (буларни ҳисобга олинг):\n" + "\n".join(examples)

        SAYQALLASH_PROMPT = f"""Сиз ўзбек тили грамматикаси, имлоси ва фармацевтик терминология бўйича юқори малакали эксперт-таҳрирчисиз.

Сизга ўзбекча матн берилган. Ундаги БАРЧА хатоликларни тўлиқ аниқланг:
- Имловий хатолар (S/Spelling)
- Контекстга номос сўз (S/Context)
- Катта/кичик ҳарф (S/LowerUpper)
- Тиниш белгилари (Punctuation)
- Келишик қўшимчалари (G/Case)
- Эгалик қўшимчалари (G/Possessive)  
- Бирга ёзиш (G/Merge)
- Ажратиб ёзиш (G/Split)
- Замон шакли (G/VerbTense)
- Бошқа грамматик хато (G/Other)
- Аниқлик/маъно (F/Clarity)
- Услубий хато (F/Style)
- Калька таржима (F/Calque)
{rules_examples}

МУҲИМ ҚОИДАЛАР:
1. from_index ва to_index матндаги символлар позициясини АНИҚ кўрсатиши керак (0 дан бошлаб)
2. old_value = матндаги хатоли сўз/фраза (АЙНАН шу шаклда)
3. new_value = тўғриланган шакл
4. error_type = юқоридаги турлардан бири
5. Хатосиз матн учун бўш массив қайтаринг

Фақат JSON форматида жавоб беринг:
{{"annotations": [{{"from_index": 0, "to_index": 5, "old_value": "хатоли", "new_value": "тўғри", "error_type": "S/Spelling"}}], "corrected_text": "тўлиқ тузатилган матн"}}"""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0,
                system=SAYQALLASH_PROMPT,
                messages=[{"role": "user", "content": f"Матнни текширинг:\n\n{text}"}]
            )
            resp_text = response.content[0].text
            match = re.search(r'\{.*\}', resp_text, re.DOTALL)
            if match:
                result = json.loads(match.group())
                for ann in result.get("annotations", []):
                    old_val = ann.get("old_value", "")
                    actual_idx = text.find(old_val)
                    if actual_idx >= 0:
                        ann["from_index"] = actual_idx
                        ann["to_index"] = actual_idx + len(old_val)
                        ann["source"] = "ai"
                        ai_annotations.append(ann)
                corrected_text = result.get("corrected_text", text)
        except Exception as e:
            print(f"AI sayqallash error: {e}")

    # ── Step 3: Merge local + AI annotations (deduplicate) ──
    all_annotations = []
    seen_positions = set()
    
    # Local rules first (higher priority — learned from user)
    for ann in local_annotations:
        key = (ann['from_index'], ann['to_index'])
        if key not in seen_positions:
            seen_positions.add(key)
            ann['source'] = 'rules_db'
            all_annotations.append(ann)
    
    # Then AI annotations
    for ann in ai_annotations:
        key = (ann.get('from_index', 0), ann.get('to_index', 0))
        if key not in seen_positions:
            seen_positions.add(key)
            all_annotations.append(ann)

    all_annotations.sort(key=lambda a: a.get("from_index", 0))
    
    return {
        "annotations": all_annotations,
        "corrected_text": corrected_text,
        "rules_count": rules_count,
        "local_matches": len(local_annotations),
        "ai_matches": len(ai_annotations)
    }

@app.post("/auto-notes")
async def auto_notes(payload: Dict[str, Any]):
    """Generate diff notes by comparing V1 with Proposed text."""
    v1 = payload.get("v1", "")
    proposed = payload.get("proposed", "")
    lang = payload.get("lang", "uz")
    notes = db.generate_diff_notes(v1, proposed, lang)
    return {"notes": notes}

@app.get("/sayqallash-rules")
async def get_sayqallash_rules(lang: str = "uz", limit: int = 100):
    """Get all learned correction rules."""
    rules = db.get_all_rules(lang, limit)
    count = db.get_rules_count(lang)
    return {"rules": rules, "total": count}

@app.post("/save")
async def save_data(payload: Dict[str, Any]):
    data = payload.get("data", [])
    try:
        db.save_alignments(data)
        return {"status": "success", "message": "Data saved to database"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save-row")
async def save_single_row(payload: Dict[str, Any]):
    try:
        new_id = db.save_single_row(payload)
        return {"status": "success", "message": "Row saved", "new_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete-row/{text_id}/{sentence_no}")
async def delete_row(text_id: str, sentence_no: int):
    try:
        db.delete_row(sentence_no, text_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{text_id}")
async def get_history(text_id: str):
    try:
        return db.get_history(text_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export")
async def export_data(payload: Dict[str, Any]):
    filename = payload.get("filename", "aligned_output.docx")
    data = payload.get("data", [])
    file_basename = os.path.basename(filename)
    output_path = os.path.abspath(os.path.join(TEMP_DIR, f"confirmed_{file_basename}"))
    try:
        export_to_docx(data, output_path)
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"confirmed_{file_basename}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
