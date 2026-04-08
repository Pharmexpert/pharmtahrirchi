"""
Helper to load Hunspell affix rules from `uzbek_affix_rules` DB table.

Used by morphology.py, bert_engine.py, sayqallash pipeline.
Cached singleton with manual reload on admin trigger.
"""
import os
import sqlite3
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("affix_db_loader")

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))

_cached_rules: Optional[List[Dict[str, Any]]] = None
_cached_by_slot: Optional[Dict[str, List[Dict[str, Any]]]] = None


def load_all_rules(force: bool = False) -> List[Dict[str, Any]]:
    """Load all affix rules from DB (cached)."""
    global _cached_rules
    if _cached_rules is not None and not force:
        return _cached_rules
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM uzbek_affix_rules")
        _cached_rules = [dict(r) for r in cur.fetchall()]
        conn.close()
        logger.info(f"[affix_db] Loaded {len(_cached_rules)} rules")
    except Exception as e:
        logger.warning(f"[affix_db] Load failed: {e}")
        _cached_rules = []
    return _cached_rules


def rules_by_slot(slot: str) -> List[Dict[str, Any]]:
    """Get all rules matching a morpheme slot (e.g. 'plural', 'case', 'possessive')."""
    global _cached_by_slot
    if _cached_by_slot is None:
        _cached_by_slot = {}
        for r in load_all_rules():
            s = r.get("morpheme_slot", "unknown")
            _cached_by_slot.setdefault(s, []).append(r)
    return _cached_by_slot.get(slot, [])


def rules_by_flag(flag: str) -> List[Dict[str, Any]]:
    """Get all rules for a Hunspell flag."""
    return [r for r in load_all_rules() if r.get("flag") == flag]


def available_slots() -> List[str]:
    """List of all morpheme slots in DB."""
    return sorted(set(r.get("morpheme_slot", "unknown") for r in load_all_rules()))


def reload_cache():
    """Force reload on next call."""
    global _cached_rules, _cached_by_slot
    _cached_rules = None
    _cached_by_slot = None


def match_affix(word: str, affix: str, strip: str = "", condition: str = ".") -> bool:
    """Check if a word matches the affix rule's condition."""
    import re as _re
    if strip and not word.endswith(strip):
        return False
    base = word[:-len(strip)] if strip else word
    # Condition is a simplified regex — e.g. "[ai]" means vowel a or i
    try:
        return bool(_re.search(condition + "$", base))
    except _re.error:
        return True  # if regex fails, accept


def apply_affix(word: str, rule: Dict[str, Any]) -> Optional[str]:
    """Apply a single affix rule to a word, return result or None."""
    strip = rule.get("strip", "")
    affix = rule.get("affix", "")
    condition = rule.get("condition", ".")
    if not match_affix(word, affix, strip, condition):
        return None
    base = word[:-len(strip)] if strip else word
    if rule.get("type") == "SFX":
        return base + affix
    elif rule.get("type") == "PFX":
        return affix + word
    return None


def stats() -> Dict[str, Any]:
    """Quick statistics about loaded rules."""
    rules = load_all_rules()
    by_slot: Dict[str, int] = {}
    by_script: Dict[str, int] = {}
    for r in rules:
        s = r.get("morpheme_slot", "unknown")
        sc = r.get("script", "unknown")
        by_slot[s] = by_slot.get(s, 0) + 1
        by_script[sc] = by_script.get(sc, 0) + 1
    return {
        "total": len(rules),
        "by_slot": by_slot,
        "by_script": by_script,
    }
