"""
MD файллардан фармацевтик терминлар чиқариш ва платформага юклаш.

Қадамлар:
1. Qonun/5/ папкасидаги MD файлларни ўқиш
2. Фарм терминларни regex/NLP билан аниқлаш
3. Янги терминларни annotated_words, sayqallash_rules, translation_memory га юклаш
4. Статистика ва ҳисобот

Фойдаланиш:
  python scripts/extract_pharma_terms_from_md.py
  python scripts/extract_pharma_terms_from_md.py --source DF_uzb   # фақат ўзбек ДФ
  python scripts/extract_pharma_terms_from_md.py --dry-run          # фақат ҳисобот
"""
import os
import re
import sys
import json
import sqlite3
import logging
import argparse
from pathlib import Path
from collections import Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger("extract_terms")

BASE = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
MD_DIR = BASE / "Qonun" / "5"
DB_PATH = os.getenv("DB_PATH", str(BASE / "backend" / "pharma_editor.db"))

# Фармацевтик терминлар regex патернлари
PHARMA_PATTERNS = [
    # Дори номлари (лотин, бош ҳарф)
    r'\b([A-Z][a-z]{3,}(?:um|in|ol|il|ne|te|de|se|le|ide|ine|one|ase|ate|ose|ene|yde))\b',
    # Доза патернлари
    r'\b(\d+[\.,]?\d*)\s*(мг|мл|мкг|г|кг|нг|МЕ|ЕД|mg|ml|mcg|g|kg|ng|IU|U)\b',
    # Фармакопея стандарт терминлари
    r'\b(субстанция|таблетка|суспензия|эритма|инъекция|капсула|мазь|крем|гель|порошок|сироп|раствор|суппозиторий|линимент|настойка|экстракт)\b',
    # Ўзбекча фарм терминлар
    r'\b(дори|субстанция|таблетка|суспензия|эритма|инъекция|капсула|малҳам|крем|гель|кукун|сироп|эритма|суппозиторий|настойка|экстракт|дамлама|қайнатма)\b',
    # Усуллар
    r'\b(HPLC|GC|UV|IR|NMR|TLC|DSC|XRPD|MS|LC-MS|GC-MS|SDS-PAGE)\b',
    # ATC кодлар
    r'\b([A-Z]\d{2}[A-Z]{2}\d{2})\b',
    # INN терминлар (кичик ҳарф, лотин суффикслар)
    r'\b([a-z]{4,}(?:pril|sartan|olol|dipine|statin|cillin|mycin|cycline|azole|conazole|prazole|gliptin|tinib|zumab|ximab))\b',
]

# Ўзбек-рус жуфтлик патерни (параллел матнлар учун)
UZ_RU_TERM_PAIRS = []


def extract_terms_from_text(text: str, source: str = "unknown") -> dict:
    """Extract pharmaceutical terms from text."""
    terms = {
        "drug_names": [],      # Дори номлари
        "doses": [],           # Доза ифодалари
        "methods": [],         # Аналитик усуллар
        "uz_terms": [],        # Ўзбекча фарм терминлар
        "ru_terms": [],        # Русча фарм терминлар
        "atc_codes": [],       # ATC кодлар
        "inn_terms": [],       # INN терминлар
        "unknown_pharma": [],  # Аниқланмаган фарм сўзлар
    }

    # Drug names (Latin, capitalized)
    for m in re.finditer(PHARMA_PATTERNS[0], text):
        terms["drug_names"].append(m.group(1))

    # Doses
    for m in re.finditer(PHARMA_PATTERNS[1], text):
        terms["doses"].append(f"{m.group(1)} {m.group(2)}")

    # Russian pharma terms
    for m in re.finditer(PHARMA_PATTERNS[2], text, re.IGNORECASE):
        terms["ru_terms"].append(m.group(1).lower())

    # Uzbek pharma terms
    for m in re.finditer(PHARMA_PATTERNS[3], text, re.IGNORECASE):
        terms["uz_terms"].append(m.group(1).lower())

    # Methods
    for m in re.finditer(PHARMA_PATTERNS[4], text):
        terms["methods"].append(m.group(1))

    # ATC codes
    for m in re.finditer(PHARMA_PATTERNS[5], text):
        terms["atc_codes"].append(m.group(1))

    # INN terms
    for m in re.finditer(PHARMA_PATTERNS[6], text):
        terms["inn_terms"].append(m.group(1).lower())

    return terms


def load_existing_terms(conn: sqlite3.Connection) -> set:
    """Load existing terms from DB to avoid duplicates."""
    existing = set()
    cur = conn.cursor()
    for table, col in [
        ("annotated_words", "word"),
        ("drugs", "inn"),
        ("drugs", "brand_name"),
        ("medical_terms", "term"),
    ]:
        try:
            cur.execute(f"SELECT DISTINCT LOWER({col}) FROM {table} WHERE {col} IS NOT NULL")
            for row in cur.fetchall():
                if row[0]:
                    existing.add(row[0].strip().lower())
        except Exception:
            pass
    return existing


