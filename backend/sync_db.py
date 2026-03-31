"""
Database Sync Script — Syncs local SQLite DB with remote (Vercel Postgres) DB.
Supports bidirectional sync: local → remote and remote → local.
Conflict resolution: uses updated_at timestamps to determine the newest data.

Usage:
  python sync_db.py export    — Export local DB to JSON
  python sync_db.py import    — Import JSON data into local DB
  python sync_db.py push      — Push local data to remote API
  python sync_db.py pull      — Pull remote data to local DB
  python sync_db.py sync      — Full bidirectional sync
"""
import sqlite3
import json
import os
import sys
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "pharma_editor.db")
SYNC_DIR = os.path.join(os.path.dirname(__file__), "..", "sync_data")
REMOTE_API = os.environ.get("VERCEL_API_URL", "")


def ensure_sync_dir():
    os.makedirs(SYNC_DIR, exist_ok=True)


def export_table(conn: sqlite3.Connection, table: str) -> List[Dict]:
    """Export all rows from a table as list of dicts."""
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"  [WARN] Cannot export {table}: {e}")
        return []


def export_db():
    """Export entire local DB to JSON files for syncing."""
    ensure_sync_dir()
    conn = sqlite3.connect(DB_PATH)
    
    tables = {
        "users": export_table(conn, "users"),
        "projects": export_table(conn, "projects"),
        "alignments": export_table(conn, "alignments"),
        "sayqallash_rules": export_table(conn, "sayqallash_rules"),
    }
    
    conn.close()
    
    # Write combined export
    export_data = {
        "exported_at": datetime.now().isoformat(),
        "source": "local_sqlite",
        "tables": tables,
        "stats": {table: len(rows) for table, rows in tables.items()}
    }
    
    export_path = os.path.join(SYNC_DIR, "db_export.json")
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"✅ Database exported to {export_path}")
    for table, rows in tables.items():
        print(f"   {table}: {len(rows)} rows")
    
    # Generate checksum
    with open(export_path, "rb") as f:
        checksum = hashlib.md5(f.read()).hexdigest()
    
    meta_path = os.path.join(SYNC_DIR, "sync_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "last_export": datetime.now().isoformat(),
            "checksum": checksum,
            "stats": export_data["stats"]
        }, f, ensure_ascii=False, indent=2)
    
    return export_data


