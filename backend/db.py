import sqlite3
from typing import List, Dict, Any, Optional
import os
import re
import difflib

DB_PATH = "pharma_editor.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sentence_no INTEGER,
        display_no TEXT,
        en_text TEXT,
        confirmed_ru_text TEXT,
        confirmed_uz_text TEXT,
        text_id TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # Migrate: add display_no if not exists
    try:
        cursor.execute("ALTER TABLE alignments ADD COLUMN display_no TEXT")
    except Exception:
        pass

    # ═══════════════════════════════════════════════
    # Sayqallash Rules — self-learning correction DB
    # ═══════════════════════════════════════════════
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sayqallash_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        wrong_form TEXT NOT NULL,
        correct_form TEXT NOT NULL,
        error_type TEXT DEFAULT 'S/Spelling',
        context TEXT DEFAULT '',
        lang TEXT DEFAULT 'uz',
        frequency INTEGER DEFAULT 1,
        source TEXT DEFAULT 'user_edit',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # Index for fast lookup
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_sayqallash_wrong ON sayqallash_rules(wrong_form)
    ''')
    cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_sayqallash_lang ON sayqallash_rules(lang)
    ''')

    # ═══════════════════════════════════════════════
    # Uzbek grammar rules — static knowledge base
    # ═══════════════════════════════════════════════
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS uz_grammar_kb (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_category TEXT NOT NULL,
        rule_description TEXT NOT NULL,
        wrong_pattern TEXT,
        correct_pattern TEXT,
        examples TEXT,
        priority INTEGER DEFAULT 5,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════════════
# Sayqallash Rules CRUD
# ═══════════════════════════════════════════════════

def add_sayqallash_rule(wrong: str, correct: str, error_type: str = 'S/Spelling',
                         context: str = '', lang: str = 'uz', source: str = 'user_edit'):
    """Add or increment a correction rule."""
    if not wrong or not correct or wrong.strip() == correct.strip():
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Check if rule exists
    cursor.execute(
        "SELECT id, frequency FROM sayqallash_rules WHERE wrong_form = ? AND correct_form = ? AND lang = ?",
        (wrong.strip(), correct.strip(), lang)
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(
            "UPDATE sayqallash_rules SET frequency = ?, updated_at = CURRENT_TIMESTAMP, context = ? WHERE id = ?",
            (row[1] + 1, context[:200] if context else '', row[0])
        )
    else:
        cursor.execute(
            "INSERT INTO sayqallash_rules (wrong_form, correct_form, error_type, context, lang, source) VALUES (?, ?, ?, ?, ?, ?)",
            (wrong.strip(), correct.strip(), error_type, context[:200] if context else '', lang, source)
        )
    conn.commit()
    conn.close()

def get_rules_for_text(text: str, lang: str = 'uz') -> List[Dict]:
    """Find known correction rules that apply to the given text."""
    if not text:
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Get all rules for this language, ordered by frequency (most common first)
    cursor.execute(
        "SELECT * FROM sayqallash_rules WHERE lang = ? ORDER BY frequency DESC",
        (lang,)
    )
    rules = cursor.fetchall()
    conn.close()

    found = []
    text_lower = text.lower()
    for rule in rules:
        wrong = rule['wrong_form']
        if wrong.lower() in text_lower:
            # Find actual position in text
            idx = text.lower().find(wrong.lower())
            if idx >= 0:
                # Get the actual text (preserve case)
                actual_wrong = text[idx:idx + len(wrong)]
                found.append({
                    'from_index': idx,
                    'to_index': idx + len(wrong),
                    'old_value': actual_wrong,
                    'new_value': rule['correct_form'],
                    'error_type': rule['error_type'],
                    'source': 'rules_db',
                    'frequency': rule['frequency']
                })
    return found

def get_all_rules(lang: str = 'uz', limit: int = 500) -> List[Dict]:
    """Get all rules for a language."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM sayqallash_rules WHERE lang = ? ORDER BY frequency DESC LIMIT ?",
        (lang, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_rules_count(lang: str = 'uz') -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sayqallash_rules WHERE lang = ?", (lang,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def delete_sayqallash_rule(rule_id: int):
    """Delete a rule by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sayqallash_rules WHERE id = ?", (rule_id,))
    conn.commit()
    conn.close()

def update_sayqallash_rule(rule_id: int, data: Dict[str, Any]):
    """Update an existing rule."""
    if not data:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Dynamically build the UPDATE statement
    fields = []
    values = []
    for k, v in data.items():
        if k in ['wrong_form', 'correct_form', 'error_type', 'context', 'lang', 'frequency']:
            fields.append(f"{k} = ?")
            values.append(v)
    
    if fields:
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(rule_id)
        query = f"UPDATE sayqallash_rules SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, tuple(values))
        conn.commit()
    conn.close()

# ═══════════════════════════════════════════════════
# Auto-diff: extract correction rules from V1 vs Proposed
# ═══════════════════════════════════════════════════

def extract_diff_rules(v1_text: str, proposed_text: str, lang: str = 'uz', en_context: str = '') -> List[Dict]:
    """
    Compare V1 (original) with Proposed (corrected) and extract word-level differences
    as correction rules for the self-learning database.
    """
    if not v1_text or not proposed_text or v1_text.strip() == proposed_text.strip():
        return []

    v1_words = v1_text.split()
    proposed_words = proposed_text.split()

    sm = difflib.SequenceMatcher(None, v1_words, proposed_words)
    rules = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'replace':
            wrong = ' '.join(v1_words[i1:i2])
            correct = ' '.join(proposed_words[j1:j2])
            if wrong != correct:
                # Determine error type
                error_type = classify_error(wrong, correct)
                rules.append({
                    'wrong_form': wrong,
                    'correct_form': correct,
                    'error_type': error_type,
                    'context': en_context[:200] if en_context else '',
                    'lang': lang
                })
        elif tag == 'delete':
            wrong = ' '.join(v1_words[i1:i2])
            rules.append({
                'wrong_form': wrong,
                'correct_form': '',
                'error_type': 'F/Clarity',
                'context': en_context[:200] if en_context else '',
                'lang': lang
            })
        elif tag == 'insert':
            correct = ' '.join(proposed_words[j1:j2])
            # Context: words around insertion point
            ctx_word = v1_words[i1-1] if i1 > 0 else ''
            rules.append({
                'wrong_form': f'[{ctx_word}]_missing',
                'correct_form': correct,
                'error_type': 'G/Other',
                'context': en_context[:200] if en_context else '',
                'lang': lang
            })
    return rules

def classify_error(wrong: str, correct: str) -> str:
    """Classify the type of error based on the difference."""
    w, c = wrong.lower(), correct.lower()

    # Check for pure case difference
    if w == c:
        return 'S/LowerUpper'

    # Check spelling (similar words, Levenshtein distance <= 2)
    if len(wrong) > 2 and len(correct) > 2:
        common = sum(1 for a, b in zip(w, c) if a == b)
        similarity = common / max(len(w), len(c))
        if similarity > 0.6:
            return 'S/Spelling'

    # Check merge/split
    if ' ' in wrong and ' ' not in correct:
        return 'G/Merge'
    if ' ' not in wrong and ' ' in correct:
        return 'G/Split'

    # Punctuation
    if re.sub(r'[^\w\s]', '', w) == re.sub(r'[^\w\s]', '', c):
        return 'Punctuation'

    return 'S/Context'

def generate_diff_notes(v1_text: str, proposed_text: str, lang: str = 'uz') -> str:
    """Generate human-readable notes about differences between V1 and Proposed."""
    if not v1_text or not proposed_text or v1_text.strip() == proposed_text.strip():
        return ''

    rules = extract_diff_rules(v1_text, proposed_text, lang)
    if not rules:
        return ''

    lang_label = 'UZ' if lang == 'uz' else 'RU'
    notes_parts = [f"[{lang_label} ўзгаришлар]:"]
    for r in rules:
        if r['correct_form']:
            notes_parts.append(f"  «{r['wrong_form']}» → «{r['correct_form']}» [{r['error_type']}]")
        else:
            notes_parts.append(f"  «{r['wrong_form']}» ўчирилди [{r['error_type']}]")
    return '\n'.join(notes_parts)

def save_corrections_as_rules(item: Dict[str, Any]):
    """Extract and save correction rules from a row's V1 vs Proposed differences."""
    # Uzbek corrections
    uz_v1 = item.get('uz_v1', '')
    uz_proposed = item.get('uz_proposed', '')
    en_context = item.get('en', '')

    if uz_v1 and uz_proposed and uz_v1.strip() != uz_proposed.strip():
        rules = extract_diff_rules(uz_v1, uz_proposed, 'uz', en_context)
        for r in rules:
            if r['correct_form']:  # Only save actual corrections
                add_sayqallash_rule(
                    r['wrong_form'], r['correct_form'], r['error_type'],
                    r['context'], r['lang'], 'user_edit'
                )

    # Russian corrections
    ru_v1 = item.get('ru_v1', '')
    ru_proposed = item.get('ru_proposed', '')
    if ru_v1 and ru_proposed and ru_v1.strip() != ru_proposed.strip():
        rules = extract_diff_rules(ru_v1, ru_proposed, 'ru', en_context)
        for r in rules:
            if r['correct_form']:
                add_sayqallash_rule(
                    r['wrong_form'], r['correct_form'], r['error_type'],
                    r['context'], r['lang'], 'user_edit'
                )


def save_alignments(data: List[Dict[str, Any]]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for item in data:
        text_id = item.get("text_id", "default")
        sentence_no = item.get("sentence_no", 0)
        if not sentence_no or sentence_no <= 0:
            continue  # skip marker rows and unsaved new rows during bulk save

        # Auto-extract correction rules before saving
        save_corrections_as_rules(item)

        cursor.execute(
            "SELECT id FROM alignments WHERE text_id = ? AND sentence_no = ?",
            (text_id, sentence_no)
        )
        row = cursor.fetchone()
        if row:
            cursor.execute('''
            UPDATE alignments SET 
                en_text = ?, confirmed_ru_text = ?, confirmed_uz_text = ?,
                notes = ?, display_no = ?
            WHERE id = ?
            ''', (
                item.get("en", ""),
                item.get("ru_proposed", ""),
                item.get("uz_proposed", ""),
                item.get("notes", ""),
                item.get("display_no", str(sentence_no)),
                row[0]
            ))
        else:
            cursor.execute('''
            INSERT INTO alignments (sentence_no, display_no, en_text, confirmed_ru_text, confirmed_uz_text, text_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                sentence_no,
                item.get("display_no", str(sentence_no)),
                item.get("en", ""),
                item.get("ru_proposed", ""),
                item.get("uz_proposed", ""),
                text_id,
                item.get("notes", "")
            ))
    conn.commit()
    conn.close()

def save_single_row(item: Dict[str, Any]) -> int:
    """Save or update a single row. Returns the real DB id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    text_id = item.get("text_id", "default")
    sentence_no = item.get("sentence_no", 0)

    # Auto-extract correction rules
    save_corrections_as_rules(item)

    if sentence_no and sentence_no > 0:
        # Check by sentence_no + text_id
        cursor.execute(
            "SELECT id FROM alignments WHERE text_id = ? AND sentence_no = ?",
            (text_id, sentence_no)
        )
        row = cursor.fetchone()
        if row:
            cursor.execute('''
            UPDATE alignments SET
                en_text = ?, confirmed_ru_text = ?, confirmed_uz_text = ?,
                notes = ?, display_no = ?
            WHERE id = ?
            ''', (
                item.get("en", ""),
                item.get("ru_proposed", ""),
                item.get("uz_proposed", ""),
                item.get("notes", ""),
                item.get("display_no", str(sentence_no)),
                row[0]
            ))
            conn.commit()
            conn.close()
            return row[0]

    # New row — INSERT
    cursor.execute('''
    INSERT INTO alignments (sentence_no, display_no, en_text, confirmed_ru_text, confirmed_uz_text, text_id, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        sentence_no if sentence_no and sentence_no > 0 else None,
        item.get("display_no", ""),
        item.get("en", ""),
        item.get("ru_proposed", ""),
        item.get("uz_proposed", ""),
        text_id,
        item.get("notes", "")
    ))
    new_id = cursor.lastrowid
    # Store DB id as sentence_no for future updates
    cursor.execute("UPDATE alignments SET sentence_no = ? WHERE id = ?", (new_id, new_id))
    conn.commit()
    conn.close()
    return new_id

def delete_row(sentence_no: int, text_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM alignments WHERE text_id = ? AND sentence_no = ?",
        (text_id, sentence_no)
    )
    conn.commit()
    conn.close()

def get_history(text_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM alignments WHERE text_id = ? ORDER BY sentence_no ASC",
        (text_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

