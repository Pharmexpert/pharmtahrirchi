"""
Import State Pharmacopoeia Volume 1 data from Qonun/Data xlsx files.

Sources:
  1. glossary_report.xlsx
     - "Изоҳли сўзлар" (4848 rows) → annotated_words (изоҳли луғат)
     - "Қисқартмалар" (785 rows) → abbreviations (қисқартмалар)
     - "Стандарт рўйхат" (88 rows) → abbreviations (standard list)
  2. jildlar_tahlil_hisoboti.xlsx — error lists per volume → sayqallash_rules
     - "1-жилд (1-қисм)", "1-жилд (2-қисм)", "2-жилд", "3-жилд", "ЖАМИ УМУМИЙ"
  3. linguistic_analysis_report.xlsx → sayqallash_rules

All imports are idempotent (dedupe via UNIQUE constraints + existence checks).
Source field is set to 'pharmacopoeia_vol1' so we can audit.
"""
import os
import sys
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[pharmacopoeia] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))

DEFAULT_DATA_DIR = Path(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "pharmacopoeia"
))


def import_glossary(data_dir: Path) -> dict:
    """Import glossary_report.xlsx → annotated_words + abbreviations."""
    import pandas as pd

    p = data_dir / "glossary_report.xlsx"
    if not p.exists():
        log.warning(f"Missing: {p}")
        return {"error": "file not found"}

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Migration: add source + frequency columns if missing
    for table in ("annotated_words", "abbreviations", "disputed_words"):
        for col, typ in (("source", "TEXT DEFAULT ''"), ("frequency", "INTEGER DEFAULT 1")):
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
            except Exception:
                pass

    # 1. Изоҳли сўзлар → annotated_words (uz + description_uz)
    try:
        df = pd.read_excel(p, sheet_name="Изоҳли сўзлар")
        annotated_added = 0
        for _, row in df.iterrows():
            term = str(row.get("Атама", "")).strip()
            annotation = str(row.get("Изоҳ", "")).strip()
            context_src = str(row.get("Манба", "")).strip()
            freq = int(row.get("Учраш", 1) or 1)
            if not term or term == "nan" or not annotation or annotation == "nan":
                continue
            try:
                # Dedupe check by uz field
                cur.execute("SELECT 1 FROM annotated_words WHERE uz = ? LIMIT 1", (term,))
                if cur.fetchone():
                    continue
                cur.execute("""
                    INSERT INTO annotated_words
                    (uz, description_uz, source_lang, source, frequency, status)
                    VALUES (?, ?, 'Uzbek', 'pharmacopoeia_vol1', ?, 'active')
                """, (term, annotation + (f"\n\nМанба: {context_src}" if context_src and context_src != "nan" else ""), freq))
                annotated_added += 1
            except Exception as e:
                log.debug(f"annotated insert fail {term}: {e}")
        log.info(f"annotated_words: +{annotated_added}")
    except Exception as e:
        log.warning(f"annotated sheet failed: {e}")
        annotated_added = 0

    # 2. Қисқартмалар → abbreviations (short_form + long_uz)
    try:
        df = pd.read_excel(p, sheet_name="Қисқартмалар")
        abbr_added = 0
        for _, row in df.iterrows():
            abbr = str(row.get("Қисқартма", "")).strip()
            full = str(row.get("Тўлиқ номи", "")).strip()
            freq = int(row.get("Учраш", 1) or 1)
            if not abbr or abbr == "nan":
                continue
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO abbreviations
                    (short_form, long_uz, source_lang, source, frequency, status)
                    VALUES (?, ?, 'Uzbek', 'pharmacopoeia_vol1', ?, 'active')
                """, (abbr, full if full != "nan" else "", freq))
                if cur.rowcount > 0:
                    abbr_added += 1
            except Exception:
                pass
        log.info(f"abbreviations (main): +{abbr_added}")
    except Exception as e:
        log.warning(f"abbr sheet failed: {e}")
        abbr_added = 0

    # 3. Стандарт рўйхат → abbreviations (short_form + long_en)
    try:
        df = pd.read_excel(p, sheet_name="Стандарт рўйхат")
        std_added = 0
        for _, row in df.iterrows():
            abbr = str(row.get("Қисқартма", "")).strip()
            full = str(row.get("Тўлиқ номи", "")).strip()
            if not abbr or abbr == "nan":
                continue
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO abbreviations
                    (short_form, long_en, source_lang, source, frequency, status)
                    VALUES (?, ?, 'English', 'pharmacopoeia_vol1_std', 1, 'active')
                """, (abbr, full if full != "nan" else ""))
                if cur.rowcount > 0:
                    std_added += 1
            except Exception:
                pass
        log.info(f"abbreviations (standard): +{std_added}")
    except Exception as e:
        log.warning(f"std sheet failed: {e}")
        std_added = 0

    conn.commit()
    conn.close()
    return {
        "annotated_added": annotated_added,
        "abbr_main_added": abbr_added,
        "abbr_std_added": std_added,
    }


