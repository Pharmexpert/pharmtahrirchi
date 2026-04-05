import sqlite3
import requests
import json
import time
import os
import sys

# Configuration
LOCAL_DB = os.path.join(os.path.dirname(__file__), "..", "pharma_editor.db")
if not os.path.exists(LOCAL_DB):
    LOCAL_DB = "pharma_editor.db"

BASE_URL = "https://pharma-backend-production-38bb.up.railway.app"
SEED_SECRET = "pharma_dev_sync_2026"

ENDPOINTS = [
    f"{BASE_URL}/api/linguistic/sync-all-rules",
    f"{BASE_URL}/api/admin/rules/batch",
]

def seed_rules():
    if not os.path.exists(LOCAL_DB):
        print(f"Error: {LOCAL_DB} not found.")
        print(f"Current dir: {os.getcwd()}")
        return

    conn = sqlite3.connect(LOCAL_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT wrong_form, correct_form, error_type, context, lang, source FROM sayqallash_rules")
    rules = [dict(row) for row in cursor.fetchall()]
    conn.close()

    total = len(rules)
    print(f"Found {total} rules locally. Starting sync...")

    # Find working endpoint
    working_url = None
    headers = {
        "Content-Type": "application/json",
        "X-Seed-Secret": SEED_SECRET
    }

    for url in ENDPOINTS:
        try:
            probe = requests.post(url, headers=headers, json=[], timeout=15)
            if probe.status_code in (200, 422):  # 422 means endpoint exists but validation error (empty list is ok)
                working_url = url
                print(f"Using endpoint: {url}")
                break
            else:
                print(f"Endpoint {url} returned {probe.status_code}, trying next...")
        except Exception as e:
            print(f"Endpoint {url} unreachable: {e}, trying next...")

    if not working_url:
        print("ERROR: No working endpoint found. Please redeploy and try again.")
        return

    batch_size = 200
    total_inserted = 0

    for i in range(0, total, batch_size):
        batch = rules[i: i + batch_size]
        for attempt in range(3):
            try:
                response = requests.post(working_url, headers=headers, json=batch, timeout=60)
                if response.status_code == 200:
                    result = response.json()
                    inserted = result.get("inserted", result.get("imported", len(batch)))
                    total_inserted += inserted
                    progress_pct = min(100, round((i + len(batch)) / total * 100))
                    print(f"[{progress_pct}%] Batch {i//batch_size + 1}: {i + len(batch)}/{total} sent, {inserted} new rules inserted.")
                    break
                else:
                    print(f"  Attempt {attempt+1}: {response.status_code} - {response.text[:200]}")
                    time.sleep(2)
            except Exception as e:
                print(f"  Attempt {attempt+1} exception: {e}")
                time.sleep(3)
        else:
            print(f"Failed batch at offset {i} after 3 attempts. Stopping.")
            break

    print(f"\nSync completed. Total new rules inserted: {total_inserted} / {total} sent.")

if __name__ == "__main__":
    seed_rules()
