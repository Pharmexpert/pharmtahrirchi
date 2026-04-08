"""
Syntax Engine — Phase 3.
Lightweight Uzbek sentence syntax analyzer (no Stanza required for v1).
Uses: Hunspell affix flags + sentence_parts/phrases DB + heuristics + LLM fallback.

Methods:
  analyze(sentence) → tokens + roles + word order + errors + suggestions
  check(text) → list of errors (for editor integration)
  reorder(sentence) → canonical word order
"""
import os
import re
import sqlite3
import logging
import json

log = logging.getLogger("syntax_engine")

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))


# ─────────────────────────────────────────────
# Heuristic POS / role detection
# ─────────────────────────────────────────────

UZBEK_VERB_SUFFIXES = (
    "moqda", "yapti", "yotir", "yotibdi", "ayotir",
    "moqchi", "moqchiman", "moqchimiz",
    "di", "ti", "gan", "kan", "qan",
    "ar", "yur", "y", "yman",
    "yapman", "yapsiz", "yapmiz",
    "moq", "ish", "uvchi",
)

UZBEK_NOUN_SUFFIXES_NOM = ("",)  # nominative
UZBEK_NOUN_SUFFIXES_OBJ = ("ni", "ga", "da", "dan")  # accusative + dative + locative + ablative
UZBEK_ADJ_HINTS = ("li", "siz", "ki", "lik", "chil")
UZBEK_ADV_HINTS = ("cha", "an", "akan", "yangi", "tez", "asta", "xira")

PUNCT_RE = re.compile(r"[.,!?;:()\"\'«»\[\]{}—]")


def _strip_punct(word: str) -> str:
    return PUNCT_RE.sub("", word).strip()


def guess_pos(word: str) -> str:
    """Lightweight POS guess from word ending."""
    w = _strip_punct(word).lower()
    if not w:
        return "PUNCT"
    for suf in UZBEK_VERB_SUFFIXES:
        if w.endswith(suf) and len(w) > len(suf):
            return "VERB"
    for suf in UZBEK_ADV_HINTS:
        if w.endswith(suf):
            return "ADV"
    for suf in UZBEK_ADJ_HINTS:
        if w.endswith(suf):
            return "ADJ"
    for suf in UZBEK_NOUN_SUFFIXES_OBJ:
        if w.endswith(suf) and len(w) > len(suf) + 1:
            return "NOUN_OBJ"  # noun in oblique case → likely object/oblique
    return "NOUN"  # default


def detect_role(token: dict, idx: int, total: int) -> str:
    """Map POS + position → ega/kesim/toldiruvchi/aniqlovchi/hol."""
    pos = token["pos"]
    is_last = idx == total - 1
    if pos == "VERB":
        return "kesim"
    if pos == "ADV":
        return "hol"
    if pos == "ADJ":
        return "aniqlovchi"
    if pos == "NOUN_OBJ":
        return "toldiruvchi"
    if pos == "NOUN":
        # First noun = likely subject; later nouns = likely object
        return "ega" if idx == 0 else "toldiruvchi"
    return "other"


# ─────────────────────────────────────────────
# DB lookups (use UD-imported data)
# ─────────────────────────────────────────────

def lookup_role_from_db(word: str) -> str | None:
    """Check syntax_sentence_parts for the most frequent role of this word."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT role, COUNT(*) as c
            FROM syntax_sentence_parts
            WHERE word = ? OR lemma = ?
            GROUP BY role
            ORDER BY c DESC
            LIMIT 1
        """, (word.lower(), word.lower()))
        row = cur.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def find_word_order_rule(pos_pattern: str) -> dict | None:
    """Find a matching word order rule."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
            SELECT pos_pattern_correct, explanation_uz, severity
            FROM syntax_word_order_rules
            WHERE pos_pattern_wrong = ?
            LIMIT 1
        """, (pos_pattern,))
        row = cur.fetchone()
        conn.close()
        if row:
            return {"correct": row[0], "explanation": row[1], "severity": row[2]}
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────
# Main analyzer
# ─────────────────────────────────────────────

