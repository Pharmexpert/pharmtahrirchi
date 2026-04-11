# -*- coding: utf-8 -*-
"""
uzbek_fdi.py
============
Uzbek.fdi (PROMT Expert NMT v23.2) файлидан конвертация қилинган
Python морфология модули.

Имкониятлар:
  - 97,004 та кирилл ўзбекча сўз
  - 77,126 та лотин ўзбекча сўз
  - Морфологик таҳлил (тамир топиш, аффикс ажратиш)
  - Луғатда қидириш

Ишлатиш:
    from uzbek_fdi import analyze, search, in_dictionary
    print(analyze("китоблар"))
    # {'word': 'китоблар', 'root': 'китоб', 'suffixes': ['лар'], ...}
"""

import json
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "uzbek_fdi_data.json"
_data = json.loads(_DATA_FILE.read_text("utf-8"))

ROOTS_CYR: frozenset = frozenset(_data["roots_cyrillic"])
ROOTS_LAT: frozenset = frozenset(_data["roots_latin"])
WORD_ID:   dict      = _data["word_ids"]

# Грамматик суффикслар — узундан қисқага тартибда
SUFFIXES = sorted([
    "ларимиздан","ларингиздан","ларидан","ларимдан","ларингдан",
    "ларимизга","ларингизга","ларига","ларимга","ларингга",
    "ларимизда","ларингизда","ларида","ларимда","ларингда",
    "ларимизни","ларингизни","ларини","ларимни","ларингни",
    "ларимизнинг","ларингизнинг","ларининг",
    "ларимиз","ларингиз","лари","ларим","ларинг",
    "ларни","ларга","ларда","лардан",
    "имиздан","ингиздан","идан","имдан","ингдан",
    "имизга","ингизга","ига","имга","ингга",
    "имизда","ингизда","ида","имда","ингда",
    "имизни","ингизни","ини","имни","ингни",
    "имизнинг","ингизнинг","ининг",
    "нинг","дан","га","да","ни",
    "имиз","ингиз","им","инг","и",
    "лар",
    "ишдан","ишга","ишда","ишни","иш",
    "ликдан","ликка","ликда","ликни","лик",
    "ларча","лаб","дек","ча",
    "даги","дagi","ги",
    "ганда","гани","гач","гунча","ган",
    "яптимиз","яптингиз","яптим","яптинг","япти",
    "моқдаман","моқдасан","моқдамиз","моқда",
    "дилар","дингиз","дим","динг","дик","ди",
    "аман","асан","амиз","асиз","ади","айди",
    "ман","сан","миз","сиз",
    "сизлик","сиз",
], key=len, reverse=True)

PREFIXES = sorted([
    "бе", "но", "ғайри", "ўта", "юқори", "паст",
    "давлат", "миллий", "халқ",
], key=len, reverse=True)


def detect_script(word: str) -> str:
    """Алифбони аниқлаш"""
    for c in word:
        if "\u0400" <= c <= "\u04FF" or c in "ўЎғҒқҚҳҲ":
            return "cyrillic"
    return "latin"


def in_dictionary(word: str) -> bool:
    """Сўз луғатда борми?"""
    return word in ROOTS_CYR or word in ROOTS_LAT


def _strip_suffix(word: str) -> tuple[str, str] | tuple[None, None]:
    """Биtta суффикс ажратиш — энг узундан бошлаб"""
    for suf in SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 2:
            root = word[: -len(suf)]
            if in_dictionary(root):
                return root, suf
    return None, None


def find_root(word: str) -> dict | None:
    """
    Морфологик таҳлил — занжир шаклида.
    Мисол: китобларимдан → китоб + -лар + -им + -дан
    """
    if in_dictionary(word):
        return {"root": word, "chain": [word], "suffixes": []}

    current = word
    suffixes_found = []
    chain = [word]

    for _ in range(5):  # максимум 5 та аффикс
        root, suf = _strip_suffix(current)
        if root:
            suffixes_found.insert(0, suf)
            chain.append(root)
            current = root
            if in_dictionary(root):
                break
        else:
            break

    if in_dictionary(current):
        return {
            "root": current,
            "chain": chain,
            "suffixes": suffixes_found,
        }
    return None


def analyze(word: str) -> dict:
    """
    Тўлиқ морфологик таҳлил.

    Returns:
        dict:
            word      — кириш сўзи
            script    — "cyrillic" | "latin"
            in_dict   — луғатда борми
            id        — PROMT ID (ёки None)
            root      — туб сўз (ёки None)
            suffixes  — аффикслар рўйхати
            chain     — морфема занжири: "китоб + -лар + -им + -дан"
    """
    script = detect_script(word)
    root_info = find_root(word)

    chain_str = word
    if root_info and root_info["suffixes"]:
        parts = [root_info["root"]] + [f"-{s}" for s in root_info["suffixes"]]
        chain_str = " + ".join(parts)

    return {
        "word":     word,
        "script":   script,
        "in_dict":  in_dictionary(word),
        "id":       WORD_ID.get(word.strip("_")),
        "root":     root_info["root"] if root_info else None,
        "suffixes": root_info["suffixes"] if root_info else [],
        "chain":    chain_str,
    }


def batch_analyze(words: list) -> list:
    """Бир вақтда бир нечта сўз таҳлили"""
    return [analyze(w) for w in words]


def search(query: str, limit: int = 20, script: str = "both") -> list:
    """
    Луғатдан қидириш.
    script: "cyrillic" | "latin" | "both"
    """
    q = query.lower()
    results = []
    if script in ("cyrillic", "both"):
        results += [w for w in ROOTS_CYR if q in w.lower()]
    if script in ("latin", "both"):
        results += [w for w in ROOTS_LAT if q in w.lower()]
    return sorted(results)[:limit]


def suggest(word: str, limit: int = 10) -> list:
    """Ўхшаш сўзлар таклифи"""
    pool = ROOTS_CYR if detect_script(word) == "cyrillic" else ROOTS_LAT
    prefix = word[:3] if len(word) >= 3 else word
    return [w for w in pool if w.startswith(prefix) and w != word][:limit]


def stats() -> dict:
    """Луғат статистикаси"""
    return {
        "total": len(ROOTS_CYR) + len(ROOTS_LAT),
        "cyrillic": len(ROOTS_CYR),
        "latin": len(ROOTS_LAT),
        "suffixes": len(SUFFIXES),
        "prefixes": len(PREFIXES),
        "source": "Uzbek.fdi (PROMT Expert NMT v23.2)",
    }


if __name__ == "__main__":
    print("=== uzbek_fdi.py — тест ===\n")

    test_words = [
        "китоб", "китоблар", "китобларимдан",
        "мактаб", "мактабда", "мактабдан",
        "давлат", "давлатнинг",
        "ўзбек", "ўзбекча",
        "ишлайди", "ишламади",
        "toshkent", "davlat", "kitob",
    ]

    for w in test_words:
        r = analyze(w)
        chain = r["chain"]
        print(f"  {w:25s}  {chain}")

    print("\nҚидириш: 'давл'")
    print(" ", search("давл", limit=10))

    print("\nСтатистика:", stats())
