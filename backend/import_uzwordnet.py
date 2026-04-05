"""
Import UzWordnet synonyms into pharma_editor.db synonyms table.
UzWordnet format: WN-LMF XML with LexicalEntry + Sense → Synset mappings.
Words sharing the same synset are synonyms.
"""
import os
import sys
import sqlite3
import xml.etree.ElementTree as ET
from collections import defaultdict
from itertools import combinations

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "pharma_editor.db")
UZWORDNET_DIR = os.path.join(SCRIPT_DIR, "..", "Qonun", "UzWordnet")


def find_xml_files(directory):
    """Find all XML files (UUID-named) in UzWordnet directory."""
    files = []
    for f in os.listdir(directory):
        path = os.path.join(directory, f)
        if os.path.isfile(path) and not f.endswith('.md'):
            # Check if it's XML
            try:
                with open(path, 'r', encoding='utf-8') as fh:
                    first_line = fh.readline()
                    if '<?xml' in first_line:
                        files.append(path)
            except Exception:
                pass
    return files


def parse_wordnet_xml(xml_path):
    """Parse WN-LMF XML and return synset → [words] mapping."""
    synsets = defaultdict(list)
    pos_map = {}

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        for lexicon in root.findall('.//Lexicon'):
            for entry in lexicon.findall('LexicalEntry'):
                lemma = entry.find('Lemma')
                if lemma is None:
                    continue
                word = lemma.get('writtenForm', '').strip()
                pos = lemma.get('partOfSpeech', '')

                if not word:
                    continue

                for sense in entry.findall('Sense'):
                    synset_id = sense.get('synset', '')
                    if synset_id:
                        synsets[synset_id].append(word)
                        pos_map[word] = pos

    except Exception as e:
        print(f"  [!] Error parsing {xml_path}: {e}")

    return synsets, pos_map


def import_to_db(synsets, pos_map, db_path):
    """Import synonym pairs from synset groups into SQLite."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure synonyms table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS synonyms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT,
            synonym TEXT,
            lang TEXT DEFAULT 'uz',
            part_of_speech TEXT DEFAULT '',
            frequency INTEGER DEFAULT 1,
            probability_scale REAL DEFAULT 0.0,
            source TEXT DEFAULT 'uzwordnet',
            created_by TEXT DEFAULT 'system',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(word, synonym, lang)
        )
    """)

    total_pairs = 0
    inserted = 0
    skipped = 0

    for synset_id, words in synsets.items():
        # Remove duplicates within synset
        unique_words = list(dict.fromkeys(words))
        if len(unique_words) < 2:
            continue

        # Generate all synonym pairs (bidirectional)
        for w1, w2 in combinations(unique_words, 2):
            if w1.lower() == w2.lower():
                continue
            total_pairs += 2  # bidirectional

            pos = pos_map.get(w1, pos_map.get(w2, ''))

            for word, synonym in [(w1, w2), (w2, w1)]:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO synonyms
                            (word, synonym, lang, part_of_speech, source, created_by)
                        VALUES (?, ?, 'uz', ?, 'uzwordnet', 'system')
                    """, (word, synonym, pos))
                    if cursor.rowcount > 0:
                        inserted += 1
                    else:
                        skipped += 1
                except Exception:
                    skipped += 1

    conn.commit()
    conn.close()

    return total_pairs, inserted, skipped


def main():
    print("=" * 50)
    print("  UzWordnet → Pharma Editor Synonyms Import")
    print("=" * 50)

    if not os.path.exists(UZWORDNET_DIR):
        print(f"[!] UzWordnet directory not found: {UZWORDNET_DIR}")
        sys.exit(1)

    xml_files = find_xml_files(UZWORDNET_DIR)
    print(f"[*] Found {len(xml_files)} XML file(s)")

    all_synsets = defaultdict(list)
    all_pos = {}

    for xml_file in xml_files:
        print(f"  Parsing: {os.path.basename(xml_file)}...")
        synsets, pos_map = parse_wordnet_xml(xml_file)
        for sid, words in synsets.items():
            all_synsets[sid].extend(words)
        all_pos.update(pos_map)

    # Stats
    total_synsets = len(all_synsets)
    multi_word_synsets = sum(1 for words in all_synsets.values() if len(set(words)) >= 2)
    unique_words = set()
    for words in all_synsets.values():
        unique_words.update(words)

    print(f"\n[*] Total synsets: {total_synsets}")
    print(f"[*] Synsets with 2+ words: {multi_word_synsets}")
    print(f"[*] Unique words: {len(unique_words)}")

    print(f"\n[*] Importing to {DB_PATH}...")
    total, inserted, skipped = import_to_db(all_synsets, all_pos, DB_PATH)

    print(f"\n[+] DONE!")
    print(f"    Total pairs generated: {total}")
    print(f"    Inserted: {inserted}")
    print(f"    Skipped (duplicates): {skipped}")


if __name__ == "__main__":
    main()
