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
import jwt
import requests
from datetime import datetime, timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.requests import Request

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
    expose_headers=["Content-Disposition"],
)

TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(os.path.join(TEMP_DIR, "imgs"), exist_ok=True)

# Serve extracted images as static files
app.mount("/static", StaticFiles(directory=TEMP_DIR), name="static")

# Security constants
JWT_SECRET = os.getenv("JWT_SECRET", "pharma_secret_key_2026")
JWT_ALGORITHM = "HS256"
GOOGLE_CLIENT_ID = "1069007349621-b47vhi16hf6rdi7phgkga9mobjvfqq3g.apps.googleusercontent.com"

security = HTTPBearer()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(res: HTTPAuthorizationCredentials = Request):
    # This is a helper, but we'll use a more standard FastAPI dependency
    pass

def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except:
        return None

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
            print(f"AI alignment error for batch {batch_start}: {e} вЂ” keeping proportional alignment")

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
    
    EXPERT_SYSTEM_PROMPT = """Role: РЎРёР· С„Р°СЂРјР°РєРѕР»РѕРіРёСЏ РІР° С…Р°Р»Т›Р°СЂРѕ СЃС‚Р°РЅРґР°СЂС‚Р»Р°СЂ (Pharmacopoeia, GMP, ISO) Р±СћР№РёС‡Р° СЋТ›РѕСЂРё РјР°Р»Р°РєР°Р»Рё СЌРєСЃРїРµСЂС‚-РјСѓТіР°СЂСЂРёСЂ РІР° С‚Р°СЂР¶РёРјРѕРЅСЃРёР·.

Task: РЎРёР·РіР° Р±РµСЂРёР»РіР°РЅ РёРЅРіР»РёР· С‚РёР»РёРґР°РіРё РћР РР“РРќРђР› (Ground Truth) РјР°С‚РЅ ТіР°РјРґР° СѓРЅРёРЅРі С‚Р°СЂР¶РёРјР°СЃРёРЅРё СћР·Р°СЂРѕ СЃРѕР»РёС€С‚РёСЂРёР±, РёР»РјРёР№ С‚Р°ТіСЂРёСЂ Т›РёР»РёРЅРі.

РР»РјРёР№ С‚Р°ТіСЂРёСЂ РјРµР·РѕРЅР»Р°СЂРё:
1. РРЅРіР»РёР·С‡Р° РјР°С‚РЅ - Р°СЃРѕСЃРёР№ РјР°РЅР±Р°. РўР°СЂР¶РёРјР° СѓРЅРёРЅРі РјР°СЉРЅРѕСЃРёРЅРё РІР° С„Р°СЂРјР°С†РµРІС‚РёРє С‚РµСЂРјРёРЅРѕР»РѕРіРёСЏСЃРёРЅРё 100% Р°РЅРёТ›Р»РёРєРґР° РёС„РѕРґР°Р»Р°С€Рё С€Р°СЂС‚.
2. РЈСЃР»СѓР± - РјР°С‚РЅ Т›Р°С‚СЉРёР№ СЂР°РІРёС€РґР° С„Р°СЂРјР°РєРѕРїРµСЏ РјР°Т›РѕР»Р°Р»Р°СЂРё СѓСЃР»СѓР±РёРґР°, РёР»РјРёР№ РІР° С‚РµСЂРјРёРЅРѕР»РѕРіРёРє Р¶РёТіР°С‚РґР°РЅ Р±РµРЅСѓТ›СЃРѕРЅ Р±СћР»РёС€Рё РєРµСЂР°Рє.
3. РђРіР°СЂ С‚Р°СЂР¶РёРјР°РґР° РёРЅРіР»РёР·С‡Р° Р°СЃР» РјР°С‚РЅРіР° Р·РёРґ С‘РєРё РЅРѕР°РЅРёТ› Р¶РѕР№Р»Р°СЂ Р±СћР»СЃР°, СѓР»Р°СЂРЅРё РёРЅРіР»РёР·С‡Р° РјР°С‚РЅРіР° РјСѓРІРѕС„РёТ›Р»Р°С€С‚РёСЂРёР± С‚СѓР·Р°С‚РёРЅРі.

РЋР·РіР°СЂС‚РёСЂРёР»РіР°РЅ СЃСћР· С‘РєРё РёР±РѕСЂР°Р»Р°СЂ РљРР РР›Р›Р§Рђ С‘Р·СѓРІРёРґР° <b>...С‚РµРіР»Р°СЂРґР°</b> Р°Р¶СЂР°С‚РёР± РєСћСЂСЃР°С‚РёР»СЃРёРЅ."""
    
    # New Rule: If English is empty but Russian exists, use Russian as source for Uzbek
    is_russian_only = not en_text.strip() and ru_text.strip()
    
    if target_lang == 'ru':
        user_prompt = f"""РРЅРіР»РёР·С‡Р° РјР°С‚РЅ (РђРЎРћРЎРР™ РњРђРќР‘Рђ): {en_text}
Р СѓСЃС‡Р° РјР°С‚РЅ (С‚Р°ТіСЂРёСЂ СѓС‡СѓРЅ Р»РѕР№РёТіР°): {ru_text}

Р¤РђТљРђРў СЂСѓСЃ С‚РёР»РёРґР°РіРё РјР°С‚РЅРЅРё РёРЅРіР»РёР·С‡Р° Р°СЃР» РјР°С‚РЅРіР° Р°СЃРѕСЃР»Р°РЅРёР±, РёР»РјРёР№ Р¶РёТіР°С‚РґР°РЅ С‚Р°ТіСЂРёСЂ Т›РёР»РёРЅРі РІР° JSON С„РѕСЂРјР°С‚РёРґР° Т›Р°Р№С‚Р°СЂРёРЅРі:
{{"ru_v2": "РёРЅРіР»РёР·С‡Р° РјР°С‚РЅРіР° РјРѕСЃ С‚СћТ“СЂРёР»Р°РЅРіР°РЅ СЂСѓСЃ РјР°С‚РЅ", "rationale": "РЅРµРіР° Р°Р№РЅР°РЅ С€СѓРЅРґР°Р№ С‚СѓР·Р°С‚РёР»РґРё (С‚РµСЂРјРёРЅРіР° Р°СЃРѕСЃ)"}}"""
    elif target_lang == 'uz':
        if is_russian_only:
            user_prompt = f"""Р СѓСЃС‡Р° РјР°С‚РЅ (РђРЎРћРЎРР™ РњРђРќР‘Рђ): {ru_text}
РЋР·Р±РµРєС‡Р° РјР°С‚РЅ (С‚Р°ТіСЂРёСЂ СѓС‡СѓРЅ Р»РѕР№РёТіР°): {uz_text}

РњР°С‚РЅ С„Р°Т›Р°С‚ СЂСѓСЃ С‚РёР»РёРґР° Р±СћР»РіР°РЅР»РёРіРё СЃР°Р±Р°Р±Р»Рё, СћР·Р±РµРє С‚РёР»РёРґР°РіРё РјР°С‚РЅРЅРё Р РЈРЎР§Рђ Р°СЃР» РјР°С‚РЅРіР° Р°СЃРѕСЃР»Р°РЅРёР±, РёР»РјРёР№ Р¶РёТіР°С‚РґР°РЅ С‚Р°ТіСЂРёСЂ Т›РёР»РёРЅРі РІР° JSON С„РѕСЂРјР°С‚РёРґР° Т›Р°Р№С‚Р°СЂРёРЅРі:
{{"uz_v2": "СЂСѓСЃС‡Р° РјР°С‚РЅРіР° РјРѕСЃ С‚СћТ“СЂРёР»Р°РЅРіР°РЅ СћР·Р±РµРє РјР°С‚РЅ", "rationale": "СЂСѓСЃС‡Р° РјР°С‚РЅРґР°РЅ РєРµР»РёР± С‡РёТ›РёР± РЅРµРіР° Р°Р№РЅР°РЅ С€СѓРЅРґР°Р№ С‚СѓР·Р°С‚РёР»РґРё"}}"""
        else:
            user_prompt = f"""РРЅРіР»РёР·С‡Р° РјР°С‚РЅ (РђРЎРћРЎРР™ РњРђРќР‘Рђ): {en_text}
РЋР·Р±РµРєС‡Р° РјР°С‚РЅ (С‚Р°ТіСЂРёСЂ СѓС‡СѓРЅ Р»РѕР№РёТіР°): {uz_text}

Р¤РђТљРђРў СћР·Р±РµРє С‚РёР»РёРґР°РіРё РјР°С‚РЅРЅРё РёРЅРіР»РёР·С‡Р° Р°СЃР» РјР°С‚РЅРіР° Р°СЃРѕСЃР»Р°РЅРёР±, РёР»РјРёР№ Р¶РёТіР°С‚РґР°РЅ С‚Р°ТіСЂРёСЂ Т›РёР»РёРЅРі РІР° JSON С„РѕСЂРјР°С‚РёРґР° Т›Р°Р№С‚Р°СЂРёРЅРі:
{{"uz_v2": "РёРЅРіР»РёР·С‡Р° РјР°С‚РЅРіР° РјРѕСЃ С‚СћТ“СЂРёР»Р°РЅРіР°РЅ СћР·Р±РµРє РјР°С‚РЅ", "rationale": "РЅРµРіР° Р°Р№РЅР°РЅ С€СѓРЅРґР°Р№ С‚СѓР·Р°С‚РёР»РґРё (С‚РµСЂРјРёРЅРіР° Р°СЃРѕСЃ)"}}"""
    else:
        user_prompt = f"""РРЅРіР»РёР·С‡Р° РјР°С‚РЅ (РђРЎРћРЎРР™ РњРђРќР‘Рђ): {en_text}
Р СѓСЃС‡Р° РјР°С‚РЅ: {ru_text}
РЋР·Р±РµРєС‡Р° РјР°С‚РЅ: {uz_text}

РРєРєР°Р»Р° С‚РёР»РґР°РіРё РјР°С‚РЅРЅРё ТіР°Рј РёРЅРіР»РёР·С‡Р° Р°СЃР» РјР°С‚РЅРіР° Р°СЃРѕСЃР»Р°РЅРёР±, С‚Р°ТіСЂРёСЂ Т›РёР»РёРЅРі РІР° JSON С„РѕСЂРјР°С‚РёРґР° Т›Р°Р№С‚Р°СЂРёРЅРі:
{{"ru_v2": "С‚СћТ“СЂРёР»Р°РЅРіР°РЅ СЂСѓСЃ РјР°С‚РЅ", "uz_v2": "С‚СћТ“СЂРёР»Р°РЅРіР°РЅ СћР·Р±РµРє РјР°С‚РЅ", "rationale": "С‚СѓР·Р°С‚РёС€Р»Р°СЂ РёР·РѕТіРё"}}"""

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
    ranked by probability (highest в†’ lowest),
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
    lang_label  = "СЂСѓСЃ" if lang == "ru" else "СћР·Р±РµРє"
    current_txt = context_ru if lang == "ru" else context_uz

    prompt = f"""Role: РЎРёР· С„Р°СЂРјР°РєРѕР»РѕРіРёСЏ РІР° С…Р°Р»Т›Р°СЂРѕ СЃС‚Р°РЅРґР°СЂС‚Р»Р°СЂ (Pharmacopoeia, GMP, ISO) Р±СћР№РёС‡Р° СЋТ›РѕСЂРё РјР°Р»Р°РєР°Р»Рё СЌРєСЃРїРµСЂС‚-РјСѓТіР°СЂСЂРёСЂ СЃРёР·СЃРёР·.

РРЅРіР»РёР·С‡Р° РѕСЂРёРіРёРЅР°Р» РіР°Рї: {context_en}
РўР°ТіСЂРёСЂ Т›РёР»РёРЅР°С‘С‚РіР°РЅ {lang_label} РјР°С‚РЅ: {current_txt}
РўР°РЅР»Р°РЅРіР°РЅ РёС„РѕРґР°: "{word}"

Task: РЈС€bu С‚Р°РЅР»Р°РЅРіР°РЅ РёС„РѕРґР° СѓС‡СѓРЅ РјР°С‚РЅРЅРёРЅРі С‚СћР»РёТ› РєРѕРЅС‚РµРєСЃС‚РёРґР°РЅ РІР° РёРЅРіР»РёР·С‡Р° РѕСЂРёРіРёРЅР°Р»РґР°РЅ РєРµР»РёР± С‡РёТ›РёР±, С„Р°СЂРјР°РєРѕР»РѕРіРёСЏ СЃС‚Р°РЅРґР°СЂС‚Р»Р°СЂРёРіР° РјРѕСЃ, РёР»РјРёР№ Р¶РёТіР°С‚РґР°РЅ РѕРїС‚РёРјР°Р» С‚Р°ТіСЂРёСЂ РІР°СЂРёР°РЅС‚Р»Р°СЂРёРЅРё СЌТіС‚РёРјРѕР»Р»РёРє СЋТ›РѕСЂРёРґР°РЅ РїР°СЃС‚РіР° Т›Р°СЂР°Р± 5 С‚Р° Р±РµСЂРёРЅРі.

РњРµР·РѕРЅР»Р°СЂ (РїСЂРѕРјС‚ Р№СћСЂРёТ›РЅРѕРјР°СЃРёРіР° Р°РјР°Р» Т›РёР»РёРЅРі):
1. Р¤Р°СЂРјР°РєРѕРїРµСЏ С‚РµСЂРјРёРЅРѕР»РѕРіРёСЏСЃРёРіР° РјРѕСЃР»РёРє
2. РРЅРіР»РёР·С‡Р° РѕСЂРёРіРёРЅР°Р» Р±РёР»Р°РЅ РјР°СЉРЅРѕРІРёР№ РјСѓРІРѕС„РёТ›Р»РёРє  
3. {lang_label} РёР»РјРёР№ СѓСЃР»СѓР± РІР° СЃС‚РёР»РёСЃС‚РёРєР°
4. Р“СЂР°РјРјР°С‚РёРє Р°РЅРёТ›Р»РёРє

Р¤Р°Т›Р°С‚ JSON С„РѕСЂРјР°С‚РёРґР° Р¶Р°РІРѕР± Р±РµСЂРёРЅРі:
{{"variants": ["СЌРЅРі СЌТіС‚РёРјРѕР»Р»Рё", "2-РІР°СЂРёР°РЅС‚", "3-РІР°СЂРёР°РЅС‚", "4-РІР°СЂРёР°РЅС‚", "5-РІР°СЂРёР°РЅС‚"], "note": "Т›РёСЃТ›Р°С‡Р° Р°СЃРѕСЃР»Р°РјР°"}}"""

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

    # в”Ђв”Ђ Step 1: Check local rules database first в”Ђв”Ђ
    local_annotations = db.get_rules_for_text(text, lang)
    rules_count = db.get_rules_count(lang)

    # в”Ђв”Ђ Step 2: Call AI for comprehensive check в”Ђв”Ђ
    client = get_client()
    ai_annotations = []
    corrected_text = text

    if client:
        # Build rules context for AI (teach it our learned patterns)
        known_rules = db.get_all_rules(lang, limit=50)
        rules_examples = ""
        if known_rules:
            examples = [f"  В«{r['wrong_form']}В» в†’ В«{r['correct_form']}В» [{r['error_type']}]" 
                       for r in known_rules[:20]]
            rules_examples = f"\n\nРћР»РґРёРЅРіРё С‚СѓР·Р°С‚РёС€Р»Р°СЂ Р±Р°Р·Р°СЃРёРґР°РЅ РЅР°РјСѓРЅР°Р»Р°СЂ (Р±СѓР»Р°СЂРЅРё ТіРёСЃРѕР±РіР° РѕР»РёРЅРі):\n" + "\n".join(examples)

        SAYQALLASH_PROMPT = f"""РЎРёР· СћР·Р±РµРє С‚РёР»Рё РіСЂР°РјРјР°С‚РёРєР°СЃРё, РёРјР»РѕСЃРё РІР° С„Р°СЂРјР°С†РµРІС‚РёРє С‚РµСЂРјРёРЅРѕР»РѕРіРёСЏ Р±СћР№РёС‡Р° СЋТ›РѕСЂРё РјР°Р»Р°РєР°Р»Рё СЌРєСЃРїРµСЂС‚-С‚Р°ТіСЂРёСЂС‡РёСЃРёР·.

РЎРёР·РіР° СћР·Р±РµРєС‡Р° РјР°С‚РЅ Р±РµСЂРёР»РіР°РЅ. РЈРЅРґР°РіРё Р‘РђР Р§Рђ С…Р°С‚РѕР»РёРєР»Р°СЂРЅРё С‚СћР»РёТ› Р°РЅРёТ›Р»Р°РЅРі.
 
РњРЈТІРРњ: Р¤Р°СЂРјР°С†РµРІС‚РёРє РјР°С‚РЅР»Р°СЂРґР° ТіР°СЂС„ С‚СѓС€РёР± Т›РѕР»РёС€Рё (РјР°СЃР°Р»Р°РЅ: "СЃРёРЅР°Р»Р°РґРіР°РЅ" -> "СЃРёРЅР°Р»Р°РґРёРіР°РЅ") СЌРЅРі РєСћРї СѓС‡СЂР°Р№РґРёРіР°РЅ С…Р°С‚Рѕ. ТІР°СЂ Р±РёСЂ СЃСћР·РЅРёРЅРі РјРѕСЂС„РѕР»РѕРіРёРє С‚СѓР·РёР»РёС€РёРЅРё Р­РЄРўРР‘РћР  Р±РёР»Р°РЅ С‚РµРєС€РёСЂРёРЅРі.
 
РҐР°С‚Рѕ С‚СѓСЂР»Р°СЂРё:
- РРјР»РѕРІРёР№ С…Р°С‚РѕР»Р°СЂ (S/Spelling) вЂ” РўРЈРЁРР‘ ТљРћР›Р“РђРќ ТІРђР Р¤Р›РђР Р“Рђ Р°Р»РѕТіРёРґР° СЌСЉС‚РёР±РѕСЂ Р±РµСЂРёРЅРі!
- РљРѕРЅС‚РµРєСЃС‚РіР° РЅРѕРјРѕСЃ СЃСћР· (S/Context)
- РљР°С‚С‚Р°/РєРёС‡РёРє ТіР°СЂС„ (S/LowerUpper)
- РўРёРЅРёС€ Р±РµР»РіРёР»Р°СЂРё (Punctuation)
- РљРµР»РёС€РёРє Т›СћС€РёРјС‡Р°Р»Р°СЂРё (G/Case)
- Р­РіР°Р»РёРє Т›СћС€РёРјС‡Р°Р»Р°СЂРё (G/Possessive)  
- Р‘РёСЂРіР° С‘Р·РёС€ (G/Merge)
- РђР¶СЂР°С‚РёР± С‘Р·РёС€ (G/Split)
- Р—Р°РјРѕРЅ С€Р°РєР»Рё (G/VerbTense)
- Р‘РѕС€Т›Р° РіСЂР°РјРјР°С‚РёРє С…Р°С‚Рѕ (G/Other)
- РђРЅРёТ›Р»РёРє/РјР°СЉРЅРѕ (F/Clarity)
- РЈСЃР»СѓР±РёР№ С…Р°С‚Рѕ (F/Style)
- РљР°Р»СЊРєР° С‚Р°СЂР¶РёРјР° (F/Calque)
{rules_examples}

РњРЈТІРРњ ТљРћРР”РђР›РђР :
1. old_value = РјР°С‚РЅРґР°РіРё С…Р°С‚РѕР»Рё СЃСћР·/С„СЂР°Р·Р° (РђР™РќРђРќ С€Сѓ С€Р°РєР»РґР°)
2. new_value = С‚СћТ“СЂРёР»Р°РЅРіР°РЅ С€Р°РєР»
3. РћР»РґРёРЅРіРё С‚СѓР·Р°С‚РёС€Р»Р°СЂ Р±Р°Р·Р°СЃРёРґР°РЅ (rules_examples) С„РѕР№РґР°Р»Р°РЅРёР±, СЏРЅРіРё С…Р°С‚РѕР»Р°СЂРЅРё ТіР°Рј РёР·Р»Р°РЅРі.
4. РҐР°С‚РѕСЃРёР· РјР°С‚РЅ СѓС‡СѓРЅ Р±СћС€ РјР°СЃСЃРёРІ Т›Р°Р№С‚Р°СЂРёРЅРі.

Р¤Р°Т›Р°С‚ JSON С„РѕСЂРјР°С‚РёРґР° Р¶Р°РІРѕР± Р±РµСЂРёРЅРі:
{{"annotations": [{{"old_value": "С…Р°С‚РѕР»Рё", "new_value": "С‚СћТ“СЂРё", "error_type": "S/Spelling"}}], "corrected_text": "С‚СћР»РёТ› С‚СѓР·Р°С‚РёР»РіР°РЅ РјР°С‚РЅ"}}"""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                temperature=0,
                system=SAYQALLASH_PROMPT,
                messages=[{"role": "user", "content": f"РњР°С‚РЅРЅРё С‚РµРєС€РёСЂРёРЅРі:\n\n{text}"}]
            )
            resp_text = response.content[0].text
            match = re.search(r'\{.*\}', resp_text, re.DOTALL)
            if match:
                result = json.loads(match.group())
                for ann in result.get("annotations", []):
                    old_val = ann.get("old_value", "")
                    if not old_val: continue
                    
                    # Exhaustive matching: find ALL occurrences
                    start_search = 0
                    while True:
                        idx = text.find(old_val, start_search)
                        if idx == -1: break
                        
                        # Create unique annotation for each instance
                        instance_ann = ann.copy()
                        instance_ann["from_index"] = idx
                        instance_ann["to_index"] = idx + len(old_val)
                        instance_ann["source"] = "ai"
                        ai_annotations.append(instance_ann)
                        start_search = idx + len(old_val)
                corrected_text = result.get("corrected_text", text)
        except Exception as e:
            print(f"AI sayqallash error: {e}")

    # в”Ђв”Ђ Step 3: Merge local + AI annotations (deduplicate) в”Ђв”Ђ
    all_annotations = []
    seen_positions = set()
    
    # Local rules first (higher priority вЂ” learned from user)
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

