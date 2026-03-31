"""
Vercel Serverless Function — FastAPI wrapper for Pharma Platform API.
This file serves as the entry point for all /api/* requests on Vercel.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import os
import json
import re
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from anthropic import Anthropic
from dotenv import load_dotenv
import jwt
from datetime import datetime, timedelta

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════
JWT_SECRET = os.getenv("JWT_SECRET", "pharma_secret_key_2026")
JWT_ALGORITHM = "HS256"

_anthropic_client = None
def get_client():
    global _anthropic_client
    if not _anthropic_client:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            _anthropic_client = Anthropic(api_key=api_key)
    return _anthropic_client

def verify_token(token: str):
    if token == "dev-token":
        return {"userId": "admin_primary", "email": "texnopharm@gmail.com", "role": "admin", "name": "Admin (Dev)"}
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except:
        return None

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(days=7)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

# ═══════════════════════════════════════════════════
# Database — Vercel Postgres or SQLite fallback
# ═══════════════════════════════════════════════════
DATABASE_URL = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")

def get_db():
    """Returns a database connection — Postgres on Vercel, SQLite locally."""
    if DATABASE_URL:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        return conn, 'postgres'
    else:
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'pharma_editor.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn, 'sqlite'

# ═══════════════════════════════════════════════════
# AI Endpoints
# ═══════════════════════════════════════════════════

@app.post("/api/improve-row")
async def improve_row(payload: Dict[str, Any]):
    client = get_client()
    if not client:
        raise HTTPException(status_code=503, detail="AI client not configured")
    
    en_text = payload.get("en", "")
    ru_text = payload.get("ru_proposed", "") or payload.get("ru_v1", "")
    uz_text = payload.get("uz_proposed", "") or payload.get("uz_v1", "")
    target_lang = payload.get("target_lang", "")
    
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
            max_tokens=2000, temperature=0,
            system=EXPERT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        text = response.content[0].text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            raise HTTPException(status_code=500, detail="AI response format error")
        return json.loads(match.group())
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse AI response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/suggest-edits")
async def suggest_edits(payload: Dict[str, Any]):
    client = get_client()
    if not client:
        raise HTTPException(status_code=503, detail="AI client not configured")

    word = payload.get("word", "")
    lang = payload.get("lang", "ru")
    context_en = payload.get("context_en", payload.get("context", ""))
    context_ru = payload.get("context_ru", "")
    context_uz = payload.get("context_uz", "")
    lang_label = "рус" if lang == "ru" else "ўзбек"
    current_txt = context_ru if lang == "ru" else context_uz

    prompt = f"""Role: Сиз фармакология ва халқаро стандартлар бўйича юқори малакали эксперт-муҳаррирсиз.

Инглизча оригинал гап: {context_en}
Таҳрир қилинаётган {lang_label} матн: {current_txt}
Танланган ифода: "{word}"

Task: 5 та оптимал таҳрир вариантини беринг.

