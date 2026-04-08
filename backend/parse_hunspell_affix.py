"""
Parse Hunspell .aff file and import SFX/PFX rules into `uzbek_affix_rules` table.

Source: /app/data/hunspell/uz_UZ.aff (u2b3k/uz-hunspell)
"""
import os
import sys
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[affix_parser] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))
HUNSPELL_DIR = os.getenv("HUNSPELL_V2_PATH", "/app/data/hunspell")


def parse_aff_file(path: str, script: str = "latin"):
    """
    Parse Hunspell .aff file.
    Returns list of rules: [{flag, type, strip, affix, condition, script}]
    """
    if not os.path.exists(path):
        log.warning(f"File not found: {path}")
        return []

    rules = []
    current_flag = None
    current_type = None

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            # Header: SFX FLAG Y count  OR  PFX FLAG Y count
            if parts[0] in ("SFX", "PFX") and len(parts) == 4 and parts[2] in ("Y", "N"):
                current_type = parts[0]
                current_flag = parts[1]
                continue

            # Rule: SFX FLAG strip affix condition
            if parts[0] in ("SFX", "PFX") and len(parts) >= 5 and parts[1] == current_flag:
                strip = parts[2] if parts[2] != "0" else ""
                affix = parts[3] if parts[3] != "0" else ""
                condition = parts[4]
                # Extract morphological tags (after condition)
                morph_tags = " ".join(parts[5:]) if len(parts) > 5 else ""

                rules.append({
                    "flag": current_flag,
                    "type": current_type,
                    "strip": strip,
                    "affix": affix,
                    "condition": condition,
                    "morph_tags": morph_tags,
                    "script": script,
                })

    return rules


def categorize_rule(rule: dict) -> str:
    """Guess morpheme category from flag + affix."""
    flag = rule.get("flag", "").upper()
    affix = rule.get("affix", "").lower()
    morph = rule.get("morph_tags", "").lower()

    # Heuristics based on Uzbek morphology
    if "lar" in affix or "lar" in morph:
        return "plural"
    if any(p in affix for p in ["ga", "ni", "da", "dan"]):
        return "case"
    if any(p in affix for p in ["im", "ing", "i", "imiz", "ingiz", "lari"]):
        return "possessive"
    if "lik" in affix or "chi" in affix:
        return "derivation"
    if "di" in affix or "yapti" in affix or "moqda" in affix:
        return "tense"
    if flag.startswith("V") or "verb" in morph:
        return "verb"
    if flag.startswith("N") or "noun" in morph:
        return "noun"
    if flag.startswith("A") or "adj" in morph:
        return "adjective"
    return "unknown"


def import_rules():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS uzbek_affix_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        flag TEXT,
        type TEXT,
        strip TEXT,
        affix TEXT,
        condition TEXT,
        morph_tags TEXT,
        morpheme_slot TEXT,
        script TEXT,
        source TEXT DEFAULT 'u2b3k_uzbek_hunspell',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(flag, type, strip, affix, condition, script)
    )
    ''')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_affix_flag ON uzbek_affix_rules(flag)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_affix_slot ON uzbek_affix_rules(morpheme_slot)')

    all_rules = []
    for fname, script in [("uz_UZ.aff", "latin"), ("uz_UZ_Cyrl.aff", "cyrillic")]:
        path = os.path.join(HUNSPELL_DIR, fname)
        rules = parse_aff_file(path, script=script)
        log.info(f"Parsed {fname}: {len(rules)} rules")
        all_rules.extend(rules)

    inserted = 0
    for r in all_rules:
        try:
            r["morpheme_slot"] = categorize_rule(r)
            cur.execute("""
                INSERT OR IGNORE INTO uzbek_affix_rules
                    (flag, type, strip, affix, condition, morph_tags, morpheme_slot, script)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r["flag"], r["type"], r["strip"], r["affix"],
                r["condition"], r["morph_tags"], r["morpheme_slot"], r["script"]
            ))
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            log.warning(f"Skip {r}: {e}")

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM uzbek_affix_rules")
    total = cur.fetchone()[0]
    conn.close()
    log.info(f"Imported {inserted} new affix rules. Total: {total}")
    return {"inserted": inserted, "total": total}


def main():
    if not os.path.exists(HUNSPELL_DIR):
        log.warning(f"Hunspell dir not found: {HUNSPELL_DIR}")
        return 0
    result = import_rules()
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
