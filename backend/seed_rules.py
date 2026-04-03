"""
Seed Sayqallash Rules — Generate 5000-10000+ spelling correction rules
Sources:
  - Russian: Common spelling mistakes from ai-forever/spellcheck_benchmark patterns
  - Uzbek: Systematic letter confusion + pharmacy-specific corrections
"""
import sqlite3
import os
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("seed_rules")

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "pharma_editor.db"))

# ═══════════════════════════════════════════════════
# UZBEK SPELLING RULES (Latin/Cyrillic confusion + common errors)
# ═══════════════════════════════════════════════════

UZ_RULES = [
    # --- Ўзбек тилида энг кўп учрайдиган имло хатолари ---
    # Apostrophe errors (o' vs o, g' vs g)
    ("ozbekiston", "o'zbekiston", "S/Apostrophe", "uz"),
    ("togri", "to'g'ri", "S/Apostrophe", "uz"),
    ("kopl", "ko'p", "S/Apostrophe", "uz"),
    ("bolish", "bo'lish", "S/Apostrophe", "uz"),
    ("qoshimcha", "qo'shimcha", "S/Apostrophe", "uz"),
    ("korsatish", "ko'rsatish", "S/Apostrophe", "uz"),
    ("yolgon", "yolg'on", "S/Apostrophe", "uz"),
    ("tori", "to'ri", "S/Apostrophe", "uz"),
    ("goz", "go'z", "S/Apostrophe", "uz"),
    ("organak", "organik", "S/Spelling", "uz"),
    
    # Common letter confusions
    ("фармацевтика", "farmatsevtika", "S/Script", "uz"),
    ("президент", "prezident", "S/Script", "uz"),
    
    # Double letter errors
    ("efekt", "effekt", "S/DoubleL", "uz"),
    ("ofitser", "ofitser", "S/DoubleL", "uz"),
    ("proffessor", "professor", "S/DoubleL", "uz"),
    ("grammer", "grammatika", "S/DoubleL", "uz"),
    ("komissiya", "komissiya", "S/DoubleL", "uz"),
    
    # Pharma-specific Uzbek
    ("dorivor", "dorivor", "P/Pharma", "uz"),
    ("tabletkalar", "tabletkalar", "P/Pharma", "uz"),
    ("vitamn", "vitamin", "P/Pharma", "uz"),
    ("antibiotk", "antibiotik", "P/Pharma", "uz"),
    ("kapsula", "kapsula", "P/Pharma", "uz"),
    ("sirop", "sirop", "P/Pharma", "uz"),
    ("retsept", "retsept", "P/Pharma", "uz"),
    ("dozalash", "dozalash", "P/Pharma", "uz"),
    
    # sh/ch confusion
    ("tashkent", "Toshkent", "S/Spelling", "uz"),
    ("mushkul", "mushkul", "S/Spelling", "uz"),
]

# Systematic Uzbek error generation patterns
UZ_LETTER_CONFUSIONS = [
    # (wrong_char, correct_char, error_type)
    ("a", "o'", "S/Apostrophe"),
    ("o", "o'", "S/Apostrophe"),
    ("g", "g'", "S/Apostrophe"),
    ("u", "o'", "S/Vowel"),
    ("e", "a", "S/Vowel"),
    ("i", "e", "S/Vowel"),
    ("sh", "ch", "S/Consonant"),
    ("ch", "sh", "S/Consonant"),
    ("k", "q", "S/Consonant"),
    ("q", "k", "S/Consonant"),
    ("ng", "n", "S/Consonant"),
    ("ts", "s", "S/Consonant"),
]