def import_db(json_path: Optional[str] = None):
    """Import JSON data into local SQLite DB (merge, not replace)."""
    if not json_path:
        json_path = os.path.join(SYNC_DIR, "db_export.json")
    
    if not os.path.exists(json_path):
        print(f"❌ File not found: {json_path}")
        return
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    tables = data.get("tables", {})
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Import users (merge by email)
    users = tables.get("users", [])
    imported_users = 0
    for user in users:
        cursor.execute("SELECT id FROM users WHERE email = ?", (user.get("email", ""),))
        if not cursor.fetchone():
            try:
                cursor.execute(
                    "INSERT INTO users (id, email, name, role, status, avatar_url, password_hash, salt, last_login, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (user["id"], user["email"], user.get("name"), user.get("role", "foydalanuvchi"),
                     user.get("status", "pending"), user.get("avatar_url"), user.get("password_hash"),
                     user.get("salt"), user.get("last_login"), user.get("created_at"))
                )
                imported_users += 1
            except Exception as e:
                print(f"  [WARN] User import error: {e}")
    
    # Import projects (merge by id)
    projects = tables.get("projects", [])
    imported_projects = 0
    for proj in projects:
        cursor.execute("SELECT id FROM projects WHERE id = ?", (proj["id"],))
        existing = cursor.fetchone()
        if not existing:
            try:
                cursor.execute(
                    "INSERT INTO projects (id, name, specialist_name, status, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                    (proj["id"], proj.get("name"), proj.get("specialist_name"),
                     proj.get("status", "in_progress"), proj.get("created_at"), proj.get("updated_at"))
                )
                imported_projects += 1
            except Exception as e:
                print(f"  [WARN] Project import error: {e}")
        else:
            # Update if remote is newer
            cursor.execute("SELECT updated_at FROM projects WHERE id = ?", (proj["id"],))
            local_updated = cursor.fetchone()
            if local_updated and local_updated[0] and proj.get("updated_at"):
                if proj["updated_at"] > local_updated[0]:
                    cursor.execute(
                        "UPDATE projects SET name=?, specialist_name=?, status=?, updated_at=? WHERE id=?",
                        (proj.get("name"), proj.get("specialist_name"), proj.get("status"), proj.get("updated_at"), proj["id"])
                    )
                    imported_projects += 1
    
    # Import alignments (merge by text_id + sentence_no)
    alignments = tables.get("alignments", [])
    imported_alignments = 0
    for align in alignments:
        text_id = align.get("text_id", "")
        sentence_no = align.get("sentence_no", 0)
        cursor.execute(
            "SELECT id FROM alignments WHERE text_id = ? AND sentence_no = ?",
            (text_id, sentence_no)
        )
        if not cursor.fetchone():
            try:
                cursor.execute(
                    "INSERT INTO alignments (sentence_no, display_no, row_type, en_text, confirmed_ru_text, confirmed_uz_text, text_id, notes, specialist_name, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (sentence_no, align.get("display_no"), align.get("row_type", "content"),
                     align.get("en_text", ""), align.get("confirmed_ru_text", ""),
                     align.get("confirmed_uz_text", ""), text_id, align.get("notes", ""),
                     align.get("specialist_name", ""), align.get("created_at"))
                )
                imported_alignments += 1
            except Exception as e:
                print(f"  [WARN] Alignment import error: {e}")
    
    # Import sayqallash rules (merge by wrong_form + correct_form + lang)
    rules = tables.get("sayqallash_rules", [])
    imported_rules = 0
    for rule in rules:
        cursor.execute(
            "SELECT id, frequency FROM sayqallash_rules WHERE wrong_form = ? AND correct_form = ? AND lang = ?",
            (rule.get("wrong_form", ""), rule.get("correct_form", ""), rule.get("lang", "uz"))
        )
        existing = cursor.fetchone()
        if not existing:
            try:
                cursor.execute(
                    "INSERT INTO sayqallash_rules (wrong_form, correct_form, error_type, context, lang, frequency, source, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (rule["wrong_form"], rule["correct_form"], rule.get("error_type", "S/Spelling"),
                     rule.get("context", ""), rule.get("lang", "uz"), rule.get("frequency", 1),
                     rule.get("source", "sync"), rule.get("created_at"), rule.get("updated_at"))
                )
                imported_rules += 1
            except Exception as e:
                print(f"  [WARN] Rule import error: {e}")
        else:
            # Merge frequency (take max)
            local_freq = existing[1] or 1
            remote_freq = rule.get("frequency", 1)
            if remote_freq > local_freq:
                cursor.execute(
                    "UPDATE sayqallash_rules SET frequency = ? WHERE id = ?",
                    (remote_freq, existing[0])
                )
                imported_rules += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ Database import complete:")
    print(f"   Users: {imported_users} new")
    print(f"   Projects: {imported_projects} new/updated")
    print(f"   Alignments: {imported_alignments} new")
    print(f"   Rules: {imported_rules} new/updated")


def push_to_remote():
    """Push local DB data to remote Vercel API."""
    if not REMOTE_API:
        print("❌ VERCEL_API_URL not set. Set it in environment or .env file.")
        print("   Example: set VERCEL_API_URL=https://your-app.vercel.app")
        return
    
    import requests
    
    data = export_db()
    
    try:
        resp = requests.post(
            f"{REMOTE_API}/api/sync/push",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        if resp.status_code == 200:
            result = resp.json()
            print(f"✅ Pushed to remote: {result}")
        else:
            print(f"❌ Push failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Push error: {e}")


def pull_from_remote():
    """Pull remote DB data and merge into local."""
    if not REMOTE_API:
        print("❌ VERCEL_API_URL not set.")
        return
    
    import requests
    
    try:
        resp = requests.get(
            f"{REMOTE_API}/api/sync/pull",
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            pull_path = os.path.join(SYNC_DIR, "remote_pull.json")
            ensure_sync_dir()
            with open(pull_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            import_db(pull_path)
            print("✅ Pull and merge complete")
        else:
            print(f"❌ Pull failed: {resp.status_code}")
    except Exception as e:
        print(f"❌ Pull error: {e}")


def full_sync():
    """Full bidirectional sync: push local → remote, pull remote → local."""
    print("🔄 Starting full sync...")
    print("\n📤 Step 1: Export local DB...")
    export_db()
    
    if REMOTE_API:
        print("\n📤 Step 2: Push to remote...")
        push_to_remote()
        print("\n📥 Step 3: Pull from remote...")
        pull_from_remote()
    else:
        print("\n⚠️ VERCEL_API_URL not set — skipping remote sync.")
        print("   Only local export was performed.")
    
    print("\n✅ Sync complete!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python sync_db.py [export|import|push|pull|sync]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "export":
        export_db()
    elif command == "import":
        json_file = sys.argv[2] if len(sys.argv) > 2 else None
        import_db(json_file)
    elif command == "push":
        push_to_remote()
    elif command == "pull":
        pull_from_remote()
    elif command == "sync":
        full_sync()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python sync_db.py [export|import|push|pull|sync]")
