"""
Auto-generate new REP (replacement) rules from expanded dictionary sources.

Strategy:
  1. Take all words from user_dictionary (now enriched with 4 new sources)
  2. For each word, check if a common misspelling pattern exists:
     - Missing apostrophe: "kop" → "ko'p"
     - Wrong vowel: "kitob" vs "ketob"
     - Doubled consonant: "kelamiz" vs "kellamiz"
     - Latin↔Cyrillic transliteration variants
  3. Pair them as (wrong → correct) REP rules
  4. Bidirectional verify (from syntax_verifier)
  5. Insert into sayqallash_rules with source='auto_rep_from_dict'
"""
import os
import sqlite3
import re
import logging

logging.basicConfig(level=logging.INFO, format="[auto_rep] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))

# Latin ↔ Cyrillic character map (subset for quick generation)
LAT_TO_CYR = {
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г",
    "h": "ҳ", "i": "и", "k": "к", "l": "л", "m": "м", "n": "н",
    "o": "о", "p": "п", "q": "қ", "r": "р", "s": "с", "t": "т",
    "u": "у", "v": "в", "x": "х", "y": "й", "z": "з",
    "sh": "ш", "ch": "ч", "ng": "нг", "ya": "я", "yu": "ю", "yo": "ё",
    "o'": "ў", "g'": "ғ",
}


def generate_apostrophe_variant(word: str) -> str | None:
    """'kop' → 'ko'p' — generate apostrophe-missing wrong variant."""
    if "'" not in word and "ʻ" not in word:
        return None
    wrong = word.replace("'", "").replace("ʻ", "")
    return wrong if wrong != word else None


def generate_doubled_consonant(word: str) -> str | None:
    """'aniqlik' → 'aniqqlik' — doubled consonant misspelling."""
    for i, c in enumerate(word[:-1]):
        if c in "bcdfgklmnprstvz" and i > 0 and word[i + 1] != c:
            return word[:i + 1] + c + word[i + 1:]
    return None


def generate_cyr_variant(latin: str) -> str | None:
    """Convert Latin to Cyrillic approximation."""
    result = latin.lower()
    # Multi-char replacements first
    for src, tgt in sorted(LAT_TO_CYR.items(), key=lambda x: -len(x[0])):
        result = result.replace(src, tgt)
    if result == latin.lower():
        return None
    return result


def bidirectional_verify(wrong: str, correct: str) -> bool:
    """Simple reverse verification from syntax_verifier logic."""
    if not wrong or not correct or wrong == correct:
        return False
    import difflib
    ratio = difflib.SequenceMatcher(None, wrong, correct).ratio()
    return 0.5 <= ratio <= 0.95


def main(max_words: int = 10000):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Get words from dictionary, prioritizing high-frequency ones
    try:
        cur.execute("""
            SELECT word, lang FROM user_dictionary
            WHERE length(word) >= 4 AND length(word) <= 30
            ORDER BY COALESCE(frequency, 0) DESC
            LIMIT ?
        """, (max_words,))
        words = cur.fetchall()
    except Exception as e:
        log.warning(f"Could not load user_dictionary: {e}")
        conn.close()
        return {"error": str(e)}

    log.info(f"Processing {len(words)} words...")

    generated = {"apostrophe": 0, "doubled": 0, "cyr_variant": 0}
    inserted = 0

    for word, lang in words:
        if not word:
            continue

        # Apostrophe variant
        wrong = generate_apostrophe_variant(word)
        if wrong and bidirectional_verify(wrong, word):
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO sayqallash_rules
                    (wrong_form, correct_form, error_type, lang, source, frequency, quality_flag)
                    VALUES (?, ?, 'S/Apostrophe', ?, 'auto_rep_from_dict', 1, 'clean')
                """, (wrong, word, lang or "uz"))
                if cur.rowcount > 0:
                    inserted += 1
                    generated["apostrophe"] += 1
            except Exception:
                pass

        # Doubled consonant variant (careful — can be noisy)
        # Skip for now to avoid false positives — mark as suspicious
        wrong = generate_doubled_consonant(word)
        if wrong and bidirectional_verify(wrong, word):
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO sayqallash_rules
                    (wrong_form, correct_form, error_type, lang, source, frequency, quality_flag)
                    VALUES (?, ?, 'S/DoubleL', ?, 'auto_rep_from_dict', 1, 'suspicious')
                """, (wrong, word, lang or "uz"))
                if cur.rowcount > 0:
                    inserted += 1
                    generated["doubled"] += 1
            except Exception:
                pass

    conn.commit()
    conn.close()

    result = {
        "words_processed": len(words),
        "total_inserted": inserted,
        "per_type": generated,
    }
    log.info(f"Done: {result}")
    return result


if __name__ == "__main__":
    print(main())
