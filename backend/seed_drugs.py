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

    # Additional WHO Essential Medicines (batch 2)
    ("Diphenhydramine", "Benadryl", "R06AA02", "injection", "antihistamine", "10mg/ml"),
    ("Chlorpheniramine", "Allerfin", "R06AB04", "tablet", "antihistamine", "4mg"),
    ("Promethazine", "Phenergan", "R06AD02", "tablet", "antihistamine", "25mg"),
    ("Dexchlorpheniramine", "Polaramine", "R06AB02", "tablet", "antihistamine", "2mg"),
    ("Adrenaline (Epinephrine)", "EpiPen", "C01CA24", "injection", "sympathomimetic", "1mg/ml"),
    ("Atropine", "Atropen", "A03BA01", "injection", "anticholinergic", "0.5mg/ml"),
    ("Naloxone", "Narcan", "V03AB15", "injection", "opioid antagonist", "0.4mg/ml"),
    ("Flumazenil", "Anexate", "V03AB25", "injection", "benzo antagonist", "0.5mg/5ml"),
    ("Calcium gluconate", "Calcinate", "A12AA03", "injection", "calcium supplement", "10%"),
    ("Magnesium sulfate", "Epsom", "B05XA05", "injection", "electrolyte", "25%"),
    ("Potassium chloride", "Kay-Cee-L", "B05XA01", "injection", "electrolyte", "7.5%"),
    ("Sodium bicarbonate", "Sodabic", "B05XA02", "injection", "alkalinizer", "8.4%"),
    ("Glucose 5%", "Dextrose", "B05BA03", "infusion", "carbohydrate", "5%"),
    ("Normal saline", "NaCl 0.9%", "B05BB01", "infusion", "electrolyte", "0.9%"),
    ("Ringer lactate", "Hartmann", "B05BB01", "infusion", "electrolyte", "500ml"),
    ("Mannitol", "Osmitrol", "B05BC01", "infusion", "osmotic diuretic", "20%"),
    ("Dopamine", "Intropin", "C01CA04", "injection", "vasopressor", "200mg/5ml"),
    ("Dobutamine", "Dobutrex", "C01CA07", "injection", "inotrope", "250mg/20ml"),
    ("Nitroglycerin", "Nitrostat", "C01DA02", "sublingual", "vasodilator", "0.5mg"),
    ("Isosorbide dinitrate", "Isordil", "C01DA08", "tablet", "vasodilator", "10mg"),
    ("Isosorbide mononitrate", "Imdur", "C01DA14", "tablet", "vasodilator", "20mg"),
    ("Digoxin", "Lanoxin", "C01AA05", "tablet", "cardiac glycoside", "0.25mg"),
    ("Amiodarone", "Cordarone", "C01BD01", "tablet", "antiarrhythmic", "200mg"),
    ("Verapamil", "Isoptin", "C08DA01", "tablet", "calcium blocker", "80mg"),
    ("Diltiazem", "Cardizem", "C08DB01", "tablet", "calcium blocker", "60mg"),
    ("Nifedipine", "Adalat", "C08CA05", "capsule", "calcium blocker", "10mg"),
    ("Valsartan", "Diovan", "C09CA03", "tablet", "ARB", "80mg"),
    ("Telmisartan", "Micardis", "C09CA07", "tablet", "ARB", "40mg"),
    ("Candesartan", "Atacand", "C09CA06", "tablet", "ARB", "8mg"),
    ("Irbesartan", "Aprovel", "C09CA04", "tablet", "ARB", "150mg"),
    ("Ramipril", "Tritace", "C09AA05", "tablet", "ACE inhibitor", "5mg"),
    ("Perindopril", "Coversyl", "C09AA04", "tablet", "ACE inhibitor", "4mg"),
    ("Nebivolol", "Nebilet", "C07AB12", "tablet", "beta-blocker", "5mg"),
    ("Carvedilol", "Coreg", "C07AG02", "tablet", "beta-blocker", "25mg"),
    ("Propranolol", "Inderal", "C07AA05", "tablet", "beta-blocker", "40mg"),
    ("Indapamide", "Natrilix", "C03BA11", "tablet", "diuretic", "1.5mg"),
    ("Torasemide", "Torem", "C03CA04", "tablet", "loop diuretic", "5mg"),
    ("Pravastatin", "Pravachol", "C10AA03", "tablet", "statin", "20mg"),
    ("Fluvastatin", "Lescol", "C10AA04", "capsule", "statin", "40mg"),
    ("Ezetimibe", "Zetia", "C10AX09", "tablet", "cholesterol absorber", "10mg"),
    ("Fenofibrate", "Lipanthyl", "C10AB05", "capsule", "fibrate", "200mg"),
    ("Gemfibrozil", "Lopid", "C10AB04", "capsule", "fibrate", "600mg"),
    ("Dipyridamole", "Persantine", "B01AC07", "tablet", "antiplatelet", "75mg"),
    ("Enoxaparin", "Clexane", "B01AB05", "injection", "LMWH", "40mg/0.4ml"),
    ("Dalteparin", "Fragmin", "B01AB04", "injection", "LMWH", "2500IU/0.2ml"),
    ("Rivaroxaban", "Xarelto", "B01AF01", "tablet", "DOAC", "20mg"),
    ("Apixaban", "Eliquis", "B01AF02", "tablet", "DOAC", "5mg"),
    ("Dabigatran", "Pradaxa", "B01AE07", "capsule", "DOAC", "150mg"),
    ("Clindamycin", "Cleocin", "J01FF01", "capsule", "antibiotic (lincosamide)", "300mg"),
    ("Linezolid", "Zyvox", "J01XX08", "tablet", "oxazolidinone", "600mg"),
    ("Meropenem", "Meronem", "J01DH02", "injection", "carbapenem", "1g"),
    ("Imipenem/Cilastatin", "Tienam", "J01DH51", "injection", "carbapenem", "500mg"),
    ("Piperacillin/Tazobactam", "Tazocin", "J01CR05", "injection", "penicillin+inhibitor", "4.5g"),
    ("Ceftazidime", "Fortum", "J01DD02", "injection", "cephalosporin 3rd", "1g"),
    ("Cefixime", "Suprax", "J01DD08", "capsule", "cephalosporin 3rd", "400mg"),
    ("Cefepime", "Maxipime", "J01DE01", "injection", "cephalosporin 4th", "1g"),
    ("Nitrofurantoin", "Macrobid", "J01XE01", "capsule", "urinary antiseptic", "100mg"),
    ("Rifampicin", "Rifadin", "J04AB02", "capsule", "antituberculosis", "300mg"),
    ("Isoniazid", "Nydrazid", "J04AC01", "tablet", "antituberculosis", "300mg"),
    ("Pyrazinamide", "Pyrazinamide", "J04AK01", "tablet", "antituberculosis", "500mg"),
    ("Ethambutol", "Myambutol", "J04AK02", "tablet", "antituberculosis", "400mg"),
    ("Streptomycin", "Streptomycin", "J01GA01", "injection", "aminoglycoside", "1g"),
    ("Amoxicillin/Clavulanate", "Augmentin", "J01CR02", "tablet", "penicillin+inhibitor", "875mg/125mg"),
    ("Sitagliptin", "Januvia", "A10BH01", "tablet", "DPP-4 inhibitor", "100mg"),
    ("Vildagliptin", "Galvus", "A10BH02", "tablet", "DPP-4 inhibitor", "50mg"),
    ("Empagliflozin", "Jardiance", "A10BK03", "tablet", "SGLT2 inhibitor", "10mg"),
    ("Dapagliflozin", "Forxiga", "A10BK01", "tablet", "SGLT2 inhibitor", "10mg"),
    ("Pioglitazone", "Actos", "A10BG03", "tablet", "thiazolidinedione", "15mg"),
    ("Glimepiride", "Amaryl", "A10BB12", "tablet", "sulfonylurea", "2mg"),
    ("Repaglinide", "NovoNorm", "A10BX02", "tablet", "meglitinide", "1mg"),
    ("Esomeprazole", "Nexium", "A02BC05", "capsule", "PPI", "20mg"),
    ("Lansoprazole", "Prevacid", "A02BC03", "capsule", "PPI", "30mg"),
    ("Rabeprazole", "Pariet", "A02BC04", "tablet", "PPI", "20mg"),
    ("Sucralfate", "Carafate", "A02BX02", "tablet", "mucosal protectant", "1g"),
    ("Bismuth subsalicylate", "Pepto-Bismol", "A07BB01", "tablet", "antidiarrheal", "262mg"),
    ("Mesalamine", "Asacol", "A07EC02", "tablet", "5-ASA", "400mg"),
    ("Sulfasalazine", "Salazopyrin", "A07EC01", "tablet", "5-ASA", "500mg"),
    ("Prucalopride", "Resolor", "A06AX05", "tablet", "5-HT4 agonist", "2mg"),
    ("Lactulose", "Duphalac", "A06AD11", "syrup", "laxative", "10g/15ml"),
    ("Domperidone", "Motilium", "A03FA03", "tablet", "prokinetic", "10mg"),
    ("Escitalopram", "Cipralex", "N06AB10", "tablet", "SSRI", "10mg"),
    ("Paroxetine", "Paxil", "N06AB05", "tablet", "SSRI", "20mg"),
    ("Citalopram", "Celexa", "N06AB04", "tablet", "SSRI", "20mg"),
    ("Venlafaxine", "Effexor", "N06AX16", "capsule", "SNRI", "75mg"),
    ("Duloxetine", "Cymbalta", "N06AX21", "capsule", "SNRI", "30mg"),
    ("Mirtazapine", "Remeron", "N06AX11", "tablet", "antidepressant", "30mg"),
    ("Bupropion", "Wellbutrin", "N06AX12", "tablet", "antidepressant", "150mg"),
    ("Clonazepam", "Klonopin", "N03AE01", "tablet", "benzodiazepine", "0.5mg"),
    ("Midazolam", "Dormicum", "N05CD08", "injection", "benzodiazepine", "5mg/ml"),
    ("Gabapentin", "Neurontin", "N03AX12", "capsule", "anticonvulsant", "300mg"),
    ("Pregabalin", "Lyrica", "N03AX16", "capsule", "anticonvulsant", "75mg"),
    ("Lamotrigine", "Lamictal", "N03AX09", "tablet", "anticonvulsant", "100mg"),
    ("Topiramate", "Topamax", "N03AX11", "tablet", "anticonvulsant", "50mg"),
    ("Risperidone", "Risperdal", "N05AX08", "tablet", "atypical antipsychotic", "2mg"),
    ("Olanzapine", "Zyprexa", "N05AH03", "tablet", "atypical antipsychotic", "10mg"),
    ("Quetiapine", "Seroquel", "N05AH04", "tablet", "atypical antipsychotic", "100mg"),
    ("Aripiprazole", "Abilify", "N05AX12", "tablet", "atypical antipsychotic", "10mg"),
    ("Haloperidol", "Haldol", "N05AD01", "tablet", "typical antipsychotic", "5mg"),
    ("Buspirone", "Buspar", "N05BE01", "tablet", "anxiolytic", "10mg"),
    ("Zolpidem", "Ambien", "N05CF02", "tablet", "hypnotic", "10mg"),
    ("Donepezil", "Aricept", "N06DA02", "tablet", "cholinesterase inhibitor", "5mg"),
    ("Memantine", "Namenda", "N06DX01", "tablet", "NMDA antagonist", "10mg"),
    ("Methotrexate", "Trexall", "L04AX03", "tablet", "immunosuppressant", "2.5mg"),
    ("Azathioprine", "Imuran", "L04AX01", "tablet", "immunosuppressant", "50mg"),
    ("Cyclosporine", "Sandimmune", "L04AD01", "capsule", "immunosuppressant", "100mg"),
    ("Tacrolimus", "Prograf", "L04AD02", "capsule", "immunosuppressant", "1mg"),
    ("Hydroxychloroquine", "Plaquenil", "P01BA02", "tablet", "antimalarial/DMARD", "200mg"),
    ("Colchicine", "Colcrys", "M04AC01", "tablet", "gout", "0.5mg"),
    ("Allopurinol", "Zyloric", "M04AA01", "tablet", "xanthine oxidase inhibitor", "100mg"),
    ("Febuxostat", "Uloric", "M04AA03", "tablet", "xanthine oxidase inhibitor", "40mg"),
    ("Meloxicam", "Mobic", "M01AC06", "tablet", "NSAID COX-2", "15mg"),
    ("Celecoxib", "Celebrex", "M01AH01", "capsule", "NSAID COX-2", "200mg"),
    ("Indomethacin", "Indocin", "M01AB01", "capsule", "NSAID", "25mg"),
    ("Piroxicam", "Feldene", "M01AC01", "capsule", "NSAID", "20mg"),
    ("Ketoprofen", "Oruvail", "M01AE03", "capsule", "NSAID", "100mg"),
    ("Baclofen", "Lioresal", "M03BX01", "tablet", "muscle relaxant", "10mg"),
    ("Tizanidine", "Zanaflex", "M03BX02", "tablet", "muscle relaxant", "2mg"),
    ("Cyclobenzaprine", "Flexeril", "M03BX08", "tablet", "muscle relaxant", "10mg"),
    ("Alendronate", "Fosamax", "M05BA04", "tablet", "bisphosphonate", "70mg"),
    ("Risedronate", "Actonel", "M05BA07", "tablet", "bisphosphonate", "35mg"),
    ("Zoledronic acid", "Zometa", "M05BA08", "infusion", "bisphosphonate", "4mg/5ml"),
    ("Raloxifene", "Evista", "G03XC01", "tablet", "SERM", "60mg"),
    ("Calcitonin salmon", "Miacalcin", "H05BA01", "nasal spray", "calcitonin", "200IU"),
    ("Tamoxifen", "Nolvadex", "L02BA01", "tablet", "SERM antiestrogen", "20mg"),
    ("Letrozole", "Femara", "L02BG04", "tablet", "aromatase inhibitor", "2.5mg"),
    ("Anastrozole", "Arimidex", "L02BG03", "tablet", "aromatase inhibitor", "1mg"),
    ("Finasteride", "Proscar", "G04CB01", "tablet", "5-alpha reductase inh", "5mg"),
    ("Tamsulosin", "Flomax", "G04CA02", "capsule", "alpha blocker", "0.4mg"),
    ("Sildenafil", "Viagra", "G04BE03", "tablet", "PDE5 inhibitor", "50mg"),
    ("Tadalafil", "Cialis", "G04BE08", "tablet", "PDE5 inhibitor", "20mg"),
    ("Oxybutynin", "Ditropan", "G04BD04", "tablet", "anticholinergic", "5mg"),
    ("Levonorgestrel", "Plan B", "G03AC03", "tablet", "progestin", "1.5mg"),
    ("Levothyroxine", "Euthyrox", "H03AA01", "tablet", "thyroid", "100mcg"),
    ("Propylthiouracil", "PTU", "H03BA02", "tablet", "antithyroid", "50mg"),
    ("Methimazole", "Tapazole", "H03BB02", "tablet", "antithyroid", "5mg"),
    ("Desmopressin", "DDAVP", "H01BA02", "tablet", "vasopressin analog", "0.1mg"),
    ("Oxytocin", "Pitocin", "H01BB02", "injection", "oxytocin", "5IU/ml"),
    ("Methylprednisolone", "Medrol", "H02AB04", "tablet", "corticosteroid", "4mg"),
    ("Betamethasone", "Celestone", "H02AB01", "injection", "corticosteroid", "4mg/ml"),
    ("Triamcinolone", "Kenalog", "H02AB08", "injection", "corticosteroid", "40mg/ml"),
    ("Epinephrine (Inhaler)", "Primatene", "R03AA01", "inhaler", "bronchodilator", "200mcg"),
    ("Ipratropium", "Atrovent", "R03BB01", "inhaler", "anticholinergic", "20mcg/dose"),
    ("Tiotropium", "Spiriva", "R03BB04", "inhaler", "anticholinergic", "18mcg"),
    ("Formoterol", "Foradil", "R03AC13", "inhaler", "LABA", "12mcg"),
    ("Salmeterol", "Serevent", "R03AC12", "inhaler", "LABA", "25mcg/dose"),
    ("Montelukast", "Singulair", "R03DC03", "tablet", "leukotriene antagonist", "10mg"),
    ("Fluticasone", "Flonase", "R01AD08", "nasal spray", "corticosteroid", "50mcg"),
    ("Beclomethasone", "QVAR", "R03BA01", "inhaler", "corticosteroid", "100mcg/dose"),
    ("Ambroxol", "Mucosolvan", "R05CB06", "tablet", "mucolytic", "30mg"),
    ("Acetylcysteine", "ACC", "R05CB01", "tablet", "mucolytic", "600mg"),
    ("Dextromethorphan", "Robitussin", "R05DA09", "syrup", "cough suppressant", "15mg/5ml"),
    ("Bromhexine", "Bisolvon", "R05CB02", "tablet", "mucolytic", "8mg"),
    ("Guaifenesin", "Mucinex", "R05CA03", "tablet", "expectorant", "600mg"),
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
