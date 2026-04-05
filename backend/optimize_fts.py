import sqlite3
import os
import time

db_path = r'c:\Users\Администратор\Desktop\2\backend\tahrirchi.db'

def optimize_dictionary_fts():
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    print(f"[*] Starting FTS5 transformation for {db_path}...")
    start_time = time.time()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Create the virtual FTS5 table
        print("[*] Creating dictionary_fts virtual table...")
        cursor.execute("DROP TABLE IF EXISTS dictionary_fts")
        cursor.execute("""
            CREATE VIRTUAL TABLE dictionary_fts USING fts5(
                word,
                content='dictionary',
                content_rowid='id'
            )
        """)
        
        # 2. Populate the FTS5 index
        print("[*] Populating FTS5 index (this may take several minutes for 8.7M rows)...")
        # For 'external content' tables, we use the build command
        cursor.execute("INSERT INTO dictionary_fts(dictionary_fts) VALUES('rebuild')")
        
        conn.commit()
        
        # 3. Optimize (compaction)
        print("[*] Optimizing FTS5 index structure...")
        cursor.execute("INSERT INTO dictionary_fts(dictionary_fts) VALUES('optimize')")
        conn.commit()
        
        end_time = time.time()
        duration = end_time - start_time
        print(f"[+] FTS5 transformation complete in {duration:.2f} seconds.")
        
        # 4. Verify count
        cursor.execute("SELECT count(*) FROM dictionary_fts")
        print(f"[+] Total indexed words: {cursor.fetchone()[0]}")
        
    except Exception as e:
        print(f"[!] Error during FTS5 transformation: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    optimize_dictionary_fts()
