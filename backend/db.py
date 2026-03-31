import sqlite3
from typing import List, Dict, Any, Optional
import os
import re
import difflib
import hashlib
import uuid

DB_PATH = "pharma_editor.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT,
        specialist_name TEXT,
        status TEXT DEFAULT 'in_progress',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sentence_no INTEGER,
        display_no TEXT,
        row_type TEXT DEFAULT 'content',
        en_text TEXT,
        confirmed_ru_text TEXT,
        confirmed_uz_text TEXT,
        text_id TEXT,
        notes TEXT DEFAULT '',
        specialist_name TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Migrate: add display_no/specialist_name/row_type if not exists
    try:
        cursor.execute("ALTER TABLE alignments ADD COLUMN display_no TEXT")
    except Exception: pass
    try:
        cursor.execute("ALTER TABLE alignments ADD COLUMN specialist_name TEXT")
    except Exception: pass
    try:
        cursor.execute("ALTER TABLE alignments ADD COLUMN row_type TEXT DEFAULT 'content'")
    except Exception: pass

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
    # User accounts & RBAC
    # ═══════════════════════════════════════════════
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        name TEXT,
        role TEXT DEFAULT 'foydalanuvchi',
        status TEXT DEFAULT 'pending',
        avatar_url TEXT,
        password_hash TEXT,
        salt TEXT,
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # Migrate: add password columns if not exists
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    except Exception: pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN salt TEXT")
    except Exception: pass
    # Seed admin if empty
    cursor.execute("SELECT COUNT(*) FROM users WHERE email = 'texnopharm@gmail.com'")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
        INSERT INTO users (id, email, name, role, status, password_hash, salt)
        VALUES ('admin_primary', 'texnopharm@gmail.com', 'Admin Texnopharm', 'admin', 'approved', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'admin_salt')
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
    """Find known correction rules that apply to the given text.
    
    IMPORTANT: Does NOT suggest replacing text that is a known correct_form.
    This prevents circular corrections (e.g., marking 'аксарият' as wrong
    when it was previously corrected FROM 'аксарияд' TO 'аксарият').
    """
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

    # Build set of known CORRECT forms (lowercase) — these should NEVER be flagged as wrong
    correct_forms_set = set()
    for rule in rules:
        cf = rule['correct_form']
        if cf:
            correct_forms_set.add(cf.strip().lower())

    found = []
    text_lower = text.lower()
    for rule in rules:
        wrong = rule['wrong_form']
        correct = rule['correct_form']
        if not wrong or not correct:
            continue
        
        wrong_lower = wrong.lower().strip()
        correct_lower = correct.lower().strip()
        
        # CRITICAL: Skip if the wrong_form is actually a known correct_form in another rule
        # This prevents suggesting "аксарият" → "аксарияд" when "аксарият" is correct
        if wrong_lower in correct_forms_set:
            continue
        
        # Skip if wrong and correct are the same
        if wrong_lower == correct_lower:
            continue
        
        start_search = 0
        while True:
            idx = text_lower.find(wrong_lower, start_search)
            if idx == -1:
                break
            
            # Verify word boundary — don't match partial words
            before_ok = (idx == 0) or not text[idx - 1].isalpha()
            after_ok = (idx + len(wrong) >= len(text)) or not text[idx + len(wrong)].isalpha()
            
            if before_ok and after_ok:
                # Get the actual text (preserve case)
                actual_wrong = text[idx:idx + len(wrong)]
                found.append({
                    'from_index': idx,
                    'to_index': idx + len(wrong),
                    'old_value': actual_wrong,
                    'new_value': correct,
                    'error_type': rule['error_type'],
                    'source': 'rules_db',
                    'frequency': rule['frequency']
                })
            start_search = idx + len(wrong)
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
        row_type = item.get("type", "content")

        # Auto-extract correction rules before saving content cells
        if row_type == "content":
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
                notes = ?, display_no = ?, specialist_name = ?, row_type = ?
            WHERE id = ?
            ''', (
                item.get("en", ""),
                item.get("ru_proposed", ""),
                item.get("uz_proposed", ""),
                item.get("notes", ""),
                item.get("display_no", str(sentence_no)),
                item.get("specialist_name", ""),
                row_type,
                row[0]
            ))
        else:
            cursor.execute('''
            INSERT INTO alignments (sentence_no, display_no, row_type, en_text, confirmed_ru_text, confirmed_uz_text, text_id, notes, specialist_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sentence_no,
                item.get("display_no", str(sentence_no)),
                row_type,
                item.get("en", ""),
                item.get("ru_proposed", ""),
                item.get("uz_proposed", ""),
                text_id,
                item.get("notes", ""),
                item.get("specialist_name", "")
            ))
    conn.commit()
    conn.close()

    
    # Update project metadata
    if data:
        update_project_metadata(data[0].get("text_id", "default"), data[0].get("specialist_name", ""))

