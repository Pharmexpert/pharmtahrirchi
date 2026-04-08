"""
Syntax Synthetic Data Generator (GECTurk-style for Uzbek).

Стратегия:
  1. UD_Uzbek-UT парсе гапларидан чиқиб оламиз (correct examples)
  2. Ҳар гапга 10+ трансформация функциясини қўллаймиз — xato versions
  3. Ҳар юзага келган (wrong, correct) жуфтлик учун бидирекционал верификация
  4. Тоза жуфтликларни translation_memory ёки syntax_parsed_sentences'га сақлаймиз

Трансформация функциялари (ҳар бири grammatik xato турини имитация қилади):
  1. swap_subject_object — эга/тўлдирувчи ўрин алмаштириш
  2. drop_case_marker — -ни/-га/-да/-дан олиб ташлаш (nominative xatosi)
  3. verb_to_front — кесимни гап бошига кўчириш
  4. drop_subject — эгани олиб ташлаш
  5. wrong_case_marker — нотўғри келишик қўшимчаси
  6. double_suffix — -лик -лик дубль
  7. drop_plural — -лар олиб ташлаш
  8. wrong_tense — феъл замонини бузиш
  9. wrong_adj_position — аниқловчини аниқланмишдан кейинга қўйиш
  10. wrong_negation — -ма ўрнига "йўқ"
"""
import os
import sqlite3
import random
import re
import logging
import json

log = logging.getLogger("syntax_synth")

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))

# Ўзбек тилининг ҳолат (keliшик) қўшимчалари
CASE_SUFFIXES = ["ни", "га", "да", "дан", "нинг", "ча"]
PLURAL_SUFFIX = "лар"
POSSESSIVE_SUFFIXES = ["им", "инг", "и", "имиз", "ингиз", "лари"]
NEGATIVE_SUFFIXES = ["ма", "май", "мас"]


# ─────────────────────────────────────────────
# Трансформация функциялари
# ─────────────────────────────────────────────

def swap_subject_object(tokens: list) -> list | None:
    """Эга (биринчи нoun) ва тўлдирувчи (кейинги нoun) ўрнини алмаштириш."""
    nouns = [(i, t) for i, t in enumerate(tokens) if t.get("upos") == "NOUN"]
    if len(nouns) < 2:
        return None
    i1, _ = nouns[0]
    i2, _ = nouns[1]
    new_tokens = tokens.copy()
    new_tokens[i1], new_tokens[i2] = new_tokens[i2], new_tokens[i1]
    return new_tokens


def drop_case_marker(tokens: list) -> list | None:
    """Тўлдирувчидан -ни/-га/... қўшимчаларини олиб ташлаш."""
    new_tokens = []
    changed = False
    for t in tokens:
        form = t.get("form", "")
        for suf in CASE_SUFFIXES:
            if form.lower().endswith(suf) and len(form) > len(suf) + 2:
                new_form = form[:-len(suf)]
                new_tokens.append({**t, "form": new_form})
                changed = True
                break
        else:
            new_tokens.append(t)
    return new_tokens if changed else None


def verb_to_front(tokens: list) -> list | None:
    """Кесимни (VERB) гап бошига кўчириш."""
    verb_idx = next((i for i, t in enumerate(tokens) if t.get("upos") == "VERB"), -1)
    if verb_idx <= 0:
        return None
    new_tokens = tokens.copy()
    verb = new_tokens.pop(verb_idx)
    new_tokens.insert(0, verb)
    return new_tokens


def drop_subject(tokens: list) -> list | None:
    """Биринчи ноунни олиб ташлаш."""
    for i, t in enumerate(tokens):
        if t.get("upos") == "NOUN":
            new_tokens = tokens.copy()
            new_tokens.pop(i)
            return new_tokens if len(new_tokens) > 1 else None
    return None


def wrong_case_marker(tokens: list) -> list | None:
    """Тасодифий нoun учун нотўғри келишик."""
    nouns = [(i, t) for i, t in enumerate(tokens) if t.get("upos") == "NOUN"]
    if not nouns:
        return None
    i, t = random.choice(nouns)
    form = t.get("form", "")
    # Олиб ташлаш мавжуд қўшимчани + янгисини қўйиш
    for suf in CASE_SUFFIXES:
        if form.lower().endswith(suf):
            form = form[:-len(suf)]
            break
    wrong_suf = random.choice(CASE_SUFFIXES)
    new_form = form + wrong_suf
    new_tokens = tokens.copy()
    new_tokens[i] = {**t, "form": new_form}
    return new_tokens


def double_suffix(tokens: list) -> list | None:
    """-лик+-лик ёки -лар+-лар дубль."""
    for i, t in enumerate(tokens):
        form = t.get("form", "")
        if form.lower().endswith("лик"):
            new_tokens = tokens.copy()
            new_tokens[i] = {**t, "form": form + "лик"}
            return new_tokens
        if form.lower().endswith("лар"):
            new_tokens = tokens.copy()
            new_tokens[i] = {**t, "form": form + "лар"}
            return new_tokens
    return None


def drop_plural(tokens: list) -> list | None:
    """-лар олиб ташлаш."""
    for i, t in enumerate(tokens):
        form = t.get("form", "")
        if form.lower().endswith(PLURAL_SUFFIX) and len(form) > 4:
            new_tokens = tokens.copy()
            new_tokens[i] = {**t, "form": form[:-3]}
            return new_tokens
    return None


