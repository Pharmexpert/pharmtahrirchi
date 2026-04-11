"""
Unified linguistic analysis endpoint.
Runs all 4 layers (Morphology, Sayqallash, Syntax, Style) in one call.

POST /api/analyze/full
  body: { text: string, layers?: string[], lang?: string }
  returns: { morph: [], sayqallash: [], syntax: [], style: [] }
"""
import os
import re
import sqlite3
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException

import db

router = APIRouter(prefix="/api/analyze", tags=["analyze"])

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))


def _detect_script(text: str) -> str:
    """Detect if text is primarily Cyrillic or Latin."""
    cyr = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    lat = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    return "cyr" if cyr >= lat else "lat"


def _ensure_script(value: str, target_script: str) -> str:
    """Convert value to match target script (cyr or lat).
    Ensures suggestions always match input text's script."""
    if not value or not value.strip():
        return value
    val_script = _detect_script(value)
    if val_script == target_script:
        return value
    try:
        import dual_script
        if target_script == "cyr":
            return dual_script.to_cyrillic(value) or value
        else:
            return dual_script.to_latin(value) or value
    except Exception:
        return value


_promt_morph = None
_promt_syntdata = None

def _get_promt_morph():
    """Lazy-load PROMT morph engine (250K roots)."""
    global _promt_morph
    if _promt_morph is not None:
        return _promt_morph
    try:
        import sys
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from promt_morph import PromtMorph
        m = PromtMorph()
        if m.initialize(backend_dir):
            _promt_morph = m
            return m
    except Exception:
        pass
    return None

def _get_syntdata():
    """Lazy-load PROMT SyntData engine (SOV + NER 30 types)."""
    global _promt_syntdata
    if _promt_syntdata is not None:
        return _promt_syntdata
    try:
        import sys
        backend_dir = os.path.dirname(os.path.dirname(__file__))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from promt_syntdata import SyntData
        sd = SyntData()
        morph = _get_promt_morph()
        if morph:
            sd.set_morph(morph)
        _promt_syntdata = sd
        return sd
    except Exception:
        pass
    return None


