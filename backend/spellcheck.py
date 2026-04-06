"""
Ўзбек тили имло текширгичи — uz-hunspell асосида.
Hunspell луғатлари: uz_UZ_Cyrl (кирилл) ва uz_UZ (лотин).
Tier 0 сифатида Sayqallash пайплайнига интеграция қилинган.
"""
import os
import re
import logging

logger = logging.getLogger("spellcheck")

HUNSPELL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hunspell")

# In-memory dictionary sets for fast lookup
_cyrillic_words = set()
_latin_words = set()
_loaded = False


def _load_dictionaries():
    """Load hunspell .dic files into memory sets."""
    global _cyrillic_words, _latin_words, _loaded
    if _loaded:
        return

    # Load Cyrillic dictionary
    cyrl_path = os.path.join(HUNSPELL_DIR, "uz_UZ_Cyrl.dic")
    if os.path.exists(cyrl_path):
        with open(cyrl_path, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip().split('/')[0].strip()  # Remove affix flags
                if word and not word.isdigit():
                    _cyrillic_words.add(word.lower())
        logger.info(f"[+] Cyrillic dictionary loaded: {len(_cyrillic_words)} words")

    # Load Latin dictionary
    lat_path = os.path.join(HUNSPELL_DIR, "uz_UZ.dic")
    if os.path.exists(lat_path):
        with open(lat_path, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip().split('/')[0].strip()
                if word and not word.isdigit():
                    _latin_words.add(word.lower())
        logger.info(f"[+] Latin dictionary loaded: {len(_latin_words)} words")

    _loaded = True


def is_correct(word: str, is_cyrillic: bool = True) -> bool:
    """Check if a word is spelled correctly."""
    _load_dictionaries()
    w = word.lower().strip()
    if not w or len(w) < 2:
        return True  # Skip very short words

    dictionary = _cyrillic_words if is_cyrillic else _latin_words
    return w in dictionary


def check_text(text: str, is_cyrillic: bool = True) -> list:
    """
    Check text for spelling errors.
    Returns list of {word, position, suggestions}.
    """
    _load_dictionaries()
    if not text or not text.strip():
        return []

    dictionary = _cyrillic_words if is_cyrillic else _latin_words
    if not dictionary:
        return []

    errors = []
    # Split into words preserving positions
    for match in re.finditer(r'[а-яёўқғҳА-ЯЁЎҚҒҲ]+|[a-zA-Z\'ʻʼ]+', text):
        word = match.group()
        if len(word) < 2:
            continue
        if word.lower() not in dictionary:
            # Try to find suggestions
            suggestions = _suggest(word.lower(), dictionary)
            errors.append({
                'word': word,
                'position': match.start(),
                'end_position': match.end(),
                'suggestions': suggestions[:5]
            })

    return errors


def _suggest(word: str, dictionary: set, max_distance: int = 2) -> list:
    """Find similar words in dictionary (simple edit distance)."""
    if not word:
        return []

    candidates = []

    # 1. Prefix match
    prefix = word[:max(3, len(word) - 2)]
    for dict_word in dictionary:
        if dict_word.startswith(prefix) and abs(len(dict_word) - len(word)) <= max_distance:
            dist = _edit_distance(word, dict_word)
            if 0 < dist <= max_distance:
                candidates.append((dict_word, dist))

    # 2. Sort by distance
    candidates.sort(key=lambda x: x[1])
    return [c[0] for c in candidates[:5]]


def _edit_distance(s1: str, s2: str) -> int:
    """Simple Levenshtein distance."""
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2 + 1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]


def get_stats() -> dict:
    """Get dictionary statistics."""
    _load_dictionaries()
    return {
        'cyrillic_words': len(_cyrillic_words),
        'latin_words': len(_latin_words),
        'loaded': _loaded
    }