# Common Uzbek words with frequent misspellings
UZ_COMMON_WORDS = [
    "bo'lish", "ko'rish", "to'g'ri", "o'zbek", "o'qish", "ko'p", "yo'l",
    "so'z", "go'zal", "mo'ljal", "to'liq", "qo'llab", "po'lat",
    "ko'rsatish", "bo'ladi", "qo'shimcha", "to'plam", "o'rganish",
    "o'zgarish", "ko'chirish", "so'rash", "bo'yicha", "yo'nalish",
    "do'stlik", "mo'min", "no'xat", "ro'yxat", "so'nggi", "to'xtatish",
    "ko'rinish", "bo'sh", "yo'q", "mo'rt", "ko'k", "to'rt", "bo'r",
    "farmatsevtik", "dorivor", "preparat", "tabletka", "kapsula",
    "injeksiya", "tarkib", "dozalash", "ta'sir", "asoratlari",
    "miqdori", "retsept", "shifoxona", "kasalxona", "diagnoz",
    "profilaktika", "gigiyena", "immunitet", "vitamin", "mineral",
    "antioksidant", "ferment", "gormon", "metabolizm", "fiziologiya",
    "patologiya", "farmakologiya", "toksikologiya", "mikrobiologiya",
    "laboratoriya", "sterilizatsiya", "dezinfeksiya", "sertifikat",
    "standart", "sifat", "nazorat", "tekshirish", "tahlil",
]

# ═══════════════════════════════════════════════════
# RUSSIAN SPELLING RULES (Pharma + Common)
# ═══════════════════════════════════════════════════

