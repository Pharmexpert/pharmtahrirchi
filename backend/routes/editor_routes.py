import os
import re
import json
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request
import db
import bert_engine
import transliterate
import spellcheck
from routes.ai_helpers import get_client, generate_ai_content
from routes.rate_limit import ai_limiter

router = APIRouter(tags=["editor"])


@router.post("/api/spellcheck")
async def spellcheck_endpoint(payload: Dict[str, Any]):
    """Check text spelling using uz-hunspell dictionaries."""
    text = payload.get("text", "")
    is_cyrillic = payload.get("is_cyrillic", True)
    if not text.strip():
        return {"errors": [], "stats": spellcheck.get_stats()}
    errors = spellcheck.check_text(text, is_cyrillic=is_cyrillic)
    return {"errors": errors, "total": len(errors), "stats": spellcheck.get_stats()}


# ═══════════════════════════════════════════════════
# Луғат (Hunspell Dictionary) endpoints
# ═══════════════════════════════════════════════════

@router.get("/api/dictionary/words")
async def get_dictionary_words(language: str = "cyrl", page: int = 0, per_page: int = 50, search: str = ""):
    """Get hunspell dictionary words enriched with frequency + source from user_dictionary."""
    import hunspell_data
    import sqlite3, os as _os
    all_words = hunspell_data.get_dictionary_words(language)

    if search:
        s = search.lower()
        all_words = [w for w in all_words if s in w['word'].lower()]

    total = len(all_words)
    start = page * per_page
    end = start + per_page
    page_words = all_words[start:end]

    # Enrich with frequency + source from user_dictionary
    if page_words:
        try:
            db_p = _os.getenv("DB_PATH", _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "pharma_editor.db"))
            conn = sqlite3.connect(db_p)
            cur = conn.cursor()
            word_keys = [w['word'].lower() for w in page_words]
            placeholders = ",".join("?" for _ in word_keys)
            cur.execute(f"""
                SELECT word, COALESCE(frequency, 0), source
                FROM user_dictionary
                WHERE LOWER(word) IN ({placeholders})
            """, word_keys)
            meta = {row[0].lower(): (row[1], row[2]) for row in cur.fetchall()}
            conn.close()
            for w in page_words:
                info = meta.get(w['word'].lower())
                if info:
                    w['frequency'] = info[0]
                    w['source'] = info[1]
        except Exception:
            pass

    return {
        "words": page_words,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


@router.get("/api/dictionary/affix-flags")
async def get_affix_flags(language: str = "cyrl", page: int = 0, per_page: int = 25, search: str = ""):
    """Get affix flags with descriptions and examples."""
    import hunspell_data
    flags = hunspell_data.get_affix_flags(language)

    if search:
        s = search.lower()
        flags = [f for f in flags if s in f['flag'].lower() or s in f['description'].lower()]

    total = len(flags)
    start = page * per_page
    end = start + per_page
    return {
        "flags": flags[start:end],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


@router.post("/api/dictionary/translate")
async def translate_dictionary_word(payload: Dict[str, Any]):
    """AI translate a single word to RU and EN."""
    word = payload.get("word", "").strip()
    if not word:
        return {"ru": "", "en": "", "definition": ""}

    # Check cache in DB
    conn = db.connect_db()
    conn.row_factory = db.sqlite3.Row
    cursor = conn.cursor()
    # Create cache table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dict_translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE,
            ru TEXT, en TEXT, definition TEXT, pos TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("SELECT * FROM dict_translations WHERE word = ?", (word,))
    cached = cursor.fetchone()
    if cached:
        conn.close()
        return dict(cached)

    # Generate via AI
    try:
        prompt = f"""Translate Uzbek word "{word}" to Russian and English. Also provide a brief definition in Uzbek.
Return ONLY JSON: {{"ru": "translation", "en": "translation", "definition": "qisqa izoh"}}"""
        ai_text = await generate_ai_content(prompt)
        match = re.search(r'\{.*\}', ai_text, re.DOTALL)
        if match:
            result = json.loads(match.group())
            cursor.execute("""
                INSERT OR REPLACE INTO dict_translations (word, ru, en, definition)
                VALUES (?, ?, ?, ?)
            """, (word, result.get("ru", ""), result.get("en", ""), result.get("definition", "")))
            conn.commit()
            conn.close()
            return {"word": word, **result}
    except Exception as e:
        pass
    conn.close()
    return {"word": word, "ru": "", "en": "", "definition": ""}


@router.post("/api/dictionary/add")
async def add_word_to_dictionary(payload: Dict[str, Any]):
    """Add a word to the user dictionary so it stops being marked as a spelling error."""
    word = (payload.get("word") or "").strip()
    lang = (payload.get("lang") or "uz").strip()
    if not word:
        return {"ok": False, "error": "empty word"}
    try:
        conn = db.connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_dictionary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                lang TEXT DEFAULT 'uz',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(word, lang)
            )
        """)
        cursor.execute("INSERT OR IGNORE INTO user_dictionary (word, lang) VALUES (?, ?)", (word, lang))
        conn.commit()
        conn.close()
        # Also try to add to running Hunspell instance
        try:
            import spellcheck
            if hasattr(spellcheck, "add_word"):
                spellcheck.add_word(word, lang)
        except Exception:
            pass
        return {"ok": True, "word": word}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/dictionary/translations")
async def get_translations(words: str = ""):
    """Get cached translations for a list of words."""
    if not words:
        return {"translations": {}}
    word_list = [w.strip() for w in words.split(",") if w.strip()]
    conn = db.connect_db()
    conn.row_factory = db.sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS dict_translations (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT UNIQUE, ru TEXT, en TEXT, definition TEXT, pos TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    placeholders = ",".join(["?"] * len(word_list))
    cursor.execute(f"SELECT word, ru, en, definition FROM dict_translations WHERE word IN ({placeholders})", word_list)
    translations = {}
    for r in cursor.fetchall():
        translations[r["word"]] = dict(r)
    conn.close()
    return {"translations": translations}


@router.get("/api/dictionary/stats")
async def get_dictionary_stats():
    """Get dictionary stats: total words, flags, REP rules."""
    import hunspell_data
    return {
        "cyrillic": {
            "words": len(hunspell_data.get_dictionary_words('cyrl')),
            "affix_flags": len(hunspell_data.get_affix_flags('cyrl')),
            "rep_rules": len(hunspell_data.get_rep_rules('cyrl'))
        },
        "latin": {
            "words": len(hunspell_data.get_dictionary_words('lat')),
            "affix_flags": len(hunspell_data.get_affix_flags('lat')),
            "rep_rules": len(hunspell_data.get_rep_rules('lat'))
        }
    }


@router.post("/api/align-document")
async def align_document(request: Request, payload: Dict[str, Any]):
    """AI-based alignment for the entire document in a single batched call."""
    client_ip = request.client.host if request.client else "unknown"
    if not ai_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Жуда кўп сўров. 1 дақиқа кутинг.")

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


@router.post("/api/paragraph-progress/update")
async def update_paragraph_progress(payload: Dict[str, Any]):
    """Update workflow status of a paragraph (pending/in_review/approved/needs_revision)."""
    try:
        conn = db.connect_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS paragraph_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text_id TEXT, sentence_no INTEGER,
                status TEXT DEFAULT 'pending', reviewer_id TEXT, reviewer_name TEXT,
                notes TEXT, ai_score REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(text_id, sentence_no)
            )
        """)
        cur.execute("""
            INSERT INTO paragraph_progress (text_id, sentence_no, status, reviewer_id, reviewer_name, notes, ai_score, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(text_id, sentence_no) DO UPDATE SET
                status=excluded.status,
                reviewer_id=excluded.reviewer_id,
                reviewer_name=excluded.reviewer_name,
                notes=excluded.notes,
                ai_score=excluded.ai_score,
                updated_at=CURRENT_TIMESTAMP
        """, (
            payload.get("text_id"), payload.get("sentence_no"),
            payload.get("status", "pending"),
            payload.get("reviewer_id", ""), payload.get("reviewer_name", ""),
            payload.get("notes", ""), payload.get("ai_score"),
        ))
        conn.commit()
        conn.close()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/paragraph-progress/{text_id}")
