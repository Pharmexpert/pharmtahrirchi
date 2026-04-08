"""
Weekly self-improvement cycle for Pharma Expert.

Runs every Sunday 03:00 Asia/Tashkent:
  1. Extract (wrong, correct) pairs from llm_training_log
  2. Add high-confidence pairs to sayqallash_rules
  3. Run sayqallash_consolidator (dedupe + semantic merge)
  4. Regenerate pharma dictionary
  5. Export fine-tune JSONL
  6. Optional: send admin report
"""
import os
import sqlite3
import logging
import json
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger("weekly_learning")

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))


def extract_pairs_from_llm_log() -> int:
    """Extract new (wrong, correct) pairs from llm_training_log → sayqallash_rules."""
    try:
        import difflib
        import re

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Ensure llm_training_log exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS llm_training_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT, prompt TEXT, response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed INTEGER DEFAULT 0
            )
        """)
        try:
            cur.execute("ALTER TABLE llm_training_log ADD COLUMN processed INTEGER DEFAULT 0")
        except Exception:
            pass

        # Get unprocessed entries from the last 7 days
        cur.execute("""
            SELECT id, kind, prompt, response FROM llm_training_log
            WHERE processed = 0 AND created_at >= datetime('now', '-7 days')
            LIMIT 1000
        """)
        rows = cur.fetchall()

        new_rules = 0
        processed_ids = []

        def split_words(s: str):
            return re.findall(r"[\w'\u2019\u02bb\u02bc\u2018-]+", s)

        for row_id, kind, prompt, response in rows:
            processed_ids.append(row_id)
            if not prompt or not response:
                continue
            if len(prompt) > 2000 or len(response) > 2000:
                continue  # skip very long samples

            # Word-level diff
            pw = split_words(prompt)
            rw = split_words(response)
            sm = difflib.SequenceMatcher(None, pw, rw)
            for tag, a1, a2, b1, b2 in sm.get_opcodes():
                if tag == "replace" and (a2 - a1) == (b2 - b1):
                    for k in range(a2 - a1):
                        wrong = pw[a1 + k]
                        correct = rw[b1 + k]
                        if wrong.lower() == correct.lower() or len(wrong) < 2 or len(correct) < 2:
                            continue
                        try:
                            # Check if rule already exists
                            cur.execute(
                                "SELECT id FROM sayqallash_rules WHERE LOWER(wrong_form) = LOWER(?) AND LOWER(correct_form) = LOWER(?) AND lang = ?",
                                (wrong, correct, "uz")
                            )
                            if cur.fetchone():
                                continue
                            cur.execute(
                                "INSERT INTO sayqallash_rules (wrong_form, correct_form, error_type, lang, source, frequency) VALUES (?, ?, ?, ?, ?, ?)",
                                (wrong, correct, "S/Spelling", "uz", f"llm_log_{kind}", 1)
                            )
                            new_rules += 1
                        except Exception:
                            pass

        # Mark as processed
        if processed_ids:
            placeholders = ",".join("?" * len(processed_ids))
            cur.execute(f"UPDATE llm_training_log SET processed = 1 WHERE id IN ({placeholders})", processed_ids)

        conn.commit()
        conn.close()
        logger.info(f"[weekly] Added {new_rules} rules from {len(rows)} LLM log entries")
        return new_rules
    except Exception as e:
        logger.error(f"[weekly] extract_pairs failed: {e}")
        return 0


def export_finetune_jsonl(out_path: str = "/tmp/finetune_dataset.jsonl") -> int:
    """Export training data as JSONL for fine-tuning."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        count = 0
        with open(out_path, "w", encoding="utf-8") as f:
            # Sayqallash pairs
            cur.execute("SELECT wrong_form, correct_form, error_type, lang FROM sayqallash_rules LIMIT 20000")
            for r in cur.fetchall():
                sample = {
                    "instruction": f"Матнни тузат ({r['lang']}):",
                    "input": r["wrong_form"],
                    "output": r["correct_form"],
                    "error_type": r["error_type"],
                    "source": "sayqallash",
                }
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
                count += 1

            # LLM log pairs (edit/translate)
            cur.execute("SELECT kind, prompt, response FROM llm_training_log WHERE LENGTH(prompt) BETWEEN 10 AND 2000 LIMIT 5000")
            for r in cur.fetchall():
                if not r["prompt"] or not r["response"]:
                    continue
                task_instr = {
                    "llama_improve_uz": "Илмий-фарма муҳаррир сифатида матнни тузат:",
                    "llama_improve_en": "Edit this scientific text as a pharma expert:",
                    "llama_translate": "Translate this text:",
                    "assistant_chat": "Ўзбек тилида илмий жавоб бер:",
                    "russian_correct": "Исправь русский текст:",
                }.get(r["kind"], "Матнни тузат:")
                sample = {
                    "instruction": task_instr,
                    "input": r["prompt"][:1500],
                    "output": r["response"][:1500],
                    "source": r["kind"],
                }
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
                count += 1

        conn.close()
        logger.info(f"[weekly] Exported {count} samples to {out_path}")
        return count
    except Exception as e:
        logger.error(f"[weekly] export_jsonl failed: {e}")
        return 0


def run_full_cycle() -> Dict[str, Any]:
    """Run all weekly learning steps in sequence."""
    start = datetime.now()
    result = {"started_at": start.isoformat()}

    # 1. Extract pairs from LLM log
    result["new_rules_from_llm"] = extract_pairs_from_llm_log()

    # 2. Consolidate Sayqallash
    try:
        import sayqallash_consolidator
        result["consolidation"] = sayqallash_consolidator.consolidate(semantic=True)
    except Exception as e:
        result["consolidation_error"] = str(e)

    # 3. Export fine-tune JSONL
    result["finetune_exported"] = export_finetune_jsonl()

    # 4. Regenerate pharma dictionary
    try:
        import uzbek_dict_generator
        result["pharma_dict"] = uzbek_dict_generator.generate_pharma_dictionary()
    except Exception as e:
        result["pharma_dict_error"] = str(e)

    # 5. Syntax module — auto-extract from approved translations
    try:
        import syntax_self_improve
        result["syntax_improve"] = syntax_self_improve.run()
    except Exception as e:
        result["syntax_improve_error"] = str(e)

    result["duration_seconds"] = (datetime.now() - start).total_seconds()
    result["completed_at"] = datetime.now().isoformat()

    # Send email report to admin (if configured)
    try:
        import email_helper
        if email_helper.is_configured():
            admin_email = os.getenv("ADMIN_EMAIL") or "texnopharm@gmail.com"
            email_helper.send_daily_cycle_report(admin_email, result)
    except Exception as e:
        logger.warning(f"[weekly] email skipped: {e}")

    # Log to weekly_cycles table
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS weekly_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("INSERT INTO weekly_cycles (result) VALUES (?)", (json.dumps(result, ensure_ascii=False, default=str),))
        conn.commit()
        conn.close()
    except Exception:
        pass

    logger.info(f"[weekly] Cycle complete: {result}")
    return result


if __name__ == "__main__":
    print(json.dumps(run_full_cycle(), indent=2, ensure_ascii=False, default=str))
