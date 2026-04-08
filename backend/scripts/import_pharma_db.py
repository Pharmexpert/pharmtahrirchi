"""
Import State Pharmacopoeia data:
  1. ДФ мундарижаси жадвали.xlsx → pharma_toc (2 sheets: 1-нашр, 2-нашр)
  2. Давлат реестри.xls → drug_registry (8287 rows)

Both are displayed in /admin/pharma page with filters + search.
"""
import os
import sys
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[pharma_db] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))
DATA_DIR = Path(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "pharma_db"
))


def ensure_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Pharmacopoeia TOC (мундарижа)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pharma_toc (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            edition TEXT NOT NULL,
            volume TEXT,
            seq_no INTEGER,
            name_uz TEXT,
            name_en TEXT,
            name_ru TEXT,
            text_no TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_toc_edition ON pharma_toc(edition)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_toc_name_uz ON pharma_toc(name_uz)")

    # Drug Registry (Давлат реестри)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS drug_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seq_no INTEGER,
            trade_name TEXT,
            inn TEXT,
            dosage_form TEXT,
            country TEXT,
            manufacturer TEXT,
            pharm_group TEXT,
            atc_code TEXT,
            registration_no TEXT,
            registration_date TEXT,
            modification_date TEXT,
            dispense_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reg_inn ON drug_registry(inn)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reg_trade ON drug_registry(trade_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reg_atc ON drug_registry(atc_code)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reg_country ON drug_registry(country)")

    conn.commit()
    conn.close()


def import_toc(data_dir: Path = None) -> dict:
    """Import 2 sheets (1-нашр, 2-нашр) from ДФ мундарижаси."""
    import pandas as pd
    d = data_dir or DATA_DIR
    p = d / "ДФ мундарижаси жадвали.xlsx"
    if not p.exists():
        log.warning(f"TOC file not found: {p}")
        return {"error": "file not found", "path": str(p)}

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Check if already populated
    cur.execute("SELECT COUNT(*) FROM pharma_toc")
    existing = cur.fetchone()[0]
    if existing > 500:
        conn.close()
        return {"skipped": True, "reason": "already populated", "count": existing}

    xl = pd.ExcelFile(p)
    total = 0
    per_sheet = {}

    for sheet_name in xl.sheet_names:
        df = pd.read_excel(p, sheet_name=sheet_name)
        added = 0
        for _, row in df.iterrows():
            try:
                seq = int(row.get("Т/р", 0) or 0)
                name_uz = str(row.get("Номланиши (ўзбек)", "") or "").strip()
                name_en = str(row.get("Номланиши (инглиз)", "") or "").strip()
                name_ru = str(row.get("Номланиши (рус)", "") or "").strip()
                text_no = str(row.get("Матн рақами", "") or "").strip()
                volume_col = row.get("Жилд", row.get("2-нашр 1-жилд", ""))
                volume = str(volume_col or "").strip()
                if not name_uz or name_uz == "nan":
                    continue
                cur.execute("""
                    INSERT INTO pharma_toc (edition, volume, seq_no, name_uz, name_en, name_ru, text_no)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (sheet_name, volume, seq, name_uz, name_en, name_ru, text_no))
                added += 1
            except Exception as e:
                log.debug(f"toc row skip: {e}")
        per_sheet[sheet_name] = added
        total += added
        log.info(f"TOC {sheet_name}: +{added}")

    conn.commit()
    conn.close()
    return {"total": total, "per_sheet": per_sheet}


def import_registry(data_dir: Path = None) -> dict:
    """Import Davlat reestri (8287 rows)."""
    import pandas as pd
    d = data_dir or DATA_DIR
    p = d / "Давлат реестри.xls"
    if not p.exists():
        log.warning(f"Registry file not found: {p}")
        return {"error": "file not found", "path": str(p)}

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM drug_registry")
    existing = cur.fetchone()[0]
    if existing > 5000:
        conn.close()
        return {"skipped": True, "reason": "already populated", "count": existing}

    df = pd.read_excel(p, sheet_name="ПРОСМОТР")

    # Normalize column names
    col_map = {}
    for col in df.columns:
        c = str(col).strip()
        if "Торговое" in c:
            col_map[col] = "trade_name"
        elif "Международное" in c:
            col_map[col] = "inn"
        elif "форма выпуска" in c or "Лекарственная" in c:
            col_map[col] = "dosage_form"
        elif "Страна" in c:
            col_map[col] = "country"
        elif "Фирма" in c:
            col_map[col] = "manufacturer"
        elif "Фармакотерапевт" in c:
            col_map[col] = "pharm_group"
        elif "АТХ" in c or "АTC" in c or "ATC" in c.upper():
            col_map[col] = "atc_code"
        elif "Регистрационного" in c or "№ Регистр" in c:
            col_map[col] = "registration_no"
        elif "Дата регистрации" in c:
            col_map[col] = "registration_date"
        elif "Дата изменения" in c:
            col_map[col] = "modification_date"
        elif "Условия" in c:
            col_map[col] = "dispense_type"
        elif "п/п" in c or c == "№":
            col_map[col] = "seq_no"

    df = df.rename(columns=col_map)

    added = 0
    for _, row in df.iterrows():
        try:
            def gv(k):
                v = row.get(k, "")
                return "" if (v is None or (hasattr(v, "__len__") and str(v) == "nan")) else str(v).strip()

            trade = gv("trade_name")
            inn = gv("inn")
            if not trade and not inn:
                continue

            cur.execute("""
                INSERT INTO drug_registry
                (seq_no, trade_name, inn, dosage_form, country, manufacturer,
                 pharm_group, atc_code, registration_no, registration_date, modification_date, dispense_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(row.get("seq_no", 0) or 0),
                trade, inn,
                gv("dosage_form"), gv("country"), gv("manufacturer"),
                gv("pharm_group"), gv("atc_code"),
                gv("registration_no"), gv("registration_date"),
                gv("modification_date"), gv("dispense_type"),
            ))
            added += 1
        except Exception as e:
            log.debug(f"registry row skip: {e}")

    conn.commit()
    conn.close()
    return {"added": added, "total_rows": len(df)}


def main():
    ensure_schema()
    result = {
        "toc": import_toc(),
        "registry": import_registry(),
    }
    log.info(f"DONE: {result}")
    return result


if __name__ == "__main__":
    print(main())
