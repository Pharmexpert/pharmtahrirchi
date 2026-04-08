"""
Seed expanded style_rules table with ~60 USP/Ph.Eur./ICH/WHO rules.
Idempotent — skips existing rule_ids.
"""
import os
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[style_seed] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))

RULES = [
    # ───── SI birlik va son (USP General Notices 8.140) ─────
    ("STYLE-SI-001", "format", "Сон ва SI бирлик орасида битта бўшлиқ", r"(\d+)(mg|g|kg|ml|l|μg|mcg|μl|mcl|IU|МЕ)\b", r"\1 \2",
     "must", "500mg → 500 mg", "USP <8.140>", "https://www.uspnf.com/general-notices"),
    ("STYLE-SI-002", "format", "% белгиси сон билан ёпишиб ёзилмайди", r"(\d+(?:\.\d+)?)(%)", r"\1 \2",
     "should", "5% → 5 %", "SI", ""),
    ("STYLE-SI-003", "format", "°C ва °F — ° билан ёпишиб ёзилиши керак", r"(\d+)\s+°", r"\1°",
     "should", "25 °C → 25°C", "SI", ""),
    ("STYLE-SI-004", "format", "m² ва m³ — superscript форматида", "", "", "may", "m2 → m²", "SI", ""),

    # ───── Sonlar formati ─────
    ("STYLE-NUM-001", "format", "Минг ажраткичи — қатъий пробел (space)", "", "", "should", "1000 → 1 000", "SI/EU", ""),
    ("STYLE-NUM-002", "format", "Ўнли каср — EU'да vergul, USA'да nuqta", "", "", "may", "0.5 vs 0,5", "regional", ""),
    ("STYLE-NUM-003", "format", "Salbiy диапазон тире орасида бўшлиқсиз", r"(\d+)\s*-\s*(\d+)", r"\1–\2",
     "should", "5 - 10 → 5–10", "general", ""),

    # ───── ATC (WHO ATC/DDD Index) ─────
    ("STYLE-ATC-001", "format", "ATC код формати: 1 ҳарф + 2 рақам + 2 ҳарф + 2 рақам", r"^[A-Z]\d{2}[A-Z]{2}\d{2}$",
     "{code}", "must", "N02BE01", "WHO ATC", "https://www.whocc.no/atc_ddd_index/"),
    ("STYLE-ATC-002", "format", "ATC ҳарфлар бош ҳарфда бўлиши шарт", r"[a-z]\d{2}[a-z]{2}\d{2}",
     "Uppercase ATC", "must", "n02be01 → N02BE01", "WHO ATC", ""),

    # ───── INN (WHO) ─────
    ("STYLE-INN-001", "abbreviation", "INN биринчи марта ишлатилганда тўлиқ номи кўрсатилиши", "", "Full INN first use",
     "should", "Paracetamol (PCT), later PCT", "WHO INN", "https://www.who.int/teams/health-product-policy-and-standards/inn"),
    ("STYLE-INN-002", "terminology", "INN номлар инглиз тилида курсивда ёзилиши", "", "Italic INN",
     "may", "*paracetamolum*", "Ph.Eur.", ""),

    # ───── Dosage form (Ph.Eur. General) ─────
    ("STYLE-DOSE-001", "terminology", "Tablet → 'Таблетка', не 'pilyus'", r"\bpilyus\b", "таблетка",
     "should", "pilyus → таблетка", "Ph.Eur.", ""),
    ("STYLE-DOSE-002", "terminology", "Capsule → 'Капсула', kalki 'sumka'", r"\bsumka\b", "капсула",
     "should", "сумка → капсула", "Ph.Eur.", ""),
    ("STYLE-DOSE-003", "terminology", "Injection → 'Ин'екция', 'ukol' emas", r"\bukol\b", "инъекция",
     "should", "укол → инъекция", "Ph.Eur.", ""),

    # ───── Qisqartmalar umumiy ─────
    ("STYLE-ABBR-001", "abbreviation", "GMP — ҳарф бошда тўлиқ ёзилсин", "", "Good Manufacturing Practice (GMP)",
     "should", "GMP → Good Manufacturing Practice (GMP)", "ICH E6", ""),
    ("STYLE-ABBR-002", "abbreviation", "HPLC — биринчи марта тўлиқ", "", "High Performance Liquid Chromatography (HPLC)",
     "should", "HPLC → HPLC (High Performance...)", "Ph.Eur. 2.2.29", ""),
    ("STYLE-ABBR-003", "abbreviation", "USP — U.S. Pharmacopeia", "", "United States Pharmacopeia (USP)",
     "may", "USP → USP (United States Pharmacopeia)", "USP General Notices", ""),
    ("STYLE-ABBR-004", "abbreviation", "QC → Quality Control тўлиқ", "", "Quality Control (QC)",
     "should", "QC → Quality Control (QC)", "ICH Q10", ""),
    ("STYLE-ABBR-005", "abbreviation", "QA → Quality Assurance", "", "Quality Assurance (QA)",
     "should", "QA → Quality Assurance (QA)", "ICH Q10", ""),

    # ───── Punctuation ─────
    ("STYLE-PUNCT-001", "punctuation", "Гап охирида нуқта бўлиши керак", r"[^.!?\"')\]]\s*$", "Add period",
     "should", "матн → матн.", "general", ""),
    ("STYLE-PUNCT-002", "punctuation", "Иккита бўшлиқ бирга ёзилмайди", r"  +", " ",
     "must", "ишла  ди → ишлади", "general", ""),
    ("STYLE-PUNCT-003", "punctuation", "Вергулдан кейин бўшлиқ", r",(\S)", r", \1",
     "must", "а,б → а, б", "general", ""),
    ("STYLE-PUNCT-004", "punctuation", "Нуқтадан кейин бўшлиқ (гап охирида)", r"\.([A-Zа-яЎўқғҳА-Я])", r". \1",
     "must", "Бир.Икки → Бир. Икки", "general", ""),
    ("STYLE-PUNCT-005", "punctuation", "Оралиқ тире — em-dash ( — )", r" - ", " — ",
     "should", "матн - матн → матн — матн", "typography", ""),
    ("STYLE-PUNCT-006", "punctuation", "Илова қавслардан кейин қавс olдин бўшлиқ", r"(\S)\(", r"\1 (",
     "should", "сўз(изоҳ) → сўз (изоҳ)", "general", ""),

    # ───── Клиник тадқиқот (ICH E6 GCP) ─────
    ("STYLE-GCP-001", "terminology", "Investigator → 'Тадқиқотчи', не 'иследуютчи'", r"\bиследуютчи\b", "тадқиқотчи",
     "should", "иследуютчи → тадқиқотчи", "ICH E6", ""),
    ("STYLE-GCP-002", "terminology", "Informed consent → 'розилик баённомаси'", "", "",
     "should", "", "ICH E6 §4.8", ""),
    ("STYLE-GCP-003", "terminology", "Adverse event → 'нохуш воқеа'", "", "",
     "should", "", "ICH E2A", ""),
    ("STYLE-GCP-004", "terminology", "Serious AE → 'оғир нохуш воқеа'", "", "",
     "should", "", "ICH E2A", ""),

    # ───── Ph.Eur. atamalar ─────
    ("STYLE-PHE-001", "terminology", "Reference standard → 'стандарт намуна'", "", "",
     "should", "reference standard → ФСН", "Ph.Eur. 5.12", ""),
    ("STYLE-PHE-002", "terminology", "Impurity → 'аралашма'", r"\bimpurit[a-z]*\b", "аралашма",
     "should", "", "Ph.Eur. 5.10", ""),
    ("STYLE-PHE-003", "terminology", "Dissolution → 'эрувчанлик'", r"\bdissolyutsiya\b", "эрувчанлик",
     "should", "", "Ph.Eur. 2.9.3", ""),
    ("STYLE-PHE-004", "terminology", "Loss on drying → 'қуритишдаги оғирлик йўқолиши'", "", "",
     "may", "", "Ph.Eur. 2.2.32", ""),

    # ───── Спецификация (Statistics) ─────
    ("STYLE-STAT-001", "format", "Statistika: n, p, r — italic", "", "",
     "may", "n=10 → *n*=10", "Statistics", ""),
    ("STYLE-STAT-002", "format", "p-value — қатъий format p < 0.05", r"p\s*[<>=]+\s*0\.", r"p \1 0.",
     "may", "p<0.05 → p < 0.05", "Statistics", ""),
    ("STYLE-STAT-003", "format", "Percent range: X%-Y% — дан-гача", r"(\d+)%-(\d+)%", r"\1% - \2%",
     "should", "5%-10% → 5% - 10%", "Statistics", ""),

    # ───── Bosh harflar & Title case ─────
    ("STYLE-CAP-001", "format", "Жадвал сарлавҳаси бош ҳарф билан", "", "",
     "should", "", "USP Nomenclature", ""),
    ("STYLE-CAP-002", "format", "Боб номи title case", "", "",
     "may", "", "Ph.Eur.", ""),
    ("STYLE-CAP-003", "format", "Proper noun (Europe, WHO) бош ҳарф", "", "",
     "must", "europe → Europe", "general", ""),

    # ───── Stabillik (ICH Q1A) ─────
    ("STYLE-STB-001", "terminology", "Shelf life → 'яроқлилик муддати'", r"\bshelf\s+life\b", "яроқлилик муддати",
     "should", "", "ICH Q1A", ""),
    ("STYLE-STB-002", "terminology", "Storage conditions → 'сақлаш шартлари'", "", "",
     "should", "", "ICH Q1A", ""),
    ("STYLE-STB-003", "terminology", "Long-term testing → 'узоқ муддатли тест'", "", "",
     "may", "", "ICH Q1A §2.1.7.1", ""),

    # ───── Taqsimlash va oshirish ─────
    ("STYLE-DILU-001", "terminology", "Dilution → 'суюлтириш'", r"\bdilyutsiya\b", "суюлтириш",
     "should", "", "Ph.Eur.", ""),
    ("STYLE-DILU-002", "terminology", "Mixture → 'аралашма'", r"\bmikstura\b", "аралашма",
     "may", "микстура → аралашма", "Ph.Eur.", ""),

    # ───── Гramматик (Formal writing) ─────
    ("STYLE-GRAM-001", "format", "Расмий услубда 'мен' — 'биз' орқали", "", "",
     "may", "мен ёзяпман → биз ёзяпмиз", "academic", ""),
    ("STYLE-GRAM-002", "format", "Паsıва шакл тавсия қилинади", "", "",
     "may", "", "academic", ""),

    # ───── Citation (USP/Ph.Eur. references) ─────
    ("STYLE-REF-001", "format", "USP citation формати: USP <1225>", r"USP\s+\d+", "USP <{number}>",
     "should", "USP 1225 → USP <1225>", "USP", ""),
    ("STYLE-REF-002", "format", "Ph.Eur. citation формати: Ph.Eur. 2.2.3", r"European Pharmacopoeia", "Ph.Eur.",
     "should", "", "Ph.Eur.", ""),
    ("STYLE-REF-003", "format", "ICH ҳужжати: ICH E6(R2)", r"ICH\s+[A-Z]\d+", "ICH {code}",
     "should", "", "ICH", ""),

    # ───── Boylar va nomenclature ─────
    ("STYLE-NOM-001", "format", "IUPAC formulalar — коди билан", "", "",
     "may", "", "IUPAC", ""),
    ("STYLE-NOM-002", "format", "CAS номлари — 123-45-6 формат", r"\d{2,7}-\d{2}-\d", "{cas}",
     "should", "", "CAS", ""),
    ("STYLE-NOM-003", "format", "Molekulyar formula — subscript", "", "",
     "may", "H2O → H₂O", "chemistry", ""),

    # ───── Common Uzbek-specific ─────
    ("STYLE-UZ-001", "terminology", "Препарат → 'препарат' ёки 'дори воситаси'", "", "",
     "may", "", "Uzbek pharma", ""),
    ("STYLE-UZ-002", "terminology", "Raw material → 'хом ашё'", "", "",
     "should", "", "Uzbek Ph.", ""),
    ("STYLE-UZ-003", "punctuation", "O'/o' apostrofi — ʻ (U+02BB)", r"([OoGg])'", "{ch}ʻ",
     "may", "O'zbek → Oʻzbek", "typography", ""),
]


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Ensure schema exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS style_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT UNIQUE,
            category TEXT,
            description TEXT,
            pattern TEXT,
            suggestion TEXT,
            severity TEXT DEFAULT 'should',
            examples TEXT,
            source TEXT,
            lang TEXT DEFAULT 'uz',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add source_ref + source_url columns if missing
    for col, typ in (("source_ref", "TEXT DEFAULT ''"), ("source_url", "TEXT DEFAULT ''")):
        try:
            cur.execute(f"ALTER TABLE style_rules ADD COLUMN {col} {typ}")
        except Exception:
            pass

    added = 0
    updated_urls = 0
    for rule in RULES:
        rule_id, category, description, pattern, suggestion, severity, examples, source, *rest = rule
        source_url = rest[0] if rest else ""
        try:
            cur.execute("""
                INSERT OR IGNORE INTO style_rules
                (rule_id, category, description, pattern, suggestion, severity, examples, source, source_ref, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (rule_id, category, description, pattern, suggestion, severity, examples, source, source, source_url))
            if cur.rowcount > 0:
                added += 1
            elif source_url:
                cur.execute("UPDATE style_rules SET source_url = ? WHERE rule_id = ? AND (source_url IS NULL OR source_url = '')",
                            (source_url, rule_id))
                if cur.rowcount > 0:
                    updated_urls += 1
        except Exception as e:
            log.debug(f"{rule_id}: {e}")

    cur.execute("SELECT COUNT(*) FROM style_rules")
    total = cur.fetchone()[0]
    conn.commit()
    conn.close()

    result = {"added": added, "urls_updated": updated_urls, "total_in_db": total}
    log.info(result)
    return result


if __name__ == "__main__":
    print(main())
