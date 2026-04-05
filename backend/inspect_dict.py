import sqlite3
import os

db_path = r'c:\Users\Администратор\Desktop\2\backend\tahrirchi.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='dictionary'")
        res = cursor.fetchone()
        print(f"Schema: {res[0] if res else 'Table not found'}")
        
        cursor.execute("SELECT COUNT(*) FROM dictionary")
        print(f"Count: {cursor.fetchone()[0]}")
        conn.close()
    except Exception as e:
        print(f"Exception: {e}")
