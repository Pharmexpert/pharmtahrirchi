"""
SimRelUz semantic similarity calibration.

Downloads elmurod1202/SimRelUz_semantic_evaluation_dataset from HuggingFace,
compares BERT ensemble similarity scores vs gold labels,
writes optimal threshold to `config_values` table.

Usage:
  python scripts/calibrate_simreluz.py

Output:
  - simreluz_calibration.json in backend/data/
  - threshold written to DB: config_values.synonym_similarity_threshold
"""
import os
import sys
import json
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[simreluz] %(message)s")
log = logging.getLogger()

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))
DATA_DIR = Path(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "simreluz"
))


def ensure_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS config_values (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS simreluz_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word1 TEXT,
            word2 TEXT,
            gold_similarity REAL,
            bert_similarity REAL,
            is_synonym INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def load_dataset():
    """Try to load SimRelUz from HuggingFace."""
    try:
        from datasets import load_dataset
        ds = load_dataset("elmurod1202/SimRelUz_semantic_evaluation_dataset")
        return ds
    except Exception as e:
        log.warning(f"Could not load from HuggingFace: {e}")
        return None


def compute_bert_similarity(w1: str, w2: str) -> float:
    """Use BERT engine to compute similarity."""
    try:
        import bert_engine
        if not bert_engine.engine.initialized:
            return 0.0
        return bert_engine.engine.sentence_similarity(w1, w2)
    except Exception as e:
        log.debug(f"sim fail: {e}")
        return 0.0


def find_optimal_threshold(pairs):
    """Find threshold that maximizes F1 on synonym detection."""
    if not pairs:
        return 0.82  # default
    # Binary: label as synonym if gold_similarity >= 0.7
    ys = [1 if p["gold"] >= 0.7 else 0 for p in pairs]
    bert_scores = [p["bert"] for p in pairs]

    best_f1 = 0
    best_thr = 0.82
    for thr in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.82, 0.85, 0.88, 0.9]:
        tp = fp = fn = 0
        for y, s in zip(ys, bert_scores):
            pred = 1 if s >= thr else 0
            if y == 1 and pred == 1:
                tp += 1
            elif y == 0 and pred == 1:
                fp += 1
            elif y == 1 and pred == 0:
                fn += 1
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        if f1 > best_f1:
            best_f1 = f1
            best_thr = thr
    return best_thr, best_f1


def main():
    ensure_schema()

    ds = load_dataset()
    if ds is None:
        log.error("Dataset not available — BERTbek_BASE_ENABLED=1 and datasets lib required")
        return {"error": "dataset unavailable"}

    # Flatten all splits
    pairs_raw = []
    for split_name in ds.keys():
        for row in ds[split_name]:
            # SimRelUz column names may vary: word1/word2/similarity or w1/w2/score
            w1 = row.get("word1") or row.get("w1") or row.get("Word1")
            w2 = row.get("word2") or row.get("w2") or row.get("Word2")
            gold = row.get("similarity") or row.get("score") or row.get("sim") or 0
            if w1 and w2:
                pairs_raw.append({"w1": w1, "w2": w2, "gold": float(gold)})

    log.info(f"Loaded {len(pairs_raw)} pairs")

    # Compute BERT similarity for each
    computed = []
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for i, p in enumerate(pairs_raw):
        if i % 100 == 0:
            log.info(f"  Processing {i}/{len(pairs_raw)}")
        bert_sim = compute_bert_similarity(p["w1"], p["w2"])
        computed.append({"w1": p["w1"], "w2": p["w2"], "gold": p["gold"], "bert": bert_sim})
        try:
            cur.execute("""
                INSERT INTO simreluz_pairs (word1, word2, gold_similarity, bert_similarity, is_synonym)
                VALUES (?, ?, ?, ?, ?)
            """, (p["w1"], p["w2"], p["gold"], bert_sim, 1 if p["gold"] >= 0.7 else 0))
        except Exception:
            pass
    conn.commit()

    # Find optimal threshold
    best_thr, best_f1 = find_optimal_threshold(computed)

    # Save to config_values
    try:
        cur.execute("""
            INSERT OR REPLACE INTO config_values (key, value, description, updated_at)
            VALUES ('synonym_similarity_threshold', ?, ?, CURRENT_TIMESTAMP)
        """, (str(best_thr), f"Calibrated from SimRelUz dataset, F1={best_f1:.3f}"))
        conn.commit()
    except Exception as e:
        log.warning(f"config save fail: {e}")
    conn.close()

    # Also write JSON summary
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "dataset_size": len(computed),
        "best_threshold": best_thr,
        "best_f1": best_f1,
        "avg_gold": sum(p["gold"] for p in computed) / max(len(computed), 1),
        "avg_bert": sum(p["bert"] for p in computed) / max(len(computed), 1),
    }
    with open(DATA_DIR / "simreluz_calibration.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    log.info(f"Calibration done: threshold={best_thr}, F1={best_f1:.3f}")
    return summary


if __name__ == "__main__":
    print(main())