def seed_terms_to_db(conn: sqlite3.Connection, all_terms: dict, dry_run: bool = False):
    """Seed extracted terms into database tables."""
    cur = conn.cursor()
    existing = load_existing_terms(conn)
    stats = {"added_whitelist": 0, "added_rules": 0, "skipped": 0}

    # 1. Drug names → correct_set (whitelist via annotated_words)
    drug_counts = Counter(all_terms.get("drug_names", []))
    for drug, freq in drug_counts.most_common(500):
        if drug.lower() in existing:
            stats["skipped"] += 1
            continue
        if not dry_run:
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO annotated_words (word, frequency, lang, source, status)
                    VALUES (?, ?, 'en', 'pharma_md_extract', 'active')
                """, (drug, freq))
                if cur.rowcount > 0:
                    stats["added_whitelist"] += 1
                    existing.add(drug.lower())
            except Exception:
                pass

    # 2. Uzbek pharma terms → whitelist
    uz_counts = Counter(all_terms.get("uz_terms", []))
    for term, freq in uz_counts.most_common(500):
        if term in existing:
            stats["skipped"] += 1
            continue
        if not dry_run:
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO annotated_words (word, frequency, lang, source, status)
                    VALUES (?, ?, 'uz', 'pharma_md_extract', 'active')
                """, (term, freq))
                if cur.rowcount > 0:
                    stats["added_whitelist"] += 1
                    existing.add(term)
            except Exception:
                pass

    # 3. Russian pharma terms → whitelist
    ru_counts = Counter(all_terms.get("ru_terms", []))
    for term, freq in ru_counts.most_common(500):
        if term in existing:
            stats["skipped"] += 1
            continue
        if not dry_run:
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO annotated_words (word, frequency, lang, source, status)
                    VALUES (?, ?, 'ru', 'pharma_md_extract', 'active')
                """, (term, freq))
                if cur.rowcount > 0:
                    stats["added_whitelist"] += 1
                    existing.add(term)
            except Exception:
                pass

    # 4. INN terms → drugs table
    inn_counts = Counter(all_terms.get("inn_terms", []))
    for inn, freq in inn_counts.most_common(200):
        if inn in existing:
            continue
        if not dry_run:
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO drugs (inn, source)
                    VALUES (?, 'pharma_md_extract')
                """, (inn,))
                if cur.rowcount > 0:
                    stats["added_whitelist"] += 1
                    existing.add(inn)
            except Exception:
                pass

    # 5. Methods → scientific whitelist (annotated_words)
    method_counts = Counter(all_terms.get("methods", []))
    for method, freq in method_counts.most_common(50):
        if method.lower() in existing:
            continue
        if not dry_run:
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO annotated_words (word, frequency, lang, source, status)
                    VALUES (?, ?, 'en', 'pharma_md_methods', 'active')
                """, (method, freq))
                if cur.rowcount > 0:
                    stats["added_whitelist"] += 1
            except Exception:
                pass

    if not dry_run:
        conn.commit()

    return stats


def main():
    parser = argparse.ArgumentParser(description="MD → фарм терминлар чиқариш")
    parser.add_argument("--source", default="all", help="DF_uzb, DF_rus, EP_9.0, all")
    parser.add_argument("--dry-run", action="store_true", help="Фақат ҳисобот, DB ўзгармайди")
    args = parser.parse_args()

    if not MD_DIR.exists():
        log.error(f"MD папка топилмади: {MD_DIR}")
        return

    # Collect all terms
    all_terms = {
        "drug_names": [], "doses": [], "methods": [],
        "uz_terms": [], "ru_terms": [], "atc_codes": [],
        "inn_terms": [], "unknown_pharma": [],
    }

    md_files = []
    for subdir in MD_DIR.iterdir():
        if args.source != "all" and subdir.name != args.source:
            continue
        if subdir.is_dir():
            md_files.extend(subdir.rglob("*.md"))

    log.info(f"MD файллар: {len(md_files)}")

    for md_file in sorted(md_files):
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
            terms = extract_terms_from_text(text, source=str(md_file))
            for key in all_terms:
                all_terms[key].extend(terms.get(key, []))
        except Exception as e:
            log.warning(f"Хато: {md_file.name}: {e}")

    # Statistics
    log.info(f"\n=== ЧИҚАРИЛГАН ТЕРМИНЛАР ===")
    for key, items in all_terms.items():
        unique = len(set(items))
        log.info(f"  {key}: {len(items)} жами, {unique} уникал")

    # Top terms
    log.info(f"\n=== ТОП ДОРИ НОМЛАРИ ===")
    for term, cnt in Counter(all_terms["drug_names"]).most_common(20):
        log.info(f"  {term}: {cnt}")

    log.info(f"\n=== ТОП INN ТЕРМИНЛАР ===")
    for term, cnt in Counter(all_terms["inn_terms"]).most_common(20):
        log.info(f"  {term}: {cnt}")

    log.info(f"\n=== ТОП УСУЛЛАР ===")
    for term, cnt in Counter(all_terms["methods"]).most_common(15):
        log.info(f"  {term}: {cnt}")

    # Seed to DB
    if not args.dry_run:
        conn = sqlite3.connect(DB_PATH)
        stats = seed_terms_to_db(conn, all_terms, dry_run=False)
        conn.close()
        log.info(f"\n=== DB НАТИЖА ===")
        log.info(f"  Whitelist'га қўшилди: {stats['added_whitelist']}")
        log.info(f"  Ўтказиб юборилди: {stats['skipped']}")
    else:
        log.info(f"\n[DRY RUN] DB ўзгармади")


if __name__ == "__main__":
    main()
