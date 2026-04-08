"""
Import Uzbek grammar rules + error corrections from uzbek_til_qoidalari_va_xatolar.md.

Extracts markdown tables:
  - "Xato → Toʻgʻri" tables → sayqallash_rules
  - Grammar explanation sections → style_rules (grammar category)
  - Section headings → context for grouping

Total ~500+ error pairs expected from @xatoliklar + @xatoliklar_lotin sources.
"""
import os
import re
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[uz_qoidalari] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))
DATA_DIR = Path(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "uzbek_qoidalari"
))

MARKDOWN_FILE = DATA_DIR / "uzbek_til_qoidalari_va_xatolar.md"


def parse_markdown_tables(text: str) -> list:
    """
    Parse all markdown tables. Returns list of {header, rows, section}.
    """
    tables = []
    lines = text.splitlines()
    current_section = ""
    current_sub = ""
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Track section headings
        if line.startswith("# "):
            current_section = line[2:].strip()
        elif line.startswith("## "):
            current_section = line[3:].strip()
            current_sub = ""
        elif line.startswith("### "):
            current_sub = line[4:].strip()

        # Table start: header row with |
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1].strip()):
            header = [c.strip() for c in line.strip("|").split("|")]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                row_line = lines[j].strip()
                cells = [c.strip() for c in row_line.strip("|").split("|")]
                rows.append(cells)
                j += 1
            tables.append({
                "header": header,
                "rows": rows,
                "section": current_section,
                "subsection": current_sub,
            })
            i = j
            continue
        i += 1
    return tables


def clean_cell(cell: str) -> str:
    """Remove markdown formatting, emojis, parentheses comments."""
    if not cell or cell == "—" or cell == "-":
        return ""
    # Remove **bold**
    cell = re.sub(r"\*\*([^*]+)\*\*", r"\1", cell)
    # Remove checkmarks/X
    cell = re.sub(r"[✅✓❌✗]", "", cell).strip()
    # Remove parenthetical notes at end
    cell = re.sub(r"\s*\([^)]*\)$", "", cell).strip()
    # Strip arrows
    cell = cell.replace("→", "").strip()
    return cell.strip()


def extract_pairs(tables: list) -> dict:
    """
    Scan tables for xato/tog'ri columns. Return both:
      - rule_pairs: (wrong, correct, error_type, source)
      - style_rules: (description, context, severity, source)
    """
    rule_pairs = []
    style_rules = []

    for t in tables:
        hdr = [h.lower() for h in t["header"]]
        section = t["section"]
        sub = t["subsection"]

        # Detect xato/to'g'ri columns
        xato_idx = -1
        togri_idx = -1
        for i, h in enumerate(hdr):
            if "xato" in h and xato_idx == -1:
                xato_idx = i
            elif ("to'g'ri" in h or "toʻgʻri" in h or "tog'ri" in h) and togri_idx == -1:
                togri_idx = i

        if xato_idx >= 0 and togri_idx >= 0:
            for row in t["rows"]:
                if len(row) <= max(xato_idx, togri_idx):
                    continue
                wrong = clean_cell(row[xato_idx])
                correct = clean_cell(row[togri_idx])
                if not wrong or not correct or wrong == correct:
                    continue
                if wrong == "—" or correct == "—":
                    continue
                err_type = "S/Spelling"
                sect_l = section.lower()
                if "феъл" in sect_l or "fe'l" in sect_l or "замon" in sect_l:
                    err_type = "G/Verb"
                elif "келишик" in sect_l or "kelishik" in sect_l:
                    err_type = "G/Case"
                elif "morf" in sect_l or "2." in sect_l[:4]:
                    err_type = "M/Morphology"
                elif "синт" in sect_l or "sintak" in sect_l or "3." in sect_l[:4]:
                    err_type = "Synt/Structure"
                elif "apostrof" in sect_l or "4.1" in sect_l:
                    err_type = "S/Apostrophe"
                elif "h vs x" in sub.lower() or "h vs x" in section.lower():
                    err_type = "S/HvsX"
                elif "ismlar" in sub.lower() or "ismlar" in section.lower():
                    err_type = "Terminology"

                rule_pairs.append({
                    "wrong": wrong,
                    "correct": correct,
                    "error_type": err_type,
                    "context": section + (f" / {sub}" if sub else ""),
                    "source": "uzbek_til_qoidalari_md",
                })

        # Also extract grammar rules if the table has a "Qoida" or "Izoh" column
        qoida_idx = -1
        for i, h in enumerate(hdr):
            if "qoida" in h or "izoh" in h or "маъно" in h or "mazmun" in h:
                qoida_idx = i
                break
        if qoida_idx >= 0 and qoida_idx != xato_idx and qoida_idx != togri_idx:
            for row in t["rows"]:
                if len(row) <= qoida_idx:
                    continue
                rule = clean_cell(row[qoida_idx])
                if not rule or len(rule) < 10:
                    continue
                style_rules.append({
                    "description": rule,
                    "section": section,
                    "sub": sub,
                })

    return {"rule_pairs": rule_pairs, "style_rules": style_rules}


def import_to_db(pairs: list) -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Ensure sayqallash_rules has context + source columns
    for col, typ in (("context", "TEXT DEFAULT ''"), ("source", "TEXT DEFAULT ''"),
                      ("quality_flag", "TEXT DEFAULT 'unverified'")):
        try:
            cur.execute(f"ALTER TABLE sayqallash_rules ADD COLUMN {col} {typ}")
        except Exception:
            pass

    added = 0
    skipped = 0
    per_type = {}

    for p in pairs:
        wrong = p["wrong"]
        correct = p["correct"]
        err_type = p["error_type"]
        context = p["context"]
        source = p["source"]

        if not wrong or not correct or wrong == correct:
            skipped += 1
            continue

        try:
            cur.execute("""
                INSERT OR IGNORE INTO sayqallash_rules
                (wrong_form, correct_form, error_type, lang, source, context, frequency, quality_flag)
                VALUES (?, ?, ?, 'uz', ?, ?, 1, 'unverified')
            """, (wrong, correct, err_type, source, context))
            if cur.rowcount > 0:
                added += 1
                per_type[err_type] = per_type.get(err_type, 0) + 1
            else:
                skipped += 1
        except Exception as e:
            log.debug(f"insert fail {wrong}: {e}")
            skipped += 1

    conn.commit()
    conn.close()
    return {"added": added, "skipped": skipped, "per_type": per_type}


def main():
    if not MARKDOWN_FILE.exists():
        log.warning(f"File not found: {MARKDOWN_FILE}")
        return {"error": "file not found"}

    with open(MARKDOWN_FILE, encoding="utf-8") as f:
        text = f.read()

    log.info(f"Loaded {len(text)} chars, {text.count(chr(10))} lines")

    tables = parse_markdown_tables(text)
    log.info(f"Parsed {len(tables)} markdown tables")

    extracted = extract_pairs(tables)
    log.info(f"Extracted {len(extracted['rule_pairs'])} error pairs, {len(extracted['style_rules'])} grammar rules")

    result = import_to_db(extracted["rule_pairs"])
    result["grammar_rules_parsed"] = len(extracted["style_rules"])
    result["tables_processed"] = len(tables)
    log.info(f"Final: {result}")
    return result


if __name__ == "__main__":
    print(main())
