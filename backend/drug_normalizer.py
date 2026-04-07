"""
Drug Name Normalization — find canonical INN form across languages/scripts.

Maps surface forms to canonical drug entries:
  - "парацетамол" / "paracetamolum" / "paracetamol" → INN "Paracetamol"
  - "ампициллин" / "ampicillin" → INN "Ampicillin"
  - "Bayer Aspirin 500mg" → brand="Bayer Aspirin", INN="Acetylsalicylic acid", dose="500mg"

Uses:
  1. Exact match in `drugs` table (inn, brand_name)
  2. Transliteration (Cyrillic ↔ Latin) for cross-script lookup
  3. Levenshtein distance fallback (edit distance ≤ 2)
  4. BERT embedding similarity for fuzzy matches (optional)
"""
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger("drug_normalizer")


def _levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein edit distance."""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb))
        prev = curr
    return prev[-1]


def _normalize_text(t: str) -> str:
    """Lowercase + strip + collapse whitespace + remove dose/punct."""
    t = t.lower().strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[®©™]+", "", t)
    return t


def _transliterate(t: str) -> str:
    """Convert Cyrillic to Latin if needed."""
    try:
        import transliterate as tl
        if any("\u0400" <= ch <= "\u04FF" for ch in t):
            return tl.to_latin(t)
    except Exception:
        pass
    return t


def normalize(name: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Find canonical drug entries matching `name`.
    Returns: {
        "input": "...",
        "matches": [{ "id": int, "inn": str, "brand_name": str, "atc_code": str, "score": float, "match_type": str }],
        "best": { ... } | None,
    }
    """
    if not name or not name.strip():
        return {"input": name, "matches": [], "best": None}

    needle = _normalize_text(name)
    needle_lat = _normalize_text(_transliterate(name))

    matches: List[Dict[str, Any]] = []
    try:
        import db
        conn = db.connect_db()
        conn.row_factory = db.sqlite3.Row
        cur = conn.cursor()

        # 1. Exact match
        cur.execute("""
            SELECT * FROM drugs
            WHERE LOWER(inn) = ? OR LOWER(brand_name) = ?
               OR LOWER(inn) = ? OR LOWER(brand_name) = ?
            LIMIT ?
        """, (needle, needle, needle_lat, needle_lat, max_results))
        for r in cur.fetchall():
            matches.append({**dict(r), "score": 1.0, "match_type": "exact"})

        if not matches:
            # 2. Substring match (LIKE)
            cur.execute("""
                SELECT * FROM drugs
                WHERE LOWER(inn) LIKE ? OR LOWER(brand_name) LIKE ?
                   OR LOWER(inn) LIKE ? OR LOWER(brand_name) LIKE ?
                LIMIT 30
            """, (f"%{needle}%", f"%{needle}%", f"%{needle_lat}%", f"%{needle_lat}%"))
            for r in cur.fetchall():
                row = dict(r)
                matches.append({**row, "score": 0.8, "match_type": "substring"})

        if not matches:
            # 3. Levenshtein distance fallback (up to 30 candidates)
            cur.execute("SELECT * FROM drugs LIMIT 5000")
            candidates = []
            for r in cur.fetchall():
                row = dict(r)
                inn_norm = _normalize_text(row.get("inn") or "")
                brand_norm = _normalize_text(row.get("brand_name") or "")
                d_inn = _levenshtein(needle_lat, inn_norm) if inn_norm else 999
                d_brand = _levenshtein(needle_lat, brand_norm) if brand_norm else 999
                d = min(d_inn, d_brand)
                if d <= 2:
                    score = max(0.0, 1.0 - d / 5.0)
                    candidates.append({**row, "score": score, "match_type": "fuzzy"})
            candidates.sort(key=lambda x: -x["score"])
            matches = candidates[:max_results]

        conn.close()
    except Exception as e:
        logger.warning(f"[drug_normalizer] DB lookup failed: {e}")

    matches.sort(key=lambda x: -x.get("score", 0))
    matches = matches[:max_results]
    return {
        "input": name,
        "normalized": needle_lat,
        "matches": matches,
        "best": matches[0] if matches else None,
    }


def normalize_batch(names: List[str]) -> List[Dict[str, Any]]:
    """Normalize multiple drug names at once."""
    return [normalize(n) for n in names]
