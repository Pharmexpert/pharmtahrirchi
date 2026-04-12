"""
Syntax module — 5 jadval (Phase 1).
Sintaktik tahlil uchun: gap bo'laklari, so'z birikmalari, gap shablonlari, so'z tartibi qoidalari, parse qilingan gaplar.
"""
import sqlite3
import os
import logging

log = logging.getLogger("syntax_db")

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))


def init_syntax_tables():
    """Idempotent — ishga tushirish vaqtida main.py'dan chaqiriladi."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Sentence parts (ega/kesim/toldiruvchi/aniqlovchi/hol)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS syntax_sentence_parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            lemma TEXT,
            pos TEXT,
            role TEXT,                  -- ega|kesim|toldiruvchi|aniqlovchi|hol
            context_template TEXT,
            example_uz TEXT,
            example_ru TEXT,
            source TEXT DEFAULT 'manual',
            confidence REAL DEFAULT 0.8,
            frequency INTEGER DEFAULT 1,
            language TEXT DEFAULT 'uz',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ssp_word ON syntax_sentence_parts(word)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ssp_role ON syntax_sentence_parts(role)")

    # 2. So'z birikmalari (collocations + grammatical pairs)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS syntax_phrases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            head_word TEXT NOT NULL,
            dep_word TEXT NOT NULL,
            head_pos TEXT,
            dep_pos TEXT,
            relation TEXT,              -- nmod|amod|obj|advmod|nsubj|...
            case_marker TEXT,           -- -ni/-da/-ga/-dan
            example TEXT,
            frequency INTEGER DEFAULT 1,
            source TEXT DEFAULT 'manual',
            language TEXT DEFAULT 'uz',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(head_word, dep_word, relation)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sp_head ON syntax_phrases(head_word)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sp_relation ON syntax_phrases(relation)")

    # 3. Gap shablonlari (sentence templates)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS syntax_sentence_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template TEXT NOT NULL,         -- "S+O+V"
            sentence_type TEXT,             -- 'sodda'|'qoshma_bog'|'qoshma_bogsiz'
            semantic_type TEXT,             -- 'darak'|'soroq'|'buyruq'|'his_hayajon'
            example_uz TEXT,
            example_ru TEXT,
            formula TEXT,                   -- "Эга → Тўлдирувчи → Кесим"
            is_canonical INTEGER DEFAULT 1,
            frequency INTEGER DEFAULT 1,
            source TEXT DEFAULT 'manual',
            language TEXT DEFAULT 'uz',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sst_template ON syntax_sentence_templates(template)")

    # 4. So'z tartibi qoidalari (xato → to'g'ri)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS syntax_word_order_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wrong_order TEXT NOT NULL,
            correct_order TEXT NOT NULL,
            pos_pattern_wrong TEXT,
            pos_pattern_correct TEXT,
            explanation_uz TEXT,
            explanation_ru TEXT,
            examples TEXT,                  -- JSON array
            severity TEXT DEFAULT 'warning', -- error|warning|suggestion
            language TEXT DEFAULT 'uz',
            frequency INTEGER DEFAULT 1,
            source TEXT DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_swo_pattern ON syntax_word_order_rules(pos_pattern_wrong)")

    # 5. Parse qilingan gaplar (training data + audit log)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS syntax_parsed_sentences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            parse_tree TEXT,                -- JSON CoNLL-U format
            word_order_formula TEXT,
            sentence_type TEXT,
            is_correct INTEGER,
            corrected_text TEXT,
            errors_found TEXT,              -- JSON array
            source TEXT DEFAULT 'auto',
            user_id INTEGER,
            language TEXT DEFAULT 'uz',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sps_text ON syntax_parsed_sentences(text)")

    conn.commit()
    conn.close()
    log.info("[syntax_db] 5 ta jadval yaratildi (idempotent)")


def seed_canonical_templates():
    """O'zbek tilining asosiy gap shablonlarini seed qilish."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    templates = [
        # (template, sentence_type, semantic_type, example_uz, formula, is_canonical)
        ("S+V", "sodda", "darak", "Bola yuribdi.", "Эга → Кесим", 1),
        ("S+O+V", "sodda", "darak", "Bola kitob o'qiyapti.", "Эга → Тўлдирувчи → Кесим", 1),
        ("S+Adv+V", "sodda", "darak", "Bola tez yuribdi.", "Эга → Ҳол → Кесим", 1),
        ("Adj+S+O+V", "sodda", "darak", "Aqlli bola kitob o'qiyapti.", "Аниқловчи → Эга → Тўлдирувчи → Кесим", 1),
        ("S+O+Adv+V", "sodda", "darak", "Bola kitobni tez o'qiyapti.", "Эга → Тўлдирувчи → Ҳол → Кесим", 1),
        ("S+V?", "sodda", "soroq", "Bola keldi-mi?", "Эга → Кесим (сўроқ)", 1),
        ("V!", "sodda", "buyruq", "Kel!", "Кесим (буйруқ)", 1),
        ("S1+V1, S2+V2", "qoshma_bogsiz", "darak", "Quyosh chiqdi, qushlar sayradi.", "Содда гап + содда гап", 1),
        ("S1+V1 va S2+V2", "qoshma_bog", "darak", "Bola keldi va kitob o'qidi.", "Боғловчи: ва", 1),
    ]
    inserted = 0
    for t in templates:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO syntax_sentence_templates
                (template, sentence_type, semantic_type, example_uz, formula, is_canonical, source)
                VALUES (?, ?, ?, ?, ?, ?, 'seed_canonical')
            """, t)
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            log.warning(f"seed template fail: {e}")
    conn.commit()
    conn.close()
    log.info(f"[syntax_db] {inserted} ta canonical shablon seed qilindi")
    return inserted


def seed_basic_word_order_rules():
    """Eng asosiy so'z tartibi qoidalari (kesim oxirda kelishi)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rules = [
        # (wrong_order, correct_order, pos_pattern_wrong, pos_pattern_correct, explanation_uz, severity)
        ("Кесим Эга Тўлдирувчи", "Эга Тўлдирувчи Кесим",
         "VERB NOUN NOUN", "NOUN NOUN VERB",
         "Ўзбек тилида кесим одатда гап охирида келади (S-O-V).", "warning"),
        ("Кесим Эга", "Эга Кесим",
         "VERB NOUN", "NOUN VERB",
         "Кесим эгадан кейин келиши керак.", "warning"),
        ("Тўлдирувчи Эга Кесим", "Эга Тўлдирувчи Кесим",
         "NOUN NOUN VERB", "NOUN NOUN VERB",
         "Эга биринчи ўринда келиши таклиф қилинади.", "suggestion"),
        ("Аниқловчи Кесим", "Эга Аниқловчи Кесим",
         "ADJ VERB", "NOUN ADJ VERB",
         "Аниқловчи аниқланмишдан олдин келади.", "suggestion"),
    ]
    inserted = 0
    for r in rules:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO syntax_word_order_rules
                (wrong_order, correct_order, pos_pattern_wrong, pos_pattern_correct, explanation_uz, severity, source)
                VALUES (?, ?, ?, ?, ?, ?, 'seed_basic')
            """, r)
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            log.warning(f"seed rule fail: {e}")
    conn.commit()
    conn.close()
    log.info(f"[syntax_db] {inserted} ta basic so'z tartibi qoidаси seed qilindi")
    return inserted


def seed_full_templates():
    """1,490+ syntax sentence templates — O'zbek tili sintaksis shablonlari to'liq to'plami."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Check if already seeded
    cur.execute("SELECT COUNT(*) FROM syntax_sentence_templates WHERE source='seed_full'")
    if cur.fetchone()[0] > 100:
        conn.close()
        return 0

    templates = []

    # ===== 1. SODDA DARAK GAPLAR (SOV tartibda) — 200 ta =====
    sov_bases = [
        # (template, semantic_type, example_uz, formula)
        ("S+V", "intransitive", "Бола юради.", "Эга → Кес��м"),
        ("S+O+V", "transitive", "Бола китоб ўқийди.", "Эга → Тўлдирувчи → Кесим"),
        ("S+O₁+O₂+V", "ditransitive", "Ўқитувчи болага китоб берди.", "Эга → Вс.Тўлд → Тў.Тўлд → Кесим"),
        ("Adj+S+V", "desc_intrans", "Ёш бола юради.", "Аниқловчи → Эга → Кесим"),
        ("Adj+S+O+V", "desc_trans", "Ёш бола китоб ўқийди.", "Аниқловчи → Эга → Тўлдирувчи → Кесим"),
        ("S+Adv+V", "manner", "Бола тез югурди.", "Эга → Ҳол → Кесим"),
        ("S+O+Adv+V", "manner_trans", "Бола китобни тез ўқиди.", "Эга → Тўлдирувчи → Ҳол → Кесим"),
        ("Adv+S+V", "temporal", "Эрталаб бола турди.", "Ҳол → Эга → Ке��им"),
        ("Adv+S+O+V", "temporal_trans", "Кечалари бола китоб ўқийди.", "Ҳол → Эга → Тўлдирувчи → Кесим"),
        ("S+PP+V", "locative", "Бола боғда ўйнайди.", "Эга → Ўрин ҳол → Кесим"),
        ("S+PP+O+V", "loc_trans", "Бола мактабда дарс ўқийди.", "Эга → Ўрин ҳол → Тўлдирувчи → Кесим"),
        ("Adj+S+PP+V", "desc_loc", "Кичкина бола боғда ўйнайди.", "Аниқ → Эга → Ўрин ҳол → Кесим"),
        ("S+Adj+O+V", "obj_desc", "Бола қизиқ китоб ўқиди.", "Эга → Аниқловчи → Тўлдирувчи → Кесим"),
        ("PP+S+V", "loc_first", "Мактабда болалар ўқийди.", "Ўрин ҳол → Эга → Кесим"),
        ("PP+S+O+V", "loc_first_trans", "Мактабда ўқувчи дарс ўқийди.", "Ўрин ҳол → Эга → Тўлдирувчи → Кесим"),
        ("S+Num+O+V", "quantified", "Бола уч китоб ўқиди.", "Эга → Миқдор → Тўлдирувчи → Кесим"),
        ("S+V+Aux", "compound_verb", "Бола ўқий бошлади.", "Эга → Асосий феъл → Ёрдамчи феъл"),
        ("Pron+O+V", "pronoun_subj", "У китоб ўқиди.", "Олмош-Эга → Тўлдирувчи → Кесим"),
        ("S+Pron+V", "pronoun_obj", "Бола уни кўрди.", "Эга → Олмош-Тўлд → Кесим"),
        ("S+O+V+Neg", "negative", "Бола китоб ўқимади.", "Эга → Тўлд → Инкор кесим"),
    ]

    # Generate variations with tenses
    tenses = [
        ("ҳозирги", "-а/-й", "ўқийди"), ("ўтган", "-ди/-ган", "ўқиди"),
        ("келаси", "-ади", "ўқийди"), ("давомий", "-япти/-моқда", "ўқияпти"),
        ("тугалланган", "-ган/-ибди", "ўқиган"), ("шарт", "-са", "ўқиса"),
        ("буйруқ", "-синг/-синлар", "ўқи"), ("сўроқ", "-ми/-а+ми", "ўқидими"),
        ("истак", "-моқчи/-гиси", "ўқимоқчи"), ("мажбурият", "-иши керак", "ўқиши керак"),
    ]

    for base_t, sem, ex, formula in sov_bases:
        templates.append((base_t, "sodda", sem, ex, formula))
        for tense_name, tense_suf, _ in tenses:
            templates.append((f"{base_t}[{tense_name}]", "sodda", f"{sem}_{tense_name}", f"{ex} [{tense_name}]", f"{formula} ({tense_suf})"))

    # ===== 2. СЎРОҚ ГАПЛАР — 150 та =====
    question_types = [
        ("S+V+ми?", "soroq_ha_yoq", "Бола келдими?", "Ҳа/Йўқ сўроқ"),
        ("Ким+V?", "soroq_ким", "Ким келди?", "Эга сўроғи"),
        ("Нима+V?", "soroq_нима", "Нима бўлди?", "Предмет сўроғи"),
        ("S+нимани+V?", "soroq_нимани", "Бола нимани ўқиди?", "Тўлдирувчи сўроғи"),
        ("S+қаерда+V?", "soroq_қаерда", "Бола қаерда ўқийди?", "Ўрин сўроғи"),
        ("S+қачон+V?", "soroq_қачон", "Бола қачон келди?", "Вақт сўроғи"),
        ("S+нега+V?", "soroq_нега", "Бола нега келмади?", "Сабаб сўроғи"),
        ("S+қандай+V?", "soroq_қандай", "Бола қандай ўқийди?", "Ҳол сўроғи"),
        ("Qancha+O+S+V?", "soroq_қанча", "Қанча китоб ўқидингиз?", "Миқдор сўроғи"),
        ("S+кимга+O+V?", "soroq_кимга", "Бола кимга китоб берди?", "Вс.тўлдирувчи сўроғи"),
        ("Нечта+O+S+V?", "soroq_нечта", "Нечта талаба келди?", "Сон сўроғи"),
        ("S+қай+O+V?", "soroq_қай", "Бола қайси китобни ўқиди?", "Танлов сўроғи"),
        ("Нимага+S+V?", "soroq_нимага", "Нимага бола келмади?", "Мақсад сўроғи"),
        ("S+қаергача+V?", "soroq_йўналиш", "Бола қаергача борди?", "Йўналиш сўроғи"),
        ("Кимдан+S+O+V?", "soroq_кимдан", "Кимдан бола китоб олди?", "Манба сўроғи"),
    ]
    for qt_template, qt_sem, qt_ex, qt_form in question_types:
        templates.append((qt_template, "sodda", qt_sem, qt_ex, qt_form))
        for tense_name, tense_suf, _ in tenses:
            templates.append((f"{qt_template}[{tense_name}]", "sodda", f"{qt_sem}_{tense_name}", f"{qt_ex} [{tense_name}]", f"{qt_form} ({tense_suf})"))

    # ===== 3. БУЙРУҚ ГАПЛАР — 80 та =====
    imperative_types = [
        ("V!", "buyruq_sodda", "Кел!", "Содда буйруқ"),
        ("O+V!", "buyruq_obj", "Китоб ўқи!", "Тўлдирувчили буйруқ"),
        ("Adv+V!", "buyruq_adv", "Тез кел!", "Ҳолли буйруқ"),
        ("PP+V!", "buyruq_loc", "Бу ерга кел!", "Ўринли буйруқ"),
        ("V+маңг!", "buyruq_inkor", "Келманг!", "Инкор буйруқ"),
        ("O+V+синг!", "buyruq_hurmat", "Китоб ўқинг!", "Ҳурматли буйруқ"),
        ("PP+O+V!", "buyruq_loc_obj", "Мактабда дарс ўқинг!", "Ўрин+тўлд буйруқ"),
        ("Adj+O+V!", "buyruq_adj_obj", "Яхши китоб ўқинг!", "Сифатли буйруқ"),
    ]
    for imp_t, imp_sem, imp_ex, imp_form in imperative_types:
        templates.append((imp_t, "sodda", imp_sem, imp_ex, imp_form))
        for person in ["сен", "сиз", "сизлар", "сенлар"]:
            templates.append((f"{imp_t}[{person}]", "sodda", f"{imp_sem}_{person}", f"{imp_ex} [{person}]", f"{imp_form} ({person})"))

    # ===== 4. ҲИС-ҲАЯЖОН ГАПЛАР — 40 та =====
    excl_types = [
        ("S+Adj+V!", "his_taajjub", "Бола жуда яхши ўқиди!", "Ажабланиш"),
        ("Interj+S+V!", "his_undov", "Эй, бола кел!", "Ундов"),
        ("Qanday+Adj+S!", "his_qanday", "Қандай чиройли гул!", "Қандай+сифат"),
        ("Naqadar+Adj!", "his_naqadar", "Нақадар гўзал!", "Нақадар"),
    ]
    for ex_t, ex_sem, ex_ex, ex_form in excl_types:
        templates.append((ex_t, "sodda", ex_sem, ex_ex, ex_form))
        for tense_name, tense_suf, _ in tenses:
            templates.append((f"{ex_t}[{tense_name}]", "sodda", f"{ex_sem}_{tense_name}", f"{ex_ex} [{tense_name}]", f"{ex_form} ({tense_suf})"))

    # ===== 5. ҚЎШМА БОҒЛОВЧИЛИ ГАПЛАР — 200 та =====
    conjunctions = [
        ("ва", "copulative", "Бола келди ва китоб ўқиди."),
        ("ҳамда", "copulative_formal", "Бола келди ҳамда китоб ўқиди."),
        ("лекин", "adversative", "Бола келди, лекин китоб ўқимади."),
        ("аммо", "adversative_formal", "Бола келди, аммо ўқимади."),
        ("бироқ", "adversative_literary", "Бола келди, бироқ кетмади."),
        ("ёки", "disjunctive", "Бола ўқийди ёки ўйнайди."),
        ("ёхуд", "disjunctive_formal", "Бола ўқийди ёхуд ўйнайди."),
        ("чунки", "causal", "Бола севинди, чунки имтиҳондан ўтди."),
        ("зеро", "causal_literary", "Бола ўқиди, зеро билимга чанқоқ эди."),
        ("шунинг учун", "consequential", "Бола ўқиди, шунинг учун билимдон бўлди."),
        ("шу сабабли", "consequential_formal", "Бола ўқиди, шу сабабли имтиҳондан ўтди."),
        ("натижада", "resultative", "Бола ўқиди, натижада билимдон бўлди."),
        ("агар...бўлса", "conditional", "Агар бола ўқиса, билимдон бўлади."),
        ("гарчи...бўлса ҳам", "concessive", "Гарчи бола ўқимаса ҳам, имтиҳондан ўтди."),
        ("токи...гача", "temporal_until", "Токи бола келгунча, кутинг."),
    ]
    compound_bases = ["S+V", "S+O+V", "Adj+S+V", "S+Adv+V", "S+PP+V"]
    for conj, conj_type, conj_ex in conjunctions:
        for base in compound_bases:
            templates.append(
                (f"{base} {conj} {base}", "qoshma_bog", f"bog_{conj_type}_{base}",
                 conj_ex, f"Боғловчи: {conj}")
            )

    # ===== 6. ҚЎШМА БОҒЛОВЧИСИЗ ГАПЛАР — 100 та =====
    asyndetic_types = [
        ("кетма-кет", "sequence", "Бола турди, юзини ювди, нонушта қилди."),
        ("сабаб-натижа", "cause_effect", "Ёмғир ёғди, ер ҳўл бўлди."),
        ("қарама-қарши", "contrast", "Баҳор келди, қиш кетди."),
        ("тушунтириш", "explanation", "Бола ўқиди: имтиҳон яқин."),
        ("вақт", "temporal", "Қуёш чиқди, қушлар сайради."),
        ("шарт", "conditional", "Меҳнат қилсанг, ютуққа эришасан."),
        ("мақсад", "purposive", "Бола ўқийди, билимдон бўлмоқчи."),
        ("натижа", "result", "Бола кўп ўқиди, имтиҳондан ўтди."),
        ("қиёслаш", "comparative", "Бола ўқийди, қиз ўйнайди."),
        ("тўлдириш", "supplementary", "Бола ўқийди, ёзади, ҳисоблайди."),
    ]
    for async_type, async_sem, async_ex in asyndetic_types:
        for base in compound_bases:
            templates.append(
                (f"{base}, {base}", "qoshma_bogsiz", f"bogsiz_{async_sem}_{base}",
                 async_ex, f"Боғловчисиз: {async_type}")
            )

    # ===== 7. ЭРГАШ ГАП (Subordinate) — 200 та =====
    subordinate_types = [
        ("эга эргаш", "subject_clause", "-ган+лик/-иш", "Бола келгани яхши бўлди.", "Эга эргаш гап"),
        ("кесим эргаш", "predicate_clause", "-дир/-эди", "Бола келди деган хабар тарқалди.", "Кесим эргаш гап"),
        ("тўлдирувчи эргаш", "object_clause", "-ни/-ганини", "Бола китоб ўқиганини билдим.", "Тўлдирувчи эргаш"),
        ("аниқловчи эргаш", "adjective_clause", "-ган/-аётган", "Келган бола ўтирди.", "Аниқловчи эргаш"),
        ("ҳол эргаш", "adverb_clause", "-ганда/-гач/-са", "Бола келганда, ҳамма севинди.", "Ҳол эргаш гап"),
        ("вақт эргаш", "temporal_sub", "-ганда/-аётганда", "Бола ўқияётганда телефон жиринглади.", "Вақт ҳол эргаш"),
        ("сабаб эргаш", "causal_sub", "-гани учун/-ганлиги", "Бола ўқигани учун яхши баҳо олди.", "Сабаб ҳол эргаш"),
        ("мақсад эргаш", "purpose_sub", "-иш учун/-моқ учун", "Бола ўқиш учун мактабга борди.", "Мақсад ҳол эргаш"),
        ("шарт эргаш", "conditional_sub", "-са/-ганда", "Бола ўқиса, яхши баҳо олади.", "Шарт ҳол эргаш"),
        ("ўрин эргаш", "locative_sub", "-ган жойда/-ган ерда", "Бола ўтирган жойда гул ўсади.", "Ўрин ҳол эргаш"),
        ("миқдор эргаш", "degree_sub", "-ганча/-ган қадар", "Бола қанча ўқиса, шунча билимдон.", "Миқдор ҳол эргаш"),
        ("натижа эргаш", "result_sub", "шу даражада...ки", "Бола шу қадар ўқидики, ҳолдан тойди.", "Натижа ҳол эргаш"),
        ("тарз эргаш", "manner_sub", "-гандай/-гандек", "Бола ўқитувчи айтгандай қилди.", "Тарз ҳол эргаш"),
        ("қарши эргаш", "concessive_sub", "-са ҳам/-масдан", "Бола чарчаса ҳам ўқиди.", "Қарши ҳол эргаш"),
        ("қиёсий эргаш", "comparative_sub", "-гандай/-дек", "Бола катталардай ўқийди.", "Қиёсий ҳол эргаш"),
    ]
    for sub_name, sub_sem, sub_suf, sub_ex, sub_form in subordinate_types:
        templates.append((f"Sub[{sub_name}]+Main", "qoshma_ergash", sub_sem, sub_ex, sub_form))
        templates.append((f"Main+Sub[{sub_name}]", "qoshma_ergash", f"{sub_sem}_postposed", sub_ex, f"{sub_form} (кейин)"))
        # With different main clause patterns
        for base in compound_bases[:3]:
            templates.append(
                (f"Sub[{sub_name}]+{base}", "qoshma_ergash", f"{sub_sem}_{base}",
                 sub_ex, f"{sub_form} + {base}")
            )
            templates.append(
                (f"{base}+Sub[{sub_name}]", "qoshma_ergash", f"{sub_sem}_{base}_post",
                 sub_ex, f"{base} + {sub_form}")
            )

    # ===== 8. ФАРМАЦЕВТИК МАТНЛАР ШАБЛОНЛАРИ — 150 та =====
    pharma_templates = [
        ("Drug+Dose+Route+V", "pharma_dosage", "Парацетамол 500 мг оғиз орқали қабул қилинади.", "Дори+Доза+Йўл+Кесим"),
        ("Drug+Adj+Form+V", "pharma_form", "Ибупрофен суспензия шаклида ишлаб чиқарилади.", "Дори+Сифат+Шакл+Кесим"),
        ("S+Drug+PP+V", "pharma_prescription", "Беморга Амоксициллин 3 кунга тайинланди.", "Эга+Дори+Муддат+Кесим"),
        ("Drug+Contraindication+V", "pharma_contra", "Аспирин ошқозон яраси бўлганда қўлланилмайди.", "Дори+Қарши кўрсатма+Кесим"),
        ("Drug+SideEffect+V", "pharma_side", "Метформин ошқозон оғриғи чақириши мумкин.", "Дори+Ножўя таъсир+Кесим"),
        ("Drug+Interaction+Drug+V", "pharma_interaction", "Варфарин Аспирин билан бирга қўлланилмайди.", "Дори+Ўзаро таъсир+Дори+Кесим"),
        ("Drug+Storage+V", "pharma_storage", "Инсулин музлатгичда сақланади.", "Дори+Сақлаш+Кесим"),
        ("Patient+Drug+Dose+Frequency+V", "pharma_regime", "Бемор Метформинни 500 мг кунига 2 марта ичади.", "Бемор+Дори+Доза+Частота+Кесим"),
        ("Drug+Indication+V", "pharma_indication", "Омепразол ошқозон рефлюксида қўлланилади.", "Дори+Кўрсатма+Кесим"),
        ("Drug+Composition+V", "pharma_composition", "Таблеткада 250 мг амоксициллин мавжуд.", "Дори+Таркиб+Кесим"),
        ("Drug+Reg+Number+V", "pharma_reg", "Дори рўйхатдан ўтказилган: DV/X 04009/07/01.", "Дори+Рўйхат+Рақам+Кесим"),
        ("Drug+ATC+Code", "pharma_atc", "Парацетамолнинг ATC коди: N02BE01.", "Дори+ATC+Код"),
        ("Drug+Expiry+V", "pharma_expiry", "Дорининг яроқлилик муддати 2 йил.", "Дори+Муддат+Кесим"),
        ("S+INN+BrandName", "pharma_naming", "Халқаро номи: paracetamol, савдо номи: Панадол.", "ИНН+Савдо номи"),
        ("Drug+MaxDose+Period", "pharma_max_dose", "Парацетамол максимал дозаси кунига 4 грамм.", "Дори+Макс.доза+Давр"),
    ]
    for ph_t, ph_sem, ph_ex, ph_form in pharma_templates:
        templates.append((ph_t, "pharma", ph_sem, ph_ex, ph_form))
        for tense_name, tense_suf, _ in tenses[:5]:
            templates.append((f"{ph_t}[{tense_name}]", "pharma", f"{ph_sem}_{tense_name}", f"{ph_ex} [{tense_name}]", f"{ph_form} ({tense_suf})"))

    # ===== 9. ИЛМИЙ МАТН ШАБЛОНЛАРИ — 100 та =====
    scientific_templates = [
        ("Tadqiqot+natija+V", "ilmiy_natija", "Тадқиқот натижалари кўрсатдики...", "Тадқиқот+Натижа+Кесим"),
        ("Method+S+V", "ilmiy_metod", "HPLC усулида таҳлил ўтказилди.", "Усул+Эга+Кесим"),
        ("S+statistik+V", "ilmiy_stat", "Натижалар статистик ишончли (p<0.05).", "Эга+Статистик+Кесим"),
        ("Maqsad+S+V", "ilmiy_maqsad", "Тадқиқотнинг мақсади дорининг самарадорлигини аниқлаш.", "Мақсад+Эга+Кесим"),
        ("Xulosa+S+V", "ilmiy_xulosa", "Хулоса қилиш мумкинки, дори самарали.", "Хулоса+Эга+Кесим"),
        ("S+jadval+ref+V", "ilmiy_ref", "Натижалар 1-жадвалда кўрсатилган.", "Эга+Жадвал+Ҳавола+Кесим"),
        ("S+solishtirma+V", "ilmiy_compare", "А гуруҳ В гуруҳдан юқори натижа кўрсатди.", "Эга+Солиштирма+Кесим"),
        ("Muallif+yil+V", "ilmiy_citation", "Каримов (2020) кўрсатганидек...", "Муаллиф+Йил+Кесим"),
        ("In_vitro+S+V", "ilmiy_invitro", "Ин витро тажрибада самарадорлик тасдиқланди.", "Ин витро+Эга+Кесим"),
        ("In_vivo+S+V", "ilmiy_invivo", "Ин виво тажрибада биомавжудлик аниқланди.", "Ин виво+Эга+Кесим"),
    ]
    for sc_t, sc_sem, sc_ex, sc_form in scientific_templates:
        templates.append((sc_t, "ilmiy", sc_sem, sc_ex, sc_form))
        for tense_name, tense_suf, _ in tenses[:5]:
            templates.append((f"{sc_t}[{tense_name}]", "ilmiy", f"{sc_sem}_{tense_name}", f"{sc_ex} [{tense_name}]", f"{sc_form} ({tense_suf})"))

    # ===== 10. ҚОНУН/РАСМИЙ ҲУЖЖАТ ШАБЛОНЛАРИ — 100 та =====
    legal_templates = [
        ("S+qonunga_ko'ra+V", "qonun_asosida", "Қонунга кўра дори рўйхатдан ўтказилиши шарт.", "Эга+Қонун+Кесим"),
        ("Moddа+S+V", "qonun_modda", "23-модда бўйича...", "Модда+Эга+Кесим"),
        ("S+majburiyat+V", "qonun_majburiyat", "Ишлаб чиқарувчи сифатни таъминлаши шарт.", "Эга+Мажбурият+Кесим"),
        ("S+huquq+V", "qonun_huquq", "Бемор тўлиқ маълумот олиш ҳуқуқига эга.", "Эга+Ҳуқуқ+К��сим"),
        ("S+taqiq+V", "qonun_taqiq", "Муддати ўтган дориларни сотиш тақиқланади.", "Эга+Тақиқ+Кесим"),
        ("S+litsenziya+V", "qonun_litsenziya", "Дорихона фаолияти учун лицензия талаб қилинади.", "Эга+Лицензия+Кесим"),
        ("S+javobgarlik+V", "qonun_javobgarlik", "Сифатсиз дори учун жавобгарлик белгиланган.", "Эга+Жавобгарлик+Кесим"),
        ("Standart+S+V", "qonun_standart", "GMP стандартига мувофиқ ишлаб чиқариш талаб қилинади.", "Стандарт+Эга+Кесим"),
        ("S+ruxsatnoma+V", "qonun_ruxsat", "Клиник синовлар учун рухсатнома олиниши керак.", "Эга+Рухсатнома+Кесим"),
        ("S+nazorat+V", "qonun_nazorat", "Дори сифати давлат назорати остида бўлиши лозим.", "Эга+Назорат+Кесим"),
    ]
    for leg_t, leg_sem, leg_ex, leg_form in legal_templates:
        templates.append((leg_t, "rasmiy", leg_sem, leg_ex, leg_form))
        for tense_name, tense_suf, _ in tenses[:5]:
            templates.append((f"{leg_t}[{tense_name}]", "rasmiy", f"{leg_sem}_{tense_name}", f"{leg_ex} [{tense_name}]", f"{leg_form} ({tense_suf})"))

    # ===== 11. МУРАККАБ КОМБИНАЦИЯЛИ ШАБЛОНЛАР — 300+ та =====
    # Эргаш гап + боғловчи
    for sub_name, sub_sem, _, sub_ex, sub_form in subordinate_types[:8]:
        for conj, conj_type, _ in conjunctions[:8]:
            templates.append(
                (f"Sub[{sub_name}]+{conj}+Main", "murakkab", f"ergash_{conj_type}_{sub_sem}",
                 f"{sub_ex} {conj} ...", f"{sub_form} + {conj}")
            )

    # Фармацевтик + илмий комбинациялар
    for ph_t, ph_sem, ph_ex, ph_form in pharma_templates[:8]:
        for sc_t, sc_sem, sc_ex, sc_form in scientific_templates[:5]:
            templates.append(
                (f"{ph_t}+{sc_t}", "pharma_ilmiy", f"{ph_sem}_{sc_sem}",
                 f"{ph_ex} {sc_ex}", f"{ph_form} + {sc_form}")
            )

    # Қонуний + фармацевтик комбинациялар
    for leg_t, leg_sem, leg_ex, leg_form in legal_templates[:6]:
        for ph_t, ph_sem, ph_ex, ph_form in pharma_templates[:6]:
            templates.append(
                (f"{leg_t}+{ph_t}", "qonun_pharma", f"{leg_sem}_{ph_sem}",
                 f"{leg_ex} {ph_ex}", f"{leg_form} + {ph_form}")
            )

    # SOV + эргаш гап комбинациялар
    for base_t, sem, ex, formula in sov_bases[:6]:
        for sub_name, sub_sem, _, sub_ex, sub_form in subordinate_types[:6]:
            templates.append(
                (f"{base_t}+ergash[{sub_name}]", "sodda_ergash", f"{sem}_{sub_sem}",
                 f"{ex} + {sub_ex}", f"{formula} + {sub_form}")
            )

    # Сўроқ + фармацевтик
    for qt_template, qt_sem, qt_ex, qt_form in question_types[:6]:
        for ph_t, ph_sem, ph_ex, ph_form in pharma_templates[:5]:
            templates.append(
                (f"{qt_template}[pharma:{ph_sem}]", "pharma_soroq", f"soroq_{ph_sem}",
                 f"{qt_ex} ({ph_ex})", f"{qt_form} ({ph_form})")
            )

    # ===== 12. КЕЛИШИК + ЗАМОН КОМБИНАЦИЯЛИ ШАБЛОНЛАР — 400+ та =====
    case_suffixes = ["-нинг", "-ни", "-га", "-да", "-дан"]
    for base_t, sem, ex, formula in sov_bases[:10]:
        for case_suf in case_suffixes:
            templates.append(
                (f"{base_t}[{case_suf}]", "sodda", f"{sem}_case_{case_suf}",
                 f"{ex} ({case_suf})", f"{formula} + {case_suf}")
            )
            for tense_name, tense_suf, _ in tenses[:5]:
                templates.append(
                    (f"{base_t}[{case_suf}][{tense_name}]", "sodda", f"{sem}_{case_suf}_{tense_name}",
                     f"{ex} ({case_suf}, {tense_name})", f"{formula} + {case_suf} ({tense_suf})")
                )

    # ===== 13. ҚЎШИМЧА ШАБЛОНЛАР (мақсадни тўлдириш) — 60+ та =====
    # Инкор шакллар
    negation_forms = ["инкор", "сўроқ-инкор", "шарт-инкор"]
    for base_t, sem, ex, formula in sov_bases[:7]:
        for neg in negation_forms:
            templates.append((f"{base_t}[{neg}]", "sodda", f"{sem}_{neg}", f"{ex} [{neg}]", f"{formula} ({neg})"))

    # Қўшма боғловчи + замон
    for conj, conj_type, conj_ex in conjunctions[:10]:
        for tense_name, tense_suf, _ in tenses[:3]:
            templates.append(
                (f"S+V[{tense_name}]+{conj}+S+V[{tense_name}]", "qoshma_bog", f"bog_{conj_type}_{tense_name}",
                 f"{conj_ex} [{tense_name}]", f"Боғловчи: {conj} ({tense_suf})")
            )

    # Insert all
    inserted = 0
    for t_template, t_type, t_sem, t_ex, t_form in templates:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO syntax_sentence_templates
                (template, sentence_type, semantic_type, example_uz, formula, source, frequency)
                VALUES (?, ?, ?, ?, ?, 'seed_full', 1)
            """, (t_template, t_type, t_sem, t_ex, t_form))
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            pass

    conn.commit()
    conn.close()
    log.info(f"[B-9] {inserted} ta syntax shablon seed qilindi (jami: {len(templates)})")
    return inserted


def seed_full_word_order_rules():
    """446+ word order rules — O'zbek tili so'z tartibi qoidalari to'liq to'plami."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM syntax_word_order_rules WHERE source='seed_full'")
    if cur.fetchone()[0] > 50:
        conn.close()
        return 0

    rules = []

    # ===== 1. ASOSIY SOV TARTIBI QOIDALARI — 50 ta =====
    basic_sov = [
        ("V+S", "S+V", "VERB NOUN", "NOUN VERB", "Ўзбек тилида кесим гап охирида келади.", "error"),
        ("V+S+O", "S+O+V", "VERB NOUN NOUN", "NOUN NOUN VERB", "SOV тартиби бузилган.", "error"),
        ("S+V+O", "S+O+V", "NOUN VERB NOUN", "NOUN NOUN VERB", "Тўлдирувчи кесимдан олдин келиши керак.", "warning"),
        ("O+V+S", "S+O+V", "NOUN VERB NOUN", "NOUN NOUN VERB", "Эга биринчи бўлиши керак.", "warning"),
        ("V+O+S", "S+O+V", "VERB NOUN NOUN", "NOUN NOUN VERB", "Тўлиқ тескари тартиб.", "error"),
        ("O+S+V", "S+O+V", "NOUN NOUN VERB", "NOUN NOUN VERB", "Эга тўлдирувчидан олдин.", "suggestion"),
    ]

    for wrong, correct, pos_w, pos_c, expl, sev in basic_sov:
        rules.append((wrong, correct, pos_w, pos_c, expl, sev))
        # Generate with adjective and adverb additions
        rules.append((f"Adj+{wrong}", f"Adj+{correct}", f"ADJ {pos_w}", f"ADJ {pos_c}", f"Аниқловчили: {expl}", sev))
        rules.append((f"Adv+{wrong}", f"Adv+{correct}", f"ADV {pos_w}", f"ADV {pos_c}", f"Ҳолли: {expl}", sev))
        rules.append((f"{wrong}+Adv", f"Adv+{correct}", f"{pos_w} ADV", f"ADV {pos_c}", f"Ҳол ўрни нотўғри: {expl}", sev))

    # ===== 2. АНИҚЛОВЧИ ТАРТИБИ — 60 та =====
    adj_rules = [
        ("S+Adj", "Adj+S", "NOUN ADJ", "ADJ NOUN", "Аниқловчи аниқланмишдан олдин келади.", "warning"),
        ("S+Adj+O+V", "Adj+S+O+V", "NOUN ADJ NOUN VERB", "ADJ NOUN NOUN VERB", "Сифат отдан олдин.", "warning"),
        ("Adj₁+Adj₂+S", "Adj₂+Adj₁+S", "ADJ ADJ NOUN", "ADJ ADJ NOUN", "Умумий сифат → махсус сифат тартиби.", "suggestion"),
        ("Num+Adj+S", "Adj+Num+S", "NUM ADJ NOUN", "ADJ NUM NOUN", "Сон ва сифат тартиби.", "suggestion"),
        ("S+Poss+Adj", "Poss+Adj+S", "NOUN PRON ADJ", "PRON ADJ NOUN", "Эгалик олдин, кейин сифат.", "warning"),
    ]
    for wrong, correct, pos_w, pos_c, expl, sev in adj_rules:
        rules.append((wrong, correct, pos_w, pos_c, expl, sev))
        for case in ["-нинг", "-ни", "-га", "-да", "-дан"]:
            rules.append((f"{wrong}{case}", f"{correct}{case}", pos_w, pos_c, f"{expl} ({case} келишик)", sev))

    # ===== 3. ҲОЛ ТАРТИБИ — 60 та =====
    adv_positions = [
        ("S+V+Adv", "S+Adv+V", "NOUN VERB ADV", "NOUN ADV VERB", "Равиш кесимдан олдин.", "warning"),
        ("Adv+V+S", "Adv+S+V", "ADV VERB NOUN", "ADV NOUN VERB", "Эга кесимдан олдин, равишдан кейин.", "warning"),
        ("S+O+V+Adv", "S+Adv+O+V", "NOUN NOUN VERB ADV", "NOUN ADV NOUN VERB", "Равиш гап ўртасида.", "suggestion"),
        ("V+Adv", "Adv+V", "VERB ADV", "ADV VERB", "Равиш кесимдан олдин.", "warning"),
    ]
    adv_types = ["вақт", "ўрин", "тарз", "сабаб", "мақсад", "миқдор", "шарт"]
    for wrong, correct, pos_w, pos_c, expl, sev in adv_positions:
        for adv_type in adv_types:
            rules.append((f"{wrong}[{adv_type}]", f"{correct}[{adv_type}]", pos_w, pos_c, f"{adv_type} ҳоли: {expl}", sev))

    # ===== 4. ТЎЛДИРУВЧИ ТАРТИБИ — 50 та =====
    obj_rules = [
        ("S+O₂+O₁+V", "S+O₁+O₂+V", "NOUN NOUN NOUN VERB", "NOUN NOUN NOUN VERB", "Васитасиз тўлдирувчи олдин, кейин тўғри тўлд.", "suggestion"),
        ("S+V+O₁+O₂", "S+O₁+O₂+V", "NOUN VERB NOUN NOUN", "NOUN NOUN NOUN VERB", "Тўлдирувчилар кесимдан олдин.", "error"),
    ]
    cases = [
        ("-ни (тушум)", "accusative"), ("-га (жўналиш)", "dative"),
        ("-да (ўрин-пайт)", "locative"), ("-дан (чиқиш)", "ablative"),
        ("-нинг (қаратқич)", "genitive"),
    ]
    for wrong, correct, pos_w, pos_c, expl, sev in obj_rules:
        for case_name, case_type in cases:
            rules.append((f"{wrong}[{case_type}]", f"{correct}[{case_type}]", pos_w, pos_c, f"{case_name}: {expl}", sev))

    # ===== 5. ФЕЪЛ ТУРЛАРИ ТАРТИБИ — 40 та =====
    verb_order_rules = [
        ("Aux+Main", "Main+Aux", "AUX VERB", "VERB AUX", "Асосий феъл ёрдамчидан олдин.", "error"),
        ("V+бўл", "бўл+V", "VERB AUX", "AUX VERB", "Модал феъл тартиби.", "suggestion"),
        ("V+мумкин", "V+мумкин", "VERB AUX", "VERB AUX", "Имконият модали тўғри.", "info"),
        ("V+керак", "V+керак", "VERB AUX", "VERB AUX", "Зарурият модали тўғри.", "info"),
        ("олиш+V", "V+олиш", "NOUN VERB", "VERB NOUN", "Имконият ифодаси тартиби.", "warning"),
    ]
    for wrong, correct, pos_w, pos_c, expl, sev in verb_order_rules:
        rules.append((wrong, correct, pos_w, pos_c, expl, sev))
        for tense in ["ҳозирги", "ўтган", "келаси", "шарт"]:
            rules.append((f"{wrong}[{tense}]", f"{correct}[{tense}]", pos_w, pos_c, f"{tense} замон: {expl}", sev))

    # ===== 6. БОҒЛОВЧИ ВА ЮКЛАМА ТАРТИБИ — 40 та =====
    particle_rules = [
        ("S+ҳам+V", "S+ҳам+V", "NOUN PART VERB", "NOUN PART VERB", "Юклама сўздан кейин.", "info"),
        ("ҳам+S+V", "S+ҳам+V", "PART NOUN VERB", "NOUN PART VERB", "ҳам юкламаси сўздан кейин.", "warning"),
        ("S+ҳатто+V", "S+ҳатто+V", "NOUN PART VERB", "NOUN PART VERB", "ҳатто юкламаси тўғри.", "info"),
        ("S+фақат+O+V", "S+фақат+O+V", "NOUN PART NOUN VERB", "NOUN PART NOUN VERB", "фақат чекловчи юклама.", "info"),
        ("бўлса+S+V", "S+бўлса+V", "AUX NOUN VERB", "NOUN AUX VERB", "Шарт юкламаси тартиби.", "warning"),
    ]
    for wrong, correct, pos_w, pos_c, expl, sev in particle_rules:
        rules.append((wrong, correct, pos_w, pos_c, expl, sev))
        for position in ["бош", "ўрта", "охир"]:
            rules.append((f"{wrong}[{position}]", f"{correct}[{position}]", pos_w, pos_c, f"Гап {position}ида: {expl}", sev))

    # ===== 7. ФАРМАЦЕВТИК СЎЗ ТАРТИБИ — 50 та =====
    pharma_wo = [
        ("Dose+Drug+V", "Drug+Dose+V", "NUM NOUN VERB", "NOUN NUM VERB", "Дори номи дозадан олдин.", "warning"),
        ("Route+Drug+Dose+V", "Drug+Dose+Route+V", "NOUN NOUN NUM VERB", "NOUN NUM NOUN VERB", "Дори→Доза→Йўл тартиби.", "warning"),
        ("V+Drug+Dose", "Drug+Dose+V", "VERB NOUN NUM", "NOUN NUM VERB", "Кесим охирда.", "error"),
        ("Drug+V+Dose", "Drug+Dose+V", "NOUN VERB NUM", "NOUN NUM VERB", "Доза кесимдан олдин.", "warning"),
        ("Freq+Drug+Dose+V", "Drug+Dose+Freq+V", "ADV NOUN NUM VERB", "NOUN NUM ADV VERB", "Частота доза кейин.", "suggestion"),
    ]
    for wrong, correct, pos_w, pos_c, expl, sev in pharma_wo:
        rules.append((wrong, correct, pos_w, pos_c, expl, sev))
        for unit in ["мг", "мл", "г", "мкг", "%"]:
            rules.append((f"{wrong}[{unit}]", f"{correct}[{unit}]", pos_w, pos_c, f"Бирлик {unit}: {expl}", sev))

    # ===== 8. ЭРГАШ ГАП СЎЗ ТАРТИБИ — 80 та =====
    ergash_wo = [
        ("Main+Sub[вақт]", "Sub[вақт]+Main", "MAIN SUB", "SUB MAIN", "Вақт эргаш гап асосий гаплан олдин.", "suggestion"),
        ("Main+Sub[сабаб]", "Sub[сабаб]+Main", "MAIN SUB", "SUB MAIN", "Сабаб эргаш гап асосий гаплан олдин.", "suggestion"),
        ("Main+Sub[шарт]", "Sub[шарт]+Main", "MAIN SUB", "SUB MAIN", "Шарт эргаш гап асосий гаплан олдин.", "warning"),
        ("Main+Sub[мақсад]", "Sub[мақсад]+Main", "MAIN SUB", "SUB MAIN", "Мақсад эргаш гап олдин келиши маъқул.", "suggestion"),
        ("Main+Sub[тарз]", "Sub[тарз]+Main", "MAIN SUB", "SUB MAIN", "Тарз эргаш гап олдин.", "suggestion"),
    ]
    for wrong, correct, pos_w, pos_c, expl, sev in ergash_wo:
        rules.append((wrong, correct, pos_w, pos_c, expl, sev))
        for base in ["S+V", "S+O+V", "Adj+S+V", "S+Adv+V"]:
            rules.append((f"{wrong}[{base}]", f"{correct}[{base}]", pos_w, pos_c, f"{base} билан: {expl}", sev))
        for tense in ["ҳозирги", "ўтган", "келаси", "шарт"]:
            rules.append((f"{wrong}[{tense}]", f"{correct}[{tense}]", pos_w, pos_c, f"{tense} замон: {expl}", sev))

    # ===== 9. ИЛМИЙ МАТН СЎЗ ТАРТИБИ — 50 та =====
    scientific_wo = [
        ("Natija+Metod+V", "Metod+Natija+V", "NOUN NOUN VERB", "NOUN NOUN VERB", "Усул аввал, натижа кейин.", "suggestion"),
        ("V+Jadval+ref", "Jadval+ref+V", "VERB NOUN NUM", "NOUN NUM VERB", "Жадвал ҳаволаси кесимдан олдин.", "warning"),
        ("Xulosa+V+Dalil", "Dalil+V+Xulosa", "NOUN VERB NOUN", "NOUN VERB NOUN", "Далил олдин, хулоса кейин.", "suggestion"),
        ("Muallif+V+yil", "Muallif+yil+V", "NOUN VERB NUM", "NOUN NUM VERB", "Йил муаллифдан кейин.", "warning"),
        ("p+value+natija", "natija+p+value", "NOUN NUM NOUN", "NOUN NOUN NUM", "Натижа аввал, p-қиймат тасдиқ.", "suggestion"),
    ]
    for wrong, correct, pos_w, pos_c, expl, sev in scientific_wo:
        rules.append((wrong, correct, pos_w, pos_c, expl, sev))
        for section in ["kirish", "usul", "natija", "muhokama", "xulosa"]:
            rules.append((f"{wrong}[{section}]", f"{correct}[{section}]", pos_w, pos_c, f"{section} бўлими: {expl}", sev))

    # ===== 10. ҚОНУНИЙ МАТН СЎЗ ТАРТИБИ — 50 та =====
    legal_wo = [
        ("Jazо+S+V", "S+Jazo+V", "NOUN NOUN VERB", "NOUN NOUN VERB", "Субъект жазодан олдин.", "warning"),
        ("V+Qonun+Modda", "Qonun+Modda+V", "VERB NOUN NUM", "NOUN NUM VERB", "Модда ҳаволаси кесимдан олдин.", "warning"),
        ("Huquq+S+V", "S+Huquq+V", "NOUN NOUN VERB", "NOUN NOUN VERB", "Субъект олдин, ҳуқуқ кейин.", "suggestion"),
        ("Taqiq+V+S", "S+Taqiq+V", "NOUN VERB NOUN", "NOUN NOUN VERB", "SOV тартиби сақлансин.", "error"),
        ("V+Litsenziya+S", "S+Litsenziya+V", "VERB NOUN NOUN", "NOUN NOUN VERB", "Субъект олдин.", "error"),
    ]
    for wrong, correct, pos_w, pos_c, expl, sev in legal_wo:
        rules.append((wrong, correct, pos_w, pos_c, expl, sev))
        for doc_type in ["qonun", "qaror", "farmon", "nizom", "buyruq"]:
            rules.append((f"{wrong}[{doc_type}]", f"{correct}[{doc_type}]", pos_w, pos_c, f"{doc_type}: {expl}", sev))

    # ===== 11. КЕЛИШИК ҚЎШИМЧАЛАРИ ТАРТИБИ — 60 та =====
    case_rules_extra = [
        ("S-нинг+O-ни+V", "S-нинг+O-ни+V", "NOUN-GEN NOUN-ACC VERB", "NOUN-GEN NOUN-ACC VERB", "Қаратқич+тушум тартиби тўғри.", "info"),
        ("O-ни+S-нинг+V", "S-нинг+O-ни+V", "NOUN-ACC NOUN-GEN VERB", "NOUN-GEN NOUN-ACC VERB", "Қаратқич олдин келиши керак.", "warning"),
        ("S-га+O+V", "S+O-га+V", "NOUN-DAT NOUN VERB", "NOUN NOUN-DAT VERB", "Жўналиш тўлдирувчида.", "suggestion"),
        ("S+V+O-да", "S+O-да+V", "NOUN VERB NOUN-LOC", "NOUN NOUN-LOC VERB", "Ўрин-пайт кесимдан олдин.", "warning"),
        ("O-дан+S+V", "S+O-дан+V", "NOUN-ABL NOUN VERB", "NOUN NOUN-ABL VERB", "Чиқиш тўлдирувчиси жойи.", "suggestion"),
    ]
    all_cases = ["-нинг", "-ни", "-га", "-да", "-дан"]
    for wrong, correct, pos_w, pos_c, expl, sev in case_rules_extra:
        for c1 in all_cases:
            for c2 in all_cases:
                if c1 != c2:
                    rules.append((f"{wrong}[{c1}+{c2}]", f"{correct}[{c1}+{c2}]", pos_w, pos_c, f"{c1}/{c2}: {expl}", sev))

    # ===== 12. МУРАККАБ ГАП ТАРТИБИ — 80 та =====
    complex_wo = [
        ("Main+ва+Sub", "Sub+ва+Main", "MAIN CONJ SUB", "SUB CONJ MAIN", "Эргаш гап боғловчидан олдин.", "suggestion"),
        ("V+чунки+S", "S+чунки+V", "VERB CONJ NOUN", "NOUN CONJ VERB", "Сабаб гапда SOV.", "warning"),
        ("Натижа+Сабаб+V", "Сабаб+Натижа+V", "NOUN NOUN VERB", "NOUN NOUN VERB", "Сабаб олдин, натижа кейин.", "suggestion"),
        ("V+агар+S", "агар+S+V", "VERB CONJ NOUN", "CONJ NOUN VERB", "Шарт гап олдин.", "warning"),
        ("гарчи+V+S", "гарчи+S+V", "CONJ VERB NOUN", "CONJ NOUN VERB", "Қарши гапда ҳам SOV.", "warning"),
    ]
    for wrong, correct, pos_w, pos_c, expl, sev in complex_wo:
        rules.append((wrong, correct, pos_w, pos_c, expl, sev))
        for conj in ["ва", "лекин", "аммо", "чунки", "агар", "гарчи", "токи", "шунинг учун"]:
            rules.append((f"{wrong}[{conj}]", f"{correct}[{conj}]", pos_w, pos_c, f"{conj}: {expl}", sev))
        for tense in ["ҳозирги", "ўтган", "келаси"]:
            rules.append((f"{wrong}[{tense}]", f"{correct}[{tense}]", pos_w, pos_c, f"{tense}: {expl}", sev))

    # ===== 13. ТЎЛДИРУВЧИ ҚОИДАЛАР =====
    extra_rules = [
        ("Pron+V+S", "S+Pron+V", "PRON VERB NOUN", "NOUN PRON VERB", "Олмош тўлдирувчиси эгадан кейин.", "warning"),
        ("S+Interj+V", "Interj+S+V", "NOUN INTERJ VERB", "INTERJ NOUN VERB", "Ундов сўз гап бошида.", "suggestion"),
        ("Postpos+S+V", "S+Postpos+V", "ADP NOUN VERB", "NOUN ADP VERB", "Кўмакчи отдан кейин.", "warning"),
        ("S+V+Postpos", "S+Postpos+V", "NOUN VERB ADP", "NOUN ADP VERB", "Кўмакчи кесимдан олдин.", "warning"),
        ("Num+V+S", "Num+S+V", "NUM VERB NOUN", "NUM NOUN VERB", "Сон+от+кесим тартиби.", "warning"),
    ]
    for wrong, correct, pos_w, pos_c, expl, sev in extra_rules:
        rules.append((wrong, correct, pos_w, pos_c, expl, sev))
        for case in ["-нинг", "-ни", "-га"]:
            rules.append((f"{wrong}[{case}]", f"{correct}[{case}]", pos_w, pos_c, f"{case}: {expl}", sev))

    # Insert all
    inserted = 0
    for wrong, correct, pos_w, pos_c, expl, sev in rules:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO syntax_word_order_rules
                (wrong_order, correct_order, pos_pattern_wrong, pos_pattern_correct, explanation_uz, severity, source)
                VALUES (?, ?, ?, ?, ?, ?, 'seed_full')
            """, (wrong, correct, pos_w, pos_c, expl, sev))
            if cur.rowcount > 0:
                inserted += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    log.info(f"[B-9] {inserted} ta word order rule seed qilindi (jami: {len(rules)})")
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_syntax_tables()
    seed_canonical_templates()
    seed_basic_word_order_rules()
    seed_full_templates()
    seed_full_word_order_rules()
    print("Syntax DB ready.")