def _run_morph(text: str) -> list:
    """Morphology layer — PROMT 250K roots + POS/Case/Number analysis.
    Also detects unknown words (potential spelling errors)."""
    results = []
    morph = _get_promt_morph()
    if not morph:
        # Fallback: basic word list
        words = re.findall(r"\w+", text)
        for w in words[:200]:
            if len(w) < 3:
                continue
            results.append({"word": w, "pos": "unknown", "root": w, "layer": "morph"})
        return results[:100]

    # PROMT morph analysis
    text_script = _detect_script(text)
    pattern = r'[а-яёўқғҳА-ЯЁЎҚҒҲ]+' if text_script == "cyr" else r"[a-zA-Z\'ʻʼ]+"
    for match in re.finditer(pattern, text):
        word = match.group()
        if len(word) < 2:
            continue
        try:
            morph.put_key(word)
            root = morph.get_key()
            mods = morph.modifs
            pos = mods.get("pos", "unknown")
            case = mods.get("case", "")
            number = mods.get("number", "")
            person = mods.get("person", "")

            # Affix breakdown (B-4: prefix support)
            suffixes = mods.get("suffixes", [])
            prefix = mods.get("prefix", "")
            affix_desc = ""
            if prefix and root and root != word:
                # e.g. "бе + тартиб" for "бетартиб", or "бе + тартиб + сиз" for "бетартибсиз"
                suffix_part = word[len(prefix) + len(root):] if len(word) > len(prefix) + len(root) else ""
                if suffix_part:
                    affix_desc = f"{prefix} + {root} + {suffix_part}"
                else:
                    affix_desc = f"{prefix} + {root}"
            elif root and root != word and root != word.lower():
                suffix_part = word[len(root):] if word.lower().startswith(root.lower()) else ""
                if suffix_part:
                    affix_desc = f"{root} + {suffix_part}"

            entry = {
                "word": word,
                "root": root,
                "pos": pos.upper() if pos != "unknown" else "UNKNOWN",
                "from": match.start(),
                "to": match.end(),
                "layer": "morph",
            }
            if case and case != "?":
                entry["case"] = case
            if number and number != "?":
                entry["number"] = number
            if person and person != "?":
                entry["person"] = person
            if affix_desc:
                entry["affix"] = affix_desc
            if suffixes:
                entry["suffixes"] = suffixes
            if prefix:
                entry["prefix"] = prefix

            # B-10: word_id from morph engine
            try:
                wid = morph.get_word_id(word)
                if wid >= 0:
                    entry["word_id"] = wid
            except Exception:
                pass

            # Description for tooltip
            parts = []
            if root and root != word:
                parts.append(f"Ўзак: {root}")
            if prefix:
                parts.append(f"Префикс: {prefix}")
            parts.append(f"Туркум: {pos}")
            if case and case != "?":
                case_labels = {"nominative": "бош", "genitive": "қаратқич", "dative": "жўналиш", "accusative": "тушум", "locative": "ўрин-пайт", "ablative": "чиқиш"}
                parts.append(f"Келишик: {case_labels.get(case, case)}")
            if number and number != "?":
                parts.append(f"Сон: {'кўплик' if number == 'plural' else 'бирлик'}")
            if affix_desc:
                parts.append(f"Таркиб: {affix_desc}")
            entry["description"] = " | ".join(parts)
            entry["message"] = entry["description"]

            # Flag unknown words
            if pos == "unknown":
                entry["is_unknown"] = True
                entry["message"] = f"'{word}' — луғатда топилмади"
                entry["description"] = entry["message"]
            results.append(entry)
        except Exception:
            results.append({"word": word, "pos": "ERROR", "root": word, "layer": "morph"})

    # B-5: Attach collocation info to morph results
    try:
        collocations = _check_collocations(text)
        if collocations and results:
            results[-1]["collocations"] = collocations
    except Exception:
        pass

    return results[:200]


def _check_collocations(text: str) -> list:
    """B-5: Collocation check — validate bigrams/trigrams against word_frequency_corpus."""
    results = []
    try:
        text_script = _detect_script(text)
        pattern = r'[а-яёўқғҳА-ЯЁЎҚҒҲ]+' if text_script == "cyr" else r"[a-zA-Z\'ʻʼ]+"
        words = [m.group().lower() for m in re.finditer(pattern, text) if len(m.group()) >= 2]
        if len(words) < 2:
            return results

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Check bigrams
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            try:
                cur.execute(
                    "SELECT frequency FROM word_frequency_corpus WHERE word = ? LIMIT 1",
                    (bigram,)
                )
                row = cur.fetchone()
                if row and row[0] and row[0] >= 3:
                    results.append({
                        "collocation": bigram,
                        "type": "bigram",
                        "frequency": row[0],
                        "status": "confirmed",
                    })
            except Exception:
                pass

        # Check trigrams
        for i in range(len(words) - 2):
            trigram = f"{words[i]} {words[i+1]} {words[i+2]}"
            try:
                cur.execute(
                    "SELECT frequency FROM word_frequency_corpus WHERE word = ? LIMIT 1",
                    (trigram,)
                )
                row = cur.fetchone()
                if row and row[0] and row[0] >= 2:
                    results.append({
                        "collocation": trigram,
                        "type": "trigram",
                        "frequency": row[0],
                        "status": "confirmed",
                    })
            except Exception:
                pass

        conn.close()
    except Exception:
        pass
    return results[:50]


