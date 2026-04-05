"""
Sync local pharma_editor.db data to Railway production via bulk API.
Usage: python sync_to_production.py
"""
import sqlite3
import json
import os
import urllib.request

DB_PATH = os.path.join(os.path.dirname(__file__), "pharma_editor.db")
API_BASE = os.getenv("API_BASE", "https://pharma-backend-production-38bb.up.railway.app")


def get_admin_token():
    email = input("Admin email [texnopharm@gmail.com]: ").strip() or "texnopharm@gmail.com"
    password = input("Admin password: ").strip()
    data = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(f"{API_BASE}/api/auth/login", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read())["token"]


def export_table(table_name):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.cursor().execute(f"SELECT * FROM {table_name}").fetchall()]
    conn.close()
    return rows


def api_post(path, payload, token):
    data = json.dumps(payload, default=str).encode()
    req = urllib.request.Request(f"{API_BASE}{path}", data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    resp = urllib.request.urlopen(req, timeout=120)
    return json.loads(resp.read())


def sync_all(token):
    # 1. Rules + Linguistic
    rules = export_table("sayqallash_rules")
    for r in rules:
        r.pop("vector", None)  # Remove binary
    annotated = export_table("annotated_words")
    disputed = export_table("disputed_words")
    abbreviations = export_table("abbreviations")

    print(f"\n[1/3] Rules + Linguistic: {len(rules)} rules, {len(annotated)} annotated, {len(disputed)} disputed, {len(abbreviations)} abbrev")
    result = api_post("/api/admin/migrate-import", {
        "rules": rules, "annotated": annotated, "disputed": disputed, "abbreviations": abbreviations
    }, token)
    print(f"  -> {result}")

    # 2. Paragraphs (bulk)
    paragraphs = export_table("paragraphs_dashboard")
    print(f"\n[2/3] Paragraphs: {len(paragraphs)} entries")
    result = api_post("/api/admin/bulk-import-paragraphs", {"entries": paragraphs}, token)
    print(f"  -> {result}")

    # 3. Synonyms (bulk, batched)
    synonyms = export_table("synonyms")
    print(f"\n[3/3] Synonyms: {len(synonyms)} records")
    BATCH = 5000
    total_imported = 0
    for i in range(0, len(synonyms), BATCH):
        batch = synonyms[i:i+BATCH]
        for s in batch:
            s.pop("id", None)
            s.pop("part_of_speech", None)
            s.pop("probability_scale", None)
            s.pop("author", None)
        result = api_post("/api/admin/bulk-import-synonyms", {"synonyms": batch}, token)
        total_imported += result.get("imported", 0)
        print(f"  [{min(i+BATCH, len(synonyms))}/{len(synonyms)}] imported: {total_imported}")

    print(f"\n{'='*50}\n  SYNC COMPLETE!\n  Synonyms: {total_imported}\n{'='*50}")


if __name__ == "__main__":
    print(f"{'='*50}\n  Pharma DB -> Production Sync\n  Local: {DB_PATH}\n  Remote: {API_BASE}\n{'='*50}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for t in ["synonyms", "paragraphs_dashboard", "sayqallash_rules"]:
        c.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"  {t}: {c.fetchone()[0]}")
    conn.close()
    print()
    token = get_admin_token()
    print("[+] Logged in!")
    sync_all(token)
