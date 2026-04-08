"""
Seed medical_terms table with common trilingual (uz/ru/en) pharma/medical terminology.
"""
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))

# (uz, ru, en, definition, category)
TERMS = [
    # Anatomy
    ("юрак", "сердце", "heart", "қон айланишининг марказий органи", "anatomy"),
    ("буйрак", "почка", "kidney", "сийдик чиқариш органи", "anatomy"),
    ("ўпка", "лёгкое", "lung", "нафас олиш органи", "anatomy"),
    ("жигар", "печень", "liver", "метаболик орган", "anatomy"),
    ("ошқозон", "желудок", "stomach", "ҳазм қилиш органи", "anatomy"),
    ("ичак", "кишечник", "intestine", "ҳазмни давом эттирувчи орган", "anatomy"),
    ("мия", "мозг", "brain", "марказий асаб тизими", "anatomy"),
    ("суяк", "кость", "bone", "таянч-ҳаракат тизими", "anatomy"),
    ("мушак", "мышца", "muscle", "ҳаракат тўқимаси", "anatomy"),
    ("тери", "кожа", "skin", "ташқи қоплама", "anatomy"),
    ("қон", "кровь", "blood", "суюқ боғловчи тўқима", "anatomy"),
    ("лимфа", "лимфа", "lymph", "лимфа тизими суюқлиги", "anatomy"),

    # Diseases
    ("гипертензия", "гипертензия", "hypertension", "юқори артериал босим", "disease"),
    ("диабет", "диабет", "diabetes", "глюкоза алмашинуви бузилиши", "disease"),
    ("астма", "астма", "asthma", "бронхлар яллиғланиши", "disease"),
    ("аллергия", "аллергия", "allergy", "иммун тизими реакцияси", "disease"),
    ("инфекция", "инфекция", "infection", "микроорганизм касаллик", "disease"),
    ("грипп", "грипп", "influenza", "вирусли нафас йўл касаллиги", "disease"),
    ("пневмония", "пневмония", "pneumonia", "ўпка яллиғланиши", "disease"),
    ("бронхит", "бронхит", "bronchitis", "бронхлар яллиғланиши", "disease"),
    ("гастрит", "гастрит", "gastritis", "ошқозон яллиғланиши", "disease"),
    ("гепатит", "гепатит", "hepatitis", "жигар яллиғланиши", "disease"),
    ("нефрит", "нефрит", "nephritis", "буйрак яллиғланиши", "disease"),
    ("цистит", "цистит", "cystitis", "сийдик қопчаси яллиғланиши", "disease"),
    ("артрит", "артрит", "arthritis", "бўғим яллиғланиши", "disease"),
    ("ринит", "ринит", "rhinitis", "бурун шиллиқ пардаси яллиғланиши", "disease"),
    ("анемия", "анемия", "anemia", "қонда гемоглобин кам", "disease"),

    # Pharmacology
    ("таблетка", "таблетка", "tablet", "дори шакли", "pharmacy"),
    ("капсула", "капсула", "capsule", "дори шакли", "pharmacy"),
    ("сироп", "сироп", "syrup", "суюқ дори шакли", "pharmacy"),
    ("ампула", "ампула", "ampoule", "инъекция учун идиш", "pharmacy"),
    ("ингалятор", "ингалятор", "inhaler", "нафас олиш дори", "pharmacy"),
    ("мазь", "мазь", "ointment", "ташқи дори шакли", "pharmacy"),
    ("крем", "крем", "cream", "эмульсия шакли", "pharmacy"),
    ("суспензия", "суспензия", "suspension", "чўкма шакли", "pharmacy"),
    ("эмульсия", "эмульсия", "emulsion", "суюқлик аралашмаси", "pharmacy"),
    ("антибиотик", "антибиотик", "antibiotic", "бактерияга қарши дори", "pharmacy"),
    ("аналгетик", "анальгетик", "analgesic", "оғриқ қолдирувчи дори", "pharmacy"),
    ("антисептик", "антисептик", "antiseptic", "микробга қарши", "pharmacy"),
    ("вакцина", "вакцина", "vaccine", "иммунизация учун", "pharmacy"),
    ("противовирусный", "противовирусный", "antiviral", "вирусга қарши", "pharmacy"),
    ("диуретик", "диуретик", "diuretic", "сийдик чиқарувчи", "pharmacy"),
    ("антигипертензив", "антигипертензивный", "antihypertensive", "босимни туширувчи", "pharmacy"),
    ("анестетик", "анестетик", "anesthetic", "оғриқсизлантирувчи", "pharmacy"),
    ("антикоагулянт", "антикоагулянт", "anticoagulant", "қон лахталашга қарши", "pharmacy"),
    ("антидепрессант", "антидепрессант", "antidepressant", "депрессияга қарши", "pharmacy"),
    ("антигистамин", "антигистамин", "antihistamine", "аллергияга қарши", "pharmacy"),

    # Procedures
    ("операция", "операция", "surgery", "жарроҳлик амалиёти", "procedure"),
    ("инъекция", "инъекция", "injection", "дори юбориш усули", "procedure"),
    ("қон таҳлили", "анализ крови", "blood test", "қон текшируви", "procedure"),
    ("рентген", "рентген", "X-ray", "нурли ташхис", "procedure"),
    ("УЗИ", "УЗИ", "ultrasound", "ултратовушли ташхис", "procedure"),
    ("МРТ", "МРТ", "MRI", "магнит резонанс", "procedure"),
    ("КТ", "КТ", "CT scan", "компьютер томографияси", "procedure"),
    ("ЭКГ", "ЭКГ", "ECG", "электрокардиограмма", "procedure"),
    ("биопсия", "биопсия", "biopsy", "тўқима намунаси олиш", "procedure"),
    ("эндоскопия", "эндоскопия", "endoscopy", "ичкариси кўрик", "procedure"),

    # Vital signs
    ("ҳарорат", "температура", "temperature", "тана иссиқлиги", "vitals"),
    ("босим", "давление", "blood pressure", "артериал босим", "vitals"),
    ("пульс", "пульс", "pulse", "юрак уриши", "vitals"),
    ("нафас", "дыхание", "respiration", "нафас олиш", "vitals"),
    ("гликемия", "гликемия", "glycemia", "қондаги глюкоза", "vitals"),
    ("сатурация", "сатурация", "saturation", "кислород даражаси", "vitals"),

    # Lab
    ("холестерин", "холестерин", "cholesterol", "ёғ алмашинуви кўрсатгич", "lab"),
    ("гемоглобин", "гемоглобин", "hemoglobin", "қон пигменти", "lab"),
    ("лейкоцит", "лейкоцит", "leukocyte", "оқ қон ҳужайраси", "lab"),
    ("эритроцит", "эритроцит", "erythrocyte", "қизил қон ҳужайраси", "lab"),
    ("тромбоцит", "тромбоцит", "platelet", "қон лахталаш ҳужайраси", "lab"),
    ("креатинин", "креатинин", "creatinine", "буйрак функцияси маркери", "lab"),
    ("мочевина", "мочевина", "urea", "азот алмашинуви", "lab"),
    ("билирубин", "билирубин", "bilirubin", "жигар пигменти", "lab"),
    ("альбумин", "альбумин", "albumin", "қон оқсили", "lab"),
    ("глюкоза", "глюкоза", "glucose", "қонда шакар", "lab"),

    # Units & measurements
    ("миллиграмм", "миллиграмм", "milligram", "оғирлик бирлиги", "unit"),
    ("микрограмм", "микрограмм", "microgram", "оғирлик бирлиги", "unit"),
    ("миллилитр", "миллилитр", "milliliter", "ҳажм бирлиги", "unit"),
    ("халқаро бирлик", "международная единица", "international unit", "биоактивлик", "unit"),
    ("моль", "моль", "mole", "кимёвий миқдор бирлиги", "unit"),
]


def seed():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS medical_terms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        term_uz TEXT, term_ru TEXT, term_en TEXT,
        definition TEXT, category TEXT, synonyms TEXT, atc_code TEXT,
        source TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(term_uz, term_ru, term_en)
    )
    ''')
    inserted = 0
    for uz, ru, en, definition, category in TERMS:
        try:
            cur.execute(
                "INSERT OR IGNORE INTO medical_terms (term_uz, term_ru, term_en, definition, category, source) VALUES (?, ?, ?, ?, ?, ?)",
                (uz, ru, en, definition, category, "seed_v1")
            )
            if cur.rowcount > 0:
                inserted += 1
        except Exception:
            pass
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM medical_terms")
    total = cur.fetchone()[0]
    conn.close()
    return {"inserted": inserted, "total": total}


if __name__ == "__main__":
    print(seed())
