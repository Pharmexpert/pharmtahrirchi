"""
Ўзбек тили имло текширгичи — uz-hunspell + spylls (тўлиқ affix support).
96K stem + 22,929 affix = ~2-3 миллион сўз шакли текширилади.
Tier 0 сифатида Sayqallash пайплайнига интеграция қилинган.
"""
import os
import re
import logging

logger = logging.getLogger("spellcheck")

HUNSPELL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hunspell")

_cyrl_dict = None
_lat_dict = None


def _load():
    """Load hunspell dictionaries via spylls (full affix support)."""
    global _cyrl_dict, _lat_dict

    if _cyrl_dict is not None:
        return

    try:
        from spylls.hunspell import Dictionary

        cyrl_path = os.path.join(HUNSPELL_DIR, "uz_UZ_Cyrl")
        if os.path.exists(cyrl_path + ".dic"):
            _cyrl_dict = Dictionary.from_files(cyrl_path)
            logger.info(f"[+] Spylls Cyrillic dictionary loaded (full affix support)")

        lat_path = os.path.join(HUNSPELL_DIR, "uz_UZ")
        if os.path.exists(lat_path + ".dic"):
            _lat_dict = Dictionary.from_files(lat_path)
            logger.info(f"[+] Spylls Latin dictionary loaded (full affix support)")

    except ImportError:
        logger.warning("[!] spylls not installed, falling back to simple dict lookup")
        _load_simple()
    except Exception as e:
        logger.error(f"[!] Spylls load error: {e}, falling back to simple")
        _load_simple()


# Fallback: simple dict-based
_cyrillic_words = None
_latin_words = None


def _load_simple():
    global _cyrillic_words, _latin_words
    _cyrillic_words = set()
    _latin_words = set()

    for fname, target in [("uz_UZ_Cyrl.dic", _cyrillic_words), ("uz_UZ.dic", _latin_words)]:
        path = os.path.join(HUNSPELL_DIR, fname)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip().split('/')[0].strip()
                    if word and not word.isdigit():
                        target.add(word.lower())


def is_correct(word: str, is_cyrillic: bool = True) -> bool:
    """Check if a word is spelled correctly (with full affix support)."""
    _load()
    w = word.strip()
    if not w or len(w) < 2:
        return True

    # Try spylls first (full affix)
    dictionary = _cyrl_dict if is_cyrillic else _lat_dict
    if dictionary:
        return dictionary.lookup(w) or dictionary.lookup(w.lower())

    # Fallback to simple
    if _cyrillic_words is not None:
        words = _cyrillic_words if is_cyrillic else _latin_words
        return w.lower() in words

    return True


def suggest(word: str, is_cyrillic: bool = True, max_suggestions: int = 5) -> list:
    """Get spelling suggestions for a word.
    Priority: sayqallash_rules DB > Hunspell suggest."""
    _load()
    w = word.strip()
    if not w:
        return []

    # PRIORITY 1: Check sayqallash_rules DB for exact correction
    try:
        import db as _db
        conn = _db.connect_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT correct_form FROM sayqallash_rules WHERE LOWER(wrong_form)=LOWER(?) AND lang='uz' ORDER BY frequency DESC LIMIT 1",
            (w,)
        )
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            return [row[0]]  # DB answer is most reliable
    except Exception:
        pass

    # PRIORITY 2: Hunspell suggest
    dictionary = _cyrl_dict if is_cyrillic else _lat_dict
    if dictionary:
        try:
            return list(dictionary.suggest(w))[:max_suggestions]
        except Exception:
            return []

    return []


def check_text(text: str, is_cyrillic: bool = True) -> list:
    """
    Check text for spelling errors with full affix support.
    Returns list of {word, position, end_position, suggestions}.
    """
    _load()
    if not text or not text.strip():
        return []

    errors = []
    pattern = r'[а-яёўқғҳА-ЯЁЎҚҒҲ]+' if is_cyrillic else r"[a-zA-Z'ʻʼ]+"

    for match in re.finditer(pattern, text):
        word = match.group()
        if len(word) < 2:
            continue
        # Skip numbers, abbreviations (all caps < 5 chars)
        if word.isupper() and len(word) < 5:
            continue

        if not is_correct(word, is_cyrillic):
            suggestions = suggest(word, is_cyrillic)
            errors.append({
                'word': word,
                'position': match.start(),
                'end_position': match.end(),
                'suggestions': suggestions
            })

    return errors


def get_stats() -> dict:
    """Get dictionary statistics."""
    _load()
    has_spylls = _cyrl_dict is not None or _lat_dict is not None
    return {
        'engine': 'spylls (full affix)' if has_spylls else 'simple dict',
        'cyrillic': 'loaded' if (_cyrl_dict or _cyrillic_words) else 'not loaded',
        'latin': 'loaded' if (_lat_dict or _latin_words) else 'not loaded',
        'stem_words_cyrl': 95994,
        'stem_words_lat': 95109,
        'affix_rules': 22929,
        'estimated_word_forms': '~2-3 million'
    }