@app.post("/sayqallash-rules")
async def add_sayqallash_rule(payload: Dict[str, Any]):
    """Manually add a new correction rule."""
    try:
        db.add_sayqallash_rule(
            wrong=payload.get("wrong_form", ""),
            correct=payload.get("correct_form", ""),
            error_type=payload.get("error_type", "S/Spelling"),
            context=payload.get("context", ""),
            lang=payload.get("lang", "uz"),
            source="manual"
        )
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/sayqallash-rules/{rule_id}")
async def update_sayqallash_rule(rule_id: int, payload: Dict[str, Any]):
    """Update an existing rule."""
    try:
        db.update_sayqallash_rule(rule_id, payload)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sayqallash-rules/{rule_id}")
async def delete_sayqallash_rule(rule_id: int):
    """Delete a rule."""
    try:
        db.delete_sayqallash_rule(rule_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        from urllib.parse import quote
        export_to_docx(data, output_path)
        download_name = f"confirmed_{file_basename}"
        if not download_name.endswith(".docx"):
            download_name += ".docx"
        
        encoded_filename = quote(download_name)
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=download_name,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/auth/google")
async def auth_google(payload: Dict[str, Any]):
    credential = payload.get("credential")
    if not credential:
        # Fallback for manual entry
        email = payload.get("email")
        name = payload.get("name")
        if not email:
            raise HTTPException(status_code=400, detail="Credential or Email required")
    else:
        # Verify with Google
        try:
            resp = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}")
            if not resp.ok:
                raise HTTPException(status_code=401, detail="Invalid Google token")
            google_data = resp.json()
            email = google_data.get("email")
            name = google_data.get("name")
            avatar_url = google_data.get("picture")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Google verification failed: {e}")

    user = db.get_user_by_email(email)
    if not user:
        # Create new user
        user_id = f"google_{int(datetime.utcnow().timestamp())}"
        db.create_user(user_id, email, name, payload.get("avatarUrl"))
        user = db.get_user_by_email(email)
    
    if user["status"] == "rejected":
        raise HTTPException(status_code=403, detail="Р’Р°С€Р° СѓС‡РµС‚РЅР°СЏ Р·Р°РїРёСЃСЊ РѕС‚РєР»РѕРЅРµРЅР° Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂРѕРј")

    # Update last login
    db.update_user_login(user["id"])
    
    # Refresh user data
    user = db.get_user_by_email(email)
    
    token = create_access_token({
        "userId": user["id"],
        "email": user["email"],
        "role": user["role"],
        "name": user["name"]
    })
    
    return {"success": True, "token": token, "user": user}

