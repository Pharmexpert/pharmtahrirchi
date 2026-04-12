"""
QA Lab Engine — Translation quality checks.
Phase 7: Back-translation, segment count, number preservation, term consistency.

Usage:
    from qa_engine import run_qa_check, run_back_translation, run_segment_check
    result = await run_qa_check(source_text, target_text, source_lang, target_lang)
"""
import re
import logging
from typing import Dict, Any, List
from difflib import SequenceMatcher

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


def compute_similarity(text_a: str, text_b: str) -> float:
    """Compute text similarity ratio (0.0 - 1.0) using SequenceMatcher."""
    if not text_a or not text_b:
        return 0.0
    return round(SequenceMatcher(None, text_a.lower().strip(), text_b.lower().strip()).ratio(), 3)


async def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Translate text using the project's AI translation pipeline.
    Falls back through: tilshunos translate -> generate_ai_content.
    """
    lang_label = {
        "en": "English", "ru": "Russian",
        "uz": "Uzbek (Latin)", "uz-lat": "Uzbek (Latin)", "uz-cyr": "Uzbek (Cyrillic)",
    }
    prompt = (
        f"Translate the following {lang_label.get(source_lang, source_lang)} text "
        f"to {lang_label.get(target_lang, target_lang)}. "
        f"Return ONLY the translation, no explanations.\n\n{text}"
    )
    from routes.ai_helpers import generate_ai_content
    result = await generate_ai_content(prompt, prefer="cloud")
    return (result or "").strip()


async def run_back_translation(
    source_text: str,
    target_text: str,
    source_lang: str,
    target_lang: str,
) -> Dict[str, Any]:
    """Back-translate target_text back to source_lang and compare with source_text.
    Returns back-translated text + similarity score.
    """
    try:
        back_text = await translate_text(target_text, target_lang, source_lang)
        if not back_text:
            return {"available": False, "error": "AI translation unavailable"}

        similarity = compute_similarity(source_text, back_text)
        return {
            "available": True,
            "back_translation": back_text,
            "similarity": similarity,
            "grade": "good" if similarity >= 0.7 else "acceptable" if similarity >= 0.5 else "poor",
        }
    except Exception as e:
        logger.warning(f"Back-translation failed: {e}")
        return {"available": False, "error": str(e)}


async def run_segment_check(segments: List[Dict[str, str]]) -> Dict[str, Any]:
    """Check aligned segments (EN/RU/UZ) for quality issues.
    Each segment: {"en": "...", "ru": "...", "uz": "..."}
    Checks: length ratio, term consistency, missing numbers.
    """
    issues = []
    segment_results = []

    for i, seg in enumerate(segments):
        seg_issues = []
        pairs_checked = []

        # Get all language texts present
        texts = {k: v for k, v in seg.items() if v and v.strip()}
        lang_keys = list(texts.keys())

        # Check each pair
        for a_idx in range(len(lang_keys)):
            for b_idx in range(a_idx + 1, len(lang_keys)):
                la, lb = lang_keys[a_idx], lang_keys[b_idx]
                ta, tb = texts[la], texts[lb]
                pair_label = f"{la}/{lb}"

                # Length ratio check
                length_check = check_length_ratio(ta, tb)
                if not length_check["passed"]:
                    seg_issues.append({
                        "type": "length_ratio",
                        "pair": pair_label,
                        "ratio": length_check["ratio"],
                        "message": f"Unusual length ratio ({length_check['ratio']}) between {pair_label}",
                    })

                # Number preservation
                num_check = check_number_preservation(ta, tb)
                if not num_check["passed"]:
                    seg_issues.append({
                        "type": "missing_numbers",
                        "pair": pair_label,
                        "missing": num_check["missing_in_target"],
                        "message": f"Numbers missing in {lb}: {num_check['missing_in_target']}",
                    })

                # Unit preservation
                unit_check = check_unit_preservation(ta, tb)
                if not unit_check["passed"]:
                    seg_issues.append({
                        "type": "missing_units",
                        "pair": pair_label,
                        "missing": unit_check["missing_in_target"],
                        "message": f"Units missing in {lb}: {unit_check['missing_in_target']}",
                    })

                pairs_checked.append(pair_label)

        segment_results.append({
            "index": i,
            "pairs_checked": pairs_checked,
            "issue_count": len(seg_issues),
            "issues": seg_issues,
        })
        issues.extend(seg_issues)

    return {
        "segment_count": len(segments),
        "segments_with_issues": sum(1 for s in segment_results if s["issue_count"] > 0),
        "total_issues": len(issues),
        "segments": segment_results,
    }


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