def _run_sayqallash(text: str, lang: str) -> list:
    """Sayqallash — multi-source fast spelling check.

    Sources (all instant, no BERT/AI):
      1. Rules DB exact match (8,000+ cached rules) — dual-script auto-convert
      2. Hunspell is_correct via DICTIONARY LOOKUP (not spylls — direct .dic set)
      3. Multiple suggestions per error (Rules DB + Hunspell .dic neighbors)

    Dual-script: Cyrillic rules match Latin text and vice versa.
    """
    import re as _re
    import math as _math

    results = []
    text_script = _detect_script(text)
    text_lower = text.lower()
    covered = set()

    # ═══ Load rules + build indexes ═══
    rules_list = db.rules_cache.get_all(lang)

    # wrong→correct index (for instant lookup by word)
    wrong_to_rules = {}
    correct_set = set()
    for rule in rules_list:
        w = (rule.get('wrong_form') or '').strip().lower()
        c = (rule.get('correct_form') or '').strip().lower()
        if w and c and w != c:
            correct_set.add(c)
            if w not in wrong_to_rules or rule.get('frequency', 0) > wrong_to_rules[w].get('frequency', 0):
                wrong_to_rules[w] = rule

    # Dual-script: also index converted forms
    try:
        import dual_script
        extra = {}
        for w, rule in wrong_to_rules.items():
            # If rule is Cyrillic, add Latin version too (and vice versa)
            w_cyr = any('\u0400' <= ch <= '\u04FF' for ch in w)
            if w_cyr:
                lat = dual_script.to_latin(w)
                if lat and lat.lower() not in wrong_to_rules:
                    extra[lat.lower()] = rule
            else:
                cyr = dual_script.to_cyrillic(w)
                if cyr and cyr.lower() not in wrong_to_rules:
                    extra[cyr.lower()] = rule
        wrong_to_rules.update(extra)
    except Exception:
        pass

    # Pharma whitelist
    try:
        correct_set.update(db._get_pharma_whitelist())
    except Exception:
        pass

    # Syntax DB dictionary (88K words) — these are CORRECT words
    try:
        _conn = sqlite3.connect(DB_PATH)
        _cur = _conn.cursor()
        for tbl_q in [
            "SELECT DISTINCT word FROM dictionary WHERE word IS NOT NULL",
            "SELECT DISTINCT lemma FROM dictionary WHERE lemma IS NOT NULL",
        ]:
            try:
                _cur.execute(tbl_q)
                for row in _cur.fetchall():
                    if row[0] and len(row[0]) > 1:
                        correct_set.add(row[0].strip().lower())
            except Exception:
                pass
        _conn.close()
    except Exception:
        pass

    # ═══ SOURCE 1: Rules DB exact match (instant) ═══
    for wrong_lower, rule in wrong_to_rules.items():
        if wrong_lower in correct_set:
            continue
        idx = 0
        while True:
            pos = text_lower.find(wrong_lower, idx)
            if pos == -1:
                break
            end = pos + len(wrong_lower)
            before_ok = (pos == 0) or not text[pos - 1].isalpha()
            after_ok = (end >= len(text)) or not text[end].isalpha()
            if before_ok and after_ok and (pos, end) not in covered:
                covered.add((pos, end))
                correct = rule.get('correct_form', '')
                # Convert suggestion to match text script
                correct = _ensure_script(correct, text_script)
                freq = rule.get('frequency', 1) or 1
                confidence = min(95, 60 + int(_math.log2(max(freq, 1)) * 5))
                results.append({
                    "from": pos,
                    "to": end,
                    "old": text[pos:end],
                    "new": correct,
                    "error_type": rule.get('error_type', 'S/Spelling'),
                    "confidence": confidence,
                    "source": "rules_db",
                    "layer": "sayqallash",
                    # Multiple suggestions for tooltip
                    "suggestions": [correct],
                })
            idx = end

    # ═══ SOURCE 2: Hunspell spylls lookup (affix-aware, no suggest) ═══
    # Only check words NOT already found by Rules DB
    # spylls lookup() supports affixes (2-3M word forms) — fast (~5ms/word)
    # spylls suggest() is slow (500ms/word) — NOT used here
    try:
        import spellcheck
        spellcheck._load()
        has_spylls = spellcheck._cyrl_dict or spellcheck._lat_dict
        if has_spylls:
            spylls_dict = spellcheck._cyrl_dict if text_script == "cyr" else spellcheck._lat_dict
            if spylls_dict:
                pattern = r'[а-яёўқғҳА-ЯЁЎҚҒҲ]+' if text_script == "cyr" else r"[a-zA-Z\'ʻʼ]+"
                for match in _re.finditer(pattern, text):
                    word = match.group()
                    pos, end = match.start(), match.end()
                    if len(word) < 3 or (word.isupper() and len(word) < 5):
                        continue
                    if (pos, end) in covered:
                        continue
                    wl = word.lower()
                    if wl in correct_set:
                        continue
                    # spylls lookup — supports affixes (96K stems × 22K rules = ~3M forms)
                    if not (spylls_dict.lookup(word) or spylls_dict.lookup(wl)):
                        # Word not in dictionary — get suggestion from Rules DB
                        suggestion = ""
                        if wl in wrong_to_rules:
                            suggestion = wrong_to_rules[wl].get('correct_form', '')
                            suggestion = _ensure_script(suggestion, text_script)
                        if suggestion:
                            covered.add((pos, end))
                            results.append({
                                "from": pos,
                                "to": end,
                                "old": word,
                                "new": suggestion,
                                "error_type": "H/Spelling",
                                "confidence": 65,
                                "source": "hunspell",
                                "layer": "sayqallash",
                                "suggestions": [suggestion],
                            })
    except Exception:
        pass

    # ═══ SORT suggestions by word frequency (most common = first) ═══
    try:
        _conn_f = sqlite3.connect(DB_PATH)
        _cur_f = _conn_f.cursor()
        for r in results:
            sugs = r.get("suggestions", [])
            if len(sugs) > 1:
                freq_map = {}
                for s in sugs:
                    try:
                        _cur_f.execute("SELECT frequency FROM word_frequency_corpus WHERE word=? LIMIT 1", (s.lower(),))
                        row = _cur_f.fetchone()
                        freq_map[s] = row[0] if row else 0
                    except Exception:
                        freq_map[s] = 0
                r["suggestions"] = sorted(sugs, key=lambda s: freq_map.get(s, 0), reverse=True)
                if r["suggestions"]:
                    r["new"] = r["suggestions"][0]  # Best suggestion = most frequent
        _conn_f.close()
    except Exception:
        pass

    return results


