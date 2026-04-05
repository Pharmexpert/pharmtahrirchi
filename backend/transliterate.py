"""
Ўзбек тили кирилл ↔ лотин конвертация модули
Расмий стандартга мувофиқ (O'zbekiston Respublikasi Вазирлар Маҳкамаси)
"""

# ═══════════════════════════════════════════════════════════
#  Кирилл → Лотин маппинг
# ═══════════════════════════════════════════════════════════

CYRILLIC_TO_LATIN = {
    # Диграфлар — аввал текширилади (тартиб муҳим!)
    'Ўз': 'Oʻz',

    # Бош ҳарфлар
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
    'Е': 'E', 'Ё': 'Yo', 'Ж': 'J', 'З': 'Z', 'И': 'I',
    'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
    'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
    'У': 'U', 'Ф': 'F', 'Х': 'X', 'Ц': 'Ts', 'Ч': 'Ch',
    'Ш': 'Sh', 'Щ': 'Sh', 'Ъ': 'ʼ', 'Ы': 'I', 'Ь': '',
    'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',

    # Ўзбекча махсус
    'Ў': 'Oʻ', 'Қ': 'Q', 'Ғ': 'Gʻ', 'Ҳ': 'H',

    # Кичик ҳарфлар
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
    'е': 'e', 'ё': 'yo', 'ж': 'j', 'з': 'z', 'и': 'i',
    'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
    'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
    'у': 'u', 'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch',
    'ш': 'sh', 'щ': 'sh', 'ъ': 'ʼ', 'ы': 'i', 'ь': '',
    'э': 'e', 'ю': 'yu', 'я': 'ya',

    # Ўзбекча махсус (кичик)
    'ў': 'oʻ', 'қ': 'q', 'ғ': 'gʻ', 'ҳ': 'h',
}

# ═══════════════════════════════════════════════════════════
#  Лотин → Кирилл маппинг
# ═══════════════════════════════════════════════════════════

# Диграфлар — олдин текширилиши керак
LATIN_DIGRAPHS_TO_CYRILLIC = {
    # Бош ҳарфлар
    'Yo': 'Ё', 'YO': 'Ё', 'Ch': 'Ч', 'CH': 'Ч',
    'Sh': 'Ш', 'SH': 'Ш', 'Ts': 'Ц', 'TS': 'Ц',
    'Yu': 'Ю', 'YU': 'Ю', 'Ya': 'Я', 'YA': 'Я',
    "Oʻ": 'Ў', "O'": 'Ў', "O`": 'Ў', "O\u2018": 'Ў', "O\u2019": 'Ў',
    "Gʻ": 'Ғ', "G'": 'Ғ', "G`": 'Ғ', "G\u2018": 'Ғ', "G\u2019": 'Ғ',
    # Кичик ҳарфлар
    'yo': 'ё', 'ch': 'ч', 'sh': 'ш', 'ts': 'ц',
    'yu': 'ю', 'ya': 'я',
    "oʻ": 'ў', "o'": 'ў', "o`": 'ў', "o\u2018": 'ў', "o\u2019": 'ў',
    "gʻ": 'ғ', "g'": 'ғ', "g`": 'ғ', "g\u2018": 'ғ', "g\u2019": 'ғ',
}

LATIN_SINGLE_TO_CYRILLIC = {
    # Бош ҳарфлар
    'A': 'А', 'B': 'Б', 'D': 'Д', 'E': 'Е',
    'F': 'Ф', 'G': 'Г', 'H': 'Ҳ', 'I': 'И',
    'J': 'Ж', 'K': 'К', 'L': 'Л', 'M': 'М',
    'N': 'Н', 'O': 'О', 'P': 'П', 'Q': 'Қ',
    'R': 'Р', 'S': 'С', 'T': 'Т', 'U': 'У',
    'V': 'В', 'X': 'Х', 'Y': 'Й', 'Z': 'З',
    # Кичик ҳарфлар
    'a': 'а', 'b': 'б', 'd': 'д', 'e': 'е',
    'f': 'ф', 'g': 'г', 'h': 'ҳ', 'i': 'и',
    'j': 'ж', 'k': 'к', 'l': 'л', 'm': 'м',
    'n': 'н', 'o': 'о', 'p': 'п', 'q': 'қ',
    'r': 'р', 's': 'с', 't': 'т', 'u': 'у',
    'v': 'в', 'x': 'х', 'y': 'й', 'z': 'з',
}

# ═══════════════════════════════════════════════════════════
#  КОНВЕРТАЦИЯ ФУНКЦИЯЛАРИ
# ═══════════════════════════════════════════════════════════

