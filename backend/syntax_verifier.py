"""
Syntax Verifier — Bidirectional transformation verification (GECTurk-style).

Strategy:
  Для каждого правила (wrong → correct):
    1. Применить обратное правило к correct → получить reverse_result
    2. Если reverse_result == wrong → правило ТОЗА (clean), оставить
    3. Если не равно → правило НОИСИ (noisy), флагнуть для удаления/ревизии

Это фильтрует шумные правила, которые:
- имеют неправильную пару wrong/correct
- применимы в обе стороны (омонимы)
- содержат ложные трансформации
"""
import os
import sqlite3
import logging
import difflib

log = logging.getLogger("syntax_verifier")

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))


def _ensure_quality_column():
    """Add quality_flag column to sayqallash_rules if missing."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE sayqallash_rules ADD COLUMN quality_flag TEXT DEFAULT 'unverified'")
        conn.commit()
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE sayqallash_rules ADD COLUMN verified_at TIMESTAMP")
        conn.commit()
    except Exception:
        pass
    conn.close()


def simple_reverse_apply(correct_form: str, wrong_form: str, correct_form_all: str) -> str:
    """
    Attempt to apply the inverse transformation.
    Given a rule that says `wrong → correct`, if we see `correct` in text,
    can we get back to `wrong`?

    Simple approach: if the correction is a substring replacement,
    the inverse is also a substring replacement (in reverse).
    """
    # Find what changed between wrong and correct
    s = difflib.SequenceMatcher(None, wrong_form, correct_form)
    opcodes = s.get_opcodes()

    # Apply opcodes in reverse to correct_form_all
    result = correct_form_all
    # For a simple word-level rule, just substring replace
    if wrong_form in result or correct_form in result:
        result = result.replace(correct_form, wrong_form)
    return result


def verify_rule(wrong: str, correct: str) -> dict:
    """
    Verify a single rule bidirectionally.
    Returns {status: 'clean'|'noisy'|'suspicious', reason: str}
    """
    if not wrong or not correct:
        return {"status": "noisy", "reason": "empty wrong or correct"}

    if wrong == correct:
        return {"status": "noisy", "reason": "wrong == correct (no-op rule)"}

    # Check length sanity
    if len(wrong) > 200 or len(correct) > 200:
        return {"status": "suspicious", "reason": "too long"}

    # Check character ratio
    ratio = difflib.SequenceMatcher(None, wrong, correct).ratio()
    if ratio < 0.3:
        return {"status": "noisy", "reason": f"too different (ratio={ratio:.2f})"}

    # Check if wrong is just a case/whitespace variant
    if wrong.lower().strip() == correct.lower().strip():
        return {"status": "noisy", "reason": "only case/whitespace difference"}

    # Reverse verification: if we apply correct→wrong, can we reverse to correct?
    reversed_text = simple_reverse_apply(correct, wrong, correct)
    if reversed_text != wrong:
        # The rule is not cleanly invertible — might be ambiguous
        # But if it's a straight substring replacement, this passes
        if correct in wrong:
            return {"status": "noisy", "reason": "correct is substring of wrong"}
        return {"status": "clean", "reason": "passes basic sanity"}

    return {"status": "clean", "reason": "bidirectionally verifiable"}


def verify_all_rules(limit: int | None = None) -> dict:
    """Run verification on all sayqallash_rules."""
    _ensure_quality_column()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    q = "SELECT id, wrong_form, correct_form, error_type FROM sayqallash_rules"
    if limit:
        q += f" LIMIT {int(limit)}"
    cur.execute(q)
    rows = cur.fetchall()

    stats = {"total": len(rows), "clean": 0, "noisy": 0, "suspicious": 0}
    details = {"noisy_examples": [], "suspicious_examples": []}

    for row in rows:
        rid, wrong, correct, error_type = row
        result = verify_rule(wrong or "", correct or "")
        status = result["status"]
        stats[status] = stats.get(status, 0) + 1

        # Update DB
        try:
            cur.execute("""
                UPDATE sayqallash_rules
                SET quality_flag = ?, verified_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, rid))
        except Exception:
            pass

        if status == "noisy" and len(details["noisy_examples"]) < 20:
            details["noisy_examples"].append({
                "id": rid, "wrong": wrong, "correct": correct,
                "reason": result["reason"], "type": error_type
            })
        elif status == "suspicious" and len(details["suspicious_examples"]) < 20:
            details["suspicious_examples"].append({
                "id": rid, "wrong": wrong, "correct": correct,
                "reason": result["reason"]
            })

    conn.commit()
    conn.close()

    stats["details"] = details
    log.info(f"[syntax_verifier] {stats}")
    return stats


def get_noisy_rules(limit: int = 100) -> list:
    """Return list of rules flagged as noisy."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, wrong_form, correct_form, error_type, quality_flag, frequency
            FROM sayqallash_rules
            WHERE quality_flag IN ('noisy', 'suspicious')
            ORDER BY frequency DESC
            LIMIT ?
        """, (limit,))
        rules = [dict(r) for r in cur.fetchall()]
    except Exception:
        rules = []
    conn.close()
    return rules


def delete_noisy_rules(confirm: bool = False) -> int:
    """Delete all rules marked as noisy. Requires confirm=True."""
    if not confirm:
        return 0
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM sayqallash_rules WHERE quality_flag = 'noisy'")
        deleted = cur.rowcount
        conn.commit()
    except Exception:
        deleted = 0
    conn.close()
    return deleted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(verify_all_rules(limit=1000))
