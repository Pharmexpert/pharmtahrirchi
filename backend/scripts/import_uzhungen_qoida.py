"""
Import u2b3k/uz-hungen .qoida files — human-readable affix rule descriptions.

Source: https://github.com/u2b3k/uz-hungen/tree/master/Affixes
Files:
  - *.qoida files describing affix patterns in a DSL:
      SFX EGALIK
          [ENDSWITH "q" STRIP]
          1SHB = "g'im"
          ...
      END SFX

Strategy:
  1. List .qoida files from the repo via GitHub API
  2. Parse DSL → structured affix rules
  3. Insert into hunspell_affix_descriptions table (new)
  4. Link to existing affix_flags table by flag name (EGALIK, KELISHIK, etc.)
"""
import os
import sqlite3
import urllib.request
import json
import re
import logging

logging.basicConfig(level=logging.INFO, format="[uzhungen] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))

REPO = "u2b3k/uz-hungen"
API = f"https://api.github.com/repos/{REPO}/contents/Affixes"


def fetch_json(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pharma-expert/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        log.warning(f"API fetch failed: {e}")
        return None


def fetch_text(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pharma-expert/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def parse_qoida(text: str, source_file: str = "") -> list:
    """Parse .qoida DSL into list of rule dicts."""
    rules = []
    current_flag = None
    current_condition = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # SFX block start
        m = re.match(r"^SFX\s+(\w+)", line)
        if m:
            current_flag = m.group(1)
            current_condition = None
            continue
        if line.startswith("END SFX"):
            current_flag = None
            current_condition = None
            continue
        # [ENDSWITH "..."] condition
        m = re.match(r"^\[(\w+)\s+(.+)\]", line)
        if m:
            current_condition = f"{m.group(1)} {m.group(2)}"
            continue
        # rule line: NAME = "suffix"
        m = re.match(r'^(\w+)\s*=\s*"([^"]*)"', line)
        if m and current_flag:
            rules.append({
                "flag": current_flag,
                "rule_name": m.group(1),
                "suffix": m.group(2),
                "condition": current_condition or "",
                "source_file": source_file,
            })
    return rules


def ensure_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hunspell_affix_descriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flag TEXT,
            rule_name TEXT,
            suffix TEXT,
            condition TEXT,
            source_file TEXT,
            description_uz TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(flag, rule_name, suffix)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_had_flag ON hunspell_affix_descriptions(flag)")
    conn.commit()
    conn.close()


def import_rules(rules: list) -> int:
    ensure_table()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    inserted = 0
    for r in rules:
        try:
            cur.execute("""
                INSERT OR IGNORE INTO hunspell_affix_descriptions
                (flag, rule_name, suffix, condition, source_file)
                VALUES (?, ?, ?, ?, ?)
            """, (r["flag"], r["rule_name"], r["suffix"], r["condition"], r["source_file"]))
            if cur.rowcount > 0:
                inserted += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return inserted


def main():
    log.info(f"Listing files in {REPO}/Affixes...")
    files = fetch_json(API)
    if not files or not isinstance(files, list):
        log.warning("Could not list directory")
        return {"error": "api failed", "inserted": 0}

    total_rules = 0
    total_inserted = 0
    per_file = {}

    for f in files:
        name = f.get("name", "")
        if not name.endswith(".qoida"):
            continue
        download_url = f.get("download_url")
        if not download_url:
            continue
        text = fetch_text(download_url)
        if not text:
            continue
        rules = parse_qoida(text, source_file=name)
        inserted = import_rules(rules)
        total_rules += len(rules)
        total_inserted += inserted
        per_file[name] = {"parsed": len(rules), "inserted": inserted}
        log.info(f"{name}: parsed={len(rules)} inserted={inserted}")

    return {
        "files_processed": len(per_file),
        "total_rules_parsed": total_rules,
        "total_inserted": total_inserted,
        "per_file": per_file,
    }


if __name__ == "__main__":
    print(main())
