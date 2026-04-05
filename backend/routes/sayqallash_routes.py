import os
import re
import json as _json_module
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request
import db
import transliterate
from routes.ai_helpers import get_client, generate_ai_content
from routes.rate_limit import ai_limiter

# Explicit binding to prevent 'name json is not defined' in async contexts
json = _json_module

logger = logging.getLogger("sayqallash")

router = APIRouter(tags=["sayqallash"])


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


async def _sayqallash_logic(payload: Dict[str, Any]) -> dict:
    """Core sayqallash logic, callable both from HTTP endpoint and internally."""
    import json  # ensure json is available in async context
    text = payload.get("text", "").strip()
    lang = payload.get("lang", "uz")
    context_en = payload.get("context_en", "")

    if not text:
        return {"annotations": [], "corrected_text": "", "rules_count": 0, "confidence": 100}

    cached_res = db.get_ai_cache(text, lang)
    if cached_res:
        cached_res["cached"] = True
        return cached_res

    is_uz_cyrillic = False
    if lang == 'uz':
        try:
            is_uz_cyrillic = transliterate.is_cyrillic(text)
        except Exception:
            pass

    # TIER 1: Rules DB
    try:
        local_annotations = db.get_rules_for_text(text, lang) or []
        rules_count = db.get_rules_count(lang) or 0
    except Exception as e:
        logger.error(f"Rules DB error: {e}")
        local_annotations = []
        rules_count = 0
    covered_ranges = [(a["from_index"], a["to_index"]) for a in local_annotations]

    ai_annotations = []
    confidence = 100

    # TIER 2: Dual AI
    if get_client():
        known_rules = db.get_all_rules(lang, limit=20) or []
        rules_examples = ""
        if known_rules:
            examples = [f"\u00ab{r['wrong_form']}\u00bb\u2192\u00ab{r['correct_form']}\u00bb" for r in known_rules]
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
            logger.warning(f"AI Tier Error: {e} -> Falling back to BERT/Dictionary logic")

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
    db.set_ai_cache(text, lang, final_result)
    return final_result


@router.post("/sayqallash")
async def sayqallash_endpoint(request: Request, payload: Dict[str, Any]):
    """HTTP endpoint with rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    if not ai_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Жуда кўп сўров. 1 дақиқа кутинг.")
    try:
        return await _sayqallash_logic(payload)
    except Exception as e:
        import traceback
        logger.error(f"Sayqallash error: {e}\n{traceback.format_exc()}")
        text = payload.get("text", "")
        return {"annotations": [], "corrected_text": text, "rules_count": 0, "confidence": 0, "error": str(e)}


# Public function for internal use (no rate limiting)
sayqallash = _sayqallash_logic


async def pre_polish_document(text_id: str):
    """Proactively run Sayqallash on all rows after upload."""
    import asyncio
    rows = db.get_alignments_by_text_id(text_id)
    if not rows: return

    total_corrected = 0
    total_annotations = 0
    total_rows = len(rows)

    BATCH_SIZE = 10
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        tasks = []
        for row in batch:
            if row.get("row_type") == "marker": continue
            tasks.append(_sayqallash_logic({"text": row["confirmed_uz_text"], "lang": "uz", "context_en": row["en_text"]}))
            tasks.append(_sayqallash_logic({"text": row["confirmed_ru_text"], "lang": "ru", "context_en": row["en_text"]}))

        if not tasks: continue
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for j, res in enumerate(results):
            if isinstance(res, Exception) or not res: continue

            row_idx = i + (j // 2)
            lang = 'uz' if j % 2 == 0 else 'ru'

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

    summary = {
        "total": total_rows,
        "corrected": total_corrected,
        "annotations": total_annotations,
        "timestamp": datetime.utcnow().isoformat()
    }
    db.save_project_polishing_summary(text_id, summary)


@router.post("/api/sayqallash/batch")
async def sayqallash_batch(payload: Dict[str, Any]):
    import asyncio
    items = payload.get("items", [])
    if not items: return {"results": []}

    tasks = [_sayqallash_logic(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    final_results = []
    for res in results:
        if isinstance(res, Exception):
            final_results.append({"error": str(res), "annotations": [], "corrected_text": ""})
        else:
            final_results.append(res)

    return {"results": final_results}


@router.post("/api/sayqallash-batch")
async def sayqallash_batch_rows(payload: Dict[str, Any]):
    rows = payload.get("rows", [])
    lang = payload.get("lang", "uz")
    if not rows: return {"results": []}
    results = []
    for row in rows:
        res = await _sayqallash_logic({"text": row.get("text", ""), "lang": lang, "context_en": row.get("en", "")})
        results.append({"id": row.get("id"), "original": row.get("text"), "corrected": res.get("corrected_text"), "annotations": res.get("annotations")})
    return {"results": results}


@router.post("/api/sayqallash/learn-batch")
async def learn_batch(payload: Dict[str, Any]):
    corrections = payload.get("corrections", [])
    lang = payload.get("lang", "uz")
    count = 0
    for c in corrections:
        old = c.get("old_value", "").strip()
        new = c.get("new_value", "").strip()
        error_type = c.get("error_type", "F/Correction")
        if old and new and old != new:
            if "[Луғатда топилмади]" in new or "[Not Found]" in new:
                continue
            db.add_sayqallash_rule(old, new, error_type, lang=lang, source="user_feedback")
            count += 1

    try:
        db.index_missing_rules()
    except: pass

    return {"success": True, "count": count}


@router.post("/api/auto-notes")
async def auto_notes(payload: Dict[str, Any]):
    v1 = payload.get("v1", "")
    proposed = payload.get("proposed", "")
    lang = payload.get("lang", "uz")
    notes = db.generate_diff_notes(v1, proposed, lang)
    return {"notes": notes}
