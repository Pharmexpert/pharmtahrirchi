"""
Seed `drugs` table with common pharmaceutical INNs.
Data source: WHO Essential Medicines List + ATC classification.

Run: python seed_drugs.py
"""
import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))

# Common pharmaceutical INNs with ATC codes
# Format: (inn, brand_name, atc_code, form, category, dose)
DRUGS = [
    # Analgesics
    ("Paracetamol", "Tylenol", "N02BE01", "tablet", "analgesic", "500mg"),
    ("Paracetamol", "Panadol", "N02BE01", "tablet", "analgesic", "500mg"),
    ("Acetylsalicylic acid", "Aspirin", "B01AC06", "tablet", "antiplatelet/analgesic", "100mg"),
    ("Ibuprofen", "Nurofen", "M01AE01", "tablet", "NSAID", "400mg"),
    ("Diclofenac", "Voltaren", "M01AB05", "tablet", "NSAID", "50mg"),
    ("Naproxen", "Naprosyn", "M01AE02", "tablet", "NSAID", "250mg"),
    ("Ketorolac", "Toradol", "M01AB15", "injection", "NSAID", "30mg/ml"),
    ("Tramadol", "Ultram", "N02AX02", "capsule", "opioid analgesic", "50mg"),
    ("Morphine", "MS Contin", "N02AA01", "injection", "opioid", "10mg/ml"),

    # Antibiotics
    ("Amoxicillin", "Amoxil", "J01CA04", "capsule", "antibiotic (penicillin)", "500mg"),
    ("Ampicillin", "Principen", "J01CA01", "capsule", "antibiotic (penicillin)", "500mg"),
    ("Azithromycin", "Zithromax", "J01FA10", "tablet", "antibiotic (macrolide)", "500mg"),
    ("Clarithromycin", "Klacid", "J01FA09", "tablet", "antibiotic (macrolide)", "500mg"),
    ("Erythromycin", "Eryc", "J01FA01", "tablet", "antibiotic (macrolide)", "250mg"),
    ("Ciprofloxacin", "Cipro", "J01MA02", "tablet", "antibiotic (fluoroquinolone)", "500mg"),
    ("Levofloxacin", "Levaquin", "J01MA12", "tablet", "antibiotic (fluoroquinolone)", "500mg"),
    ("Doxycycline", "Vibramycin", "J01AA02", "capsule", "antibiotic (tetracycline)", "100mg"),
    ("Ceftriaxone", "Rocephin", "J01DD04", "injection", "antibiotic (cephalosporin)", "1g"),
    ("Cefuroxime", "Zinacef", "J01DC02", "tablet", "antibiotic (cephalosporin)", "500mg"),
    ("Metronidazole", "Flagyl", "J01XD01", "tablet", "antibiotic/antiprotozoal", "500mg"),
    ("Sulfamethoxazole/Trimethoprim", "Bactrim", "J01EE01", "tablet", "antibiotic (sulfonamide)", "800mg/160mg"),
    ("Vancomycin", "Vancocin", "J01XA01", "injection", "antibiotic (glycopeptide)", "500mg"),
    ("Gentamicin", "Garamycin", "J01GB03", "injection", "antibiotic (aminoglycoside)", "80mg/2ml"),

    # Cardiovascular
    ("Amlodipine", "Norvasc", "C08CA01", "tablet", "calcium channel blocker", "5mg"),
    ("Losartan", "Cozaar", "C09CA01", "tablet", "ARB antihypertensive", "50mg"),
    ("Lisinopril", "Prinivil", "C09AA03", "tablet", "ACE inhibitor", "10mg"),
    ("Enalapril", "Vasotec", "C09AA02", "tablet", "ACE inhibitor", "10mg"),
    ("Captopril", "Capoten", "C09AA01", "tablet", "ACE inhibitor", "25mg"),
    ("Metoprolol", "Lopressor", "C07AB02", "tablet", "beta-blocker", "50mg"),
    ("Atenolol", "Tenormin", "C07AB03", "tablet", "beta-blocker", "50mg"),
    ("Bisoprolol", "Concor", "C07AB07", "tablet", "beta-blocker", "5mg"),
    ("Furosemide", "Lasix", "C03CA01", "tablet", "loop diuretic", "40mg"),
    ("Hydrochlorothiazide", "Microzide", "C03AA03", "tablet", "thiazide diuretic", "25mg"),
    ("Spironolactone", "Aldactone", "C03DA01", "tablet", "K-sparing diuretic", "25mg"),
    ("Atorvastatin", "Lipitor", "C10AA05", "tablet", "statin", "20mg"),
    ("Simvastatin", "Zocor", "C10AA01", "tablet", "statin", "20mg"),
    ("Rosuvastatin", "Crestor", "C10AA07", "tablet", "statin", "10mg"),
    ("Warfarin", "Coumadin", "B01AA03", "tablet", "anticoagulant", "5mg"),
    ("Clopidogrel", "Plavix", "B01AC04", "tablet", "antiplatelet", "75mg"),
    ("Heparin", "Hep-Lock", "B01AB01", "injection", "anticoagulant", "5000IU/ml"),

    # Diabetes
    ("Metformin", "Glucophage", "A10BA02", "tablet", "biguanide", "500mg"),
    ("Glibenclamide", "Daonil", "A10BB01", "tablet", "sulfonylurea", "5mg"),
    ("Gliclazide", "Diamicron", "A10BB09", "tablet", "sulfonylurea", "80mg"),
    ("Insulin glargine", "Lantus", "A10AE04", "injection", "insulin", "100IU/ml"),
    ("Insulin lispro", "Humalog", "A10AB04", "injection", "insulin", "100IU/ml"),
    ("Insulin aspart", "NovoRapid", "A10AB05", "injection", "insulin", "100IU/ml"),

    # GI
    ("Omeprazole", "Prilosec", "A02BC01", "capsule", "PPI", "20mg"),
    ("Pantoprazole", "Protonix", "A02BC02", "tablet", "PPI", "40mg"),
    ("Ranitidine", "Zantac", "A02BA02", "tablet", "H2 blocker", "150mg"),
    ("Famotidine", "Pepcid", "A02BA03", "tablet", "H2 blocker", "20mg"),
    ("Loperamide", "Imodium", "A07DA03", "capsule", "antidiarrheal", "2mg"),
    ("Ondansetron", "Zofran", "A04AA01", "tablet", "antiemetic", "8mg"),
    ("Metoclopramide", "Reglan", "A03FA01", "tablet", "prokinetic", "10mg"),
    ("Drotaverine", "No-Spa", "A03AD02", "tablet", "antispasmodic", "40mg"),

    # Respiratory
    ("Salbutamol", "Ventolin", "R03AC02", "inhaler", "bronchodilator", "100mcg/dose"),
    ("Budesonide", "Pulmicort", "R03BA02", "inhaler", "corticosteroid (inhaled)", "200mcg/dose"),
    ("Theophylline", "Theo-24", "R03DA04", "tablet", "bronchodilator", "300mg"),
    ("Loratadine", "Claritin", "R06AX13", "tablet", "antihistamine", "10mg"),
    ("Cetirizine", "Zyrtec", "R06AE07", "tablet", "antihistamine", "10mg"),
    ("Diphenhydramine", "Benadryl", "R06AA02", "tablet", "antihistamine", "25mg"),

    # Psychiatry / Neurology
    ("Diazepam", "Valium", "N05BA01", "tablet", "benzodiazepine", "5mg"),
    ("Lorazepam", "Ativan", "N05BA06", "tablet", "benzodiazepine", "1mg"),
    ("Alprazolam", "Xanax", "N05BA12", "tablet", "benzodiazepine", "0.5mg"),
    ("Sertraline", "Zoloft", "N06AB06", "tablet", "SSRI", "50mg"),
    ("Fluoxetine", "Prozac", "N06AB03", "capsule", "SSRI", "20mg"),
    ("Amitriptyline", "Elavil", "N06AA09", "tablet", "TCA", "25mg"),
    ("Carbamazepine", "Tegretol", "N03AF01", "tablet", "anticonvulsant", "200mg"),
    ("Phenytoin", "Dilantin", "N03AB02", "capsule", "anticonvulsant", "100mg"),
    ("Valproic acid", "Depakine", "N03AG01", "tablet", "anticonvulsant", "500mg"),
    ("Levetiracetam", "Keppra", "N03AX14", "tablet", "anticonvulsant", "500mg"),

    # Endocrine
    ("Levothyroxine", "Synthroid", "H03AA01", "tablet", "thyroid hormone", "50mcg"),
    ("Prednisolone", "Prelone", "H02AB06", "tablet", "corticosteroid", "5mg"),
    ("Dexamethasone", "Decadron", "H02AB02", "tablet", "corticosteroid", "0.5mg"),
    ("Hydrocortisone", "Cortef", "H02AB09", "tablet", "corticosteroid", "10mg"),

    # Vitamins/Supplements
    ("Folic acid", "Folvite", "B03BB01", "tablet", "vitamin", "5mg"),
    ("Vitamin B12 (Cyanocobalamin)", "Cobalin-H", "B03BA01", "injection", "vitamin", "1mg/ml"),
    ("Iron (Ferrous sulfate)", "Feosol", "B03AA07", "tablet", "iron supplement", "325mg"),
    ("Vitamin D3 (Cholecalciferol)", "Drisdol", "A11CC05", "tablet", "vitamin", "1000IU"),

    # Antifungal/Antiviral
    ("Fluconazole", "Diflucan", "J02AC01", "capsule", "antifungal", "150mg"),
    ("Itraconazole", "Sporanox", "J02AC02", "capsule", "antifungal", "100mg"),
    ("Acyclovir", "Zovirax", "J05AB01", "tablet", "antiviral", "400mg"),
    ("Oseltamivir", "Tamiflu", "J05AH02", "capsule", "antiviral", "75mg"),

    # Miscellaneous (uzbek-relevant brands)
    ("Cotrimoxazole", "Biseptol", "J01EE01", "tablet", "antibiotic", "480mg"),
    ("Nimesulide", "Nise", "M01AX17", "tablet", "NSAID", "100mg"),
    ("Mebendazole", "Vermox", "P02CA01", "tablet", "antihelminthic", "100mg"),
    ("Albendazole", "Zentel", "P02CA03", "tablet", "antihelminthic", "400mg"),
    ("Pyrantel", "Pirantel", "P02CC01", "tablet", "antihelminthic", "250mg"),
]


def seed():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS drugs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inn TEXT, brand_name TEXT, atc_code TEXT,
        form TEXT, dose TEXT, manufacturer TEXT, country TEXT,
        registration_number TEXT, category TEXT, description TEXT,
        lang TEXT DEFAULT 'uz',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(inn, brand_name, dose, lang)
    )
    ''')
    inserted = 0
    for inn, brand, atc, form, category, dose in DRUGS:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO drugs (inn, brand_name, atc_code, form, dose, category, lang)
                VALUES (?, ?, ?, ?, ?, ?, 'en')
            """, (inn, brand, atc, form, dose, category))
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            print(f"Skip {inn}: {e}")
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM drugs")
    total = cur.fetchone()[0]
    conn.close()
    print(f"[seed_drugs] Inserted {inserted} new drugs. Total in DB: {total}")
    return inserted


if __name__ == "__main__":
    seed()
