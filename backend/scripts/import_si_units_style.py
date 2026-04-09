"""
Import SI units + pharma-standards from Uzbek Cabinet of Ministers
resolution 21 dated 10.01.2018 + Pharmacopoeia Chapter 1.

Extracts:
  - SI basic units (7 base)
  - SI derived units (~50)
  - SI prefixes (10^-24 to 10^24)
  - Non-SI units allowed in Uzbekistan
  - Solubility descriptor terms (Pharmacopoeia ch 1)
  - Temperature storage conditions

Creates:
  - si_units table (full reference)
  - style_rules entries (format enforcement rules)
  - annotated_words entries (definition dictionary)
"""
import os
import sys
import sqlite3
import logging
from pathlib import Path
import re

logging.basicConfig(level=logging.INFO, format="[si_units] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))
DATA_DIR = Path(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "si_units"
))


def ensure_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS si_units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seq_no INTEGER,
            category TEXT NOT NULL,
            quantity TEXT,
            quantity_symbol TEXT,
            unit_name_uz TEXT,
            unit_symbol TEXT,
            definition TEXT,
            si_equivalent TEXT,
            allowed_in_uz INTEGER DEFAULT 1,
            source_doc TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, unit_name_uz, unit_symbol)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_si_symbol ON si_units(unit_symbol)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_si_cat ON si_units(category)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pharma_solubility_terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term_uz TEXT UNIQUE,
            ratio_uz TEXT,
            ratio_ml_per_g TEXT,
            source TEXT DEFAULT 'pharmacopoeia_ch1'
        )
    """)
    conn.commit()
    conn.close()


def parse_si_doc():
    """Parse '21 10.01.2018.doc' (HTML inside) for SI units tables."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {"error": "bs4 not installed"}

    p = DATA_DIR / "si_units_resolution.doc"
    if not p.exists():
        return {"error": "file not found", "path": str(p)}

    with open(p, "rb") as f:
        html_bytes = f.read()
    text = html_bytes.decode("utf-8", errors="ignore")
    soup = BeautifulSoup(text, "html.parser")

    tables = soup.find_all("table")
    log.info(f"Found {len(tables)} tables in SI resolution")

    units_extracted = []

    # Table 0: Base units (7)
    if len(tables) >= 1:
        t = tables[0]
        rows = t.find_all("tr")
        for row in rows[2:]:  # skip 2 header rows
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) >= 6:
                try:
                    seq = int(re.sub(r"\D", "", cells[0]) or 0)
                except Exception:
                    seq = 0
                units_extracted.append({
                    "category": "si_base",
                    "seq_no": seq,
                    "quantity": cells[1],
                    "quantity_symbol": cells[2],
                    "unit_name_uz": cells[3],
                    "unit_symbol": cells[4],
                    "definition": cells[5],
                    "si_equivalent": "",
                })

    # Table 1: Derived units (many)
    if len(tables) >= 2:
        t = tables[1]
        rows = t.find_all("tr")
        for row in rows[3:]:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) >= 6:
                try:
                    seq = int(re.sub(r"\D", "", cells[0]) or 0)
                except Exception:
                    seq = 0
                if not cells[1] or len(cells) < 6:
                    continue
                units_extracted.append({
                    "category": "si_derived",
                    "seq_no": seq,
                    "quantity": cells[1],
                    "quantity_symbol": cells[2] if len(cells) > 2 else "",
                    "unit_name_uz": cells[3] if len(cells) > 3 else "",
                    "unit_symbol": cells[4] if len(cells) > 4 else "",
                    "definition": "",
                    "si_equivalent": cells[5] if len(cells) > 5 else "",
                })

    return {"units": units_extracted, "table_count": len(tables)}


def parse_bob_docx():
    """Parse 1. - БОБ..docx for solubility + storage tables."""
    try:
        from docx import Document
    except ImportError:
        return {"error": "python-docx not installed"}

    p = DATA_DIR / "pharma_ch1.docx"
    if not p.exists():
        return {"error": "file not found"}

    doc = Document(str(p))
    solubility = []
    storage = []

    for ti, t in enumerate(doc.tables):
        if ti == 0 and len(t.rows) >= 5:
            # Storage conditions
            for row in t.rows:
                cells = [c.text.strip() for c in row.cells]
                if len(cells) >= 2 and cells[0] and cells[1]:
                    storage.append({"condition": cells[0], "temperature": cells[1]})
        elif ti == 1 and len(t.rows) >= 5:
            # Solubility
            for row in t.rows[1:]:
                cells = [c.text.strip() for c in row.cells]
                if len(cells) >= 2 and cells[0] and cells[1]:
                    solubility.append({"term_uz": cells[0], "ratio_uz": cells[1]})

    return {"solubility": solubility, "storage": storage}


def import_to_db(si_data: dict, bob_data: dict) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    si_added = 0
    for u in si_data.get("units", []):
        try:
            cur.execute("""
                INSERT OR IGNORE INTO si_units
                (seq_no, category, quantity, quantity_symbol, unit_name_uz, unit_symbol, definition, si_equivalent, source_doc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'CM_21_10.01.2018')
            """, (u["seq_no"], u["category"], u["quantity"], u["quantity_symbol"],
                  u["unit_name_uz"], u["unit_symbol"], u["definition"], u["si_equivalent"]))
            if cur.rowcount > 0:
                si_added += 1
        except Exception as e:
            log.debug(f"si insert: {e}")

    sol_added = 0
    for s in bob_data.get("solubility", []):
        try:
            cur.execute("""
                INSERT OR IGNORE INTO pharma_solubility_terms (term_uz, ratio_uz, source)
                VALUES (?, ?, 'pharmacopoeia_ch1')
            """, (s["term_uz"], s["ratio_uz"]))
            if cur.rowcount > 0:
                sol_added += 1
        except Exception:
            pass

    # Generate style_rules from SI units (enforce correct symbol usage)
    style_added = 0
    for u in si_data.get("units", []):
        sym = u.get("unit_symbol", "").strip()
        name = u.get("unit_name_uz", "").strip()
        if not sym or len(sym) > 10 or not name:
            continue
        # Create "space between number and unit" rule per unit
        rule_id = f"STYLE-SI-UZ-{u['category']}-{u['seq_no']:03d}"
        desc = f"{name} бирлик ({sym}) сондан кейин пробел билан ёзилиши керак"
        try:
            cur.execute("""
                INSERT OR IGNORE INTO style_rules
                (rule_id, category, description, pattern, suggestion, severity, examples, source)
                VALUES (?, 'si_format', ?, ?, ?, 'should', ?, 'CM 21 (10.01.2018)')
            """, (rule_id, desc, f"(\\d+){re.escape(sym)}", f"{{n}} {sym}", f"5{sym} → 5 {sym}"))
            if cur.rowcount > 0:
                style_added += 1
        except Exception as e:
            log.debug(f"style rule: {e}")

    conn.commit()
    conn.close()
    return {
        "si_units_added": si_added,
        "solubility_added": sol_added,
        "style_rules_added": style_added,
    }


def main():
    ensure_schema()
    si = parse_si_doc()
    bob = parse_bob_docx()
    result = import_to_db(si, bob)
    log.info(result)
    return result


if __name__ == "__main__":
    print(main())
