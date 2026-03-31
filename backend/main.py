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

def verify_token(token: str):
    # Developer Bypass for local testing
    if token == "dev-token":
        return {"userId": "admin_primary", "email": "texnopharm@gmail.com", "role": "admin", "name": "Admin (Dev)"}
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
@app.post("/upload-docx") # frontend uses this alias
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
        
        # Save project to DB automatically
        text_id = f"proj_{int(datetime.utcnow().timestamp())}"
        for row in data:
            row["text_id"] = text_id
        
        db.update_project_metadata(text_id, "Yangi Mutaxassis")
        
        # Save alignment data to DB
        db.save_alignments(data)
        
        return {"filename": file.filename, "data": data, "text_id": text_id}
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
        if blk["marker"]: result_data.append(blk["marker"])
        result_data.extend(blk["rows"])

    return {"data": result_data}

@app.post("/improve-row")
async def improve_row(payload: Dict[str, Any]):
    client = get_client()
    if not client: raise HTTPException(status_code=503, detail="AI client not configured")
    
    en_text = payload.get("en", "")
    ru_text = payload.get("ru_proposed", "") or payload.get("ru_v1", "")
    uz_text = payload.get("uz_proposed", "") or payload.get("uz_v1", "")
    target_lang = payload.get("target_lang", "")
    
    system_prompt = "Role: Farmautika va xalqaro standartlar bo'yicha ekspert-muharrir. Ilmiy tahrir qiling."
    user_prompt = f"EN: {en_text}\nRU: {ru_text}\nUZ: {uz_text}\nTarget: {target_lang}\nReturn JSON: {{'ru_v2': '...', 'uz_v2': '...', 'rationale': '...'}}"
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        return json.loads(match.group()) if match else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/suggest-edits")
@app.post("/synonyms")
async def suggest_edits(payload: Dict[str, Any]):
    client = get_client()
    if not client: raise HTTPException(status_code=503, detail="AI client not configured")
    
    word = payload.get("word", "")
    lang = payload.get("lang", "ru")
    prompt = f"Phrase: '{word}' in {lang}. Context: {payload.get('context_en')}. Give 5 pharma-style variants in JSON: {{'variants': [...]}}"
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system="Pharmaceutical expert editor.",
            messages=[{"role": "user", "content": prompt}]
        )
        match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
        result = json.loads(match.group()) if match else {"variants": []}
        result["synonyms"] = result.get("variants", [])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sayqallash")
async def sayqallash(payload: Dict[str, Any]):
    text = payload.get("text", "").strip()
    lang = payload.get("lang", "uz")
    if not text: return {"annotations": [], "corrected_text": "", "rules_count": 0}

    local_annotations = db.get_rules_for_text(text, lang)
    rules_count = db.get_rules_count(lang)
    client = get_client()
    ai_annotations = []
    corrected_text = text

    if client:
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                system="Uzbek grammar/pharma corrector.",
                messages=[{"role": "user", "content": f"Check: {text}. JSON: {{'annotations': [{{'old_value': '...', 'new_value': '...', 'error_type': '...'}}], 'corrected_text': '...'}}"}]
            )
            match = re.search(r'\{.*\}', response.content[0].text, re.DOTALL)
            if match:
                result = json.loads(match.group())
                for ann in result.get("annotations", []):
                    old_val = ann.get("old_value")
                    if old_val:
                        idx = text.find(old_val)
                        if idx != -1:
                            ann.update({"from_index": idx, "to_index": idx + len(old_val), "source": "ai"})
                            ai_annotations.append(ann)
                corrected_text = result.get("corrected_text", text)
        except Exception: pass

    all_annotations = local_annotations + [a for a in ai_annotations if not any(la['from_index'] == a['from_index'] for la in local_annotations)]
    all_annotations.sort(key=lambda a: a.get("from_index", 0))
    return {"annotations": all_annotations, "corrected_text": corrected_text, "rules_count": rules_count}

# ═══════════════════════════════════════════════════
# Sayqallash Rules CRUD
# ═══════════════════════════════════════════════════

@app.get("/sayqallash-rules")
async def get_sayqallash_rules(lang: str = "uz", limit: int = 500):
    rules = db.get_all_rules(lang, limit)
    return {"rules": rules}

@app.post("/sayqallash-rules")
async def add_sayqallash_rule(payload: Dict[str, Any]):
    try:
        db.add_sayqallash_rule(
            wrong=payload.get("wrong_form", ""),
            correct=payload.get("correct_form", ""),
            error_type=payload.get("error_type", "S/Spelling"),
            context=payload.get("context", ""),
            lang=payload.get("lang", "uz"),
            source=payload.get("source", "manual")
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/sayqallash-rules/{rule_id}")
async def update_sayqallash_rule(rule_id: int, payload: Dict[str, Any]):
    try:
        db.update_sayqallash_rule(rule_id, payload)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sayqallash-rules/{rule_id}")
async def delete_sayqallash_rule(rule_id: int):
    try:
        db.delete_sayqallash_rule(rule_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auto-notes")
async def auto_notes(payload: Dict[str, Any]):
    notes = db.generate_diff_notes(payload.get("v1", ""), payload.get("proposed", ""), payload.get("lang", "uz"))
    return {"notes": notes}


@app.post("/save")
async def save_data(payload: Dict[str, Any]):
    try:
        db.save_alignments(payload.get("data", []))
        return {"status": "success"}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/save-row")
async def save_single_row(payload: Dict[str, Any]):
    try:
        new_id = db.save_single_row(payload)
        return {"status": "success", "new_id": new_id}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{text_id}")
async def get_history(text_id: str):
    return db.get_history(text_id)

@app.post("/export")
async def export_data(payload: Dict[str, Any]):
    filename = payload.get("filename", "aligned_output.docx")
    output_path = os.path.abspath(os.path.join(TEMP_DIR, f"confirmed_{filename}"))
    try:
        export_to_docx(payload.get("data", []), output_path)
        return FileResponse(output_path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=f"confirmed_{filename}")
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

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
        db.create_user(user_id, email, name, avatar_url=google_data.get("picture"))
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
    if not email or not name or not password:
        raise HTTPException(status_code=400, detail="Barcha maydonlarni тўлдиринг")
    if db.get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Бундай Email аллақачон мавжуд")
    user_id = f"user_{int(datetime.utcnow().timestamp())}"
    db.create_user(user_id, email, name, password=password)
    return {"success": True, "message": "Рўйхатдан ўтиш муваффақиятли! Админ тасдиқлашини кутинг."}

@app.post("/api/auth/login")
async def login_api(payload: Dict[str, Any]):
    email = payload.get("email", "").lower().strip()
    password = payload.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email ва паролни тўлдиринг")
    if not db.verify_password(email, password):
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

@app.get("/api/projects")
async def get_projects(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header: raise HTTPException(status_code=401)
    projects = db.list_projects()
    return {"projects": projects}

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, request: Request):
    db.delete_project(project_id)
    return {"success": True}

@app.get("/api/admin/users")
async def get_admin_users(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header: raise HTTPException(status_code=401)
    token = auth_header.split(" ")[1]
    payload = verify_token(token)
    if not payload or payload.get("role") != "admin": raise HTTPException(status_code=403)
    return {"users": db.list_all_users()}

@app.post("/api/admin/approve")
async def approve_user(payload: Dict[str, Any], request: Request):
    db.update_user_status(payload.get("userId"), payload.get("status"))
    return {"success": True}

@app.post("/api/admin/role")
async def change_role(payload: Dict[str, Any], request: Request):
    db.update_user_role(payload.get("userId"), payload.get("role"))
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