def update_project_metadata(text_id: str, specialist: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM projects WHERE id = ?", (text_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE projects SET specialist_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (specialist, text_id))
    else:
        cursor.execute("INSERT INTO projects (id, name, specialist_name) VALUES (?, ?, ?)", (text_id, f"Project {text_id}", specialist))
    conn.commit()
    conn.close()

def list_projects() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_project(text_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (text_id,))
    cursor.execute("DELETE FROM alignments WHERE text_id = ?", (text_id,))
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
                notes = ?, display_no = ?, specialist_name = ?
            WHERE id = ?
            ''', (
                item.get("en", ""),
                item.get("ru_proposed", ""),
                item.get("uz_proposed", ""),
                item.get("notes", ""),
                item.get("display_no", str(sentence_no)),
                item.get("specialist_name", ""),
                row[0]
            ))
            conn.commit()
            conn.close()
            return row[0]

    # New row — INSERT
    cursor.execute('''
    INSERT INTO alignments (sentence_no, display_no, en_text, confirmed_ru_text, confirmed_uz_text, text_id, notes, specialist_name)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        sentence_no if sentence_no and sentence_no > 0 else None,
        item.get("display_no", ""),
        item.get("en", ""),
        item.get("ru_proposed", ""),
        item.get("uz_proposed", ""),
        text_id,
        item.get("notes", ""),
        item.get("specialist_name", "")
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
    
    # Map DB column names to frontend field names
    result = []
    for r in rows:
        d = dict(r)
        result.append({
            'type': d.get('row_type', 'content'),
            'sentence_no': d.get('sentence_no', 0),
            'display_no': d.get('display_no', str(d.get('sentence_no', ''))),
            'en': d.get('en_text', ''),
            'ru_v1': d.get('confirmed_ru_text', ''),
            'ru_proposed': d.get('confirmed_ru_text', ''),
            'uz_v1': d.get('confirmed_uz_text', ''),
            'uz_proposed': d.get('confirmed_uz_text', ''),
            'text_id': d.get('text_id', text_id),
            'notes': d.get('notes', ''),
            'status': 'aligned',
            'specialist_name': d.get('specialist_name', '')
        })
    return result


# ═══════════════════════════════════════════════════
# User Management
# ═══════════════════════════════════════════════════

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(user_id: str, email: str, name: str, avatar_url: Optional[str] = None, password: Optional[str] = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    password_hash = None
    salt = None
    if password:
        salt = uuid.uuid4().hex
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()

    cursor.execute('''
    INSERT INTO users (id, email, name, avatar_url, status, password_hash, salt)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, email.lower().strip(), name, avatar_url, 'pending', password_hash, salt))
    conn.commit()
    conn.close()

def verify_password(email: str, password: str) -> bool:
    user = get_user_by_email(email)
    if not user or not user.get('password_hash') or not user.get('salt'):
        return False
    
    stored_hash = user['password_hash']
    salt = user['salt']
    # If admin with hardcoded salt
    if email == 'texnopharm@gmail.com' and stored_hash == '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918':
        return password == 'admin123' or hashlib.sha256((password + salt).encode()).hexdigest() == stored_hash

    return hashlib.sha256((password + salt).encode()).hexdigest() == stored_hash

def update_user_login(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def list_all_users() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_user_role(user_id: str, role: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
    conn.commit()
    conn.close()

def reorder_alignments(text_id: str):
    """Ensure sentence_no and display_no are sequential for a project."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM alignments WHERE text_id = ? ORDER BY id ASC", (text_id,))
    rows = cursor.fetchall()
    for idx, row in enumerate(rows, 1):
        cursor.execute("UPDATE alignments SET sentence_no = ?, display_no = ? WHERE id = ?", (idx, str(idx), row[0]))
    conn.commit()
    conn.close()

def delete_alignment(alignment_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alignments WHERE id = ?", (alignment_id,))
    conn.commit()
    conn.close()


def get_unique_specialists() -> List[str]:
    """Get unique specialist names from both alignments and projects tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Union names from both tables for robustness
    query = """
        SELECT DISTINCT specialist_name FROM alignments WHERE specialist_name IS NOT NULL AND specialist_name != ''
        UNION
        SELECT DISTINCT specialist_name FROM projects WHERE specialist_name IS NOT NULL AND specialist_name != ''
        ORDER BY specialist_name
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


def update_user_status(user_id: str, status: str):
    """Update user approval status (pending/approved/rejected)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
    conn.commit()
    conn.close()
