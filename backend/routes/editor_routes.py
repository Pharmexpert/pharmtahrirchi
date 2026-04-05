import os
import re
import json
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request
import db
import bert_engine
import transliterate
from routes.ai_helpers import get_client, generate_ai_content
from routes.rate_limit import ai_limiter

router = APIRouter(tags=["editor"])


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


@router.post("/api/improve-row")
async def improve_row(payload: Dict[str, Any]):
    from routes.sayqallash_routes import sayqallash
    target_lang = payload.get("target_lang", "uz")
    text = payload.get(f"{target_lang}_proposed", "") or payload.get(f"{target_lang}_v1", "")
    en_text = payload.get("en", "")

    sayqallash_res = await sayqallash({"text": text, "lang": target_lang, "context_en": en_text})

    return {
        f"{target_lang}_v2": sayqallash_res["corrected_text"],
        "annotations": sayqallash_res["annotations"],
        "rationale": "Sayqallash алгоритми (3-босқичли) асосида тузатилди."
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