RU_RULES = [
    # --- Фармацевтическая терминология ---
    ("фармацевт", "фармацевт", "P/Pharma", "ru"),
    ("фармоцевтика", "фармацевтика", "P/Pharma", "ru"),
    ("фармоцевт", "фармацевт", "P/Pharma", "ru"),
    ("фармокология", "фармакология", "P/Pharma", "ru"),
    ("фармокопея", "фармакопея", "P/Pharma", "ru"),
    ("фамакология", "фармакология", "P/Pharma", "ru"),
    ("антибиотк", "антибиотик", "P/Pharma", "ru"),
    ("антибиотек", "антибиотик", "P/Pharma", "ru"),
    ("витамн", "витамин", "P/Pharma", "ru"),
    ("таблетк", "таблетка", "P/Pharma", "ru"),
    ("инекция", "инъекция", "P/Pharma", "ru"),
    ("инъкция", "инъекция", "P/Pharma", "ru"),
    ("иньекция", "инъекция", "P/Pharma", "ru"),
    ("гигиена", "гигиена", "P/Pharma", "ru"),
    ("макрофлора", "микрофлора", "P/Pharma", "ru"),
    ("метоболизм", "метаболизм", "P/Pharma", "ru"),
    ("метобализм", "метаболизм", "P/Pharma", "ru"),
    ("лаборатория", "лаборатория", "P/Pharma", "ru"),
    ("лобаратория", "лаборатория", "P/Pharma", "ru"),
    ("лаборотория", "лаборатория", "P/Pharma", "ru"),
    ("стерелизация", "стерилизация", "P/Pharma", "ru"),
    ("стерилезация", "стерилизация", "P/Pharma", "ru"),
    ("дизинфекция", "дезинфекция", "P/Pharma", "ru"),
    ("дезинфекция", "дезинфекция", "P/Pharma", "ru"),
    ("серитификат", "сертификат", "P/Pharma", "ru"),
    ("сертефикат", "сертификат", "P/Pharma", "ru"),
    ("диагноз", "диагноз", "P/Pharma", "ru"),
    ("диагнос", "диагноз", "P/Pharma", "ru"),
    ("профелактика", "профилактика", "P/Pharma", "ru"),
    ("профилактека", "профилактика", "P/Pharma", "ru"),
    ("имунитет", "иммунитет", "P/Pharma", "ru"),
    ("иммунетет", "иммунитет", "P/Pharma", "ru"),
    ("имуннитет", "иммунитет", "P/Pharma", "ru"),
    ("иммунитед", "иммунитет", "P/Pharma", "ru"),
    ("токсекология", "токсикология", "P/Pharma", "ru"),
    ("микробеология", "микробиология", "P/Pharma", "ru"),
    ("физеология", "физиология", "P/Pharma", "ru"),
    ("патаология", "патология", "P/Pharma", "ru"),
    ("субстанция", "субстанция", "P/Pharma", "ru"),
    ("эксципиент", "эксципиент", "P/Pharma", "ru"),
    ("суспензия", "суспензия", "P/Pharma", "ru"),
    ("суспенсия", "суспензия", "P/Pharma", "ru"),
    ("эмульсия", "эмульсия", "P/Pharma", "ru"),
    ("эмулсия", "эмульсия", "P/Pharma", "ru"),
    
    # --- Общие русские орфографические ошибки ---
    ("агенство", "агентство", "S/Spelling", "ru"),
    ("адекватный", "адекватный", "S/Spelling", "ru"),
    ("будующий", "будущий", "S/Spelling", "ru"),
    ("втечение", "в течение", "S/Spacing", "ru"),
    ("в течении", "в течение", "S/Grammar", "ru"),
    ("вобщем", "в общем", "S/Spacing", "ru"),
    ("вообщем", "в общем", "S/Spacing", "ru"),
    ("вследствии", "вследствие", "S/Grammar", "ru"),
    ("дерматин", "дерматин", "S/Spelling", "ru"),
    ("друшлаг", "дуршлаг", "S/Spelling", "ru"),
    ("естесственно", "естественно", "S/Spelling", "ru"),
    ("извените", "извините", "S/Spelling", "ru"),
    ("инциндент", "инцидент", "S/Spelling", "ru"),
    ("инцедент", "инцидент", "S/Spelling", "ru"),
    ("искренне", "искренне", "S/Spelling", "ru"),
    ("искренно", "искренне", "S/Spelling", "ru"),
    ("итого", "итого", "S/Spelling", "ru"),
    ("колличество", "количество", "S/Spelling", "ru"),
    ("компания", "компания", "S/Spelling", "ru"),
    ("конкретный", "конкретный", "S/Spelling", "ru"),
    ("координально", "кардинально", "S/Spelling", "ru"),
    ("лутше", "лучше", "S/Spelling", "ru"),
    ("лутьше", "лучше", "S/Spelling", "ru"),
    ("мошеничество", "мошенничество", "S/Spelling", "ru"),
    ("навсего", "навсегда", "S/Spelling", "ru"),
    ("насчет", "насчёт", "S/Spelling", "ru"),
    ("нащет", "насчёт", "S/Spelling", "ru"),
    ("не зависимо", "независимо", "S/Spacing", "ru"),
    ("не смотря", "несмотря", "S/Spacing", "ru"),
    ("обезательно", "обязательно", "S/Spelling", "ru"),
    ("обязательство", "обязательство", "S/Spelling", "ru"),
    ("одновременно", "одновременно", "S/Spelling", "ru"),
    ("опастность", "опасность", "S/Spelling", "ru"),
    ("оффициальный", "официальный", "S/Spelling", "ru"),
    ("официальный", "официальный", "S/Spelling", "ru"),
    ("поставщик", "поставщик", "S/Spelling", "ru"),
    ("празник", "праздник", "S/Spelling", "ru"),
    ("прецедент", "прецедент", "S/Spelling", "ru"),
    ("прецендент", "прецедент", "S/Spelling", "ru"),
    ("привелегия", "привилегия", "S/Spelling", "ru"),
    ("привилегия", "привилегия", "S/Spelling", "ru"),
    ("приемлемо", "приемлемо", "S/Spelling", "ru"),
    ("приемлимо", "приемлемо", "S/Spelling", "ru"),
    ("призедент", "президент", "S/Spelling", "ru"),
    ("процесс", "процесс", "S/Spelling", "ru"),
    ("процес", "процесс", "S/Spelling", "ru"),
    ("результат", "результат", "S/Spelling", "ru"),
    ("резолтат", "результат", "S/Spelling", "ru"),
    ("росия", "Россия", "S/Spelling", "ru"),
    ("рассчитывать", "рассчитывать", "S/Spelling", "ru"),
    ("расчитывать", "рассчитывать", "S/Spelling", "ru"),
    ("симптомы", "симптомы", "P/Pharma", "ru"),
    ("семптомы", "симптомы", "P/Pharma", "ru"),
    ("симтомы", "симптомы", "P/Pharma", "ru"),
    ("следующий", "следующий", "S/Spelling", "ru"),
    ("следущий", "следующий", "S/Spelling", "ru"),
    ("сосредоточить", "сосредоточить", "S/Spelling", "ru"),
    ("сосредоточеть", "сосредоточить", "S/Spelling", "ru"),
    ("тоже", "тоже", "S/Spacing", "ru"),
    ("то же", "то же", "S/Spacing", "ru"),
    ("учавствовать", "участвовать", "S/Spelling", "ru"),
    ("чувствовать", "чувствовать", "S/Spelling", "ru"),
    ("чуствовать", "чувствовать", "S/Spelling", "ru"),
    ("щастье", "счастье", "S/Spelling", "ru"),
    ("щетчик", "счётчик", "S/Spelling", "ru"),
    ("экземпляр", "экземпляр", "S/Spelling", "ru"),
    ("экзэмпляр", "экземпляр", "S/Spelling", "ru"),
]

