"""
Import 3 pharmacopoeia report XLSX files that were previously unused:
  1. glossary_report.xlsx       → definitions + abbreviations
  2. jildlar_tahlil_hisoboti.xlsx → sayqallash_rules (per volume)
  3. linguistic_analysis_report.xlsx → sayqallash_rules (summary)

Idempotent: uses INSERT OR IGNORE on UNIQUE keys.
Run via: python -m scripts.import_pharma_reports  OR  admin endpoint.
"""
import os
import sqlite3
import logging

log = logging.getLogger("import_pharma_reports")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "pharmacopoeia")
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pharma_editor.db"))


def _ensure_schemas(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT NOT NULL,
            definition TEXT,
            source TEXT,
            frequency INTEGER DEFAULT 1,
            UNIQUE(term, source)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS abbreviations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            abbreviation TEXT NOT NULL,
            full_form TEXT,
            source TEXT,
            frequency INTEGER DEFAULT 1,
            UNIQUE(abbreviation, full_form)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sayqallash_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wrong_form TEXT NOT NULL,
            correct_form TEXT NOT NULL,
            error_type TEXT,
            frequency INTEGER DEFAULT 1,
            lang TEXT DEFAULT 'uz',
            source TEXT,
            context TEXT,
            UNIQUE(wrong_form, correct_form)
        )
    """)


def _import_glossary(cur) -> dict:
    path = os.path.join(DATA_DIR, "glossary_report.xlsx")
    if not os.path.exists(path):
        return {"definitions": 0, "abbreviations": 0, "error": "file_not_found"}
    try:
        import openpyxl
    except ImportError:
        return {"error": "openpyxl_missing"}
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    defs_ins = 0
    abbr_ins = 0

    # Sheet 1: Изоҳли сўзлар → definitions
    if "Изоҳли сўзлар" in wb.sheetnames:
        ws = wb["Изоҳли сўзлар"]
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0 or not row or len(row) < 3:
                continue
            _, term, definition, freq, src = (list(row) + [None] * 5)[:5]
            if not term or not definition:
                continue
            try:
                cur.execute(
                    "INSERT OR IGNORE INTO definitions (term, definition, source, frequency) VALUES (?,?,?,?)",
                    (str(term).strip(), str(definition).strip(), str(src or "ДФ глоссарий")[:120], int(freq or 1)),
                )
                defs_ins += cur.rowcount
            except Exception:
                pass

    # Sheet 2: Қисқартмалар + Sheet 3: Стандарт рўйхат → abbreviations
    for sheet in ("Қисқартмалар", "Стандарт рўйхат"):
        if sheet not in wb.sheetnames:
            continue
        ws = wb[sheet]
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0 or not row or len(row) < 3:
                continue
            _, abbr, full, *rest = list(row) + [None] * 3
            freq = rest[0] if rest else 1
            if not abbr or not full:
                continue
            try:
                cur.execute(
                    "INSERT OR IGNORE INTO abbreviations (abbreviation, full_form, source, frequency) VALUES (?,?,?,?)",
                    (str(abbr).strip(), str(full).strip(), f"ДФ {sheet}", int(freq or 1) if isinstance(freq, (int, float)) else 1),
                )
                abbr_ins += cur.rowcount
            except Exception:
                pass
    wb.close()
    return {"definitions": defs_ins, "abbreviations": abbr_ins}


def _import_error_xlsx(cur, path: str, source_label: str) -> int:
    if not os.path.exists(path):
        return 0
    try:
        import openpyxl
    except ImportError:
        return 0
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    inserted = 0
    for sheet in wb.sheetnames:
        if sheet.upper().startswith("ЖАМИ"):
            continue  # skip totals
        ws = wb[sheet]
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0 or not row or len(row) < 4:
                continue
            _, wrong, correct, etype, *rest = list(row) + [None] * 5
            freq = rest[0] if rest else 1
            if not wrong or not correct:
                continue
            try:
                cur.execute(
                    """INSERT OR IGNORE INTO sayqallash_rules
                       (wrong_form, correct_form, error_type, frequency, lang, source, context)
                       VALUES (?,?,?,?,'uz',?,?)""",
                    (
                        str(wrong).strip(),
                        str(correct).strip(),
                        str(etype or "Stilistik")[:80],
                        int(freq or 1) if isinstance(freq, (int, float)) else 1,
                        source_label,
                        f"{source_label} / {sheet}",
                    ),
                )
                inserted += cur.rowcount
            except Exception:
                pass
    wb.close()
    return inserted


def main() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    _ensure_schemas(cur)

    glossary = _import_glossary(cur)
    jildlar = _import_error_xlsx(cur, os.path.join(DATA_DIR, "jildlar_tahlil_hisoboti.xlsx"), "ДФ жилдлар таҳлили")
    linguistic = _import_error_xlsx(cur, os.path.join(DATA_DIR, "linguistic_analysis_report.xlsx"), "ДФ лингвистик ҳисобот")

    conn.commit()
    conn.close()

    result = {
        "definitions_inserted": glossary.get("definitions", 0),
        "abbreviations_inserted": glossary.get("abbreviations", 0),
        "sayqallash_from_jildlar": jildlar,
        "sayqallash_from_linguistic": linguistic,
        "total_sayqallash": jildlar + linguistic,
    }
    log.info("import_pharma_reports result: %s", result)
    return result


if __name__ == "__main__":
    print(main())
