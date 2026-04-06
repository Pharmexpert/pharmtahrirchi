"""
Hunspell луғат ва affix маълумотларини бошқариш модули.
- get_dictionary_words(): барча сўзларни оладиган
- get_affix_flags(): барча SFX гуруҳларни тавсифлари билан
- get_rep_rules(): REP алмаштириш қоидалари
"""
import os
import re

HUNSPELL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hunspell")

# Affix flag тавсифлари (Sifat/o'xshatish, 1-shaxs egalik, ...)
FLAG_DESCRIPTIONS = {
    'A': 'Сифат/ўхшатиш қўшимчалари',
    'B': '1-шахс эгалик (унлисиз)',
    'C': '1-шахс эгалик (унлидан кейин)',
    'D': '2-шахс эгалик',
    'E': 'Ундош алмашуви (-к → +г)',
    'F': 'Феъл шакллари',
    'G': 'Грамматик категория',
    'H': 'Ҳол қўшимчалари',
    'I': 'Юклама (-ки, -ми, -чи, -ку)',
    'J': 'Феъл (эканлик)',
    'K': 'Сўроқ (микан, миканми)',
    'L': '2-шахс сўроқ (мисан, мисиз)',
    'M': 'Эгалик + сифат (-лигим, -лигинг)',
    'N': 'Жой/йўналиш',
    'P': 'Префикс',
    'Q': '1-шахс феъл (-ам, -амки)',
    'R': 'Қўшимча белги',
    'S': 'Кўплик (-лар, -ларни)',
    'T': 'Тус ўзгариши',
    'U': 'Уйғунлик',
    'V': 'Келишик (-дан, -да, -ни, -га)',
    'W': 'Тартиб',
    'X': 'Феъл тусланиши (-син, -май, -ган, -моқда)',
    'Y': 'Йордамчи',
    'Z': 'Зарф',
    'q': 'Эгалик кичик ҳарф',
    '-': 'Махсус белги (тире)',
}


_dict_cache = None
_aff_cache = None


def get_dictionary_words(language='cyrl', limit=None):
    """
    Барча луғат сўзларини олиш.
    language: 'cyrl' or 'lat'
    Returns: list of {word, pos, flags, language}
    """
    global _dict_cache
    if _dict_cache is None:
        _dict_cache = {}

    cache_key = f"dic_{language}"
    if cache_key in _dict_cache:
        return _dict_cache[cache_key][:limit] if limit else _dict_cache[cache_key]

    fname = "uz_UZ_Cyrl.dic" if language == 'cyrl' else "uz_UZ.dic"
    path = os.path.join(HUNSPELL_DIR, fname)
    if not os.path.exists(path):
        return []

    words = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.isdigit():
                continue
            if '/' in line:
                word, flags = line.split('/', 1)
            else:
                word, flags = line, ''
            if not word or word.startswith('#'):
                continue
            words.append({
                'word': word,
                'flags': flags,
                'language': language,
                'pos': _detect_pos(flags)
            })

    _dict_cache[cache_key] = words
    return words[:limit] if limit else words


def _detect_pos(flags):
    """Affix flags асосида сўз туркумини аниқлаш."""
    if not flags:
        return 'noun'
    if 'X' in flags or 'Q' in flags or 'F' in flags:
        return 'verb'
    if 'A' in flags:
        return 'adj'
    if 'Z' in flags:
        return 'adv'
    if 'B' in flags or 'C' in flags or 'V' in flags or 'S' in flags:
        return 'noun'
    return 'other'


def get_affix_flags(language='cyrl'):
    """
    Affix flag гуруҳларини тўлиқ маълумоти билан олиш.
    Returns: list of {flag, count, description, examples}
    """
    global _aff_cache
    if _aff_cache is None:
        _aff_cache = {}

    cache_key = f"aff_{language}"
    if cache_key in _aff_cache:
        return _aff_cache[cache_key]

    fname = "uz_UZ_Cyrl.aff" if language == 'cyrl' else "uz_UZ.aff"
    path = os.path.join(HUNSPELL_DIR, fname)
    if not os.path.exists(path):
        return []

    flags = {}  # flag → list of rules
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 4 and parts[0] == 'SFX' and parts[2] not in ('Y', 'N'):
                flag = parts[1]
                if flag not in flags:
                    flags[flag] = []
                remove = '' if parts[2] == '0' else parts[2]
                add = '' if parts[3] == '0' else parts[3]
                flags[flag].append({'remove': remove, 'add': add})
            elif len(parts) >= 4 and parts[0] == 'PFX' and parts[2] not in ('Y', 'N'):
                flag = 'PFX_' + parts[1]
                if flag not in flags:
                    flags[flag] = []
                remove = '' if parts[2] == '0' else parts[2]
                add = '' if parts[3] == '0' else parts[3]
                flags[flag].append({'remove': remove, 'add': add})

    result = []
    for flag, rules in flags.items():
        result.append({
            'flag': flag,
            'count': len(rules),
            'description': FLAG_DESCRIPTIONS.get(flag, 'Махсус қоида'),
            'examples': rules[:10],
            'language': language
        })

    result.sort(key=lambda x: -x['count'])
    _aff_cache[cache_key] = result
    return result


def get_rep_rules(language='cyrl'):
    """
    REP (replacement) қоидаларини олиш.
    Returns: list of {wrong, correct}
    """
    fname = "uz_UZ_Cyrl.aff" if language == 'cyrl' else "uz_UZ.aff"
    path = os.path.join(HUNSPELL_DIR, fname)
    if not os.path.exists(path):
        return []

    rules = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 3 and parts[0] == 'REP':
                rules.append({'wrong': parts[1], 'correct': parts[2]})

    return rules


def import_rep_to_sayqallash():
    """REP қоидаларини sayqallash_rules жадвалига импорт қилиш."""
    import db
    rules = get_rep_rules('cyrl') + get_rep_rules('lat')
    conn = db.connect_db()
    cursor = conn.cursor()
    count = 0
    for r in rules:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO sayqallash_rules
                    (wrong_form, correct_form, error_type, lang, source, frequency)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (r['wrong'], r['correct'], 'REP/Hunspell', 'uz', 'hunspell_rep', 1))
            count += cursor.rowcount
        except Exception:
            pass
    conn.commit()
    conn.close()
    return count
