import re

def patch_db():
    with open('db.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Add department column to users table
    if 'department TEXT' not in content:
        content = content.replace(
            "avatar_url TEXT\n        )\n    ''')",
            "avatar_url TEXT,\n            department TEXT\n        )\n    ''')"
        )

    # Patch create_user definition
    content = re.sub(
        r"def create_user\(user_id: str, email: str, name: str, password: str = None, avatar_url: str = None, role: str = 'specialist'\):",
        "def create_user(user_id: str, email: str, name: str, password: str = None, avatar_url: str = None, role: str = 'specialist', department: str = None):",
        content
    )

    # Patch create_user INSERT query
    if "avatar_url, department" not in content:
        content = content.replace(
            "(id, email, name, password_hash, role, status, created_at, avatar_url)",
            "(id, email, name, password_hash, role, status, created_at, avatar_url, department)"
        )
        content = content.replace(
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        content = content.replace(
            "role, 'pending', now, avatar_url))",
            "role, 'pending', now, avatar_url, department))"
        )
        
    # Patch _row_to_user
    if '"department": row[8]' not in content:
        content = content.replace(
            '"created_at": row[6]\n    }',
            '"created_at": row[6],\n        "department": row[8] if len(row) > 8 else None\n    }'
        )

    with open('db.py', 'w', encoding='utf-8') as f:
        f.write(content)

def patch_main():
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Patch register payload to include department
    if 'department = payload.get("department"' not in content:
        content = content.replace(
            'password = payload.get("password")',
            'password = payload.get("password")\n    department = payload.get("department", "Давлат фармакопеяси ишлаб чиқиш бўлими")'
        )
        content = content.replace(
            "db.create_user(user_id, email, name, password=password)",
            "db.create_user(user_id, email, name, password=password, department=department)"
        )

    # Missing Endpoints mapping
    missing_endpoints = """
@app.get("/api/specialists")
async def get_specialists(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header: raise HTTPException(status_code=401)
    users = [u for u in db.list_all_users() if u["role"] in ["specialist", "editor", "admin"]]
    return {"specialists": users}

@app.get("/api/linguistic/all")
async def verify_linguistic_all(request: Request):
    import google.generativeai as genai
    apiKey = os.getenv("GOOGLE_API_KEY")
    if not apiKey: return {"results": [], "error": "Google API key missing"}
    text = request.query_params.get("text", "")
    lang = request.query_params.get("lang", "uz")
    if not text: return {"results": []}
    
    try:
        genai.configure(api_key=apiKey)
        model = genai.GenerativeModel("gemini-1.5-pro")
        prompt = f"Analyze the following {lang} pharmaceutical text for errors and terminology issues. Return a detailed JSON array: [{{\\"original\\": \\"...\\", \\"suggestion\\": \\"...\\", \\"reason\\": \\"...\\", \\"severity\\": \\"high|medium|low\\"}}]. Text: {text}"
        res = model.generate_content(prompt)
        import json, re
        match = re.search(r'\\[.*\\]', res.text, re.DOTALL)
        if match:
             return {"results": json.loads(match.group())}
        return {"results": []}
    except Exception as e:
        return {"results": [], "error": str(e)}

@app.post("/api/upload")
async def handle_upload(mode: str = "auto", file: UploadFile = File(...)):
    upload_id = f"proj_{int(datetime.utcnow().timestamp())}"
    filepath = os.path.join(TEMP_DIR, f"{upload_id}.docx")
    with open(filepath, "wb") as f:
        import shutil
        shutil.copyfileobj(file.file, f)
    
    from processor import ParagraphAligner
    aligner = ParagraphAligner(filepath)
    success = aligner.process()
    if not success: raise HTTPException(status_code=400, detail="Failed to parse")
    
    db.create_project(upload_id, file.filename, "uploaded")
    for r in aligner.aligned_rows:
        db.save_alignment(upload_id, r["id"], r["en"], r.get("ru",""), r.get("uz",""))
    return {"success": True, "projectId": upload_id}

@app.get("/api/admin/rules")
async def get_admin_rules(lang: str = "uz", limit: int = 500, request: Request = None):
    rules = db.get_all_rules(lang, limit)
    return {"rules": rules, "count": len(rules)}

@app.get("/api/admin/stats")
async def get_admin_stats(request: Request):
    return {
        "totalProjects": len(db.list_projects()),
        "totalRules": db.get_rules_count("en") + db.get_rules_count("ru") + db.get_rules_count("uz"),
        "totalUsers": len(db.list_all_users())
    }

"""
    if "def get_specialists(" not in content:
        content = content.replace('if __name__ == "__main__":', missing_endpoints + '\nif __name__ == "__main__":')

    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    patch_db()
    patch_main()
    print("Backend patched successfully.")
