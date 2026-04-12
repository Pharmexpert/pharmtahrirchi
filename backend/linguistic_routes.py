from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any
import json
import re
import db
from auth import get_current_user
import bert_engine
import os
from datetime import datetime
import asyncio

router = APIRouter(prefix="/api/linguistic", tags=["linguistic"])


LINGUISTIC_SYSTEM = """Siz farmatsevtika sohasidagi yuqori malakali lingvist-ekspertsiz.
O'zbekiston Respublikasi Davlat farmakopeyasi (DF) va Yevropa farmakopeyasi (Ph.Eur.) terminologiyasini mukammal bilasiz.
Farmatsevtik terminlarni uch tilda (o'zbek, rus, ingliz) aniq tarjima qilasiz.
Faqat JSON massiv qaytaring, boshqa hech narsa yozmang."""


async def get_ai_text_async(user_prompt: str) -> str:
    """Claude Sonnet direct call for linguistic analysis. Falls back to cascade."""
    from routes.ai_helpers import get_anthropic, generate_ai_content
    client = get_anthropic()
    if client:
        try:
            loop = asyncio.get_event_loop()
            msg = await loop.run_in_executor(
                None,
                lambda: client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system=LINGUISTIC_SYSTEM,
                    messages=[{"role": "user", "content": user_prompt}]
                )
            )
            return msg.content[0].text
        except Exception as e:
            print(f"[linguistic] Claude Sonnet failed: {e}, falling back")
    # Fallback to cascade
    return await generate_ai_content(f"{LINGUISTIC_SYSTEM}\n\n{user_prompt}", prefer="cloud")


