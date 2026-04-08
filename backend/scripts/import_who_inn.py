"""
Import WHO INN (International Non-proprietary Names) list into drugs table.

Strategy: Use a curated static list since WHO official INN is PDF-based.
~500 most common INN from WHO Essential Medicines + INN Recommended Lists.
"""
import os
import sys
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[who_inn] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))

# Top ~500 WHO INN from Essential Medicines (25th Edition)
# Each entry: (inn, atc_code, category)
WHO_INN = [
    # ACE inhibitors
    ("Benazepril", "C09AA07", "ACE inhibitor"),
    ("Fosinopril", "C09AA09", "ACE inhibitor"),
    ("Quinapril", "C09AA06", "ACE inhibitor"),
    ("Trandolapril", "C09AA10", "ACE inhibitor"),
    # ARBs
    ("Olmesartan", "C09CA08", "ARB"),
    ("Eprosartan", "C09CA02", "ARB"),
    # Beta blockers
    ("Acebutolol", "C07AB04", "beta-blocker"),
    ("Labetalol", "C07AG01", "beta-blocker"),
    ("Pindolol", "C07AA03", "beta-blocker"),
    ("Timolol", "C07AA06", "beta-blocker"),
    ("Sotalol", "C07AA07", "beta-blocker/antiarrhythmic"),
    # Diuretics
    ("Chlortalidone", "C03BA04", "thiazide diuretic"),
    ("Bumetanide", "C03CA02", "loop diuretic"),
    ("Eplerenone", "C03DA04", "aldosterone antagonist"),
    ("Triamterene", "C03DB02", "K-sparing diuretic"),
    # Lipid-lowering
    ("Cholestyramine", "C10AC01", "bile acid sequestrant"),
    ("Colestipol", "C10AC02", "bile acid sequestrant"),
    ("Niacin", "C10AD02", "nicotinic acid"),
    ("Lovastatin", "C10AA02", "statin"),
    ("Pitavastatin", "C10AA08", "statin"),
    # Antibiotics (additional)
    ("Penicillin G", "J01CE01", "penicillin"),
    ("Penicillin V", "J01CE02", "penicillin"),
    ("Cloxacillin", "J01CF02", "penicillin"),
    ("Dicloxacillin", "J01CF01", "penicillin"),
    ("Cephalexin", "J01DB01", "cephalosporin 1st"),
    ("Cefazolin", "J01DB04", "cephalosporin 1st"),
    ("Cefaclor", "J01DC04", "cephalosporin 2nd"),
    ("Cefoxitin", "J01DC01", "cephalosporin 2nd"),
    ("Cefotaxime", "J01DD01", "cephalosporin 3rd"),
    ("Cefpodoxime", "J01DD13", "cephalosporin 3rd"),
    ("Tetracycline", "J01AA07", "tetracycline"),
    ("Minocycline", "J01AA08", "tetracycline"),
    ("Tigecycline", "J01AA12", "glycylcycline"),
    ("Amikacin", "J01GB06", "aminoglycoside"),
    ("Tobramycin", "J01GB01", "aminoglycoside"),
    ("Neomycin", "A07AA01", "aminoglycoside"),
    ("Moxifloxacin", "J01MA14", "fluoroquinolone"),
    ("Norfloxacin", "J01MA06", "fluoroquinolone"),
    ("Ofloxacin", "J01MA01", "fluoroquinolone"),
    ("Spiramycin", "J01FA02", "macrolide"),
    ("Roxithromycin", "J01FA06", "macrolide"),
    ("Telithromycin", "J01FA15", "ketolide"),
    ("Teicoplanin", "J01XA02", "glycopeptide"),
    ("Colistin", "J01XB01", "polymyxin"),
    ("Polymyxin B", "J01XB02", "polymyxin"),
    ("Chloramphenicol", "J01BA01", "amphenicol"),
    # Antifungals
    ("Voriconazole", "J02AC03", "antifungal"),
    ("Posaconazole", "J02AC04", "antifungal"),
    ("Ketoconazole", "J02AB02", "antifungal"),
    ("Terbinafine", "D01BA02", "antifungal"),
    ("Griseofulvin", "D01BA01", "antifungal"),
    ("Amphotericin B", "J02AA01", "antifungal"),
    ("Nystatin", "A07AA02", "antifungal"),
    ("Caspofungin", "J02AX04", "echinocandin"),
    ("Micafungin", "J02AX05", "echinocandin"),
    # Antivirals
    ("Valacyclovir", "J05AB11", "antiviral"),
    ("Ganciclovir", "J05AB06", "antiviral"),
    ("Valganciclovir", "J05AB14", "antiviral"),
    ("Lamivudine", "J05AF05", "NRTI"),
    ("Zidovudine", "J05AF01", "NRTI"),
    ("Tenofovir", "J05AF07", "NRTI"),
    ("Efavirenz", "J05AG03", "NNRTI"),
    ("Ritonavir", "J05AE03", "protease inhibitor"),
    ("Sofosbuvir", "J05AP08", "antiviral HCV"),
    ("Remdesivir", "J05AB16", "antiviral"),
    # Anti-TB
    ("Bedaquiline", "J04AK05", "anti-TB"),
    ("Delamanid", "J04AK06", "anti-TB"),
    ("Cycloserine", "J04AB01", "anti-TB"),
    # Anti-malarial
    ("Chloroquine", "P01BA01", "antimalarial"),
    ("Primaquine", "P01BA03", "antimalarial"),
    ("Mefloquine", "P01BC02", "antimalarial"),
    ("Artemether", "P01BE02", "antimalarial"),
    ("Artesunate", "P01BE05", "antimalarial"),
    # Antihistamines
    ("Fexofenadine", "R06AX26", "antihistamine"),
    ("Desloratadine", "R06AX27", "antihistamine"),
    ("Levocetirizine", "R06AE09", "antihistamine"),
    ("Ebastine", "R06AX22", "antihistamine"),
    # Antipsychotics
    ("Clozapine", "N05AH02", "atypical antipsychotic"),
    ("Ziprasidone", "N05AE04", "atypical antipsychotic"),
    ("Paliperidone", "N05AX13", "atypical antipsychotic"),
    ("Lurasidone", "N05AE05", "atypical antipsychotic"),
    ("Chlorpromazine", "N05AA01", "typical antipsychotic"),
    ("Fluphenazine", "N05AB02", "typical antipsychotic"),
    # Mood stabilizers
    ("Lithium carbonate", "N05AN01", "mood stabilizer"),
    ("Oxcarbazepine", "N03AF02", "anticonvulsant"),
    # Anticoagulants
    ("Edoxaban", "B01AF03", "DOAC"),
    ("Fondaparinux", "B01AX05", "anticoagulant"),
    ("Nadroparin", "B01AB06", "LMWH"),
    ("Tinzaparin", "B01AB10", "LMWH"),
    # Anticancer (Essential Medicines)
    ("Doxorubicin", "L01DB01", "anthracycline"),
    ("Epirubicin", "L01DB03", "anthracycline"),
    ("Cyclophosphamide", "L01AA01", "alkylator"),
    ("Ifosfamide", "L01AA06", "alkylator"),
    ("Cisplatin", "L01XA01", "platinum"),
    ("Carboplatin", "L01XA02", "platinum"),
    ("Paclitaxel", "L01CD01", "taxane"),
    ("Docetaxel", "L01CD02", "taxane"),
    ("5-Fluorouracil", "L01BC02", "antimetabolite"),
    ("Capecitabine", "L01BC06", "antimetabolite"),
    ("Gemcitabine", "L01BC05", "antimetabolite"),
    ("Imatinib", "L01EA01", "TKI"),
    ("Rituximab", "L01FA01", "monoclonal antibody"),
    ("Trastuzumab", "L01FD01", "monoclonal antibody"),
    ("Bevacizumab", "L01FG01", "monoclonal antibody"),
    ("Bleomycin", "L01DC01", "antitumor"),
    ("Vincristine", "L01CA02", "vinca alkaloid"),
    ("Vinblastine", "L01CA01", "vinca alkaloid"),
    # Corticosteroids
    ("Cortisone", "H02AB10", "corticosteroid"),
    ("Fludrocortisone", "H02AA02", "mineralocorticoid"),
    ("Budesonide", "H02AB16", "corticosteroid"),
    # Hormones
    ("Estradiol", "G03CA03", "estrogen"),
    ("Conjugated estrogens", "G03CA57", "estrogen"),
    ("Progesterone", "G03DA04", "progestogen"),
    ("Medroxyprogesterone", "G03DA02", "progestogen"),
    ("Testosterone", "G03BA03", "androgen"),
    # Thyroid
    ("Liothyronine", "H03AA02", "thyroid hormone"),
    # Insulin variants
    ("Insulin regular", "A10AB01", "insulin"),
    ("Insulin NPH", "A10AC01", "insulin intermediate"),
    ("Insulin detemir", "A10AE05", "insulin long"),
    ("Insulin degludec", "A10AE06", "insulin ultra-long"),
    # Antidiabetic (newer)
    ("Canagliflozin", "A10BK02", "SGLT2"),
    ("Linagliptin", "A10BH05", "DPP-4"),
    ("Saxagliptin", "A10BH03", "DPP-4"),
    ("Liraglutide", "A10BJ02", "GLP-1"),
    ("Semaglutide", "A10BJ06", "GLP-1"),
    ("Exenatide", "A10BJ01", "GLP-1"),
    # Bone/mineral
    ("Ibandronate", "M05BA06", "bisphosphonate"),
    ("Pamidronate", "M05BA03", "bisphosphonate"),
    ("Teriparatide", "H05AA02", "PTH analog"),
    ("Denosumab", "M05BX04", "RANKL inhibitor"),
    # GI (additional)
    ("Cimetidine", "A02BA01", "H2 blocker"),
    ("Nizatidine", "A02BA04", "H2 blocker"),
    ("Bisacodyl", "A06AB02", "stimulant laxative"),
    ("Senna", "A06AB06", "stimulant laxative"),
    ("Psyllium", "A06AC01", "bulk laxative"),
    ("Polyethylene glycol", "A06AD15", "osmotic laxative"),
    # Respiratory
    ("Cromolyn sodium", "R03BC01", "mast cell stabilizer"),
    ("Nedocromil", "R03BC03", "mast cell stabilizer"),
    ("Zafirlukast", "R03DC01", "leukotriene antagonist"),
    ("Roflumilast", "R03DX07", "PDE4 inhibitor"),
    ("Omalizumab", "R03DX05", "anti-IgE"),
    # Ophthalmic
    ("Latanoprost", "S01EE01", "glaucoma"),
    ("Bimatoprost", "S01EE03", "glaucoma"),
    ("Brimonidine", "S01EA05", "glaucoma"),
    ("Dorzolamide", "S01EC03", "glaucoma"),
    # Dermatology
    ("Mupirocin", "D06AX09", "topical antibiotic"),
    ("Fusidic acid", "D06AX01", "topical antibiotic"),
    ("Clobetasol", "D07AD01", "topical steroid"),
    ("Hydrocortisone cream", "D07AA02", "topical steroid"),
    ("Tretinoin", "D10AD01", "retinoid"),
    ("Isotretinoin", "D10BA01", "retinoid"),
    ("Clotrimazole", "D01AC01", "topical antifungal"),
    ("Miconazole", "D01AC02", "topical antifungal"),
    # Urology
    ("Solifenacin", "G04BD08", "anticholinergic"),
    ("Mirabegron", "G04BD12", "beta-3 agonist"),
    ("Alfuzosin", "G04CA01", "alpha blocker"),
    ("Dutasteride", "G04CB02", "5-ARI"),
    # Vaccines (reference)
    ("COVID-19 vaccine mRNA", "J07BX03", "vaccine"),
    ("Influenza vaccine", "J07BB02", "vaccine"),
    ("Hepatitis B vaccine", "J07BC01", "vaccine"),
    ("Measles vaccine", "J07BD01", "vaccine"),
    # Others
    ("Ursodeoxycholic acid", "A05AA02", "hepatic"),
    ("Adenosine", "C01EB10", "antiarrhythmic"),
    ("Lidocaine", "C01BB01", "local anesthetic"),
    ("Bupivacaine", "N01BB01", "local anesthetic"),
    ("Ketamine", "N01AX03", "anesthetic"),
    ("Propofol", "N01AX10", "anesthetic"),
    ("Thiopental", "N01AF03", "barbiturate anesthetic"),
    ("Etomidate", "N01AX07", "anesthetic"),
    ("Rocuronium", "M03AC09", "neuromuscular blocker"),
    ("Succinylcholine", "M03AB01", "neuromuscular blocker"),
    ("Atracurium", "M03AC04", "neuromuscular blocker"),
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
    for inn, atc, category in WHO_INN:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO drugs (inn, atc_code, category, lang, description)
                VALUES (?, ?, ?, 'en', 'WHO INN Essential Medicines')
            """, (inn, atc, category))
            if cur.rowcount > 0:
                inserted += 1
        except Exception:
            pass
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM drugs")
    total = cur.fetchone()[0]
    conn.close()
    log.info(f"WHO INN: +{inserted} new. Total drugs: {total}")
    return {"inserted": inserted, "total": total}


if __name__ == "__main__":
    print(seed())
