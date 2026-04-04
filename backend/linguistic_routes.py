from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any
import json
import re
import db
from auth import get_current_user
import bert_engine
import google.generativeai as genai
import os
from datetime import datetime

router = APIRouter(prefix="/api/linguistic", tags=["linguistic"])

import anthropic as _anthropic_lib

def get_ai_text(prompt: str) -> str:
    """Dual-AI: Gemini first, Anthropic Claude fallback."""
    # Try Gemini
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("models/gemini-2.0-flash")
            return model.generate_content(prompt).text
        except Exception as e:
            print(f"[linguistic] Gemini failed: {e} → trying Anthropic...")

    # Fallback to Anthropic
    ant_key = os.getenv("ANTHROPIC_API_KEY")
    if ant_key:
        try:
            client = _anthropic_lib.Anthropic(api_key=ant_key)
            msg = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text
        except Exception as e:
            print(f"[linguistic] Anthropic also failed: {e}")
            raise

    raise Exception("No AI configured. Set GOOGLE_API_KEY or ANTHROPIC_API_KEY.")


@router.post("/analyze")
async def analyze_text(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Analyze full text to extract annotated words, disputed words, and abbreviations."""
    text = payload.get("text", "")
    category = payload.get("category", "annotated") 
    source_lang = payload.get("source_lang", "English")
    
    if not text:
        return {"results": []}

    if category == "annotated":
        prompt_task = """Extract 10-15 most critical pharmaceutical terms (Annotated Words).
Return ONLY a JSON array. Each object MUST have: en, ru, uz, description_en, description_ru, description_uz."""
    elif category == "disputed":
        prompt_task = """Extract 10-15 'Disputed Words' (context-heavy translations).
Return ONLY a JSON array. Each object MUST have: en, ru, uz, context_en, context_ru, context_uz."""
    else:
        prompt_task = """Extract 10-15 abbreviations and acronyms.
Return ONLY a JSON array. Each object MUST have: short_form, long_en, long_ru, long_uz."""

    try:
        full_prompt = f"Role: Pharmaceutical expert editor. Task: {prompt_task}\nText: {text[:6000]}"
        result_text = get_ai_text(full_prompt)

        match = re.search(r'\[.*\]', result_text, re.DOTALL)
        if match:
            results = json.loads(match.group())
            
            # Duplicate detection
            conn = db.connect_db()
            cursor = conn.cursor()
            try:
                for item in results:
                    if category == "annotated":
                        cursor.execute("SELECT id FROM annotated_words WHERE LOWER(en) = ?", (item.get("en", "").lower(),))
                    elif category == "disputed":
                        cursor.execute("SELECT id FROM disputed_words WHERE LOWER(en) = ?", (item.get("en", "").lower(),))
                    elif category == "abbreviations":
                        cursor.execute("SELECT id FROM abbreviations WHERE LOWER(short_form) = ?", (item.get("short_form", "").lower(),))
                    
                    row = cursor.fetchone()
                    if row:
                        item["is_duplicate"] = True
                        item["status"] = "duplicate_pending"
                    else:
                        item["is_duplicate"] = False
                        item["status"] = "active"
            finally:
                conn.close()
                
            return {"results": results}
    except Exception as e:
        print(f"AI error: {e}")
        return await fallback_analysis(text, category, current_user["id"])


async def fallback_analysis(text: str, category: str, user_id: str):
    return {"results": [], "note": "BERT Fallback: Automated term extraction requires LLM access for definitions."}

@router.post("/save")
async def save_linguistic_items(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Save linguistic items. If item has 'id', update it (and set modified_by); otherwise insert new."""
    category = payload.get("category")
    items = payload.get("items", [])
    text_id = payload.get("text_id", "")
    
    if not category or not items:
        raise HTTPException(status_code=400, detail="Category and items required")
    
    conn = db.connect_db()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    try:
        for item in items:
            item_id = item.get("id")
            item_text_id = item.get("text_id", text_id)
            status = item.get("status", "active")
            
            if category == "annotated":
                if item_id:
                    cursor.execute('''
                        UPDATE annotated_words 
                        SET en = ?, ru = ?, uz = ?, description_en = ?, description_ru = ?, description_uz = ?,
                            modified_by_id = ?, modified_at = ?, text_id = ?, status = ?
                        WHERE id = ?
                    ''', (
                        item.get("en", ""), item.get("ru", ""), item.get("uz", ""),
                        item.get("description_en", ""), item.get("description_ru", ""), item.get("description_uz", ""),
                        current_user["id"], now, item_text_id, status, item_id
                    ))
                else:
                    cursor.execute('''
                        INSERT INTO annotated_words (en, ru, uz, description_en, description_ru, description_uz, user_id, text_id, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get("en", ""), item.get("ru", ""), item.get("uz", ""),
                        item.get("description_en", ""), item.get("description_ru", ""), item.get("description_uz", ""),
                        current_user["id"], item_text_id, status
                    ))
                    
            elif category == "disputed":
                if item_id:
                    cursor.execute('''
                        UPDATE disputed_words 
                        SET en = ?, ru = ?, uz = ?, context_en = ?, context_ru = ?, context_uz = ?,
                            modified_by_id = ?, modified_at = ?, text_id = ?, status = ?
                        WHERE id = ?
                    ''', (
                        item.get("en", ""), item.get("ru", ""), item.get("uz", ""),
                        item.get("context_en", ""), item.get("context_ru", ""), item.get("context_uz", ""),
                        current_user["id"], now, item_text_id, status, item_id
                    ))
                else:
                    cursor.execute('''
                        INSERT INTO disputed_words (en, ru, uz, context_en, context_ru, context_uz, user_id, text_id, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get("en", ""), item.get("ru", ""), item.get("uz", ""),
                        item.get("context_en", ""), item.get("context_ru", ""), item.get("context_uz", ""),
                        current_user["id"], item_text_id, status
                    ))
                    
            elif category == "abbreviations":
                if item_id:
                    cursor.execute('''
                        UPDATE abbreviations 
                        SET short_form = ?, long_en = ?, long_ru = ?, long_uz = ?,
                            modified_by_id = ?, modified_at = ?, text_id = ?, status = ?
                        WHERE id = ?
                    ''', (
                        item.get("short_form", ""), item.get("long_en", ""),
                        item.get("long_ru", ""), item.get("long_uz", ""),
                        current_user["id"], now, item_text_id, status, item_id
                    ))
                else:
                    cursor.execute('''
                        INSERT OR REPLACE INTO abbreviations (short_form, long_en, long_ru, long_uz, user_id, text_id, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get("short_form", ""), item.get("long_en", ""),
                        item.get("long_ru", ""), item.get("long_uz", ""),
                        current_user["id"], item_text_id, status
                    ))
        conn.commit()
    finally:
        conn.close()
    
    return {"success": True, "count": len(items)}

@router.put("/update/{category}/{item_id}")
async def update_linguistic_item(category: str, item_id: int, payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Update a single linguistic item — tracks who modified it."""
    valid_categories = ["annotated", "disputed", "abbreviations", "paragraphs"]
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail="Invalid category")
    
    conn = db.connect_db()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    try:
        if category == "annotated":
            cursor.execute('''
                UPDATE annotated_words 
                SET en = ?, ru = ?, uz = ?, description_en = ?, description_ru = ?, description_uz = ?,
                    modified_by_id = ?, modified_at = ?
                WHERE id = ?
            ''', (
                payload.get("en", ""), payload.get("ru", ""), payload.get("uz", ""),
                payload.get("description_en", ""), payload.get("description_ru", ""), payload.get("description_uz", ""),
                current_user["id"], now, item_id
            ))
        elif category == "disputed":
            cursor.execute('''
                UPDATE disputed_words 
                SET en = ?, ru = ?, uz = ?, context_en = ?, context_ru = ?, context_uz = ?,
                    modified_by_id = ?, modified_at = ?
                WHERE id = ?
            ''', (
                payload.get("en", ""), payload.get("ru", ""), payload.get("uz", ""),
                payload.get("context_en", ""), payload.get("context_ru", ""), payload.get("context_uz", ""),
                current_user["id"], now, item_id
            ))
        elif category == "abbreviations":
            cursor.execute('''
                UPDATE abbreviations 
                SET short_form = ?, long_en = ?, long_ru = ?, long_uz = ?,
                    modified_by_id = ?, modified_at = ?
                WHERE id = ?
            ''', (
                payload.get("short_form", ""), payload.get("long_en", ""),
                payload.get("long_ru", ""), payload.get("long_uz", ""),
                current_user["id"], now, item_id
            ))
        elif category == "paragraphs":
            cursor.execute('''
                UPDATE paragraphs_dashboard 
                SET en_text = ?, ru_text = ?, uz_text = ?, specialist_name = ?
                WHERE id = ?
            ''', (
                payload.get("en_text", ""), payload.get("ru_text", ""), payload.get("uz_text", ""),
                payload.get("specialist_name", ""), item_id
            ))
            # TRIGGER SYNC BACK TO ALIGNMENTS
            db.sync_paragraphs_to_alignments(
                payload.get("text_id", ""), 
                payload.get("en_text", ""), 
                payload.get("ru_text", ""), 
                payload.get("uz_text", "")
            )
        
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")
    finally:
        conn.close()
    
    return {"success": True}

@router.get("/all")
async def get_all_linguistic_data():
    """Get all encyclopedia data with creator and modifier info."""
    conn = db.connect_db()
    conn.row_factory = db.sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT a.*, 
               u.name as user_name, u.email as user_email,
               m.name as modified_by_name, m.email as modified_by_email
        FROM annotated_words a
        LEFT JOIN users u ON a.user_id = u.id
        LEFT JOIN users m ON a.modified_by_id = m.id
        ORDER BY a.created_at DESC
    """)
    annotated = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT d.*, 
               u.name as user_name, u.email as user_email,
               m.name as modified_by_name, m.email as modified_by_email
        FROM disputed_words d
        LEFT JOIN users u ON d.user_id = u.id
        LEFT JOIN users m ON d.modified_by_id = m.id
        ORDER BY d.created_at DESC
    """)
    disputed = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("""
        SELECT b.*, 
               u.name as user_name, u.email as user_email,
               m.name as modified_by_name, m.email as modified_by_email
        FROM abbreviations b
        LEFT JOIN users u ON b.user_id = u.id
        LEFT JOIN users m ON b.modified_by_id = m.id
        ORDER BY b.created_at DESC
    """)
    abbreviations = [dict(r) for r in cursor.fetchall()]
    
    
    cursor.execute("""
        SELECT * FROM paragraphs_dashboard ORDER BY created_at DESC
    """)
    paragraphs = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "annotated": annotated,
        "disputed": disputed,
        "abbreviations": abbreviations,
        "paragraphs": paragraphs
    }

@router.delete("/delete/{category}/{item_id}")
async def delete_linguistic_item(category: str, item_id: int, current_user: Dict = Depends(get_current_user)):
    """Delete a linguistic item by category and ID."""
    valid_categories = ["annotated", "disputed", "abbreviations", "paragraphs"]
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail="Invalid category")
    
    table_map = {
        "annotated": "annotated_words",
        "disputed": "disputed_words",
        "abbreviations": "abbreviations",
        "paragraphs": "paragraphs_dashboard"
    }
    table_name = table_map[category]
    
    conn = db.connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (item_id,))
        conn.commit()
    finally:
        conn.close()
    
    return {"success": True}
