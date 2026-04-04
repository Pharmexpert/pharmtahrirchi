import os
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UZWORDNET_DIR = os.path.join(BASE_DIR, "Qonun", "UzWordnet")
DB_PATH = os.path.join(BASE_DIR, "backend", "pharma_editor.db")

def import_uzwordnet():
    if not os.path.exists(UZWORDNET_DIR):
        print(f"Error: UzWordnet directory not found at {UZWORDNET_DIR}")
        return

    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table if not exists (redundant, but safe)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS synonyms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            synonym TEXT NOT NULL,
            lang TEXT NOT NULL DEFAULT 'uz',
            frequency INTEGER DEFAULT 0,
            source TEXT DEFAULT 'ai',
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(word, synonym, lang)
        )
    ''')

    synsets = {} # synset_id -> set of lemmas

    xml_files = [f for f in os.listdir(UZWORDNET_DIR) if not f.endswith(".md")]
    print(f"Found {len(xml_files)} potential data files.")

    for filename in xml_files:
        file_path = os.path.join(UZWORDNET_DIR, filename)
        print(f"Processing: {filename}...")
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # WN-LMF structure: LexicalResource -> Lexicon -> LexicalEntry
            lexicon = root.find("Lexicon")
            if lexicon is None: continue
            
            for entry in lexicon.findall("LexicalEntry"):
                lemma = entry.find("Lemma")
                if lemma is None: continue
                word = lemma.get("writtenForm")
                
                for sense in entry.findall("Sense"):
                    synset_id = sense.get("synset")
                    if synset_id not in synsets:
                        synsets[synset_id] = set()
                    synsets[synset_id].add(word)
                    
        except Exception as e:
            print(f"Error parsing {filename}: {e}")

    print(f"Extracted {len(synsets)} synsets. Inserting into database...")

    count = 0
    for synset_id, words in synsets.items():
        words_list = list(words)
        if len(words_list) < 2: continue
        
        # Insert all pairs as synonyms
        for i in range(len(words_list)):
            for j in range(len(words_list)):
                if i == j: continue
                
                word = words_list[i]
                synonym = words_list[j]
                
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO synonyms (word, synonym, lang, source, created_by)
                        VALUES (?, ?, 'uz', 'wordnet', 'system_import')
                    ''', (word, synonym))
                    if cursor.rowcount > 0:
                        count += 1
                except Exception as e:
                    pass

    conn.commit()
    conn.close()
    print(f"Successfully imported {count} synonym pairs.")

if __name__ == "__main__":
    import_uzwordnet()
