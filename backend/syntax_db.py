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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_syntax_tables()
    seed_canonical_templates()
    seed_basic_word_order_rules()
    print("Syntax DB ready.")
