"""
Tilshunos (Linguist) integrated workflow endpoints.

This is the unified text-improvement pipeline that combines all platform tools:
  1. Translation (EN ↔ RU ↔ UZ via AI)
  2. Spell-check (Hunspell + tahrirchi.db)
  3. Morphology (morphology.py)
  4. Grammar checker (grammar_checker.py)
  5. Sayqallash rules (sayqallash_rules)
  6. Pattern-based linguistic rules (uzbek_linguistic_rules)
  7. Self-learning loop (db.learn_from_correction)

User submits 4 text panels (3 languages + outcome) → backend returns
unified analysis with categorized issues, suggestions, and confidence scores.
"""
import logging
import re
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
import db

logger = logging.getLogger("tilshunos_routes")
router = APIRouter(prefix="/api/tilshunos", tags=["tilshunos"])


@router.get("/rules/stats")
async def get_rules_stats(current_user: Dict = Depends(get_current_user)):
    """
    Return total counts of all linguistic rules across the platform.

    Used by dashboard to show: orthography rules, punctuation rules, etc.
    """
    try:
        from uzbek_linguistic_rules import get_rules_summary
        canonical_summary = get_rules_summary()
    except Exception as e:
        canonical_summary = {"error": str(e)}

    # Sayqallash rules from DB
    conn = db.connect_db()
    cur = conn.cursor()
    sayqallash_total = 0
    sayqallash_by_type = {}
    try:
        cur.execute("SELECT error_type, COUNT(*) FROM sayqallash_rules GROUP BY error_type")
        for row in cur.fetchall():
            sayqallash_by_type[row[0] or "unknown"] = row[1]
        sayqallash_total = sum(sayqallash_by_type.values())
    except Exception:
        pass

    # Hunspell stats
    hunspell_stats = {}
    try:
        import os
        HUNSPELL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hunspell")
        for fname, key in [("uz_UZ.dic", "lat_words"), ("uz_UZ_Cyrl.dic", "cyr_words"),
                            ("uz_UZ.aff", "lat_aff"), ("uz_UZ_Cyrl.aff", "cyr_aff")]:
            path = os.path.join(HUNSPELL_DIR, fname)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                if fname.endswith(".dic"):
                    hunspell_stats[key] = len([l for l in content.split("\n") if l.strip() and not l.strip().isdigit()])
                else:
                    hunspell_stats[key + "_sfx"] = content.count("SFX ")
                    hunspell_stats[key + "_pfx"] = content.count("PFX ")
                    hunspell_stats[key + "_rep"] = content.count("REP ")
    except Exception:
        pass

    # Tahrirchi lexicon
    tahrirchi_words = 0
    try:
        import sqlite3
        if hasattr(db, "TAHRIRCHI_DB_PATH"):
            import os as _os
            if _os.path.exists(db.TAHRIRCHI_DB_PATH):
                tc = sqlite3.connect(db.TAHRIRCHI_DB_PATH)
                tahrirchi_words = tc.execute("SELECT COUNT(*) FROM dictionary").fetchone()[0]
                tc.close()
    except Exception:
        pass

    # Counts from other tables
    counts = {}
    for table in ("synonyms", "annotated_words", "disputed_words", "abbreviations", "alignments"):
        try:
            counts[table] = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:
            counts[table] = 0
    conn.close()

    return {
        "canonical_rules": canonical_summary,
        "sayqallash_total": sayqallash_total,
        "sayqallash_by_type": sayqallash_by_type,
        "hunspell": hunspell_stats,
        "tahrirchi_lexicon_words": tahrirchi_words,
        "platform_databases": counts,
    }