async def get_paragraph_progress(text_id: str):
    """Get progress for all paragraphs in a project."""
    try:
        conn = db.connect_db()
        conn.row_factory = db.sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM paragraph_progress WHERE text_id = ?", (text_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        # Aggregate stats
        stats = {"pending": 0, "in_review": 0, "approved": 0, "needs_revision": 0}
        for r in rows:
            s = r.get("status", "pending")
            stats[s] = stats.get(s, 0) + 1
        return {"rows": rows, "stats": stats, "total": len(rows)}
    except Exception as e:
        return {"rows": [], "error": str(e)}


@router.post("/api/document-versions/save")
async def save_document_version(payload: Dict[str, Any]):
    """Save a snapshot of a row to the version history."""
    try:
        conn = db.connect_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS document_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text_id TEXT, sentence_no INTEGER, lang TEXT,
                version INTEGER DEFAULT 1, content TEXT,
                author_id TEXT, author_name TEXT, action TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute(
            "SELECT MAX(version) FROM document_versions WHERE text_id = ? AND sentence_no = ? AND lang = ?",
            (payload.get("text_id"), payload.get("sentence_no"), payload.get("lang"))
        )
        row = cur.fetchone()
        next_v = (row[0] or 0) + 1
        cur.execute("""
            INSERT INTO document_versions (text_id, sentence_no, lang, version, content, author_id, author_name, action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.get("text_id"), payload.get("sentence_no"), payload.get("lang"),
            next_v, payload.get("content", ""), payload.get("author_id", ""),
            payload.get("author_name", ""), payload.get("action", "edit"),
        ))
        conn.commit()
        conn.close()
        return {"success": True, "version": next_v}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/document-versions/{text_id}/{sentence_no}")
async def get_document_versions(text_id: str, sentence_no: int, lang: str = None):
    """Get version history for a specific row."""
    try:
        conn = db.connect_db()
        conn.row_factory = db.sqlite3.Row
        cur = conn.cursor()
        if lang:
            cur.execute("SELECT * FROM document_versions WHERE text_id = ? AND sentence_no = ? AND lang = ? ORDER BY version DESC LIMIT 50",
                        (text_id, sentence_no, lang))
        else:
            cur.execute("SELECT * FROM document_versions WHERE text_id = ? AND sentence_no = ? ORDER BY version DESC LIMIT 50",
                        (text_id, sentence_no))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"versions": rows}
    except Exception as e:
        return {"versions": [], "error": str(e)}


@router.post("/api/improve-row")
async def improve_row(payload: Dict[str, Any]):
    """
    Multi-engine row improvement:
      - uz → Llama 3.1 (or Mistral fallback) + Sayqallash
      - ru → sage-fredt5-large + Sayqallash
      - en → Llama 3.1 (or Mistral) for grammar
    Sayqallash always runs as a final dictionary-grounded pass.
    """
    from routes.sayqallash_routes import sayqallash
    target_lang = payload.get("target_lang", "uz")
    text = payload.get(f"{target_lang}_proposed", "") or payload.get(f"{target_lang}_v1", "")
    en_text = payload.get("en", "")

    if not text:
        return {f"{target_lang}_v2": "", "annotations": [], "rationale": "Empty input"}

    ai_text = text
    engine_used = "sayqallash_only"

    # 1. Language-specific AI improver
    if target_lang == "ru":
        try:
            import russian_engine
            if russian_engine.is_available():
                ai_text = await russian_engine.improve(text)
                engine_used = "russian_" + russian_engine.get_mode()
        except Exception:
            pass
    else:
        # Uzbek/English → Llama 3.1 first, Mistral fallback
        try:
            import llama_engine
            if llama_engine.is_available():
                ai_text = await llama_engine.improve_text(text, target_lang)
                if ai_text and ai_text != text:
                    llama_engine.learn_record(text, ai_text, kind=f"llama_improve_{target_lang}")
                    engine_used = "llama_" + llama_engine.get_mode()
        except Exception:
            pass
        if ai_text == text or not ai_text:
            try:
                import mistral_engine
                if mistral_engine.is_available():
                    ai_text = await mistral_engine.improve_text(text, target_lang)
                    if ai_text and ai_text != text:
                        engine_used = "mistral_" + mistral_engine.get_mode()
            except Exception:
                pass

    # 2. Final pass: Sayqallash (dictionary-grounded corrections)
    try:
        sayqallash_res = await sayqallash({"text": ai_text or text, "lang": target_lang, "context_en": en_text})
        final_text = sayqallash_res.get("corrected_text", ai_text or text)
        annotations = sayqallash_res.get("annotations", [])
    except Exception:
        final_text = ai_text or text
        annotations = []

    return {
        f"{target_lang}_v2": final_text,
        "annotations": annotations,
        "rationale": f"Engine: {engine_used} → Sayqallash → Final.",
        "engine": engine_used,
    }


@router.post("/api/bert/synonyms")
async def bert_synonyms(payload: Dict[str, Any]):
    word = payload.get("word", "")
    context = payload.get("context", "")
    lang = payload.get("lang", "uz")

    if not word:
        return {"synonyms": [], "source": "none"}

    suggestions = []

    if bert_engine.engine.initialized and context:
        masked = context.replace(word, "[MASK]", 1)
        if "[MASK]" in masked:
            predictions = bert_engine.engine.predict_mask(masked, top_k=10)
            suggestions.extend([p for p in predictions if p.strip() and p.lower() != word.lower()])

    if lang == 'uz' and os.path.exists(db.TAHRIRCHI_DB_PATH):
        try:
            dict_conn = __import__('sqlite3').connect(db.TAHRIRCHI_DB_PATH)
            dc = dict_conn.cursor()
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


@router.post("/api/dictionary/autocomplete")
async def dict_autocomplete(payload: Dict[str, Any]):
    prefix = payload.get("prefix", "").strip().lower()
    limit = min(payload.get("limit", 10), 20)

    if len(prefix) < 2 or not os.path.exists(db.TAHRIRCHI_DB_PATH):
        return {"words": []}

    # Cross-alphabet search: try both Cyrillic and Latin variants
    variants = transliterate.cross_alphabet_variants(prefix)

    import sqlite3 as sq
    conn = sq.connect(db.TAHRIRCHI_DB_PATH)
    cursor = conn.cursor()

    seen = set()
    results = []
    for variant in variants:
        cursor.execute(
            "SELECT word, frequency FROM dictionary WHERE word LIKE ? ORDER BY frequency DESC LIMIT ?",
            (variant.lower() + '%', limit)
        )
        for w, f in cursor.fetchall():
            if w not in seen:
                seen.add(w)
                results.append({"word": w, "frequency": f})

    conn.close()
    results.sort(key=lambda x: -x["frequency"])
    return {"words": results[:limit]}


@router.post("/api/dictionary/suggest")
async def dict_suggest(payload: Dict[str, Any]):
    word = payload.get("word", "").strip().lower()

    if len(word) < 2 or not os.path.exists(db.TAHRIRCHI_DB_PATH):
        return {"suggestions": [], "in_dictionary": False}

    import sqlite3 as sq
    conn = sq.connect(db.TAHRIRCHI_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM dictionary WHERE word = ? LIMIT 1", (word,))
    exists = cursor.fetchone() is not None

    if exists:
        conn.close()
        return {"suggestions": [], "in_dictionary": True}

    candidates = []
    for prefix_len in [len(word)-1, len(word)-2, 3]:
        if prefix_len < 2:
            continue
        cursor.execute(
            "SELECT word, frequency FROM dictionary WHERE word LIKE ? AND length(word) BETWEEN ? AND ? ORDER BY frequency DESC LIMIT 10",
            (word[:prefix_len] + '%', len(word)-2, len(word)+2)
        )
        for w, f in cursor.fetchall():
            if w != word:
                dist = sum(1 for a, b in zip(word, w) if a != b) + abs(len(word) - len(w))
                if dist <= 3:
                    candidates.append({"word": w, "frequency": f, "distance": dist})

    conn.close()

    candidates.sort(key=lambda x: (x["distance"], -x["frequency"]))
    seen = set()
    unique = []
    for c in candidates:
        if c["word"] not in seen:
            seen.add(c["word"])
            unique.append(c)

    return {"suggestions": unique[:5], "in_dictionary": False}


@router.post("/suggest-edits")
@router.post("/synonyms")
async def suggest_edits(payload: Dict[str, Any]):
    model = get_client()
    if not model:
        raise HTTPException(status_code=503, detail="AI client not configured")

    word = payload.get("word", "")
    lang = payload.get("lang", "ru")
    context_en = payload.get("context_en", payload.get("context", ""))
    context_ru = payload.get("context_ru", "")
    context_uz = payload.get("context_uz", "")
    lang_label = "рус" if lang == "ru" else "ўзбек"
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

        syns = result.get("synonyms", [])[:5]
        if syns:
            try:
                db.save_synonyms_batch(word, syns, lang, source='ai')
            except Exception as se:
                print(f"Synonym save error: {se}")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/suggest-edits")
async def suggest_edits_alias(payload: Dict[str, Any]):
    return await suggest_edits(payload)


@router.post("/api/synonyms-lookup")
async def synonyms_lookup_alias(payload: Dict[str, Any]):
    return await suggest_edits(payload)


@router.post("/api/split-row")
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

            resp_text = await generate_ai_content(prompt)
            match = re.search(r'\{.*\}', resp_text, re.DOTALL)
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


@router.post("/api/transliterate")
async def transliterate_text(payload: Dict[str, Any]):
    text = payload.get("text", "")
    target = payload.get("target", "latin")
    if not text:
        return {"text": ""}
    result = transliterate.convert_text(text, target=target)
    return {"text": result}


@router.post("/api/transliterate-batch")
async def transliterate_batch(payload: Dict[str, Any]):
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