def _run_syntax(text: str) -> list:
    """Syntax layer — PROMT SyntData SOV analysis + morph POS roles.
    Uses SyntData for SOV structure, NER entities, EventFrames.
    Analyzes: SOV word order, sentence members (Эга/Кесим/Тўлдирувчи/Аниқловчи/Ҳол).
    Each word gets a syntactic role label shown in purple."""
    results = []
    morph = _get_promt_morph()

    # SyntData full parse (SOV + NER + EventFrame)
    sd = _get_syntdata()
    if sd:
        try:
            pr = sd.parse(text)
            # Add SOV structure info
            if pr.syntax:
                results.append({
                    "type": "sov_structure",
                    "subject": pr.syntax.get("subject"),
                    "predicate": pr.syntax.get("predicate"),
                    "objects": pr.syntax.get("objects", []),
                    "message": f"SOV: Эга={pr.syntax.get('subject', '—')} | Кесим={pr.syntax.get('predicate', '—')} | Тўлдирувчи={', '.join(pr.syntax.get('objects', []))}",
                    "severity": "info",
                    "layer": "syntax",
                })
            # Add NER entities as syntax-layer annotations
            for ent in pr.entities:
                etype = ent.entity_type.replace("entity_", "").upper()
                results.append({
                    "word": ent.text,
                    "from": ent.start,
                    "to": ent.end,
                    "role": f"NER: {etype}",
                    "message": f"{ent.text} — {etype}",
                    "description": f"Объект: {etype} | {ent.text}",
                    "layer": "syntax",
                    "severity": "info",
                    "ner_type": ent.entity_type,
                })
            # Add EventFrames
            for fr in pr.frames:
                results.append({
                    "type": "event_frame",
                    "event": fr.event_type,
                    "agent": fr.agent,
                    "location": fr.location,
                    "message": f"Ҳодиса: {fr.event_type}" + (f" (агент: {fr.agent})" if fr.agent else ""),
                    "severity": "info",
                    "layer": "syntax",
                })
        except Exception:
            pass

    # Split into sentences
    sentences = re.split(r'[.!?;]\s*', text)
    offset = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 3:
            offset += len(sentence) + 2
            continue

        # Analyze each word with PROMT morph
        words_info = []
        text_script = _detect_script(sentence)
        pattern = r'[а-яёўқғҳА-ЯЁЎҚҒҲ]+' if text_script == "cyr" else r"[a-zA-Z\'ʻʼ]+"
        for match in re.finditer(pattern, sentence):
            word = match.group()
            if len(word) < 2:
                continue
            pos = "unknown"
            case_val = ""
            root = word
            if morph:
                try:
                    morph.put_key(word)
                    root = morph.get_key()
                    mods = morph.modifs
                    pos = mods.get("pos", "unknown")
                    case_val = mods.get("case", "")
                except Exception:
                    pass

            # Determine syntactic role
            role = ""
            if pos == "verb":
                role = "КЕСИМ (феъл)"
            elif pos == "noun" and case_val == "nominative":
                role = "ЭГА (от, бош келишик)"
            elif pos == "noun" and case_val == "accusative":
                role = "ТЎЛДИРУВЧИ (тушум к.)"
            elif pos == "noun" and case_val == "dative":
                role = "ТЎЛДИРУВЧИ (жўналиш к.)"
            elif pos == "noun" and case_val == "locative":
                role = "ҲОЛ (ўрин-пайт к.)"
            elif pos == "noun" and case_val == "ablative":
                role = "ҲОЛ (чиқиш к.)"
            elif pos == "noun" and case_val == "genitive":
                role = "АНИҚЛОВЧИ (қаратқич к.)"
            elif pos == "noun":
                role = "ОТ"
            elif pos == "adjective" or pos == "adj":
                role = "АНИҚЛОВЧИ (сифат)"
            elif pos == "adverb":
                role = "ҲОЛ (равиш)"
            elif pos == "pronoun":
                role = "ОЛМОШ"
            elif pos == "postposition":
                role = "КЎМАКЧИ"
            elif pos == "conjunction":
                role = "БОҒЛОВЧИ"
            elif pos == "numeral":
                role = "СОН"
            elif pos == "particle":
                role = "ЮКЛАМА"
            elif pos != "unknown":
                role = pos.upper()

            if role:
                abs_from = offset + match.start()
                abs_to = offset + match.end()
                results.append({
                    "word": word,
                    "root": root,
                    "pos": pos,
                    "role": role,
                    "case": case_val,
                    "from": abs_from,
                    "to": abs_to,
                    "message": f"{word} — {role}",
                    "description": f"Ўзак: {root} | Сўз туркуми: {pos} | Келишик: {case_val or '—'}",
                    "layer": "syntax",
                    "severity": "info",
                })

            words_info.append({"word": word, "pos": pos, "role": role, "case": case_val})

        # Check: does sentence have a predicate (verb)?
        has_verb = any(w["pos"] == "verb" for w in words_info)
        if not has_verb and len(words_info) > 2:
            results.append({
                "type": "missing_predicate",
                "message": "Гапда кесим (феъл) йўқ",
                "sentence": sentence,
                "severity": "warning",
                "layer": "syntax",
            })

        # B-9: Match against syntax_sentence_templates (1,490 patterns)
        try:
            role_sequence = "+".join(
                "S" if "ЭГА" in w.get("role", "") else
                "V" if "КЕСИМ" in w.get("role", "") else
                "O" if "ТЎЛДИРУВЧИ" in w.get("role", "") else
                "Adj" if "АНИҚЛОВЧИ" in w.get("role", "") else
                "Adv" if "ҲОЛ" in w.get("role", "") else
                w.get("pos", "X")[:3].upper()
                for w in words_info if w.get("role")
            )
            if role_sequence:
                tpl_conn = sqlite3.connect(DB_PATH)
                tpl_cur = tpl_conn.cursor()
                tpl_cur.execute(
                    "SELECT template, sentence_type, semantic_type, formula FROM syntax_sentence_templates WHERE template = ? LIMIT 1",
                    (role_sequence,)
                )
                tpl_row = tpl_cur.fetchone()
                if tpl_row:
                    results.append({
                        "type": "template_match",
                        "template": tpl_row[0],
                        "sentence_type": tpl_row[1],
                        "semantic_type": tpl_row[2],
                        "formula": tpl_row[3],
                        "sentence": sentence,
                        "message": f"Шаблон: {tpl_row[0]} ({tpl_row[1]}) — {tpl_row[3] or ''}",
                        "severity": "info",
                        "layer": "syntax",
                    })
                tpl_conn.close()
        except Exception:
            pass

        # B-9: Check word order rules (446 rules)
        try:
            pos_sequence = " ".join(w.get("pos", "unknown").upper() for w in words_info if w.get("pos") != "unknown")
            if pos_sequence:
                wo_conn = sqlite3.connect(DB_PATH)
                wo_cur = wo_conn.cursor()
                wo_cur.execute(
                    "SELECT wrong_order, correct_order, pos_pattern_wrong, pos_pattern_correct, explanation_uz, severity FROM syntax_word_order_rules"
                )
                for wo_row in wo_cur.fetchall():
                    wrong_pat = wo_row[2] or ""
                    if wrong_pat and wrong_pat in pos_sequence:
                        results.append({
                            "type": "word_order_issue",
                            "wrong_order": wo_row[0],
                            "correct_order": wo_row[1],
                            "explanation": wo_row[4],
                            "sentence": sentence,
                            "message": wo_row[4] or f"Сўз тартиби: {wo_row[0]} → {wo_row[1]}",
                            "severity": wo_row[5] or "warning",
                            "layer": "syntax",
                        })
                wo_conn.close()
        except Exception:
            pass

        offset += len(sentence) + 2  # +2 for ". " separator

    return results


