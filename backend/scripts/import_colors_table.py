"""
Import 'Ранглар жадвали' from Qonun/SP/Ранглар жадвали.xlsx
285 colors in uz/ru/en.
"""
import os
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[colors] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))
DATA_DIR = Path(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "colors_table"
))


def ensure_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS colors_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seq_no INTEGER,
            uz TEXT NOT NULL,
            ru TEXT,
            en TEXT,
            source TEXT DEFAULT 'state_pharmacopoeia',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(uz, ru, en)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_colors_uz ON colors_table(uz)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_colors_en ON colors_table(en)")
    conn.commit()
    conn.close()


def main():
    try:
        import pandas as pd
    except ImportError:
        return {"error": "pandas not installed"}

    ensure_schema()
    p = DATA_DIR / "colors_table.xlsx"
    if not p.exists():
        log.warning(f"File not found: {p}")
        return {"error": "file not found"}

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    df = pd.read_excel(p, sheet_name="Ўзбек", header=None)
    added = 0
    for i in range(5, len(df)):  # data starts at row 5
        row = df.iloc[i].tolist()
        try:
            seq = int(row[1]) if row[1] is not None and str(row[1]).replace('.', '').isdigit() else i - 4
        except Exception:
            seq = i - 4
        uz = str(row[2] or "").strip()
        ru = str(row[3] or "").strip()
        en = str(row[4] or "").strip()
        if not uz or uz == "nan":
            continue
        try:
            cur.execute("""
                INSERT OR IGNORE INTO colors_table (seq_no, uz, ru, en)
                VALUES (?, ?, ?, ?)
            """, (seq, uz, ru if ru != "nan" else "", en if en != "nan" else ""))
            if cur.rowcount > 0:
                added += 1
        except Exception as e:
            log.debug(f"skip {i}: {e}")

    conn.commit()
    conn.close()
    log.info(f"+{added} colors")
    return {"added": added}


if __name__ == "__main__":
    print(main())
