"""
Syntax Self-Improvement (Phase 6).

Strategy:
  1. Find all approved/finalized uz translations from the dashboard table.
  2. Run them through syntax_engine.analyze() to extract:
     - new sentence templates (POS sequences) → frequency boost
     - new head-dep phrases → syntax_phrases
  3. Detect anomalies: template not in canonical list → flag for review
  4. Boost confidence of frequently-seen patterns

Run weekly via weekly_learning_cycle.py
"""
import sqlite3
import os
import logging

log = logging.getLogger("syntax_self_improve")

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))


def run() -> dict:
    """Execute self-improvement cycle."""
    try:
        import syntax_engine
    except ImportError:
        return {"error": "syntax_engine not available"}

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Get recently approved translations
    try:
        cur.execute("""
            SELECT DISTINCT confirmed_uz_text FROM dashboard
            WHERE confirmed_uz_text IS NOT NULL AND confirmed_uz_text != ''
            ORDER BY id DESC LIMIT 200
        """)
        rows = [r[0] for r in cur.fetchall()]
    except Exception:
        rows = []

    if not rows:
        conn.close()
        return {"processed": 0, "reason": "no approved translations"}

    new_templates = 0
    new_phrases = 0
    boosted = 0

    for text in rows:
        if not text or len(text) < 10:
            continue

        # Split to sentences
        import re
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        for sent in sentences:
            if not sent.strip() or len(sent) < 5:
                continue
            try:
                result = syntax_engine.analyze(sent)
                tokens = result.get("tokens", [])
                if not tokens:
                    continue

                # Extract template
                role_seq = "+".join(_short(t["role"]) for t in tokens if t.get("role") and t["role"] != "other")
                if role_seq:
                    cur.execute("""
                        UPDATE syntax_sentence_templates SET frequency = frequency + 1
                        WHERE template = ?
                    """, (role_seq,))
                    if cur.rowcount > 0:
                        boosted += 1
                    else:
                        cur.execute("""
                            INSERT OR IGNORE INTO syntax_sentence_templates
                            (template, sentence_type, example_uz, source, frequency)
                            VALUES (?, 'sodda', ?, 'self_improve', 1)
                        """, (role_seq, sent[:300]))
                        if cur.rowcount > 0:
                            new_templates += 1

                # Extract head-dep phrases (heuristic: each non-verb → root verb)
                root_verb = next((t for t in tokens if t.get("pos") == "VERB"), None)
                if root_verb:
                    for tok in tokens:
                        if tok is root_verb:
                            continue
                        try:
                            cur.execute("""
                                INSERT OR IGNORE INTO syntax_phrases
                                (head_word, dep_word, head_pos, dep_pos, relation, example, source)
                                VALUES (?, ?, ?, ?, 'auto', ?, 'self_improve')
                            """, (root_verb["clean"].lower(), tok["clean"].lower(),
                                  root_verb["pos"], tok["pos"], sent[:300]))
                            if cur.rowcount > 0:
                                new_phrases += 1
                        except Exception:
                            pass
            except Exception as e:
                log.debug(f"analyze fail: {e}")

    conn.commit()
    conn.close()
    result = {
        "processed_sentences": len(rows),
        "new_templates": new_templates,
        "templates_boosted": boosted,
        "new_phrases": new_phrases,
    }
    log.info(f"[syntax_self_improve] {result}")
    return result


def _short(role: str) -> str:
    return {
        "ega": "S",
        "toldiruvchi": "O",
        "kesim": "V",
        "aniqlovchi": "Adj",
        "hol": "Adv",
    }.get(role, "X")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
