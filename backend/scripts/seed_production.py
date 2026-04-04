import sqlite3
import requests
import json
import time
import os

# Configuration
LOCAL_DB = "pharma_editor.db"
# PRODUCTION_URL = "https://pharma-backend-production-38bb.up.railway.app/api/admin/rules/batch"
PRODUCTION_URL = "https://pharma-backend-production-38bb.up.railway.app/api/admin/rules/batch"
SEED_SECRET = "pharma_dev_sync_2026"

def seed_rules():
    if not os.path.exists(LOCAL_DB):
        print(f"Error: {LOCAL_DB} not found in current directory.")
        return

    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT wrong_form, correct_form, error_type, context, lang, source FROM sayqallash_rules")
    rules = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    total = len(rules)
    print(f"Found {total} rules locally. Starting sync...")
    
    batch_size = 100
    headers = {
        "Content-Type": "application/json",
        "X-Seed-Secret": SEED_SECRET
    }
    
    for i in range(0, total, batch_size):
        batch = rules[i : i + batch_size]
        try:
            response = requests.post(PRODUCTION_URL, headers=headers, json=batch, timeout=30)
            if response.status_code == 200:
                print(f"Progress: {i + len(batch)} / {total} synced.")
            else:
                print(f"Error at batch {i}: {response.status_code} - {response.text}")
                break
        except Exception as e:
            print(f"Exception at batch {i}: {e}")
            break
            
    print("Sync process completed.")

if __name__ == "__main__":
    seed_rules()
