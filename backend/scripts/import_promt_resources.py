"""
Import ALL usable PROMT Expert NMT v23.2 resources from Qonun/1/:

  1. TMX (Basic_UZ_EN_RU.tmx) → translation_memory table
  2. Abbrs_uz.xml             → abbreviations (short_form, long_uz)
  3. Abbrs_en.xml             → abbreviations (short_form, long_en)
  4. Abbrs_ru.xml             → abbreviations (short_form, long_ru)
  5. Abbrs_Common.xml         → abbreviations (international)
  6. UZ_correction_rules.txt  → sayqallash_rules (regex-based)
  7. UZ_transliteration_rules → dual_script_rules table (official 2019)

All idempotent via INSERT OR IGNORE.
"""
import os
import re
import sqlite3
import logging
import xml.etree.ElementTree as ET

log = logging.getLogger("import_promt")

DB_PATH = os.getenv("DB_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pharma_editor.db"
))

# Paths relative to project root
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QONUN = os.path.join(_root, "Qonun", "1")
if not os.path.isdir(QONUN):
    # Railway: files may be at /app/Qonun/1
    QONUN = os.path.join("/app", "Qonun", "1")


def _ensure_schemas(cur):
    """Create tables if not exist."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS translation_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            src_lang TEXT NOT NULL,
            src_text TEXT NOT NULL,
            tgt_lang TEXT NOT NULL,
            tgt_text TEXT NOT NULL,
            domain TEXT DEFAULT 'general',
            quality_score REAL DEFAULT 1.0,
            source TEXT DEFAULT 'promt_v23',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(src_lang, tgt_lang, src_text)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tm_src ON translation_memory(src_lang, src_text)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tm_tgt ON translation_memory(tgt_lang)")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS abbreviations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_form TEXT UNIQUE NOT NULL,
            long_en TEXT, long_ru TEXT, long_uz TEXT,
            source_lang TEXT DEFAULT 'multi',
            user_id TEXT, text_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            modified_by_id TEXT, modified_at TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS dual_script_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            direction TEXT NOT NULL,
            source_char TEXT NOT NULL,
            target_char TEXT NOT NULL,
            priority INTEGER DEFAULT 0,
            notes TEXT,
            UNIQUE(direction, source_char)
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


# ────────────────────────────────────────────────
# 1. TMX Import
# ────────────────────────────────────────────────
def import_tmx(cur) -> dict:
    p = os.path.join(QONUN, "Uzb", "06_Online_Resources_NMT_NER_TTS", "Basic_UZ_EN_RU.tmx")
    if not os.path.exists(p):
        return {"tmx_error": "file not found", "path": p}
    tree = ET.parse(p)
    body = tree.find("body")
    added = 0
    for tu in body.findall("tu"):
        segs = {}
        for tuv in tu.findall("tuv"):
            lang = tuv.get("{http://www.w3.org/XML/1998/namespace}lang", "")
            seg = tuv.findtext("seg", "").strip()
            if lang and seg:
                segs[lang] = seg
        if "uz" not in segs:
            continue
        for tgt_lang in ("en", "ru"):
            if tgt_lang in segs:
                try:
                    cur.execute(
                        """INSERT OR IGNORE INTO translation_memory
                           (src_lang, src_text, tgt_lang, tgt_text, domain, source)
                           VALUES ('uz', ?, ?, ?, 'general', 'promt_v23_tmx')""",
                        (segs["uz"], tgt_lang, segs[tgt_lang]),
                    )
                    added += cur.rowcount
                except Exception:
                    pass
        # Also add en→ru, ru→en pairs
        if "en" in segs and "ru" in segs:
            try:
                cur.execute(
                    """INSERT OR IGNORE INTO translation_memory
                       (src_lang, src_text, tgt_lang, tgt_text, domain, source)
                       VALUES ('en', ?, 'ru', ?, 'general', 'promt_v23_tmx')""",
                    (segs["en"], segs["ru"]),
                )
                added += cur.rowcount
                cur.execute(
                    """INSERT OR IGNORE INTO translation_memory
                       (src_lang, src_text, tgt_lang, tgt_text, domain, source)
                       VALUES ('ru', ?, 'en', ?, 'general', 'promt_v23_tmx')""",
                    (segs["ru"], segs["en"]),
                )
                added += cur.rowcount
            except Exception:
                pass
    return {"tmx_segments_added": added}


# ────────────────────────────────────────────────
# 2. Abbreviations XML import
# ────────────────────────────────────────────────
def _parse_abbrs_xml(path: str) -> list:
    if not os.path.exists(path):
        return []
    tree = ET.parse(path)
    root = tree.getroot()
    return [item.get("value", "").strip().rstrip(".") for item in root.findall("item") if item.get("value")]


def import_abbreviations(cur) -> dict:
    files = {
        "uz": os.path.join(QONUN, "Uzb", "02_Abbreviations_UZ", "Abbrs_uz.xml"),
        "en": os.path.join(QONUN, "03_Rules_and_Customization", "Abbreviations", "Abbrs_en.xml"),
        "ru": os.path.join(QONUN, "03_Rules_and_Customization", "Abbreviations", "Abbrs_ru.xml"),
        "common": os.path.join(QONUN, "03_Rules_and_Customization", "Abbreviations", "Abbrs_Common.xml"),
    }
    stats = {}
    for lang, path in files.items():
        abbrs = _parse_abbrs_xml(path)
        added = 0
        for a in abbrs:
            if not a or len(a) > 50:
                continue
            try:
                # Try insert; if exists, update the lang column
                cur.execute(
                    "INSERT OR IGNORE INTO abbreviations (short_form, source_lang, status) VALUES (?, ?, 'active')",
                    (a, lang),
                )
                if cur.rowcount > 0:
                    added += 1
                # Always update long_* column if applicable
                if lang == "uz":
                    cur.execute("UPDATE abbreviations SET long_uz = COALESCE(NULLIF(long_uz,''), ?) WHERE short_form = ?", (a, a))
                elif lang == "en":
                    cur.execute("UPDATE abbreviations SET long_en = COALESCE(NULLIF(long_en,''), ?) WHERE short_form = ?", (a, a))
                elif lang == "ru":
                    cur.execute("UPDATE abbreviations SET long_ru = COALESCE(NULLIF(long_ru,''), ?) WHERE short_form = ?", (a, a))
            except Exception:
                pass
        stats[f"abbrs_{lang}"] = {"total": len(abbrs), "new": added}
    return stats


# ────────────────────────────────────────────────
# 3. Correction rules → sayqallash_rules
# ────────────────────────────────────────────────
def import_correction_rules(cur) -> dict:
    p = os.path.join(QONUN, "Uzb", "05_Correction_Rules_UZ", "UZ_correction_rules.txt")
    if not os.path.exists(p):
        return {"correction_error": "file not found"}
    added = 0
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Format: [CATEGORY] pattern → replacement
            m = re.match(r'\[(\w+)\]\s*(.+?)\s*[→→]\s*(.+)', line)
            if not m:
                continue
            category, wrong, correct = m.group(1), m.group(2).strip(), m.group(3).strip()
            if not wrong or not correct:
                continue
            try:
                cur.execute(
                    """INSERT OR IGNORE INTO sayqallash_rules
                       (wrong_form, correct_form, error_type, lang, source, context)
                       VALUES (?, ?, ?, 'uz', 'promt_correction_rules', ?)""",
                    (wrong, correct, category, f"PROMT UZ_{category}"),
                )
                added += cur.rowcount
            except Exception:
                pass
    return {"correction_rules_added": added}


# ────────────────────────────────────────────────
# 4. Transliteration rules → dual_script_rules
# ────────────────────────────────────────────────
def import_transliteration_rules(cur) -> dict:
    p = os.path.join(QONUN, "Uzb", "04_Transliteration_Rules_UZ", "UZ_transliteration_rules.txt")
    if not os.path.exists(p):
        return {"translit_error": "file not found"}
    added = 0
    direction = "cyr2lat"
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                # detect direction switch
                if "ЛОТИН → КИРИЛЛ" in line or "Latin to Cyrillic" in line:
                    direction = "lat2cyr"
                elif "КИРИЛЛ → ЛОТИН" in line or "Cyrillic to Latin" in line:
                    direction = "cyr2lat"
                continue
            # Format: source → target
            parts = re.split(r'\s*[→→]\s*', line, maxsplit=1)
            if len(parts) != 2:
                continue
            src, tgt = parts[0].strip(), parts[1].strip()
            if not src or not tgt:
                continue
            # Priority: longer source chars first (multi-char like Ё→Yo)
            priority = len(src) * 10
            try:
                cur.execute(
                    """INSERT OR IGNORE INTO dual_script_rules
                       (direction, source_char, target_char, priority, notes)
                       VALUES (?, ?, ?, ?, 'promt_2019_official')""",
                    (direction, src, tgt, priority),
                )
                added += cur.rowcount
            except Exception:
                pass
    return {"translit_rules_added": added}


# ────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────
def main() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    _ensure_schemas(cur)

    result = {}
    result.update(import_tmx(cur))
    result.update(import_abbreviations(cur))
    result.update(import_correction_rules(cur))
    result.update(import_transliteration_rules(cur))

    conn.commit()

    # Final counts
    for tbl in ("translation_memory", "abbreviations", "dual_script_rules"):
        try:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            result[f"total_{tbl}"] = cur.fetchone()[0]
        except Exception:
            pass

    conn.close()
    log.info(f"import_promt_resources: {result}")
    return result


if __name__ == "__main__":
    import json
    print(json.dumps(main(), ensure_ascii=False, indent=2))