def analyze(sentence: str) -> dict:
    """Full syntax analysis of one sentence.
    Uses BERTbek POS tagger if BERTBEK_ENABLED=1, otherwise falls back to rule-based guess.
    """
    sentence = sentence.strip()
    if not sentence:
        return {"tokens": [], "errors": [], "suggestions": [], "valid": False}

    # Try BERTbek POS tagger first (92% accuracy vs 60% rule-based)
    pos_tags = None
    try:
        import bertbek_engine
        if bertbek_engine.is_available():
            pos_tags = bertbek_engine.tag_pos(sentence)
    except Exception:
        pass

    tokens = []
    if pos_tags:
        # Use BERTbek tags
        for word, upos in pos_tags:
            clean = _strip_punct(word)
            if not clean:
                continue
            # Map UD tags to our internal POS
            internal_pos = upos
            if upos == "NOUN" and any(clean.lower().endswith(s) for s in UZBEK_NOUN_SUFFIXES_OBJ):
                internal_pos = "NOUN_OBJ"
            tokens.append({"word": word, "clean": clean, "pos": internal_pos})
    else:
        # Fallback: rule-based POS guess
        raw_words = sentence.split()
        for w in raw_words:
            clean = _strip_punct(w)
            if not clean:
                continue
            pos = guess_pos(clean)
            tokens.append({"word": w, "clean": clean, "pos": pos})

    total = len(tokens)
    for i, tok in enumerate(tokens):
        # Try DB lookup first
        db_role = lookup_role_from_db(tok["clean"])
        tok["role"] = db_role or detect_role(tok, i, total)

    # Compute word order formula
    role_seq = "+".join(_role_short(t["role"]) for t in tokens if t["role"] != "other")
    pos_seq = " ".join(t["pos"].split("_")[0] for t in tokens)

    # Detect errors
    errors = []
    suggestions = []

    # Rule 1: kesim (verb) must be last in canonical Uzbek SOV
    if tokens:
        last_pos = tokens[-1]["pos"]
        verb_idx = next((i for i, t in enumerate(tokens) if t["pos"] == "VERB"), -1)
        if verb_idx >= 0 and verb_idx != total - 1 and last_pos != "VERB":
            errors.append({
                "type": "word_order",
                "severity": "warning",
                "message": "Кесим (феъл) гап охирида келиши керак (S-O-V).",
                "wrong_position": verb_idx,
                "suggestion": "Кесимни гап охирига кўчиринг",
            })

    # Rule 2: lookup matching wrong patterns in DB
    rule = find_word_order_rule(pos_seq)
    if rule:
        errors.append({
            "type": "word_order_db",
            "severity": rule["severity"],
            "message": rule["explanation"],
            "suggestion": f"Тўғри тартиб: {rule['correct']}",
        })

    # Rule 3: subject existence check
    has_subject = any(t["role"] == "ega" for t in tokens)
    if not has_subject and total > 1:
        suggestions.append({
            "type": "missing_subject",
            "severity": "suggestion",
            "message": "Гапда эга йўқ ёки аниқ эмас",
        })

    # Rule 4: predicate existence check
    has_verb = any(t["pos"] == "VERB" for t in tokens)
    if not has_verb:
        errors.append({
            "type": "missing_predicate",
            "severity": "warning",
            "message": "Гапда кесим (феъл) йўқ",
        })

    return {
        "tokens": tokens,
        "word_order_formula": role_seq,
        "pos_sequence": pos_seq,
        "errors": errors,
        "suggestions": suggestions,
        "valid": len(errors) == 0,
        "has_subject": has_subject,
        "has_predicate": has_verb,
    }


def _role_short(role: str) -> str:
    return {
        "ega": "S",
        "toldiruvchi": "O",
        "kesim": "V",
        "aniqlovchi": "Adj",
        "hol": "Adv",
    }.get(role, "X")


def check_text(text: str) -> list:
    """Check a multi-sentence text and return all errors."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    all_errors = []
    for i, s in enumerate(sentences):
        if not s.strip():
            continue
        result = analyze(s)
        for e in result["errors"]:
            e["sentence_index"] = i
            e["sentence"] = s
            all_errors.append(e)
    return all_errors


def reorder_canonical(sentence: str) -> str:
    """Reorder words to canonical S-O-V (best-effort heuristic)."""
    result = analyze(sentence)
    if not result["tokens"]:
        return sentence
    # Sort by role priority: ega → aniqlovchi → toldiruvchi → hol → kesim
    priority = {"ega": 1, "aniqlovchi": 2, "toldiruvchi": 3, "hol": 4, "kesim": 5, "other": 6}
    sorted_tokens = sorted(result["tokens"], key=lambda t: priority.get(t["role"], 6))
    return " ".join(t["word"] for t in sorted_tokens)


def save_user_rule(wrong: str, correct: str, explanation: str = "", user_id: int | None = None) -> dict:
    """User saves a corrected word order → syntax_word_order_rules."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        wrong_pos = " ".join(guess_pos(w).split("_")[0] for w in wrong.split())
        correct_pos = " ".join(guess_pos(w).split("_")[0] for w in correct.split())
        cur.execute("""
            INSERT INTO syntax_word_order_rules
            (wrong_order, correct_order, pos_pattern_wrong, pos_pattern_correct, explanation_uz, severity, source)
            VALUES (?, ?, ?, ?, ?, 'warning', 'user_save')
        """, (wrong, correct, wrong_pos, correct_pos, explanation))
        rule_id = cur.lastrowid
        conn.commit()
        conn.close()
        return {"success": True, "id": rule_id}
    except Exception as e:
        return {"success": False, "error": str(e)}