# Russian letter confusion patterns for mass generation
RU_CONFUSIONS = {
    "а": ["о", "я"],
    "о": ["а", "е"],
    "е": ["и", "э"],
    "и": ["е", "ы"],
    "у": ["ю"],
    "с": ["з"],
    "з": ["с"],
    "д": ["т"],
    "т": ["д"],
    "б": ["п"],
    "п": ["б"],
    "г": ["к"],
    "к": ["г"],
    "ж": ["ш"],
    "ш": ["ж"],
    "нн": ["н"],
    "сс": ["с"],
    "лл": ["л"],
    "мм": ["м"],
    "тт": ["т"],
}

# High-frequency Russian pharma/medical words for synthetic error generation
RU_PHARMA_WORDS = [
    "анализ", "аналитический", "антибиотик", "антисептик", "ацетилсалициловая",
    "бактерия", "биохимия", "валидация", "верификация", "витамин",
    "вспомогательное", "гигиена", "глюкоза", "действующее", "дезинфекция",
    "дозировка", "измерение", "иммунитет", "ингредиент", "инструкция",
    "испытание", "калибровка", "капсула", "квалификация", "клинический",
    "количество", "компонент", "концентрация", "контроль", "лаборатория",
    "лекарственное", "лицензия", "маркировка", "метаболизм", "методика",
    "микробиология", "мониторинг", "наименование", "определение", "очистка",
    "параметр", "патология", "показатель", "полимер", "постановление",
    "препарат", "применение", "производство", "протокол", "противопоказание",
    "профилактика", "растворитель", "реагент", "регистрация", "рекомбинантный",
    "результат", "сертификат", "сертификация", "спецификация", "стабильность",
    "стандарт", "стерилизация", "субстанция", "суспензия", "таблетка",
    "тестирование", "технология", "токсикология", "требование", "упаковка",
    "утверждение", "фармакопея", "фармацевтический", "физиология", "фильтрация",
    "формула", "характеристика", "хранение", "эквивалент", "эксперимент",
    "эмульсия", "этикетка",
]

UZ_PHARMA_WORDS = [
    "tahlil", "analitik", "antibiotik", "antiseptik", "atsetilsalitsil",
    "bakteriya", "biokimyo", "validatsiya", "verifikatsiya", "vitamin",
    "yordamchi", "gigiyena", "glyukoza", "ta'sir", "dezinfeksiya",
    "dozalash", "o'lchash", "immunitet", "ingredient", "yo'riqnoma",
    "sinov", "kalibrlash", "kapsula", "kvalifikatsiya", "klinik",
    "miqdor", "komponent", "konsentratsiya", "nazorat", "laboratoriya",
    "dorivor", "litsenziya", "markirovka", "metabolizm", "metodika",
    "mikrobiologiya", "monitoring", "nomenklatura", "aniqlash", "tozalash",
    "parametr", "patologiya", "ko'rsatkich", "polimer", "qaror",
    "preparat", "qo'llash", "ishlab chiqarish", "protokol", "qarshi ko'rsatma",
    "profilaktika", "erituvchi", "reagent", "ro'yxatga olish", "rekombinant",
    "natija", "sertifikat", "sertifikatsiya", "spetsifikatsiya", "barqarorlik",
    "standart", "sterilizatsiya", "substansiya", "suspenziya", "tabletka",
    "sinash", "texnologiya", "toksikologiya", "talab", "qadoqlash",
    "tasdiqlash", "farmakologiya", "farmatsevtik", "fiziologiya", "filtratsiya",
    "formula", "xarakteristika", "saqlash", "ekvivalent", "tajriba",
    "emulsiya", "yorliq",
]


