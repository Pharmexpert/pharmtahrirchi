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
    """Generate 30,000+ systematic ў↔у, қ↔к, ғ↔г, ҳ↔х patterns."""
    pairs = set()

    # MASSIVE suffix matrix (120+ variants for 30K+ coverage)
    suffixes = [
        # Base
        "", "а", "и", "иш",
        # Past tense
        "ди", "дим", "динг", "дингиз", "дик", "дилар",
        # Past participle
        "ган", "ганда", "ганлар", "гани", "ганим", "ганинг", "ганмиз",
        # Present/future
        "ади", "аман", "асан", "амиз", "асиз", "адилар",
        "яптим", "япман", "япти", "япсиз", "яптилар",
        "аётган", "аётир", "аётганда", "аётганлар",
        "адиган", "ар", "арди", "армиди",
        # Infinitive/gerund
        "моқ", "моқда", "моқчи", "иш", "ишда", "ишга", "ишдан", "ишни", "ишлар",
        # Negative
        "ма", "масдан", "маган", "масин", "масди", "маяпти",
        "олмас", "олмай", "олмади",
        # Conditional/optative
        "са", "сам", "санг", "сангиз", "сак",
        # Imperative
        "инг", "ингиз", "син", "синлар", "айлик",
        # Case endings (noun)
        "нинг", "ни", "да", "дан", "га",
        "лар", "лари", "ларни", "ларда", "лардан", "ларга", "ларнинг",
        # Possessive
        "им", "инг", "ингиз", "имиз", "и", "си", "лари",
        # Derivational
        "лик", "чи", "чилик", "сиз", "сизлик", "ли", "кор", "дор", "гар",
        "нома", "хона", "зор", "дош", "бон", "парвар",
        # Compound suffixes
        "ишлик", "ишчан", "ишсиз", "ганлик", "гандай", "ганча",
        "ладим", "ладинг", "лади", "лаган", "ланиш", "лашиш",
        "тириш", "тирди", "тирган", "тирмоқ",
        "дириш", "дирди", "дирган", "дирмоқ",
        # Verb + noun combos
        "увчи", "увчилар", "увчилик",
        # More case combos
        "ида", "идан", "ига", "ини", "инда", "индан", "инга",
        "ларида", "ларидан", "ларига",
        # -tion/-ment equivalents
        "иш", "лаш", "таш", "ниш", "миш",
        # Pharma-specific endings
        "ланган", "ланиши", "ланмаган", "ланаётган",
        # Double suffixes
        "ишларни", "ишларда", "ишлардан", "ишларга",
        "ликлар", "ликларни", "ликларда",
        "чиларни", "чиларга", "чилардан",
        "сизларни", "сизларга",
    ]

    # ═══════ ў↔у (MOST COMMON — ~8000 pairs) ═══════
    u_stems = [
        "бўл", "кўр", "тўл", "йўл", "ўз", "ўр", "ўт", "ўқ", "ўч",
        "ўй", "ўс", "ўн", "ўп", "кўп", "тўп", "сўз", "ўзб", "кўч",
        "бўш", "тўш", "кўш", "йўқ", "ўрг", "ўрн", "ўлч", "ўтк",
        "бўй", "тўй", "ўйл", "ўйн", "кўрс", "тўғр", "ўзг", "бўлг",
        "кўрг", "сўр", "тўхт", "ўтир", "ўтказ", "ўқит", "ўрат",
        "ўлтир", "кўтар", "тўлдир", "йўнал", "ўйлаш", "ўйнаш",
        "кўмак", "тўплам", "сўров", "ўртоқ", "ўзлаш", "бўлак",
        "кўрик", "тўғон", "йўриқ", "ўрмон", "ўзан", "бўлим",
        "кўмик", "тўсиқ", "йўлак", "ўрин", "ўсим", "бўлма",
        "кўнгил", "тўкис", "ўчоқ", "ўроқ", "бўғин", "кўзгу",
        "тўш", "ўзар", "кўник", "бўрон", "тўнғич", "ўриш",
        "бўсағ", "кўрпа", "тўрт", "ўн", "бўри", "кўлмак",
        "сўнг", "ўтин", "кўйлак", "бўйин", "тўқим", "ўрдак",
        "кўзойнак", "бўйра", "тўнка", "ўртанча", "бўлмас",
        "кўринар", "тўғрила", "ўзлаштир", "бўшат", "кўчир",
        "тўлиқ", "ўтмиш", "кўрсат", "бўлажак", "тўплан",
        # compound/longer stems
        "ўзгартир", "кўрсатиш", "тўлдириш", "бўлишиш", "ўрнатиш",
        "кўчириш", "тўғрила", "ўзлаштириш", "бўшатиш", "ўқитиш",
        "кўтариш", "тўплаш", "ўйлаш", "ўйнаш", "бўлинмас",
    ]
    for stem in u_stems:
        wrong_stem = stem.replace("ў", "у")
        if wrong_stem == stem:
            continue
        for sfx in suffixes:
            w = wrong_stem + sfx
            c = stem + sfx
            if w != c and len(w) > 2:
                pairs.add((w, c))

    # ═══════ қ↔к (~6000 pairs) ═══════
    q_stems = [
        "қил", "қар", "қўш", "қат", "қай", "қўл", "қор", "қол",
        "қоз", "қиз", "қув", "қур", "қўрқ", "қўнг", "қаб", "қаш",
        "қўй", "қўнд", "қўлл", "қара", "қайт", "қўшим", "қидир",
        "қаттиқ", "қисқа", "қимм", "қўрғ", "қабул", "қарш",
        "қалб", "қанд", "қаноат", "қарз", "қариш", "қатл",
        "қатнаш", "қатор", "қаҳрамон", "қийин", "қилич", "қиммат",
        "қирғоқ", "қисм", "қиш", "қиёс", "қовурға", "қоғоз",
        "қозон", "қолдиқ", "қонун", "қоплаш", "қоришиш", "қора",
        "қориш", "қош", "қочириш", "қўзғатиш", "қўлланма",
        "қўмондон", "қўнғироқ", "қўриқ", "қўрсатиш", "қўшиш",
        "қувват", "қудрат", "қулай", "қулоқ", "қумлоқ", "қур",
        "қурилиш", "қуриш", "қуроқ", "қурол", "қурувчи",
        "қуёш", "қўзи", "қўшни", "қўллаш", "қўлга", "қўйиш",
        "қўриқла", "қўрқинч", "қўрғон", "қўрғоч", "қўш",
        # common words with қ at end
        "тўғриликқа", "ишлатиқ", "боғлиқ", "яқин", "чиқ",
        "тиқ", "йиқ", "миқ", "оқ", "иқ", "ўқ", "уқ",
    ]
    for stem in q_stems:
        wrong_stem = stem.replace("қ", "к")
        if wrong_stem == stem:
            continue
        for sfx in suffixes:
            w = wrong_stem + sfx
            c = stem + sfx
            if w != c and len(w) > 2:
                pairs.add((w, c))

    # ═══════ ғ↔г (~4000 pairs) ═══════
    gh_stems = [
        "ғал", "ғам", "ғов", "ғоя", "ғир", "ғиш", "ғол", "ғоз",
        "тўғр", "боғ", "соғ", "тоғ", "ёғ", "оғ", "ағ",
        "ғалаба", "ғамгин", "ғаним", "ғариб", "ғафлат", "ғайрат",
        "ғизо", "ғилдирак", "ғилоф", "ғишт", "ғов", "ғоят",
        "ғояланиш", "ғуруб", "ғурур", "ғусл", "тўғри",
        "яғни", "бағри", "тағин", "ағдар", "соғлом", "боғла",
        "тоғри", "оғир", "оғиз", "оғриқ", "юғ", "суғор",
        "ғанимат", "ғариблик", "ғашлик", "ғафлатда", "ғайри",
        "ғижжак", "ғилдирак", "ғилофла", "ғозолиш",
        "ғоялар", "ғурурли", "ғуруббоши",
        "чоғ", "боғ", "тоғ", "ёғ", "доғ", "соғ", "зоғ",
        "ағдариш", "сағлом", "бағрикенг", "тағвил",
    ]
    for stem in gh_stems:
        wrong_stem = stem.replace("ғ", "г")
        if wrong_stem == stem:
            continue
        for sfx in suffixes:
            w = wrong_stem + sfx
            c = stem + sfx
            if w != c and len(w) > 2:
                pairs.add((w, c))

    # ═══════ ҳ↔х (~6000 pairs) ═══════
    h_stems = [
        "ҳол", "ҳам", "ҳар", "ҳат", "ҳил", "ҳуқ", "ҳур", "ҳис",
        "ҳеч", "ҳай", "ҳақ", "ҳос", "ҳимо", "ҳуж", "ҳукум",
        "ҳалқ", "ҳисоб", "ҳозир", "ҳодис", "ҳаракат", "ҳайвон",
        "ҳабар", "ҳавас", "ҳаво", "ҳавола", "ҳад", "ҳажм",
        "ҳазил", "ҳайдаш", "ҳайрат", "ҳайрон", "ҳал", "ҳалол",
        "ҳамиша", "ҳамкор", "ҳамон", "ҳамсоя", "ҳамширалик",
        "ҳаммом", "ҳандаса", "ҳарбий", "ҳарф", "ҳасад",
        "ҳашарат", "ҳаёт", "ҳидоят", "ҳижоб", "ҳикмат",
        "ҳикоя", "ҳимоя", "ҳиндча", "ҳисоблаш", "ҳисса",
        "ҳозирги", "ҳокимият", "ҳол", "ҳоли", "ҳосил",
        "ҳосила", "ҳотин", "ҳудуд", "ҳуж", "ҳужайра",
        "ҳужжат", "ҳукм", "ҳукумат", "ҳуқуқ", "ҳур",
        "ҳурмат", "ҳусн", "ҳушёр",
        "маҳ", "таҳ", "саҳ", "наҳ", "баҳ", "даҳ", "раҳ", "ваҳ",
        "маҳсулот", "таҳлил", "саҳифа", "баҳо", "раҳмат",
        "таҳрир", "маҳаллий", "маҳкама", "таҳдид", "баҳром",
    ]
    for stem in h_stems:
        wrong_stem = stem.replace("ҳ", "х")
        if wrong_stem == stem:
            continue
        for sfx in suffixes:
            w = wrong_stem + sfx
            c = stem + sfx
            if w != c and len(w) > 2:
                pairs.add((w, c))

    # ═══════ ъ missing (~2000 pairs) ═══════
    hamza_words = [
        ("тасир", "таъсир"), ("мано", "маъно"), ("талим", "таълим"),
        ("мамурий", "маъмурий"), ("мулумот", "маълумот"), ("масул", "масъул"),
        ("маруза", "маъруза"), ("тариф", "таъриф"),
        ("манавий", "маънавий"), ("маноси", "маъноси"), ("масулият", "масъулият"),
        ("таминлаш", "таъминлаш"), ("тасирланиш", "таъсирланиш"),
        ("тасирчан", "таъсирчан"), ("тасирли", "таъсирли"),
        ("талимот", "таълимот"), ("талимий", "таълимий"),
        ("маърифат", "маърифат"), ("маъқул", "маъқул"),
        ("жамият", "жамият"), ("ваъда", "ваъда"), ("даъво", "даъво"),
        ("қаъла", "қаълаш"), ("саъй", "саъй"), ("шаъм", "шаъм"),
        ("баъзан", "баъзан"), ("баъзи", "баъзи"),
    ]
    for w, c in hamza_words:
        if w != c:
            pairs.add((w, c))
            for sfx in suffixes[:30]:
                ww = w + sfx
                cc = c + sfx
                if ww != cc:
                    pairs.add((ww, cc))

    # ═══════ Common full-word errors (~5000 pairs) ═══════
    common_words = [
        # ў↔у in full words
        ("булмоқ", "бўлмоқ"), ("курмоқ", "кўрмоқ"), ("тугри", "тўғри"),
        ("буйича", "бўйича"), ("курсатиш", "кўрсатиш"), ("булиш", "бўлиш"),
        ("кушимча", "қўшимча"), ("урганиш", "ўрганиш"), ("утказиш", "ўтказиш"),
        ("утириш", "ўтириш"), ("утмиш", "ўтмиш"), ("узгариш", "ўзгариш"),
        ("узлаштириш", "ўзлаштириш"), ("укитиш", "ўқитиш"),
        # ҳ↔х in full words
        ("хамма", "ҳамма"), ("холат", "ҳолат"), ("хукук", "ҳуқуқ"),
        ("хукумат", "ҳукумат"), ("хужжат", "ҳужжат"), ("халк", "ҳалқ"),
        ("харакат", "ҳаракат"), ("хайвон", "ҳайвон"), ("хикоя", "ҳикоя"),
        ("хисоб", "ҳисоб"), ("хизмат", "хизмат"), ("химоя", "ҳимоя"),
        ("ходим", "ҳодим"), ("хозирги", "ҳозирги"),
        # қ↔к in full words
        ("килиш", "қилиш"), ("караш", "қараш"), ("конун", "қонун"),
        ("каттик", "қаттиқ"), ("кийин", "қийин"), ("кимматли", "қимматли"),
        ("курилиш", "қурилиш"), ("кувват", "қувват"), ("кулай", "қулай"),
        # ғ↔г in full words
        ("галаба", "ғалаба"), ("гайрат", "ғайрат"), ("гариб", "ғариб"),
        ("говор", "ғовор"), ("гоят", "ғоят"), ("гишт", "ғишт"),
        # mixed errors
        ("хукукий", "ҳуқуқий"), ("холатлар", "ҳолатлар"),
        ("аниклаш", "аниқлаш"), ("булган", "бўлган"), ("килган", "қилган"),
        ("хаммаси", "ҳаммаси"), ("курган", "кўрган"),
        ("тулдириш", "тўлдириш"), ("узбекистон", "Ўзбекистон"),
    ]
    for w, c in common_words:
        if w != c:
            pairs.add((w, c))
            for sfx in suffixes[:20]:
                ww = w + sfx
                cc = c + sfx
                if ww != cc:
                    pairs.add((ww, cc))

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


MAX_REP_RULES = 30000  # Limit to prevent slow spylls parsing on Railway


def inject_rep_into_aff(aff_path, pairs):
    """Replace REP section in .aff file with new rules (capped at MAX_REP_RULES)."""
    # Prioritize: shorter pairs first (more likely to match), then DB pairs
    sorted_pairs = sorted(pairs, key=lambda p: len(p[0]))[:MAX_REP_RULES]
    pairs = set(sorted_pairs)
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