def _run_style(text: str) -> list:
    """Style Guide layer — format/pharma standard enforcement.
    Supports dual-script: if text is Cyrillic, also tries Latin-converted patterns."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT rule_id, category, description, pattern, suggestion, severity, examples, source, COALESCE(source_ref,'') as source_ref, COALESCE(source_url,'') as source_url FROM style_rules WHERE pattern IS NOT NULL AND pattern != ''")
        rules = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception:
        return []

    # Detect script for dual-script matching
    try:
        import dual_script
        text_script = dual_script.detect_script(text)
    except Exception:
        text_script = "unknown"

    issues = []
    for rule in rules:
        pattern = rule.get("pattern", "")
        if not pattern:
            continue
        patterns_to_try = [pattern]
        # If text is in different script than pattern, convert pattern
        if text_script in ("cyr", "lat"):
            try:
                import dual_script
                pat_has_cyr = any("\u0400" <= ch <= "\u04FF" for ch in pattern if ch.isalpha())
                pat_has_lat = any("a" <= ch.lower() <= "z" for ch in pattern if ch.isalpha())
                if text_script == "cyr" and pat_has_lat and not pat_has_cyr:
                    converted = dual_script.to_cyrillic(pattern)
                    if converted and converted != pattern:
                        patterns_to_try.append(converted)
                elif text_script == "lat" and pat_has_cyr and not pat_has_lat:
                    converted = dual_script.to_latin(pattern)
                    if converted and converted != pattern:
                        patterns_to_try.append(converted)
            except Exception:
                pass

        for pat in patterns_to_try:
            try:
                for m in re.finditer(pat, text):
                    issues.append({
                        "rule_id": rule["rule_id"],
                        "category": rule["category"],
                        "description": rule["description"],
                        "from": m.start(),
                        "to": m.end(),
                        "old": m.group(0),
                        "suggestion": rule.get("suggestion", ""),
                        "severity": rule.get("severity", "should"),
                        "examples": rule.get("examples", ""),
                        "source": rule.get("source", ""),
                        "source_ref": rule.get("source_ref", ""),
                        "source_url": rule.get("source_url", ""),
                        "layer": "style",
                    })
            except re.error:
                continue

    return issues[:200]


@router.post("/ner")
async def analyze_ner(payload: Dict[str, Any]):
    """Extract named entities from text — uses PROMT SyntData (30 types) + ner_engine (pharma)."""
    text = (payload.get("text") or "").strip()
    if not text:
        return {"entities": [], "total": 0}
    entities = []
    # 1. PROMT SyntData NER (30 entity types: NAME, PROFESSION, POSITION, ORG, ADDRESS...)
    sd = _get_syntdata()
    if sd:
        try:
            pr = sd.parse(text)
            for ent in pr.entities:
                entities.append({
                    "text": ent.text,
                    "type": ent.entity_type,
                    "start": ent.start,
                    "end": ent.end,
                    "source": "promt_syntdata",
                    "attributes": ent.attributes,
                })
        except Exception:
            pass
    # 2. Pharma NER (DRUG, DOSE, CHEMICAL, etc.)
    try:
        import ner_engine
        pharma_ents = ner_engine.extract_entities(text)
        # Merge avoiding duplicates
        covered = {(e["start"], e["end"]) for e in entities}
        for pe in pharma_ents:
            s, e = pe.get("start", 0), pe.get("end", 0)
            if (s, e) not in covered:
                entities.append(pe)
    except Exception:
        pass
    return {"entities": entities, "total": len(entities)}


@router.post("/protect-entities")
async def protect_entities(payload: Dict[str, Any]):
    """Replace named entities with placeholders for safe translation."""
    text = (payload.get("text") or "").strip()
    if not text:
        return {"protected_text": text, "placeholder_map": {}}
    try:
        import ner_engine
        protected, pmap = ner_engine.protect_entities(text)
        return {"protected_text": protected, "placeholder_map": pmap, "entities_count": len(pmap)}
    except Exception as e:
        return {"protected_text": text, "placeholder_map": {}, "error": str(e)}


@router.post("/restore-entities")
async def restore_entities(payload: Dict[str, Any]):
    """Restore placeholders back to original entity text after translation."""
    text = (payload.get("text") or "").strip()
    pmap = payload.get("placeholder_map") or {}
    if not text or not pmap:
        return {"text": text}
    try:
        import ner_engine
        restored = ner_engine.restore_entities(text, pmap)
        return {"text": restored}
    except Exception:
        return {"text": text}


@router.post("/full")
async def analyze_full(payload: Dict[str, Any]):
    """Run all 4 linguistic layers on text."""
    text = (payload.get("text") or "").strip()
    layers = payload.get("layers") or ["morph", "sayqallash", "syntax", "style"]
    lang = payload.get("lang") or "uz"

    if not text:
        return {"morph": [], "sayqallash": [], "syntax": [], "style": [], "total": 0}

    result = {}
    if "morph" in layers:
        result["morph"] = _run_morph(text)
    if "sayqallash" in layers:
        result["sayqallash"] = _run_sayqallash(text, lang)
    if "syntax" in layers:
        result["syntax"] = _run_syntax(text)
    if "style" in layers:
        result["style"] = _run_style(text)

    result["total"] = sum(len(v) for k, v in result.items() if isinstance(v, list))
    result["summary"] = {
        "morph_count": len(result.get("morph", [])),
        "sayqallash_count": len(result.get("sayqallash", [])),
        "syntax_count": len(result.get("syntax", [])),
        "style_count": len(result.get("style", [])),
    }
    return result
