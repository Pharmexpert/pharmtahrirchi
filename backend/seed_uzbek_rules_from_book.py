"""
Extract Uzbek language rules from "Ona tili" textbook (M.Hamroyev et al., 2007)
and seed them into the Sayqallash + canonical_rules databases.

Source: 276 pages, ~593K characters covering:
  - Phonetics (sounds, syllables, stress)
  - Lexicology (synonyms, antonyms, polysemy)
  - Morphology (parts of speech, suffixes)
  - Syntax (sentences, word order)
  - Stylistics (5 styles)
  - Punctuation
"""
import json
import re
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))
PDF_JSON = "/tmp/ona_tili.json"


def load_pages():
    # First try bundled text file
    text_file = os.path.join(os.path.dirname(__file__), "ona_tili_text.txt")
    if os.path.exists(text_file):
        with open(text_file, encoding="utf-8") as f:
            full = f.read()
        chunks = full.split("[PAGE_BREAK]")
        return [{"page": i + 1, "text": c} for i, c in enumerate(chunks) if c.strip()]
    if os.path.exists(PDF_JSON):
        with open(PDF_JSON, encoding="utf-8") as f:
            return json.load(f)
    try:
        from pypdf import PdfReader
        reader = PdfReader(os.path.expanduser("~/Desktop/Ona tili (M.Hamroyev, D.Muhamedova va b.).pdf"))
        return [{"page": i + 1, "text": p.extract_text() or ""} for i, p in enumerate(reader.pages)]
    except Exception as e:
        print(f"Cannot read source: {e}")
        return []


def extract_rules(pages):
    """Extract spelling/grammar/punctuation rules from book text."""
    rules = []

    full_text = "\n".join(p["text"] for p in pages)

    # 1. Find numbered list patterns (1. ... 2. ... 3. ...) which often define rules
    # 2. Find "deyiladi" / "ataladi" / "hisoblanadi" / "qoidasi" markers
    # 3. Find example pairs like "X>Y" or "X-Y"

    # Pattern 1: phonetic alternations (e.g., "kechdi>keshti")
    alt_pattern = re.compile(r"\b([a-zA-ZёЁўғқҳЎҒҚҲ\u02bb\u02bc\u2019']+)\s*[>→]\s*([a-zA-ZёЁўғқҳЎҒҚҲ\u02bb\u02bc\u2019']+)\b")
    for m in alt_pattern.finditer(full_text):
        wrong = m.group(1).strip()
        correct = m.group(2).strip()
        if 2 < len(wrong) < 30 and 2 < len(correct) < 30 and wrong != correct:
            rules.append({
                "wrong_form": wrong,
                "correct_form": correct,
                "error_type": "S/Phonetic",
                "source": "ona_tili_book_2007",
                "lang": "uz",
                "context": "phonetic alternation",
            })

    # Pattern 2: Cyrillic equivalents from rules ("ё" "э" "ў" mentions)
    # Pattern 3: Common spelling errors mentioned

    # Pattern 4: Looking for definitions: "X — bu Y deyiladi"
    def_pattern = re.compile(r"([A-ZА-ЯЎҒҚҲ][a-zA-ZёЁўғқҳЎҒҚҲ\u02bb\u02bc\u2019\' ]{4,40})\s+deyiladi[\.\,]")
    definitions = []
    for m in def_pattern.finditer(full_text):
        defn = m.group(1).strip()
        if len(defn) < 50:
            definitions.append(defn)

    # Pattern 5: Suffix rules — find -<suffix> patterns
    suffix_pattern = re.compile(r"-([a-z\u02bb\u2019']{1,5})\s+(?:qo'shimchasi|affiksi|qo'shimcha)")
    suffixes = set()
    for m in suffix_pattern.finditer(full_text):
        suffixes.add(m.group(1))

    # Deduplicate spelling rules
    seen = set()
    unique_rules = []
    for r in rules:
        key = (r["wrong_form"].lower(), r["correct_form"].lower())
        if key not in seen and r["wrong_form"].lower() != r["correct_form"].lower():
            seen.add(key)
            unique_rules.append(r)

    return {
        "rules": unique_rules,
        "definitions": list(set(definitions))[:200],
        "suffixes": list(suffixes),
    }


def import_to_sayqallash(rules):
    """Import extracted rules into sayqallash_rules table."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sayqallash_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wrong_form TEXT,
        correct_form TEXT,
        error_type TEXT,
        context TEXT,
        lang TEXT,
        frequency INTEGER DEFAULT 1,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    inserted = 0
    for r in rules:
        try:
            cur.execute(
                "SELECT 1 FROM sayqallash_rules WHERE wrong_form = ? AND correct_form = ? AND lang = ?",
                (r["wrong_form"], r["correct_form"], r["lang"])
            )
            if cur.fetchone():
                continue
            cur.execute(
                "INSERT INTO sayqallash_rules (wrong_form, correct_form, error_type, context, lang, source) VALUES (?, ?, ?, ?, ?, ?)",
                (r["wrong_form"], r["correct_form"], r["error_type"], r.get("context", ""), r["lang"], r["source"])
            )
            inserted += 1
        except Exception as e:
            print(f"Skip {r}: {e}")
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM sayqallash_rules")
    total = cur.fetchone()[0]
    conn.close()
    return inserted, total


def import_to_book_terms(definitions, suffixes):
    """Save extracted definitions to a new linguistic_definitions table."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS linguistic_definitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        term TEXT UNIQUE,
        category TEXT,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS uzbek_suffixes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        suffix TEXT UNIQUE,
        category TEXT,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    d_count = 0
    for d in definitions:
        try:
            cur.execute("INSERT OR IGNORE INTO linguistic_definitions (term, source) VALUES (?, ?)", (d, "ona_tili_book_2007"))
            if cur.rowcount > 0:
                d_count += 1
        except Exception:
            pass
    s_count = 0
    for s in suffixes:
        try:
            cur.execute("INSERT OR IGNORE INTO uzbek_suffixes (suffix, source) VALUES (?, ?)", (s, "ona_tili_book_2007"))
            if cur.rowcount > 0:
                s_count += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return d_count, s_count


def main():
    pages = load_pages()
    if not pages:
        print("No pages to process")
        return
    print(f"Loaded {len(pages)} pages")
    extracted = extract_rules(pages)
    print(f"Extracted: {len(extracted['rules'])} spelling rules, {len(extracted['definitions'])} definitions, {len(extracted['suffixes'])} suffixes")

    inserted, total = import_to_sayqallash(extracted["rules"])
    print(f"Sayqallash rules: +{inserted} new (total: {total})")

    d_count, s_count = import_to_book_terms(extracted["definitions"], extracted["suffixes"])
    print(f"Definitions: +{d_count}, Suffixes: +{s_count}")

    return {
        "spelling_rules_inserted": inserted,
        "sayqallash_total": total,
        "definitions_added": d_count,
        "suffixes_added": s_count,
    }


if __name__ == "__main__":
    main()
