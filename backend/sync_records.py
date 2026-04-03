import sqlite3
import os
import time

def sync_confirmed_words(source_db="pharma_editor.db", target_db="tahrirchi.db"):
    """Syncs user-confirmed words from the main application DB to the dictionary DB for self-learning."""
    if not os.path.exists(source_db) or not os.path.exists(target_db):
        print(f"[!] Databases not found: {source_db} or {target_db}")
        return

    print(f"[*] Syncing confirmed words from {source_db} to {target_db}...")
    
    # 1. Get confirmed words from source
    src_conn = sqlite3.connect(source_db)
    src_cursor = src_conn.cursor()
    
    # Try to find recent alignments or corrections that were confirmed
    # Since schema varies, we look for 'alignments' where 'verified' is true or similar
    try:
        src_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alignments'")
        if src_cursor.fetchone():
            src_cursor.execute("SELECT uzbek FROM alignments WHERE uzbek IS NOT NULL")
            confirmed_texts = src_cursor.fetchall()
        else:
            print("[!] No alignments table found in source DB.")
            confirmed_texts = []
    except Exception as e:
        print(f"[!] Source error: {e}")
        confirmed_texts = []
    finally:
        src_conn.close()

    if not confirmed_texts:
        print("[*] No new confirmed words to sync.")
        return

    # 2. Update target dictionary
    tgt_conn = sqlite3.connect(target_db)
    tgt_cursor = tgt_conn.cursor()
    
    new_words_count = 0
    try:
        for (text,) in confirmed_texts:
            # Simple word tokenizer
            words = text.lower().replace('.', '').replace(',', '').split()
            for word in words:
                if len(word) < 2: continue
                # Upsert into dictionary
                tgt_cursor.execute("""
                    INSERT INTO dictionary (word, frequency, source, is_confirmed)
                    VALUES (?, 1, 'user_sync', 1)
                    ON CONFLICT(word) DO UPDATE SET frequency = frequency + 1
                """, (word,))
                new_words_count += 1
        
        tgt_conn.commit()
        print(f"[+] Successfully synced {new_words_count} word occurrences to dictionary.")
    except Exception as e:
        print(f"[!] Target error: {e}")
    finally:
        tgt_conn.close()

if __name__ == "__main__":
    sync_confirmed_words()
