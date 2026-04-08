"""
Dual-script support: detect Uzbek text script (Cyrillic vs Latin)
and generate the other variant for transparent bilingual matching.

Used by:
  - sayqallash_engine: match text against rules regardless of script
  - import scripts: auto-generate dual variants for new entries
  - admin API: show both variants in UI
"""
import re
from typing import Optional

# Reuse existing transliterate.py
try:
    import transliterate as _tr
    _HAS_LOCAL = True
except Exception:
    _HAS_LOCAL = False

CYR_RANGE = re.compile(r"[\u0400-\u04FF]")
LAT_UZ_SPECIALS = re.compile(r"[a-zA-Z']")


def detect_script(text: str) -> str:
    """Return 'cyr' or 'lat' or 'mixed' or 'unknown' based on character majority."""
    if not text:
        return "unknown"
    cyr_count = len(CYR_RANGE.findall(text))
    lat_count = len(LAT_UZ_SPECIALS.findall(text))
    if cyr_count == 0 and lat_count == 0:
        return "unknown"
    if cyr_count > lat_count * 2:
        return "cyr"
    if lat_count > cyr_count * 2:
        return "lat"
    return "mixed"


def to_latin(text: str) -> Optional[str]:
    """Convert Cyrillic to Latin. Return None on failure."""
    if not text:
        return text
    if not _HAS_LOCAL:
        return None
    try:
        return _tr.to_latin(text)
    except Exception:
        return None


def to_cyrillic(text: str) -> Optional[str]:
    """Convert Latin to Cyrillic. Return None on failure."""
    if not text:
        return text
    if not _HAS_LOCAL:
        return None
    try:
        return _tr.to_cyrillic(text)
    except Exception:
        return None


def both_variants(text: str) -> dict:
    """
    Return {'cyr': ..., 'lat': ..., 'detected': ...} for any input.
    If input is Cyrillic, 'lat' is generated.
    If input is Latin, 'cyr' is generated.
    If mixed/unknown, only 'original' is set.
    """
    if not text:
        return {"cyr": "", "lat": "", "detected": "unknown"}
    detected = detect_script(text)
    if detected == "cyr":
        return {"cyr": text, "lat": to_latin(text) or "", "detected": "cyr"}
    elif detected == "lat":
        return {"cyr": to_cyrillic(text) or "", "lat": text, "detected": "lat"}
    else:
        return {"cyr": text, "lat": text, "detected": detected}


def match_both_scripts(needle: str, haystack: str) -> bool:
    """
    Check if needle is in haystack, trying both scripts.
    Example: needle='китоб' (cyr), haystack='kitob yaxshi' (lat) → True
    """
    if not needle or not haystack:
        return False

    if needle in haystack:
        return True

    # Try converting needle to haystack's script
    hay_script = detect_script(haystack)
    needle_script = detect_script(needle)

    if hay_script != needle_script and hay_script in ("cyr", "lat") and needle_script in ("cyr", "lat"):
        if hay_script == "lat":
            converted = to_latin(needle)
        else:
            converted = to_cyrillic(needle)
        if converted and converted in haystack:
            return True

    return False


if __name__ == "__main__":
    tests = [
        "китоб",
        "kitob",
        "Саволлар ва таклифлар",
        "Savollar va takliflar",
        "mixed Английский test",
    ]
    for t in tests:
        print(f"{t!r:35} → {both_variants(t)}")