@router.post("/check")
async def comprehensive_check(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """
    Comprehensive text check across all 5 dimensions.

    Request:
        {
            "text": "...",
            "lang": "uz" | "ru" | "en",
            "categories": ["orthography", "punctuation", "syntax", "morphology", "grammar"]
                          (optional, defaults to all)
        }

    Response:
        {
            "text": "...",
            "lang": "uz",
            "issues": [
                {
                    "category": "orthography|punctuation|syntax|morphology|grammar",
                    "subcategory": "...",
                    "rule_id": "ORTH-001" | "GRAM-005" | "RULE_DB:1234" | "MORPH",
                    "error_type": "S/Apostrophe",
                    "from_index": N, "to_index": M,
                    "matched_text": "...",
                    "suggestion": "...",
                    "message": "...",
                    "severity": "low|medium|high",
                    "source": "pattern|sayqallash|morphology|grammar_checker"
                }
            ],
            "by_category": { "orthography": N, ... },
            "by_severity": { "high": X, "medium": Y, "low": Z },
            "total": N,
            "morphology": [...],
            "score": 0.0-1.0  (text quality estimate)
        }
    """
    text = payload.get("text", "").strip()
    lang = payload.get("lang", "uz")
    requested_categories = payload.get("categories", None)

    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    if len(text) > 50000:
        raise HTTPException(status_code=400, detail="text too long (max 50000)")

    all_issues = []
    # Track which word spans already have issues to avoid duplicates
    seen_spans = set()  # (from_index, to_index)

    # Uzbek-aware tokenizer: include straight apostrophe (') curly (\u2019)
    # and ʻ (\u02bb) and ʼ (\u02bc) as part of words so "o'quvchilaga" stays whole.
    UZ_WORD_RE = r"[\w'\u2019\u02bb\u02bc\u2018]+"

    # ───── 1. Per-word Hunspell spell check (Uzbek) ─────
    if lang == "uz":
        try:
            import spellcheck
            # Detect script by checking any cyrillic character
            is_cyr = any("\u0400" <= ch <= "\u04FF" for ch in text)

            for match in re.finditer(UZ_WORD_RE, text, re.UNICODE):
                word = match.group()
                # Strip surrounding apostrophes (not part of word) but keep inner ones
                word = word.strip("'\u2019\u02bb\u02bc\u2018")
                if len(word) < 2:
                    continue
                # Skip digits / mixed
                if any(ch.isdigit() for ch in word):
                    continue

                try:
                    # Uzbek Hunspell dict uses ʻ (\u02bb modifier letter). Users often
                    # type ' (straight) or ' (\u2019 curly). Try ALL apostrophe variants.
                    variants = [word]
                    normalized_straight = word.replace("\u2019", "'").replace("\u02bb", "'").replace("\u02bc", "'").replace("\u2018", "'")
                    normalized_hunspell = word.replace("'", "\u02bb").replace("\u2019", "\u02bb").replace("\u02bc", "\u02bb").replace("\u2018", "\u02bb")
                    if normalized_straight != word:
                        variants.append(normalized_straight)
                    if normalized_hunspell != word:
                        variants.append(normalized_hunspell)

                    ok = any(spellcheck.is_correct(v, is_cyrillic=is_cyr) for v in variants)
                    if ok:
                        continue

                    # Try suggestions from all variants
                    suggestions = []
                    for v in variants:
                        s = spellcheck.suggest(v, is_cyrillic=is_cyr, max_suggestions=5)
                        suggestions.extend(s)
                    # Dedupe while preserving order, convert all to straight apostrophe for UX
                    seen = set()
                    clean_suggestions = []
                    for s in suggestions:
                        s_clean = s.replace("\u02bb", "'").replace("\u2019", "'").replace("\u02bc", "'").replace("\u2018", "'")
                        if s_clean not in seen and s_clean != normalized_straight:
                            seen.add(s_clean)
                            clean_suggestions.append(s_clean)
                    suggestions = clean_suggestions[:5]
                    if not suggestions:
                        continue

                    span = (match.start(), match.end())
                    if span in seen_spans:
                        continue
                    seen_spans.add(span)

                    all_issues.append({
                        "category": "orthography",
                        "subcategory": "spelling",
                        "rule_id": "HUNSPELL",
                        "error_type": "S/Spelling",
                        "from_index": match.start(),
                        "to_index": match.end(),
                        "matched_text": word,
                        "suggestion": suggestions[0] if suggestions else "",
                        "suggestions": suggestions,
                        "message": f"Имло хатоси: '{word}' луғатда топилмади",
                        "severity": "high",
                        "source": "hunspell",
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"[tilshunos] hunspell check failed: {e}")

    # ───── 2. Sayqallash rules (DB-based exact + semantic) ─────
    if lang == "uz" and (not requested_categories or "orthography" in requested_categories or "spelling" in requested_categories):
        try:
            from db import find_corrections
            sayqallash_results = []
            find_corrections(text, lang, sayqallash_results)
            for r in sayqallash_results:
                span = (r.get("from_index", 0), r.get("to_index", 0))
                if span in seen_spans:
                    continue
                seen_spans.add(span)

                all_issues.append({
                    "category": "orthography",
                    "subcategory": "sayqallash_db",
                    "rule_id": f"RULE_DB:{r.get('frequency', 0)}",
                    "error_type": r.get("error_type", "S/Spelling"),
                    "from_index": r.get("from_index", 0),
                    "to_index": r.get("to_index", 0),
                    "matched_text": r.get("old_value", ""),
                    "suggestion": r.get("new_value", ""),
                    "suggestions": [r.get("new_value", "")],
                    "message": f"Sayqallash қоидаси: {r.get('error_type', '')}",
                    "severity": "medium",
                    "source": "sayqallash_db",
                })
        except Exception as e:
            logger.warning(f"[tilshunos] sayqallash check failed: {e}")

    # ───── 3. Sentence-level pattern rules (orthography/punctuation sentence-wide only) ─────
    try:
        from uzbek_linguistic_rules import check_text_against_rules
        # Only sentence-level rules, not single-char patterns that cause false positives
        violations = check_text_against_rules(
            text,
            categories=["punctuation"],  # only punctuation patterns are reliable
            script="both",
        )
        for v in violations:
            span = (v.from_index, v.to_index)
            if span in seen_spans:
                continue
            seen_spans.add(span)
            issue = v.to_dict()
            issue["source"] = "pattern_rules"
            issue["suggestions"] = [v.suggestion] if v.suggestion else []
            all_issues.append(issue)
    except Exception as e:
        logger.warning(f"[tilshunos] pattern rules check failed: {e}")

    # ───── 3. Morphology analysis ─────
    morphology_results = []
    if lang == "uz" and (not requested_categories or "morphology" in requested_categories):
        try:
            import morphology
            analyzer = morphology.get_analyzer()
            for word in re.findall(r"\w+", text, re.UNICODE):
                if len(word) < 2:
                    continue
                analysis = analyzer.analyze(word)
                if analysis:
                    morphology_results.append(analysis.to_dict())
                    if not analysis.valid_order:
                        all_issues.append({
                            "category": "morphology",
                            "subcategory": "slot_order",
                            "rule_id": "MORPH-ORDER",
                            "error_type": "G/Morphology",
                            "from_index": text.find(word),
                            "to_index": text.find(word) + len(word),
                            "matched_text": word,
                            "suggestion": "",
                            "message": " | ".join(analysis.order_issues),
                            "severity": "medium",
                            "source": "morphology",
                        })
        except Exception as e:
            logger.warning(f"[tilshunos] morphology failed: {e}")

    # ───── 4. Grammar checker ─────
    if lang == "uz" and (not requested_categories or "grammar" in requested_categories):
        try:
            import grammar_checker
            checker = grammar_checker.get_checker()
            grammar_issues = checker.check(text, lang=lang)
            for gi in grammar_issues:
                all_issues.append({
                    "category": "grammar",
                    "subcategory": gi.issue_type.split("/")[-1] if "/" in gi.issue_type else gi.issue_type,
                    "rule_id": f"GRAM-CHECKER",
                    "error_type": gi.issue_type,
                    "from_index": gi.from_index,
                    "to_index": gi.to_index,
                    "matched_text": gi.word,
                    "suggestion": ", ".join(gi.suggestions[:3]) if gi.suggestions else "",
                    "message": gi.message,
                    "severity": "high" if gi.confidence > 0.7 else "medium",
                    "source": "grammar_checker",
                })
        except Exception as e:
            logger.warning(f"[tilshunos] grammar check failed: {e}")

    # Aggregate stats
    by_category = {}
    by_severity = {"low": 0, "medium": 0, "high": 0}
    for issue in all_issues:
        cat = issue.get("category", "unknown")
        by_category[cat] = by_category.get(cat, 0) + 1
        sev = issue.get("severity", "medium")
        by_severity[sev] = by_severity.get(sev, 0) + 1

    # Quality score: 1.0 if no issues, decrease with high-severity issues
    word_count = len(text.split())
    if word_count == 0:
        score = 1.0
    else:
        weight = by_severity["high"] * 3 + by_severity["medium"] * 1 + by_severity["low"] * 0.3
        score = max(0.0, 1.0 - (weight / max(1, word_count)))

    return {
        "text": text,
        "lang": lang,
        "issues": all_issues,
        "by_category": by_category,
        "by_severity": by_severity,
        "total": len(all_issues),
        "morphology": morphology_results[:30],  # cap to avoid huge response
        "score": round(score, 3),
        "word_count": word_count,
    }


@router.post("/classify")
async def classify_words(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """
    Classify every word in text by its source category.

    Returns spans with one of:
      - "unknown"    → not in any dict (red error)
      - "annotated"  → in annotated_words table (teal #0891B2)
      - "disputed"   → in disputed_words table (orange #F97316)
      - "abbreviation" → in abbreviations table (indigo #6366F1)
      - "known"      → in Hunspell dict (dark blue #1E40AF)
    """
    text = payload.get("text", "")
    lang = payload.get("lang", "uz")

    if not text:
        return {"spans": [], "counts": {}}

    # Load all "known-in-platform" word sets once
    annotated_set = set()
    disputed_set = set()
    abbr_set = set()
    try:
        conn = db.connect_db()
        cur = conn.cursor()
        for table, target in (("annotated_words", annotated_set),
                              ("disputed_words", disputed_set),
                              ("abbreviations", abbr_set)):
            try:
                cur.execute(f"SELECT * FROM {table}")
                cols = [d[0] for d in cur.description]
                for row in cur.fetchall():
                    row_dict = dict(zip(cols, row))
                    for key in ("uz", "ru", "en", "word", "short_form", "abbreviation"):
                        val = row_dict.get(key)
                        if val and isinstance(val, str):
                            target.add(val.strip().lower())
            except Exception:
                pass
        conn.close()
    except Exception as e:
        logger.warning(f"[classify] db load failed: {e}")

    # Tokenize
    UZ_WORD_RE = r"[\w'\u2019\u02bb\u02bc\u2018]+"
    import spellcheck

    is_cyr = any("\u0400" <= ch <= "\u04FF" for ch in text)
    spans = []
    counts = {"known": 0, "annotated": 0, "disputed": 0, "abbreviation": 0, "unknown": 0}

    for match in re.finditer(UZ_WORD_RE, text, re.UNICODE):
        word_raw = match.group()
        word = word_raw.strip("'\u2019\u02bb\u02bc\u2018")
        if len(word) < 2:
            continue
        if any(ch.isdigit() for ch in word):
            continue
        wl = word.lower()
        category = "unknown"
        if wl in annotated_set:
            category = "annotated"
        elif wl in disputed_set:
            category = "disputed"
        elif wl in abbr_set:
            category = "abbreviation"
        else:
            # Check Hunspell
            variants = [word, word.replace("'", "\u02bb"), word.replace("\u2019", "\u02bb")]
            if any(spellcheck.is_correct(v, is_cyrillic=is_cyr) for v in variants):
                category = "known"
        spans.append({
            "from": match.start(),
            "to": match.end(),
            "word": word_raw,
            "category": category,
        })
        counts[category] = counts.get(category, 0) + 1

    return {"spans": spans, "counts": counts}


@router.post("/improve")
async def improve_text(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """
    Apply auto-fixes for high-confidence issues and return improved text.

    Request: { "text": "...", "lang": "uz", "auto_apply_severity": "high" }
    Response: { "improved_text": "...", "applied_fixes": [...], "remaining_issues": [...] }
    """
    text = payload.get("text", "").strip()
    lang = payload.get("lang", "uz")
    auto_severity = payload.get("auto_apply_severity", "high")

    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    # First check
    check_payload = {"text": text, "lang": lang}
    check_result = await comprehensive_check(check_payload, current_user)

    issues = check_result["issues"]
    severity_threshold = {"low": 0, "medium": 1, "high": 2}
    threshold = severity_threshold.get(auto_severity, 2)

    # Sort by from_index DESC so we replace from end to avoid index shifts
    fixable = [
        i for i in issues
        if i.get("suggestion") and severity_threshold.get(i.get("severity", "medium"), 1) >= threshold
    ]
    fixable.sort(key=lambda x: -x["from_index"])

    improved = text
    applied = []
    for issue in fixable:
        start = issue["from_index"]
        end = issue["to_index"]
        old = issue["matched_text"]
        new = issue["suggestion"]
        if not new or new == old:
            continue
        improved = improved[:start] + new + improved[end:]
        applied.append({
            "from": start, "to": end, "old": old, "new": new,
            "rule_id": issue.get("rule_id"), "category": issue.get("category"),
        })

    return {
        "original_text": text,
        "improved_text": improved,
        "applied_fixes": applied,
        "fix_count": len(applied),
        "remaining_issues": [i for i in issues if i not in fixable],
    }


@router.post("/confirm")
async def confirm_correction(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """
    User confirms a correction → triggers self-learning loop.

    Request: { "wrong": "...", "correct": "...", "context": "...", "category": "...", "lang": "uz" }
    Response: result of db.learn_from_correction
    """
    wrong = payload.get("wrong", "").strip()
    correct = payload.get("correct", "").strip()
    if not wrong or not correct:
        raise HTTPException(status_code=400, detail="wrong and correct are required")

    return db.learn_from_correction(
        wrong=wrong,
        correct=correct,
        user_id=current_user.get("id", ""),
        user_name=current_user.get("name", ""),
        context=payload.get("context", ""),
        error_type=payload.get("category", "S/Spelling"),
        lang=payload.get("lang", "uz"),
        source="tilshunos_confirmed",
    )