def get_ai_text(prompt: str) -> str:
    """Sync wrapper for backward compatibility."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, get_ai_text_async(prompt))
            return future.result(timeout=120)
    else:
        return asyncio.run(get_ai_text_async(prompt))


@router.post("/analyze")
async def analyze_text(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Analyze full text to extract annotated words, disputed words, and abbreviations (with chunking)."""
    text = payload.get("text", "")
    category = payload.get("category", "annotated") 
    source_lang = payload.get("source_lang", "English")
    
    if not text:
        return {"results": []}

    # Chunking logic for full document analysis
    chunk_size = 4000
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    
    all_results = []
    seen_terms = set()

    if category == "annotated":
        prompt_task = """Farmatsevtik terminlarni (Изоҳли сўзлар) ajratib chiqaring.
Faqat JSON massiv qaytaring. Har bir obyektda bo'lishi SHART:
- en: inglizcha termin
- ru: ruscha tarjima
- uz: o'zbekcha tarjima
- description_en: inglizcha izoh (1-2 gap)
- description_ru: ruscha izoh
- description_uz: o'zbekcha izoh
Masalan: {"en":"Assay","ru":"Количественное определение","uz":"Миқдорий аниқлаш","description_en":"Quantitative determination of active substance content","description_ru":"Количественное определение содержания действующего вещества","description_uz":"Таъсир этувчи модда миқдорини аниқлаш"}"""
    elif category == "disputed":
        prompt_task = """Kontekstga bog'liq tarjimalari bor so'zlarni (Мунозарали сўзлар) ajrating.
Faqat JSON massiv qaytaring. Har bir obyektda:
- en: inglizcha so'z
- ru: ruscha tarjima
- uz: o'zbekcha tarjima
- context_en: qaysi kontekstda ishlatiladi (inglizcha)
- context_ru: kontekst (ruscha)
- context_uz: kontekst (o'zbekcha)"""
    else:
        prompt_task = """Qisqartmalar va akronimlarni ajratib chiqaring.
Faqat JSON massiv qaytaring. Har bir obyektda:
- short_form: qisqartma (masalan: INN, GMP, USP)
- long_en: to'liq shakli inglizcha
- long_ru: to'liq shakli ruscha
- long_uz: to'liq shakli o'zbekcha"""

    try:
        for chunk in chunks[:10]:
            full_prompt = f"Manba tili: {source_lang}.\nVazifa: {prompt_task}\n\nMatn:\n{chunk}"
            result_text = await get_ai_text_async(full_prompt)

            match = re.search(r'\[.*\]', result_text, re.DOTALL)
            if match:
                results = json.loads(match.group())
                
                # Deduplicate and attach source_lang
                for item in results:
                    # Term identifier for deduplication
                    term_id = item.get("en") or item.get("short_form")
                    if term_id and term_id.lower() not in seen_terms:
                        item["source_lang"] = source_lang
                        all_results.append(item)
                        seen_terms.add(term_id.lower())

        # Duplicate detection in database
        conn = db.connect_db()
        cursor = conn.cursor()
        try:
            for item in all_results:
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
            
        return {"results": all_results}
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
                        INSERT INTO annotated_words (en, ru, uz, description_en, description_ru, description_uz, source_lang, user_id, text_id, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get("en", ""), item.get("ru", ""), item.get("uz", ""),
                        item.get("description_en", ""), item.get("description_ru", ""), item.get("description_uz", ""),
                        item.get("source_lang", "English"),
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
                        INSERT INTO disputed_words (en, ru, uz, context_en, context_ru, context_uz, source_lang, user_id, text_id, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get("en", ""), item.get("ru", ""), item.get("uz", ""),
                        item.get("context_en", ""), item.get("context_ru", ""), item.get("context_uz", ""),
                        item.get("source_lang", "English"),
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
                        INSERT OR REPLACE INTO abbreviations (short_form, long_en, long_ru, long_uz, source_lang, user_id, text_id, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item.get("short_form", ""), item.get("long_en", ""),
                        item.get("long_ru", ""), item.get("long_uz", ""),
                        item.get("source_lang", "English"),
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
async def get_all_linguistic_data(q: str = Query(None), current_user: Dict = Depends(get_current_user)):
    """Get linguistic data — dual-script search (Cyr ↔ Lat)."""
    conn = db.connect_db()
    conn.row_factory = db.sqlite3.Row
    cursor = conn.cursor()

    # Build dual-script search variants
    search_variants = []
    if q:
        search_variants = [q]
        try:
            import dual_script
            detected = dual_script.detect_script(q)
            if detected == "cyr":
                lat = dual_script.to_latin(q)
                if lat: search_variants.append(lat)
            elif detected == "lat":
                cyr = dual_script.to_cyrillic(q)
                if cyr: search_variants.append(cyr)
        except Exception:
            pass

    def _build_search(columns: list) -> tuple:
        """Return (where_clause, params) for dual-script search across columns."""
        if not search_variants:
            return "", []
        or_clauses = []
        params = []
        for v in search_variants:
            like = f"%{v}%"
            col_clause = " OR ".join(f"{c} LIKE ?" for c in columns)
            or_clauses.append(f"({col_clause})")
            params.extend([like] * len(columns))
        return " WHERE " + " OR ".join(or_clauses), params

    # 1. Annotated
    an_where, an_params = _build_search(["en", "ru", "uz"])
    cursor.execute(f"""
        SELECT a.*,
               u.name as user_name, u.email as user_email,
               m.name as modified_by_name, m.email as modified_by_email
        FROM annotated_words a
        LEFT JOIN users u ON a.user_id = u.id
        LEFT JOIN users m ON a.modified_by_id = m.id
        {an_where}
        ORDER BY a.created_at DESC
    """, an_params)
    annotated = [dict(r) for r in cursor.fetchall()]

    # 2. Disputed
    cursor.execute(f"""
        SELECT d.*,
               u.name as user_name, u.email as user_email,
               m.name as modified_by_name, m.email as modified_by_email
        FROM disputed_words d
        LEFT JOIN users u ON d.user_id = u.id
        LEFT JOIN users m ON d.modified_by_id = m.id
        {an_where}
        ORDER BY d.created_at DESC
    """, an_params)
    disputed = [dict(r) for r in cursor.fetchall()]

    # 3. Abbreviations — dual-script
    ab_where, ab_params = _build_search(["short_form", "long_en", "long_ru", "long_uz"])
    cursor.execute(f"""
        SELECT b.*,
               u.name as user_name, u.email as user_email,
               m.name as modified_by_name, m.email as modified_by_email
        FROM abbreviations b
        LEFT JOIN users u ON b.user_id = u.id
        LEFT JOIN users m ON b.modified_by_id = m.id
        {ab_where}
        ORDER BY b.created_at DESC
    """, ab_params)
    abbreviations = [dict(r) for r in cursor.fetchall()]

    # 4. Paragraphs — dual-script search
    pa_where, pa_params = _build_search(["en_text", "ru_text", "uz_text"])
    cursor.execute(f"""
        SELECT * FROM paragraphs_dashboard {pa_where} ORDER BY created_at DESC
    """, pa_params)
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
    cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    return {"success": True, "deleted_id": item_id}


@router.post("/delete-bulk/{category}")
async def delete_linguistic_bulk(category: str, payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Bulk delete linguistic items by ID range or list."""
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

    ids = payload.get("ids", [])
    from_id = payload.get("from_id")
    to_id = payload.get("to_id")

    conn = db.connect_db()
    cursor = conn.cursor()

    if ids:
        placeholders = ','.join(['?'] * len(ids))
        cursor.execute(f"DELETE FROM {table_name} WHERE id IN ({placeholders})", ids)
    elif from_id is not None and to_id is not None:
        cursor.execute(f"DELETE FROM {table_name} WHERE id >= ? AND id <= ?", (from_id, to_id))
    else:
        raise HTTPException(status_code=400, detail="ids yoki from_id/to_id kerak")

    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return {"success": True, "deleted": deleted}

@router.post("/synonyms/select")
async def select_synonym(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Record a user choice in the Tier 1 synonym database."""
    word = payload.get("word")
    synonym = payload.get("synonym")
    lang = payload.get("lang", "uz")
    if word and synonym:
        db.increment_synonym_frequency(word, synonym, lang)
    return {"success": True}

@router.post("/synonyms")
async def get_synonyms(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Get synonyms: DB first (top frequency), then AI fallback (immediate save)."""
    word = payload.get("word", "").strip()
    lang = payload.get("lang", "uz")
    context_en = payload.get("context_en", "")
    
    if not word:
        return {"synonyms": []}
    
    # 1. Try DB
    db_results = db.get_synonyms_with_stats(word, lang)
    
    # 2. If less than 5, or expert wants fresh AI
    ai_syns = []
    if len(db_results) < 5:
        prompt = f"""Role: Pharmaceutical expert. Source Language: {payload.get('source_lang', 'English')}.
Text: {context_en}
Word: "{word}" in {lang}.
Find 5+ pharma synonyms/alternatives. Return ONLY a JSON array of strings."""
        
        try:
            resp = get_ai_text(prompt)
            match = re.search(r'\[.*\]', resp, re.DOTALL)
            if match:
                ai_syns = json.loads(match.group())
                # Filter wrong words
                ai_syns = [s for s in ai_syns if not db.is_word_wrong(s, lang)]
                # Immediate save to DB
                db.add_synonyms_batch(word, ai_syns, lang, author='ai')
        except Exception as e:
            print(f"Synonym AI error: {e}")

    # Merge results
    seen = set()
    final_syns = []
    
    # DB results first (highest frequency)
    for r in db_results:
        if r['synonym'] not in seen:
            final_syns.append({
                "word": r['synonym'],
                "frequency": r['frequency'],
                "source": r['source'],
                "probability": r['probability_scale'] or (0.9 if r['frequency'] > 10 else 0.5)
            })
            seen.add(r['synonym'])
            
    # AI results next
    for s in ai_syns:
        if s not in seen:
            final_syns.append({
                "word": s,
                "frequency": 0,
                "source": "ai",
                "probability": 0.5
            })
            seen.add(s)
            
    return {"synonyms": final_syns[:10]}

@router.post("/transliterate-batch")
async def transliterate_batch(payload: Dict[str, Any]):
    """Convert multiple texts between Latin and Cyrillic (Uzbek)."""
    import transliterate
    texts = payload.get("texts", [])
    target = payload.get("target", "latin") # 'latin' or 'cyrillic'
    
    results = [transliterate.convert_text(t, target) for t in texts]
    return {"results": results}

@router.post("/project/source-lang")
async def set_project_source_lang(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Persist source language selection for a project."""
    text_id = payload.get("text_id")
    lang = payload.get("lang")
    if text_id and lang:
        db.update_source_lang(text_id, lang)
        return {"success": True}
    return {"success": False, "error": "Missing params"}


@router.get("/terms-dictionary")
async def get_terms_dictionary(current_user: Dict = Depends(get_current_user)):
    """Get all annotated words, disputed words, and abbreviations for text highlighting."""
    conn = db.connect_db()
    conn.row_factory = db.sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, en, ru, uz, description_en, description_ru, description_uz FROM annotated_words WHERE status = 'active'")
    annotated = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT id, en, ru, uz, context_en, context_ru, context_uz FROM disputed_words WHERE status = 'active'")
    disputed = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT id, short_form, long_en, long_ru, long_uz FROM abbreviations WHERE status = 'active'")
    abbreviations = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {"annotated": annotated, "disputed": disputed, "abbreviations": abbreviations}


from fastapi import Request as FastAPIRequest

@router.post("/sync-all-rules")
async def sync_all_rules(payload: List[Dict[str, Any]], request: FastAPIRequest):
    """
    Secure batch endpoint for migrating sayqallash rules to production.
    Requires X-Seed-Secret header matching SEED_SECRET env var.
    Uses INSERT OR IGNORE to safely skip existing duplicates.
    """
    seed_secret = os.getenv("SEED_SECRET", "pharma_dev_sync_2026")
    header_secret = request.headers.get("X-Seed-Secret", "")
    if header_secret != seed_secret:
        raise HTTPException(status_code=403, detail="Invalid seed secret")

    conn = db.connect_db()
    cursor = conn.cursor()
    count = 0
    try:
        for r in payload:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO sayqallash_rules
                        (wrong_form, correct_form, error_type, context, lang, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    r.get("wrong_form", ""),
                    r.get("correct_form", ""),
                    r.get("error_type", "S/Spelling"),
                    r.get("context", ""),
                    r.get("lang", "uz"),
                    r.get("source", "seed")
                ))
                count += cursor.rowcount
            except Exception:
                pass
        conn.commit()
    finally:
        conn.close()

    return {"status": "success", "inserted": count, "total_sent": len(payload)}