def is_cyrillic(text):
    """Матн кирилл алифбосидами?"""
    cyrillic_count = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    latin_count = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    return cyrillic_count > latin_count


def is_latin(text):
    """Матн лотин алифбосидами?"""
    return not is_cyrillic(text)


def to_latin(text):
    """Кирилл матнни лотин алифбосига ўгириш"""
    if not text:
        return text

    result = []
    i = 0
    while i < len(text):
        char = text[i]

        # Кирилл ҳарфми?
        if char in CYRILLIC_TO_LATIN:
            # "Е" сўз бошида → "Ye"
            if char in ('Е', 'е') and (i == 0 or not text[i-1].isalpha()):
                result.append('Ye' if char == 'Е' else 'ye')
            else:
                result.append(CYRILLIC_TO_LATIN[char])
        else:
            result.append(char)
        i += 1

    return ''.join(result)


def to_cyrillic(text):
    """Лотин матнни кирилл алифбосига ўгириш"""
    if not text:
        return text

    result = []
    i = 0
    length = len(text)

    while i < length:
        matched = False

        # 3 ҳарфли комбинациялар (oʻ, gʻ ва ҳ.к.)
        if i + 2 < length:
            tri = text[i:i+3]
            # Апостроф вариантлари
            for key, val in LATIN_DIGRAPHS_TO_CYRILLIC.items():
                if len(key) == 3 and tri == key:
                    result.append(val)
                    i += 3
                    matched = True
                    break
            if matched:
                continue

        # 2 ҳарфли диграфлар
        if i + 1 < length:
            di = text[i:i+2]
            if di in LATIN_DIGRAPHS_TO_CYRILLIC:
                result.append(LATIN_DIGRAPHS_TO_CYRILLIC[di])
                i += 2
                continue

        # 1 ҳарфли маппинг
        char = text[i]
        if char in LATIN_SINGLE_TO_CYRILLIC:
            result.append(LATIN_SINGLE_TO_CYRILLIC[char])
        else:
            result.append(char)
        i += 1

    return ''.join(result)


def normalize_for_lookup(word):
    """
    Сўзни луғатдан қидириш учун нормаллаш.
    Иккала вариантда қайтаради: [latin_form, cyrillic_form]
    """
    word_lower = word.lower().strip()
    if not word_lower:
        return []

    if is_cyrillic(word_lower):
        latin_form = to_latin(word_lower)
        return [word_lower, latin_form]
    else:
        cyrillic_form = to_cyrillic(word_lower)
        return [word_lower, cyrillic_form]


def convert_text(text, target='latin'):
    """
    Матнни мақсад алифбосига ўгириш.
    target: 'latin' ёки 'cyrillic'
    """
    if target == 'latin':
        return to_latin(text)
    elif target == 'cyrillic':
        return to_cyrillic(text)
    return text


def cross_alphabet_variants(text):
    """
    Қидирув учун матнни ҳар иккала алифбода қайтаради.
    Returns both Cyrillic and Latin variants for cross-alphabet search.
    """
    if not text or not text.strip():
        return []
    text = text.strip()
    variants = [text]
    if is_cyrillic(text):
        latin = to_latin(text)
        if latin and latin != text:
            variants.append(latin)
    else:
        cyrillic = to_cyrillic(text)
        if cyrillic and cyrillic != text:
            variants.append(cyrillic)
    return variants


# ═══════════════════════════════════════════════════════════
#  ТЕСТ
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    test_cyrillic = [
        "Вазирлар Маҳкамасининг қарори",
        "Фармакология фанининг асослари",
        "Ўзбекистон Республикаси",
        "Дори воситалари ишлаб чиқариш",
        "Ёшлар учун",
    ]

    test_latin = [
        "Vazirlar Mahkamasining qarori",
        "Farmakologiya fanining asoslari",
        "O'zbekiston Respublikasi",
        "Dori vositalari ishlab chiqarish",
        "Yoshlar uchun",
    ]

    print("=" * 60)
    print("  Кирилл → Лотин")
    print("=" * 60)
    for text in test_cyrillic:
        latin = to_latin(text)
        print(f"  {text}")
        print(f"  → {latin}")
        print()

    print("=" * 60)
    print("  Лотин → Кирилл")
    print("=" * 60)
    for text in test_latin:
        cyrillic = to_cyrillic(text)
        print(f"  {text}")
        print(f"  → {cyrillic}")
        print()

    print("=" * 60)
    print("  normalize_for_lookup")
    print("=" * 60)
    for word in ["маҳкама", "farmakologiya", "Ўзбекистон", "prezident"]:
        variants = normalize_for_lookup(word)
        print(f"  {word} → {variants}")