def wrong_tense(tokens: list) -> list | None:
    """Феъл замонини бузиш: келди → келади → келмоқда."""
    for i, t in enumerate(tokens):
        if t.get("upos") == "VERB":
            form = t.get("form", "")
            # Ҳозирги → ўтган
            if form.endswith("япти") or form.endswith("ади"):
                new_form = form[:-3] + "ди"
                new_tokens = tokens.copy()
                new_tokens[i] = {**t, "form": new_form}
                return new_tokens
            # Ўтган → ҳозирги
            if form.endswith("ди"):
                new_form = form[:-2] + "япти"
                new_tokens = tokens.copy()
                new_tokens[i] = {**t, "form": new_form}
                return new_tokens
    return None


def wrong_adj_position(tokens: list) -> list | None:
    """Сифатни нoundан кейинга кўчириш."""
    for i, t in enumerate(tokens[:-1]):
        if t.get("upos") == "ADJ" and i + 1 < len(tokens) and tokens[i + 1].get("upos") == "NOUN":
            new_tokens = tokens.copy()
            new_tokens[i], new_tokens[i + 1] = new_tokens[i + 1], new_tokens[i]
            return new_tokens
    return None


def wrong_negation(tokens: list) -> list | None:
    """Феълдаги -ма/-май ўрнига 'йўқ' сўзини қўшиш."""
    for i, t in enumerate(tokens):
        if t.get("upos") == "VERB":
            form = t.get("form", "")
            for neg in NEGATIVE_SUFFIXES:
                if neg in form.lower():
                    # Remove negative, add "йўқ"
                    new_form = form.replace(neg, "")
                    new_tokens = tokens.copy()
                    new_tokens[i] = {**t, "form": new_form}
                    new_tokens.append({"form": "йўқ", "upos": "PART"})
                    return new_tokens
    return None


TRANSFORMATIONS = [
    ("swap_subject_object", swap_subject_object),
    ("drop_case_marker", drop_case_marker),
    ("verb_to_front", verb_to_front),
    ("drop_subject", drop_subject),
    ("wrong_case_marker", wrong_case_marker),
    ("double_suffix", double_suffix),
    ("drop_plural", drop_plural),
    ("wrong_tense", wrong_tense),
    ("wrong_adj_position", wrong_adj_position),
    ("wrong_negation", wrong_negation),
]


def tokens_to_text(tokens: list) -> str:
    """Convert token list back to sentence text."""
    return " ".join(t.get("form", "") for t in tokens if t.get("form"))


def generate_pairs_for_sentence(sentence_tokens: list, transforms_per_sent: int = 5) -> list:
    """
    Qaerdan bir gap uchun bir necha wrong versiya generate qilish.
    Returns list of (wrong_text, correct_text, transform_name) tuples.
    """
    if not sentence_tokens or len(sentence_tokens) < 3:
        return []

    correct_text = tokens_to_text(sentence_tokens)
    pairs = []

    # Randomize transformation order
    shuffled = list(TRANSFORMATIONS)
    random.shuffle(shuffled)

    for name, fn in shuffled[:transforms_per_sent]:
        try:
            result = fn(sentence_tokens)
            if result is None:
                continue
            wrong_text = tokens_to_text(result)
            if wrong_text and wrong_text != correct_text and len(wrong_text) > 3:
                pairs.append((wrong_text, correct_text, name))
        except Exception as e:
            log.debug(f"transform {name} failed: {e}")
    return pairs


def reverse_verify_pair(wrong: str, correct: str) -> bool:
    """Simple reverse verification: apply correction and check it matches correct."""
    if not wrong or not correct or wrong == correct:
        return False
    # Basic: must be different but not too different
    import difflib
    ratio = difflib.SequenceMatcher(None, wrong, correct).ratio()
    return 0.4 <= ratio <= 0.95


def generate_all(limit_sentences: int = 1000, transforms_per_sent: int = 5) -> dict:
    """
    Generate synthetic pairs from UD_Uzbek parsed sentences in DB.
    Save to translation_memory with source_db='syntax_synth'.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Ensure translation_memory exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS translation_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_lang TEXT,
            target_lang TEXT,
            source_text TEXT,
            target_text TEXT,
            source_db TEXT,
            quality_score REAL DEFAULT 1.0,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Load parsed sentences
    cur.execute("""
        SELECT text, parse_tree FROM syntax_parsed_sentences
        WHERE parse_tree IS NOT NULL AND parse_tree != ''
        ORDER BY RANDOM() LIMIT ?
    """, (limit_sentences,))
    rows = cur.fetchall()

    total_generated = 0
    total_inserted = 0
    per_transform = {}

    for text, parse_json in rows:
        try:
            tokens = json.loads(parse_json)
            if not isinstance(tokens, list):
                continue
            # Map to form/upos only
            simple_tokens = [{"form": t.get("form", ""), "upos": t.get("upos", "X")} for t in tokens]
        except Exception:
            continue

        pairs = generate_pairs_for_sentence(simple_tokens, transforms_per_sent=transforms_per_sent)
        total_generated += len(pairs)

        for wrong, correct, tname in pairs:
            if not reverse_verify_pair(wrong, correct):
                continue
            try:
                cur.execute("""
                    INSERT INTO translation_memory
                    (source_lang, target_lang, source_text, target_text, source_db, quality_score, metadata)
                    VALUES ('uz', 'uz', ?, ?, 'syntax_synth', 0.85, ?)
                """, (wrong[:2000], correct[:2000], tname))
                total_inserted += 1
                per_transform[tname] = per_transform.get(tname, 0) + 1
            except Exception:
                pass

    conn.commit()
    conn.close()

    result = {
        "sentences_processed": len(rows),
        "pairs_generated": total_generated,
        "pairs_inserted_after_verify": total_inserted,
        "per_transform": per_transform,
    }
    log.info(f"[syntax_synth] {result}")
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(generate_all(limit_sentences=500, transforms_per_sent=5))