def generate_uz_synthetic_errors(words, max_rules=3000):
    """Generate synthetic Uzbek spelling errors."""
    rules = []
    
    for word in words:
        if len(word) < 3:
            continue
        
        # 1. Remove apostrophe: o' -> o, g' -> g
        if "'" in word:
            wrong = word.replace("'", "")
            if wrong != word:
                rules.append((wrong, word, "S/Apostrophe", "uz"))
        
        # 2. Wrong apostrophe: o' -> o`, o' -> o'
        if "'" in word:
            wrong = word.replace("'", "`")
            rules.append((wrong, word, "S/Apostrophe", "uz"))
        
        # 3. k/q confusion
        if "q" in word:
            wrong = word.replace("q", "k", 1)
            if wrong != word:
                rules.append((wrong, word, "S/Consonant", "uz"))
        if "k" in word and "q" not in word:
            wrong = word.replace("k", "q", 1)
            if wrong != word:
                rules.append((wrong, word, "S/Consonant", "uz"))
        
        # 4. sh/ch confusion
        if "sh" in word:
            wrong = word.replace("sh", "ch", 1)
            if wrong != word:
                rules.append((wrong, word, "S/Consonant", "uz"))
        
        # 5. Double letter omission
        for dl in ["ff", "ss", "ll", "mm", "tt", "nn", "rr", "kk"]:
            if dl in word:
                wrong = word.replace(dl, dl[0], 1)
                if wrong != word:
                    rules.append((wrong, word, "S/DoubleL", "uz"))
        
        # 6. Missing letter
        if len(word) > 4:
            mid = len(word) // 2
            wrong = word[:mid] + word[mid+1:]
            rules.append((wrong, word, "S/Missing", "uz"))
        
        # 7. Swapped adjacent letters
        if len(word) > 3:
            mid = len(word) // 2
            wrong = word[:mid] + word[mid+1] + word[mid] + word[mid+2:]
            if wrong != word:
                rules.append((wrong, word, "S/Swap", "uz"))
        
        if len(rules) >= max_rules:
            break
    
    return rules


def generate_ru_synthetic_errors(words, max_rules=3000):
    """Generate synthetic Russian spelling errors."""
    rules = []
    
    for word in words:
        if len(word) < 3:
            continue
        word_lower = word.lower()
        
        # 1. Vowel confusion (а/о, е/и, etc.)
        for correct_char, wrong_chars in RU_CONFUSIONS.items():
            if correct_char in word_lower:
                for wc in wrong_chars:
                    wrong = word_lower.replace(correct_char, wc, 1)
                    if wrong != word_lower:
                        rules.append((wrong, word_lower, "S/Vowel", "ru"))
        
        # 2. Missing letter
        if len(word) > 4:
            mid = len(word) // 2
            wrong = word_lower[:mid] + word_lower[mid+1:]
            rules.append((wrong, word_lower, "S/Missing", "ru"))
        
        # 3. Double letter error
        for dl in ["нн", "сс", "лл", "мм", "тт"]:
            if dl in word_lower:
                wrong = word_lower.replace(dl, dl[0], 1)
                if wrong != word_lower:
                    rules.append((wrong, word_lower, "S/DoubleL", "ru"))
        
        # 4. Extra letter
        if len(word) > 3:
            mid = len(word) // 2
            wrong = word_lower[:mid] + word_lower[mid] + word_lower[mid:]
            if wrong != word_lower:
                rules.append((wrong, word_lower, "S/Extra", "ru"))
        
        # 5. Swapped adjacent letters
        if len(word) > 3:
            mid = len(word) // 2
            chars = list(word_lower)
            chars[mid], chars[mid+1] = chars[mid+1], chars[mid]
            wrong = "".join(chars)
            if wrong != word_lower:
                rules.append((wrong, word_lower, "S/Swap", "ru"))
        
        if len(rules) >= max_rules:
            break
    
    return rules


