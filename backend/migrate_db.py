import sqlite3
import os

DB_PATH = r'c:\Users\Администратор\Desktop\2\backend\pharma_editor.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"File not found: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN department TEXT')
        conn.commit()
        print("Success: Column 'department' added to 'users' table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Notice: Column 'department' already exists.")
        else:
            print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
