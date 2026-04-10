"""
Build comprehensive Hunspell REP rules from sayqallash_rules DB.
Merges DB-extracted pairs with systematic Uzbek error patterns.
Outputs updated .aff files for both Cyrillic and Latin dictionaries.

Usage:
    python scripts/build_hunspell_rep.py
"""
import os
import sys
import sqlite3
import re

# Paths
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("DB_PATH", os.path.join(BACKEND, "pharma_editor.db"))
HUNSPELL_DIR = os.path.join(BACKEND, "hunspell")

# ═══════════════════════════════════════════════
# 1. Extract from sayqallash_rules DB
# ═══════════════════════════════════════════════
def extract_db_pairs():
    """Extract wrong→correct pairs from sayqallash_rules."""
    pairs = set()
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT wrong_form, correct_form FROM sayqallash_rules WHERE lang='uz' AND wrong_form IS NOT NULL AND correct_form IS NOT NULL")
        for wrong, correct in cur.fetchall():
            w = wrong.strip().lower()
            c = correct.strip().lower()
            if w and c and w != c and ' ' not in w and ' ' not in c and len(w) > 1 and len(c) > 1:
                pairs.add((w, c))
        conn.close()
    except Exception as e:
        print(f"DB error: {e}")
    return pairs


# ═══════════════════════════════════════════════
# 2. Systematic Uzbek error patterns
# ═══════════════════════════════════════════════
def generate_systematic_pairs():
    """Generate systematic ў↔у, қ↔к, ғ↔г, ҳ↔х patterns."""
    pairs = set()

    # ── ў↔у (most common) ──
    u_stems = [
        "бўл", "кўр", "тўл", "йўл", "ўз", "ўр", "ўт", "ўқ", "ўч",
        "ўй", "ўс", "ўн", "ўп", "кўп", "тўп", "сўз", "ўзб", "кўч",
        "бўш", "тўш", "кўш", "йўқ", "ўрг", "ўрн", "ўлч", "ўтк",
        "бўй", "тўй", "ўйл", "ўйн", "кўрс", "тўғр", "ўзг", "бўлг",
        "кўрг", "ўқиш", "ўрг", "сўр", "тўхт", "ўтир", "ўтказ",
    ]
    suffixes = ["", "иш", "ди", "ган", "моқ", "ади", "лар", "нинг",
                "ни", "да", "дан", "га", "лари", "ларни", "ларда",
                "иб", "илди", "илган", "илади", "а", "и", "адиган"]

    for stem in u_stems:
        wrong_stem = stem.replace("ў", "у")
        if wrong_stem == stem:
            continue
        for sfx in suffixes:
            w = wrong_stem + sfx
            c = stem + sfx
            if w != c:
                pairs.add((w, c))

    # ── қ↔к ──
    q_stems = [
        "қил", "қар", "қўш", "қат", "қай", "қўл", "қор", "қол",
        "қоз", "қиз", "қув", "қур", "қўрқ", "қўнг", "қаб", "қаш",
        "қўй", "қўнд", "қўлл", "қара", "қайт", "қўшим", "қидир",
        "қаттиқ", "қисқа", "қимм", "қўрғ", "қабул", "қарш",
    ]
    for stem in q_stems:
        wrong_stem = stem.replace("қ", "к")
        if wrong_stem == stem:
            continue
        for sfx in suffixes[:12]:
            w = wrong_stem + sfx
            c = stem + sfx
            if w != c:
                pairs.add((w, c))

    # ── ғ↔г ──
    gh_stems = [
        "ғал", "ғам", "ғов", "ғоя", "ғир", "ғиш", "ғол", "ғоз",
        "тўғр", "боғ", "соғ", "тоғ", "ёғ", "оғ", "ағ",
    ]
    for stem in gh_stems:
        wrong_stem = stem.replace("ғ", "г")
        if wrong_stem == stem:
            continue
        for sfx in suffixes[:10]:
            w = wrong_stem + sfx
            c = stem + sfx
            if w != c:
                pairs.add((w, c))

    # ── ҳ↔х ──
    h_stems = [
        "ҳол", "ҳам", "ҳар", "ҳат", "ҳил", "ҳуқ", "ҳур", "ҳис",
        "ҳеч", "ҳай", "ҳақ", "ҳос", "ҳимо", "ҳуж", "ҳукум",
        "ҳалқ", "ҳисоб", "ҳозир", "ҳодис", "ҳаракат", "ҳайвон",
    ]
    for stem in h_stems:
        wrong_stem = stem.replace("ҳ", "х")
        if wrong_stem == stem:
            continue
        for sfx in suffixes[:12]:
            w = wrong_stem + sfx
            c = stem + sfx
            if w != c:
                pairs.add((w, c))

    # ── ъ missing ──
    hamza_words = [
        ("тасир", "таъсир"), ("мано", "маъно"), ("талим", "таълим"),
        ("мамурий", "маъмурий"), ("мулумот", "маълумот"), ("масул", "масъул"),
        ("маруза", "маъруза"), ("тариф", "таъриф"), ("мавжуд", "маъвжуд"),
    ]
    for w, c in hamza_words:
        pairs.add((w, c))
        for sfx in ["лар", "нинг", "ни", "да", "дан", "га", "и"]:
            pairs.add((w + sfx, c + sfx))

    return pairs