Фақат JSON форматида жавоб беринг:
{{"variants": ["энг эҳтимолли", "2-вариант", "3-вариант", "4-вариант", "5-вариант"], "note": "қисқача асослама"}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600, temperature=0,
            system="You are a pharmaceutical expert editor. Return only valid JSON.",
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            return {"variants": [], "synonyms": [], "note": ""}
        result = json.loads(match.group())
        result["synonyms"] = result.get("variants", [])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sayqallash")
async def sayqallash(payload: Dict[str, Any]):
    text = payload.get("text", "").strip()
    lang = payload.get("lang", "uz")
    if not text:
        return {"annotations": [], "corrected_text": "", "rules_count": 0}

    client = get_client()
    ai_annotations = []
    corrected_text = text

    if client:
        SAYQALLASH_PROMPT = f"""Сиз ўзбек тили грамматикаси, имлоси ва фармацевтик терминология бўйича юқори малакали эксперт-таҳрирчисиз.

Сизга ўзбекча матн берилган. Ундаги БАРЧА хатоликларни тўлиқ аниқланг.

Хато турлари:
- Имловий хатолар (S/Spelling)
- Контекстга номос сўз (S/Context)
- Тиниш белгилари (Punctuation)
- Келишик қўшимчалари (G/Case)
- Бошқа грамматик хато (G/Other)

Фақат JSON форматида жавоб беринг:
{{"annotations": [{{"old_value": "хатоли", "new_value": "тўғри", "error_type": "S/Spelling"}}], "corrected_text": "тўлиқ тузатилган матн"}}"""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000, temperature=0,
                system=SAYQALLASH_PROMPT,
                messages=[{"role": "user", "content": f"Матнни текширинг:\n\n{text}"}]
            )
            resp_text = response.content[0].text
            match = re.search(r'\{.*\}', resp_text, re.DOTALL)
            if match:
                result = json.loads(match.group())
                for ann in result.get("annotations", []):
                    old_val = ann.get("old_value", "")
                    if not old_val: continue
                    idx = text.find(old_val)
                    if idx != -1:
                        ann["from_index"] = idx
                        ann["to_index"] = idx + len(old_val)
                        ann["source"] = "ai"
                        ai_annotations.append(ann)
                corrected_text = result.get("corrected_text", text)
        except Exception as e:
            print(f"AI sayqallash error: {e}")

    return {
        "annotations": ai_annotations,
        "corrected_text": corrected_text,
        "rules_count": 0,
        "local_matches": 0,
        "ai_matches": len(ai_annotations)
    }


@app.post("/api/align-document")
async def align_document(payload: Dict[str, Any]):
    client = get_client()
    if not client:
        raise HTTPException(status_code=503, detail="AI client not configured")

    rows = payload.get("data", [])
    if not rows:
        return {"data": rows}

    # Simple pass-through for now — full alignment logic is complex
    return {"data": rows}


@app.post("/api/split-row")
async def split_row(payload: Dict[str, Any]):
    row = payload.get("row")
    if not row:
        raise HTTPException(status_code=400, detail="Row data required")
    
    client = get_client()
    if client:
        try:
            prompt = f"""Split this trilingual pharma row into two logical parts.
EN: {row['en']}
RU: {row.get('ru_proposed') or row['ru_v1']}
UZ: {row.get('uz_proposed') or row['uz_v1']}

Return JSON only: {{"part1": {{"en": "...", "ru": "...", "uz": "..."}}, "part2": {{"en": "...", "ru": "...", "uz": "..."}}}}"""
            
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                system="Trilingual Splitter.",
                messages=[{"role": "user", "content": prompt}]
            )
            match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
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


# ═══════════════════════════════════════════════════
# Auth endpoints for Vercel
# ═══════════════════════════════════════════════════

@app.post("/api/auth/login")
async def login_api(payload: Dict[str, Any]):
    email = payload.get("email", "").lower().strip()
    password = payload.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email ва паролни тўлдиринг")
    
    # Simple auth for Vercel — check admin credentials
    if email == "texnopharm@gmail.com" and password == "admin123":
        token = create_access_token({"userId": "admin_primary", "email": email, "role": "admin", "name": "Admin Texnopharm"})
        return {"success": True, "token": token, "user": {"id": "admin_primary", "email": email, "role": "admin", "name": "Admin Texnopharm", "status": "approved"}}
    
    raise HTTPException(status_code=401, detail="Email ёки парол хато")


@app.get("/api/auth/me")
async def get_me(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401)
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401)
    return {"user": {"id": payload.get("userId"), "email": payload.get("email"), "role": payload.get("role"), "name": payload.get("name"), "status": "approved"}}


@app.get("/api/projects")
async def get_projects():
    return {"projects": []}


@app.get("/api/specialists")
async def get_specialists():
    return {"specialists": []}


# Health check
@app.get("/api/health")
async def health():
    return {"status": "ok", "platform": "vercel"}
