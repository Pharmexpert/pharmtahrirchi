"""
QA Lab Engine — Translation quality checks.
Phase 7: Back-translation, segment count, number preservation.

Usage:
    from qa_engine import run_qa_check
    result = await run_qa_check(source_text, target_text, source_lang, target_lang)
"""
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger("qa_engine")

# Number pattern: integers, decimals, percentages
NUMBER_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)?%?\b")

# Unit pattern: common pharma units
UNIT_PATTERN = re.compile(
    r"\b(?:mg|mkg|μg|µg|g|kg|ml|mL|L|IU|ME|МЕ|мг|мкг|г|кг|мл|л)\b",
    re.IGNORECASE,
)


def count_segments(text: str) -> int:
    """Count sentence-level segments."""
    if not text.strip():
        return 0
    # Split by sentence-ending punctuation
    segments = re.split(r"[.!?;]\s+", text.strip())
    return len([s for s in segments if s.strip()])


def extract_numbers(text: str) -> List[str]:
    """Extract all numbers from text."""
    return NUMBER_PATTERN.findall(text)


def extract_units(text: str) -> List[str]:
    """Extract all measurement units from text."""
    return [m.group(0) for m in UNIT_PATTERN.finditer(text)]


def check_number_preservation(source: str, target: str) -> Dict[str, Any]:
    """Check if all numbers from source are preserved in target."""
    src_numbers = extract_numbers(source)
    tgt_numbers = extract_numbers(target)
    src_set = set(src_numbers)
    tgt_set = set(tgt_numbers)
    missing = src_set - tgt_set
    extra = tgt_set - src_set
    return {
        "passed": len(missing) == 0,
        "source_numbers": src_numbers,
        "target_numbers": tgt_numbers,
        "missing_in_target": list(missing),
        "extra_in_target": list(extra),
    }


def check_unit_preservation(source: str, target: str) -> Dict[str, Any]:
    """Check if measurement units are preserved."""
    src_units = extract_units(source)
    tgt_units = extract_units(target)
    # Normalize: mg/мг are equivalent
    normalize = {"мг": "mg", "мкг": "mkg", "г": "g", "кг": "kg", "мл": "ml", "л": "L", "МЕ": "IU", "ME": "IU"}
    src_norm = [normalize.get(u, u.lower()) for u in src_units]
    tgt_norm = [normalize.get(u, u.lower()) for u in tgt_units]
    missing = set(src_norm) - set(tgt_norm)
    return {
        "passed": len(missing) == 0,
        "source_units": src_units,
        "target_units": tgt_units,
        "missing_in_target": list(missing),
    }


def check_segment_count(source: str, target: str) -> Dict[str, Any]:
    """Check if segment counts match (±20% tolerance)."""
    src_count = count_segments(source)
    tgt_count = count_segments(target)
    if src_count == 0:
        return {"passed": True, "source_segments": 0, "target_segments": tgt_count, "ratio": 0}
    ratio = tgt_count / src_count
    passed = 0.8 <= ratio <= 1.2  # ±20% tolerance
    return {
        "passed": passed,
        "source_segments": src_count,
        "target_segments": tgt_count,
        "ratio": round(ratio, 2),
    }


def check_length_ratio(source: str, target: str) -> Dict[str, Any]:
    """Check if text length ratio is reasonable."""
    src_len = len(source.strip())
    tgt_len = len(target.strip())
    if src_len == 0:
        return {"passed": True, "source_chars": 0, "target_chars": tgt_len, "ratio": 0}
    ratio = tgt_len / src_len
    # Translations can vary, but extreme ratios (< 0.3 or > 3.0) are suspicious
    passed = 0.3 <= ratio <= 3.0
    return {
        "passed": passed,
        "source_chars": src_len,
        "target_chars": tgt_len,
        "ratio": round(ratio, 2),
    }


async def run_back_translation(text: str, src_lang: str, tgt_lang: str) -> Dict[str, Any]:
    """Back-translate: src→tgt→src and compare."""
    try:
        from routes.ai_helpers import call_ai
        # Forward: src → tgt (already done, text IS the target)
        # Back: tgt → src
        prompt = f"Translate the following text back to {src_lang}. Only return the translation, no explanations:\n\n{text}"
        back_text = await call_ai(prompt, system="You are a professional pharmaceutical translator.")
        if not back_text:
            return {"available": False, "error": "AI unavailable"}
        return {
            "available": True,
            "back_translation": back_text.strip(),
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


async def run_qa_check(
    source_text: str,
    target_text: str,
    source_lang: str = "en",
    target_lang: str = "uz",
    include_back_translation: bool = False,
) -> Dict[str, Any]:
    """Run all QA checks on a translation pair."""
    checks = {}

    # 1. Number preservation
    checks["numbers"] = check_number_preservation(source_text, target_text)

    # 2. Unit preservation
    checks["units"] = check_unit_preservation(source_text, target_text)

    # 3. Segment count
    checks["segments"] = check_segment_count(source_text, target_text)

    # 4. Length ratio
    checks["length"] = check_length_ratio(source_text, target_text)

    # 5. Back-translation (optional, costs AI tokens)
    if include_back_translation:
        checks["back_translation"] = await run_back_translation(target_text, target_lang, source_lang)

    # Overall score
    passed_checks = sum(1 for c in checks.values() if c.get("passed", False))
    total_checks = sum(1 for c in checks.values() if "passed" in c)
    score = round(passed_checks / max(total_checks, 1) * 100)

    return {
        "checks": checks,
        "score": score,
        "passed": passed_checks,
        "total": total_checks,
        "grade": "A" if score >= 90 else "B" if score >= 70 else "C" if score >= 50 else "D",
    }