def import_error_list(data_dir: Path, filename: str, sheet: str = None, error_label: str = "pharmacopoeia") -> dict:
    """Import error list (жилд файли) → sayqallash_rules."""
    import pandas as pd

    p = data_dir / filename
    if not p.exists():
        return {"error": "file not found", "file": filename}

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    sheets_to_process = [sheet] if sheet else pd.ExcelFile(p).sheet_names
    total = 0
    per_sheet = {}

    for s in sheets_to_process:
        try:
            df = pd.read_excel(p, sheet_name=s)
        except Exception as e:
            log.warning(f"{filename}/{s} read failed: {e}")
            continue

        added = 0
        for _, row in df.iterrows():
            wrong = str(row.get("Хато сўз", "")).strip()
            correct = str(row.get("Тўғри вариант", "")).strip()
            err_type = str(row.get("Хато тури", "")).strip()
            freq = int(row.get("Келиш частотаси", row.get("Учраш", 1)) or 1)

            if not wrong or wrong == "nan" or not correct or correct == "nan":
                continue
            if wrong == correct:
                continue

            # Determine category
            err_type_lower = err_type.lower()
            if "услуб" in err_type_lower or "стилистик" in err_type_lower:
                category = "S/Style"
            elif "терм" in err_type_lower:
                category = "Terminology"
            elif "грамматик" in err_type_lower:
                category = "G/Grammar"
            elif "имло" in err_type_lower or "spelling" in err_type_lower:
                category = "S/Spelling"
            else:
                category = "S/Style"

            try:
                cur.execute("""
                    INSERT OR IGNORE INTO sayqallash_rules
                    (wrong_form, correct_form, error_type, lang, source, frequency,
                     quality_flag, context)
                    VALUES (?, ?, ?, 'uz', ?, ?, 'unverified', ?)
                """, (wrong, correct, category, f"pharmacopoeia_{error_label}_{s}", freq, err_type))
                if cur.rowcount > 0:
                    added += 1
                else:
                    # Update frequency if exists
                    cur.execute("""
                        UPDATE sayqallash_rules
                        SET frequency = frequency + ?
                        WHERE wrong_form = ? AND correct_form = ?
                    """, (freq, wrong, correct))
            except Exception as e:
                log.debug(f"rule insert fail: {e}")

        per_sheet[s] = added
        total += added
        log.info(f"{filename}/{s}: +{added} new rules")

    conn.commit()
    conn.close()
    return {"file": filename, "total_added": total, "per_sheet": per_sheet}


def main(data_dir: str = None):
    d = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    if not d.exists():
        log.error(f"Data dir not found: {d}")
        return {"error": "data_dir_missing"}

    result = {}

    # 1. Glossary (annotations + abbreviations)
    log.info("== Importing glossary_report.xlsx ==")
    result["glossary"] = import_glossary(d)

    # 2. Jildlar tahlil (per-volume error lists)
    log.info("== Importing jildlar_tahlil_hisoboti.xlsx ==")
    result["jildlar"] = import_error_list(d, "jildlar_tahlil_hisoboti.xlsx", error_label="vol")

    # 3. Linguistic analysis
    log.info("== Importing linguistic_analysis_report.xlsx ==")
    result["linguistic"] = import_error_list(d, "linguistic_analysis_report.xlsx", error_label="ling")

    log.info(f"DONE: {result}")
    return result


if __name__ == "__main__":
    data_dir_arg = sys.argv[1] if len(sys.argv) > 1 else None
    print(main(data_dir_arg))