def get_dictionary_words(db_path, limit=2000):
    """Get high-frequency words from tahrirchi dictionary for rule generation."""
    tahrirchi_path = os.path.join(os.path.dirname(db_path), "tahrirchi.db")
    if not os.path.exists(tahrirchi_path):
        return []
    
    conn = sqlite3.connect(tahrirchi_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT word FROM dictionary WHERE length(word) >= 4 AND frequency > 1000 ORDER BY frequency DESC LIMIT ?",
        (limit,)
    )
    words = [r[0] for r in cursor.fetchall()]
    conn.close()
    return words


def seed_rules():
    """Main seeding function."""
    logger.info("=" * 60)
    logger.info("SAYQALLASH RULES SEEDER")
    logger.info("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check current count
    cursor.execute("SELECT COUNT(*) FROM sayqallash_rules")
    current = cursor.fetchone()[0]
    logger.info(f"Current rules: {current}")
    
    all_rules = []
    
    # 1. Manual curated rules (high confidence)
    logger.info("[1/4] Adding curated rules...")
    valid_uz = [(w, c, t, l) for w, c, t, l in UZ_RULES if w.strip() != c.strip()]
    valid_ru = [(w, c, t, l) for w, c, t, l in RU_RULES if w.strip() != c.strip()]
    all_rules.extend(valid_uz)
    all_rules.extend(valid_ru)
    logger.info(f"      Curated: {len(valid_uz)} UZ + {len(valid_ru)} RU")
    
    # 2. Synthetic Uzbek errors from pharma words
    logger.info("[2/4] Generating synthetic Uzbek errors...")
    uz_dict_words = get_dictionary_words(DB_PATH, limit=2000)
    uz_source = UZ_PHARMA_WORDS + UZ_COMMON_WORDS + uz_dict_words
    uz_synthetic = generate_uz_synthetic_errors(uz_source, max_rules=3500)
    all_rules.extend(uz_synthetic)
    logger.info(f"      Synthetic UZ: {len(uz_synthetic)}")
    
    # 3. Synthetic Russian errors from pharma words
    logger.info("[3/4] Generating synthetic Russian errors...")
    ru_synthetic = generate_ru_synthetic_errors(RU_PHARMA_WORDS, max_rules=3500)
    all_rules.extend(ru_synthetic)
    logger.info(f"      Synthetic RU: {len(ru_synthetic)}")
    
    # 4. Deduplicate
    logger.info("[4/4] Deduplicating and inserting...")
    seen = set()
    unique_rules = []
    for wrong, correct, etype, lang in all_rules:
        key = (wrong.strip().lower(), correct.strip().lower(), lang)
        if key not in seen and wrong.strip().lower() != correct.strip().lower():
            seen.add(key)
            unique_rules.append((wrong.strip(), correct.strip(), etype, lang))
    
    # Insert rules
    inserted = 0
    for wrong, correct, etype, lang in unique_rules:
        try:
            cursor.execute(
                """INSERT OR IGNORE INTO sayqallash_rules 
                   (wrong_form, correct_form, error_type, context, lang, frequency, source)
                   VALUES (?, ?, ?, '', ?, 1, 'seed')""",
                (wrong, correct, etype, lang)
            )
            if cursor.rowcount > 0:
                inserted += 1
        except Exception as e:
            pass
    
    conn.commit()
    
    # Final count
    cursor.execute("SELECT COUNT(*) FROM sayqallash_rules")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT lang, COUNT(*) FROM sayqallash_rules GROUP BY lang")
    by_lang = cursor.fetchall()
    conn.close()
    
    logger.info(f"\n{'='*60}")
    logger.info(f"RESULTS:")
    logger.info(f"  New rules inserted: {inserted}")
    logger.info(f"  Total rules now: {total}")
    for lang, count in by_lang:
        logger.info(f"  {lang}: {count} rules")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    seed_rules()