@app.get("/api/auth/me")
async def get_me(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.get_user_by_id(payload["userId"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    return {"user": user}

@app.get("/api/admin/users")
async def get_admin_users(request: Request):
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1] if auth_header else ""
    payload = verify_token(token)
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
        
    users = db.list_all_users()
    return {"users": users}

@app.post("/api/admin/approve")
async def approve_user(payload: Dict[str, Any], request: Request):
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1] if auth_header else ""
    payload_token = verify_token(token)
    if not payload_token or payload_token.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    target_id = payload.get("userId")
    status = payload.get("status") # approved/rejected
    db.update_user_status(target_id, status)
    return {"success": True}

@app.post("/api/admin/role")
async def change_role(payload: Dict[str, Any], request: Request):
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1] if auth_header else ""
    payload_token = verify_token(token)
    if not payload_token or payload_token.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    target_id = payload.get("userId")
    role = payload.get("role")
    db.update_user_role(target_id, role)
    return {"success": True}

@app.get("/specialists")
async def get_specialists():
    """Get unique specialist names for autocomplete."""
    try:
        names = db.get_unique_specialists()
        return {"specialists": names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects")
async def get_projects(request: Request):
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1] if auth_header else ""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    projects = db.list_projects()
    return {"projects": projects}

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, request: Request):
    auth_header = request.headers.get("Authorization")
    token = auth_header.split(" ")[1] if auth_header else ""
    payload = verify_token(token)
    if not payload or payload.get("role") not in ["admin", "rahbar"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete_project(project_id)
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