# ═══════════════════════════════════════════════
# 3. Merge and write
# ═══════════════════════════════════════════════
def merge_and_count(db_pairs, systematic_pairs):
    """Merge all pairs, deduplicate."""
    all_pairs = db_pairs | systematic_pairs
    # Filter out pairs where wrong == correct
    all_pairs = {(w, c) for w, c in all_pairs if w != c and len(w) > 1}
    return all_pairs


def inject_rep_into_aff(aff_path, pairs):
    """Replace REP section in .aff file with new rules."""
    with open(aff_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove old REP section
    lines = content.split('\n')
    new_lines = []
    skip_rep = False
    for line in lines:
        if line.startswith('REP ') and not skip_rep:
            # Check if it's the count line
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                skip_rep = True
                continue
        if skip_rep:
            if line.startswith('REP '):
                continue
            else:
                skip_rep = False
        new_lines.append(line)

    # Insert new REP section after MAP section (or after NOSPLITSUGS)
    insert_idx = 0
    for i, line in enumerate(new_lines):
        if 'NOSPLITSUGS' in line or 'MAP' in line:
            insert_idx = i + 1
            # Skip any MAP lines
            while insert_idx < len(new_lines) and new_lines[insert_idx].startswith('MAP '):
                insert_idx += 1
            break

    rep_lines = [f'REP {len(pairs)}']
    for w, c in sorted(pairs):
        rep_lines.append(f'REP {w} {c}')

    new_lines = new_lines[:insert_idx] + rep_lines + new_lines[insert_idx:]

    with open(aff_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))

    return len(pairs)


def main():
    print("Extracting from DB...")
    db_pairs = extract_db_pairs()
    print(f"  DB pairs: {len(db_pairs)}")

    print("Generating systematic patterns...")
    sys_pairs = generate_systematic_pairs()
    print(f"  Systematic pairs: {len(sys_pairs)}")

    all_pairs = merge_and_count(db_pairs, sys_pairs)
    print(f"  Total unique: {len(all_pairs)}")

    # Cyrillic
    cyrl_aff = os.path.join(HUNSPELL_DIR, "uz_UZ_Cyrl.aff")
    if os.path.exists(cyrl_aff):
        # Filter only Cyrillic pairs
        cyrl_pairs = {(w, c) for w, c in all_pairs if any('\u0400' <= ch <= '\u04FF' for ch in w)}
        n = inject_rep_into_aff(cyrl_aff, cyrl_pairs)
        print(f"  Cyrillic .aff: {n} REP rules")

    # Latin — convert Cyrillic pairs to Latin
    lat_aff = os.path.join(HUNSPELL_DIR, "uz_UZ.aff")
    if os.path.exists(lat_aff):
        try:
            sys.path.insert(0, BACKEND)
            import dual_script
            lat_pairs = set()
            for w, c in all_pairs:
                wl = dual_script.to_latin(w)
                cl = dual_script.to_latin(c)
                if wl and cl and wl != cl:
                    lat_pairs.add((wl.lower(), cl.lower()))
            # Also add original Latin pairs
            lat_only = {(w, c) for w, c in all_pairs if all(ch < '\u0400' or ch > '\u04FF' for ch in w)}
            lat_pairs |= lat_only
            n = inject_rep_into_aff(lat_aff, lat_pairs)
            print(f"  Latin .aff: {n} REP rules")
        except Exception as e:
            print(f"  Latin conversion failed: {e}")

    return {"db": len(db_pairs), "systematic": len(sys_pairs), "total": len(all_pairs)}


if __name__ == "__main__":
    result = main()
    print(f"\nDone: {result}")
