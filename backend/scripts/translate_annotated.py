"""
Batch-translate annotated_words rows that are missing EN and/or RU translations.

Strategy:
  - Select rows where (en IS NULL/'' OR ru IS NULL/'') AND
                      (uz IS NOT NULL AND uz != '')
  - Batch N rows into a single AI call, ask for JSON array back
  - Parse response, UPDATE each row with en/ru/description_en/description_ru
  - Idempotent: only fills empty fields, never overwrites human-entered ones

Run via:
  python -m scripts.translate_annotated           # default: 100 rows
  TRANSLATE_LIMIT=500 python -m scripts.translate_annotated
  OR admin endpoint /api/admin/annotated/translate-batch
"""
import os
import sys
import json
import sqlite3
import logging

log = logging.getLogger("translate_annotated")

DB_PATH = os.getenv(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pharma_editor.db"),
)

BATCH_SIZE = 20        # rows per AI call
DEFAULT_LIMIT = 100    # total rows per invocation


PROMPT_TEMPLATE = """You are a professional pharmaceutical translator.

Below are {n} pharmaceutical terms in Uzbek with Uzbek definitions.
For each one, provide:
  - en:             the term in English
  - ru:             the term in Russian
  - description_en: the definition in English (≤200 chars)
  - description_ru: the definition in Russian (≤200 chars)

Keep translations CONCISE and FAITHFUL to the Uzbek source. Use standard
pharmaceutical terminology (ICH, USP, Ph.Eur., WHO).

Return ONLY a valid JSON array of {n} objects in the SAME order as the input.
Do NOT wrap in markdown. Each object must have exactly: id, en, ru,
description_en, description_ru.

Input (JSON):
{items}

Output (JSON array only):"""


def _fetch_batch(cur, limit: int) -> list:
    cur.execute(
        """
        SELECT id, uz, description_uz
        FROM annotated_words
        WHERE (en IS NULL OR TRIM(en) = '')
          AND (uz IS NOT NULL AND TRIM(uz) != '')
          AND (description_uz IS NOT NULL AND TRIM(description_uz) != '')
        ORDER BY id ASC
        LIMIT ?
        """,
        (limit,),
    )
    return [
        {"id": r[0], "uz": r[1] or "", "description_uz": (r[2] or "")[:400]}
        for r in cur.fetchall()
    ]


def _call_ai(batch: list) -> list:
    """Sync wrapper around AI translator. Returns parsed JSON list or [] on failure."""
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        client = anthropic.Anthropic(api_key=api_key)
        prompt = PROMPT_TEMPLATE.format(
            n=len(batch),
            items=json.dumps(batch, ensure_ascii=False),
        )
        try:
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            txt = msg.content[0].text.strip()
            # Strip common markdown wrappers
            if txt.startswith("```"):
                txt = txt.split("```", 2)[1]
                if txt.startswith("json"):
                    txt = txt[4:]
                txt = txt.strip("` \n")
            # Find first [ ... last ]
            start = txt.find("[")
            end = txt.rfind("]")
            if start >= 0 and end > start:
                txt = txt[start : end + 1]
            return json.loads(txt)
        except Exception as e:
            log.error(f"Claude call failed: {e}")
            return []
    log.error("ANTHROPIC_API_KEY not set")
    return []


def _update_row(cur, row: dict) -> bool:
    try:
        cur.execute(
            """
            UPDATE annotated_words
            SET en = CASE WHEN (en IS NULL OR TRIM(en) = '') THEN ? ELSE en END,
                ru = CASE WHEN (ru IS NULL OR TRIM(ru) = '') THEN ? ELSE ru END,
                description_en = CASE WHEN (description_en IS NULL OR TRIM(description_en) = '') THEN ? ELSE description_en END,
                description_ru = CASE WHEN (description_ru IS NULL OR TRIM(description_ru) = '') THEN ? ELSE description_ru END,
                modified_at = datetime('now')
            WHERE id = ?
            """,
            (
                (row.get("en") or "").strip()[:500],
                (row.get("ru") or "").strip()[:500],
                (row.get("description_en") or "").strip()[:2000],
                (row.get("description_ru") or "").strip()[:2000],
                int(row.get("id", 0)),
            ),
        )
        return cur.rowcount > 0
    except Exception as e:
        log.debug(f"update failed for id={row.get('id')}: {e}")
        return False


def run(limit: int = None) -> dict:
    """Translate up to `limit` rows. Returns progress dict."""
    limit = int(limit or os.getenv("TRANSLATE_LIMIT", DEFAULT_LIMIT))
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Pre-check how many rows remain overall
    cur.execute(
        """
        SELECT COUNT(*) FROM annotated_words
        WHERE (en IS NULL OR TRIM(en) = '')
          AND (uz IS NOT NULL AND TRIM(uz) != '')
          AND (description_uz IS NOT NULL AND TRIM(description_uz) != '')
        """
    )
    remaining_before = cur.fetchone()[0]

    processed = 0
    updated = 0
    failed_batches = 0
    while processed < limit:
        take = min(BATCH_SIZE, limit - processed)
        batch = _fetch_batch(cur, take)
        if not batch:
            break
        result = _call_ai(batch)
        if not result:
            failed_batches += 1
            # To avoid infinite loop: mark batch IDs as attempted by moving on
            # via small sleep is not needed; just break out
            break
        by_id = {int(r.get("id", -1)): r for r in result if isinstance(r, dict)}
        for item in batch:
            rid = item["id"]
            if rid in by_id:
                if _update_row(cur, {**by_id[rid], "id": rid}):
                    updated += 1
        processed += len(batch)
        conn.commit()
        log.info(f"batch done: processed={processed} updated={updated}")

    cur.execute(
        """
        SELECT COUNT(*) FROM annotated_words
        WHERE (en IS NULL OR TRIM(en) = '')
          AND (uz IS NOT NULL AND TRIM(uz) != '')
          AND (description_uz IS NOT NULL AND TRIM(description_uz) != '')
        """
    )
    remaining_after = cur.fetchone()[0]
    conn.close()

    return {
        "requested": limit,
        "processed": processed,
        "updated": updated,
        "failed_batches": failed_batches,
        "remaining_before": remaining_before,
        "remaining_after": remaining_after,
    }


def main():
    return run()


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))
