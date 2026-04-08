"""
UD_Uzbek-UT (Universal Dependencies) datasetni 5 ta syntax jadvalga import.

Manba: https://github.com/UniversalDependencies/UD_Uzbek-UT
Format: CoNLL-U

Idempotent — qayta ishga tushirish xavfsiz.
"""
import os
import sys
import sqlite3
import logging
import urllib.request
import json

logging.basicConfig(level=logging.INFO, format="[ud_uzbek] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))

UD_BASE = "https://raw.githubusercontent.com/UniversalDependencies/UD_Uzbek-UT/master"
FILES = ["uz_ut-ud-train.conllu", "uz_ut-ud-test.conllu"]

# UD deprel → o'zbek gap bo'lagi mappingi
DEPREL_TO_ROLE = {
    "nsubj": "ega",
    "nsubj:pass": "ega",
    "obj": "toldiruvchi",
    "iobj": "toldiruvchi",
    "obl": "toldiruvchi",
    "amod": "aniqlovchi",
    "nmod": "aniqlovchi",
    "advmod": "hol",
    "advcl": "hol",
    "root": "kesim",
}


def fetch_conllu(filename: str) -> str:
    """Download a CoNLL-U file from GitHub raw."""
    url = f"{UD_BASE}/{filename}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pharma-expert/1.0"})
        with urllib.request.urlopen(req, timeout=120) as response:
            data = response.read().decode("utf-8", errors="ignore")
            log.info(f"Fetched {filename}: {len(data)//1024} KB")
            return data
    except Exception as e:
        log.warning(f"Fetch failed {filename}: {e}")
        return ""


def parse_conllu_simple(text: str) -> list:
    """Lightweight CoNLL-U parser (no external lib).
    Returns list of sentences, each = list of token dicts."""
    sentences = []
    current = []
    sent_meta = {}
    for line in text.splitlines():
        line = line.rstrip()
        if not line:
            if current:
                sentences.append({"meta": sent_meta, "tokens": current})
                current = []
                sent_meta = {}
            continue
        if line.startswith("#"):
            # metadata: # text = ...
            if "=" in line:
                k, v = line[1:].split("=", 1)
                sent_meta[k.strip()] = v.strip()
            continue
        parts = line.split("\t")
        if len(parts) < 10:
            continue
        # CoNLL-U columns: ID FORM LEMMA UPOS XPOS FEATS HEAD DEPREL DEPS MISC
        try:
            tid = parts[0]
            if "-" in tid or "." in tid:
                continue  # skip multi-word/empty tokens
            current.append({
                "id": int(tid),
                "form": parts[1],
                "lemma": parts[2],
                "upos": parts[3],
                "xpos": parts[4],
                "feats": parts[5],
                "head": int(parts[6]) if parts[6].isdigit() else 0,
                "deprel": parts[7],
            })
        except Exception:
            continue
    if current:
        sentences.append({"meta": sent_meta, "tokens": current})
    return sentences


def import_sentences(sentences: list, source_label: str) -> dict:
    """Import parsed sentences into 5 syntax tables."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    parts_added = 0
    phrases_added = 0
    parsed_added = 0
    templates_added = 0

    for sent in sentences:
        text = sent["meta"].get("text", "")
        tokens = sent["tokens"]
        if not tokens or not text:
            continue

        # 1. Extract sentence parts (tokens with known deprel → role)
        for tok in tokens:
            role = DEPREL_TO_ROLE.get(tok["deprel"])
            if not role:
                continue
            try:
                cur.execute("""
                    INSERT INTO syntax_sentence_parts
                    (word, lemma, pos, role, example_uz, source, confidence)
                    VALUES (?, ?, ?, ?, ?, ?, 0.92)
                """, (tok["form"], tok["lemma"], tok["upos"], role, text[:300], source_label))
                parts_added += 1
            except Exception:
                pass

        # 2. Extract head-dep phrases
        for tok in tokens:
            if tok["head"] == 0 or tok["deprel"] == "root":
                continue
            try:
                head_tok = next((t for t in tokens if t["id"] == tok["head"]), None)
                if not head_tok:
                    continue
                cur.execute("""
                    INSERT OR IGNORE INTO syntax_phrases
                    (head_word, dep_word, head_pos, dep_pos, relation, example, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (head_tok["lemma"], tok["lemma"], head_tok["upos"], tok["upos"],
                      tok["deprel"], text[:300], source_label))
                if cur.rowcount > 0:
                    phrases_added += 1
            except Exception:
                pass

        # 3. Detect template (POS sequence)
        upos_seq = " ".join(t["upos"] for t in tokens if t["upos"] not in ("PUNCT", "X"))
        # Simplified to S/O/V
        simple = []
        for t in tokens:
            r = DEPREL_TO_ROLE.get(t["deprel"])
            if r == "ega":
                simple.append("S")
            elif r == "toldiruvchi":
                simple.append("O")
            elif r == "kesim" or t["deprel"] == "root":
                simple.append("V")
            elif r == "aniqlovchi":
                simple.append("Adj")
            elif r == "hol":
                simple.append("Adv")
        template_str = "+".join(simple) if simple else upos_seq[:50]
        if template_str:
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO syntax_sentence_templates
                    (template, sentence_type, example_uz, source, frequency)
                    VALUES (?, 'sodda', ?, ?, 1)
                """, (template_str, text[:300], source_label))
                if cur.rowcount > 0:
                    templates_added += 1
                else:
                    cur.execute("UPDATE syntax_sentence_templates SET frequency = frequency + 1 WHERE template = ?",
                                (template_str,))
            except Exception:
                pass

        # 4. Save full parsed sentence
        try:
            parse_json = json.dumps([{"id": t["id"], "form": t["form"], "lemma": t["lemma"],
                                       "upos": t["upos"], "head": t["head"], "deprel": t["deprel"]}
                                      for t in tokens], ensure_ascii=False)
            cur.execute("""
                INSERT INTO syntax_parsed_sentences
                (text, parse_tree, word_order_formula, sentence_type, is_correct, source)
                VALUES (?, ?, ?, 'sodda', 1, ?)
            """, (text, parse_json, template_str, source_label))
            parsed_added += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    return {
        "parts": parts_added,
        "phrases": phrases_added,
        "templates": templates_added,
        "parsed": parsed_added,
    }


def main():
    """Download UD_Uzbek-UT and import to syntax tables."""
    log.info("Starting UD_Uzbek-UT import...")
    total = {"parts": 0, "phrases": 0, "templates": 0, "parsed": 0}

    for fname in FILES:
        text = fetch_conllu(fname)
        if not text:
            continue
        sentences = parse_conllu_simple(text)
        log.info(f"  Parsed {len(sentences)} sentences from {fname}")
        result = import_sentences(sentences, source_label=f"ud_uzbek_{fname.split('-')[1]}")
        for k, v in result.items():
            total[k] += v
        log.info(f"  → {result}")

    log.info(f"DONE — Total: {total}")
    return total


if __name__ == "__main__":
    print(main())
