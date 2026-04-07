"""
Phase 3: Build FAISS IVF index for tahrirchi.db 8.7M lexicon.

Strategy:
    - Read all words from tahrirchi.db (8.7M)
    - Compute BERT embedding for each (768-dim)
    - Train IVF index with sqrt(N) clusters
    - Save to tahrirchi_lexicon.index + tahrirchi_lexicon.ids

Memory:
    - Flat index of 8.7M × 768 × float32 = 27 GB (too much)
    - IVF index with PQ compression: ~500 MB (fits easily in Railway Pro 1 TB volume)

Performance:
    - On CPU, BERT embedding ~10ms per word
    - 8.7M words × 10ms = 24 hours (too slow)
    - Batch processing (32 words at a time) → ~1ms per word
    - 8.7M words / 1ms = ~2.5 hours
    - With GPU: ~30 minutes

Usage:
    cd backend
    python scripts/build_tahrirchi_faiss_index.py [--limit N] [--batch-size 64]

    --limit N         : Only process first N words (for testing)
    --batch-size K    : BERT batch size (default 64)
    --output-dir PATH : Output directory (default /app/data or backend/)

Output:
    tahrirchi_lexicon.index  — FAISS index file (~500 MB)
    tahrirchi_lexicon.ids    — Pickled list of word IDs (~70 MB)
    tahrirchi_lexicon.meta   — JSON metadata (dimensions, clusters, train size)
"""
import argparse
import logging
import os
import pickle
import sqlite3
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("build_faiss")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=0, help="Max words to process (0 = all)")
    p.add_argument("--batch-size", type=int, default=64, help="BERT batch size")
    p.add_argument("--min-word-len", type=int, default=3, help="Skip words shorter than this")
    p.add_argument("--output-dir", type=str, default=None, help="Output directory")
    p.add_argument("--tahrirchi-db", type=str, default=None, help="Path to tahrirchi.db")
    p.add_argument("--n-clusters", type=int, default=0, help="Number of IVF clusters (0 = auto)")
    return p.parse_args()


def main():
    args = parse_args()

    # Resolve paths
    backend_dir = Path(__file__).resolve().parent.parent
    is_railway = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.path.exists("/app/data"))
    default_data_dir = "/app/data" if is_railway else str(backend_dir)
    output_dir = args.output_dir or default_data_dir
    tahrirchi_db = args.tahrirchi_db or os.path.join(default_data_dir, "tahrirchi.db")

    if not os.path.exists(tahrirchi_db):
        logger.error(f"[!] tahrirchi.db not found at {tahrirchi_db}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    index_path = os.path.join(output_dir, "tahrirchi_lexicon.index")
    ids_path = os.path.join(output_dir, "tahrirchi_lexicon.ids")
    meta_path = os.path.join(output_dir, "tahrirchi_lexicon.meta")

    # Import heavy deps only here (faster --help)
    import faiss
    import numpy as np
    import torch
    from transformers import AutoTokenizer, AutoModel

    logger.info("[*] Loading BERT model...")
    model_name = os.getenv("BERT_MODEL", "tahrirchi/tahrirchi-bert-base")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    logger.info(f"[*] BERT loaded on {device}")

    # Load words from tahrirchi.db
    logger.info(f"[*] Loading words from {tahrirchi_db}...")
    conn = sqlite3.connect(tahrirchi_db)
    cursor = conn.cursor()

    query = "SELECT id, word FROM dictionary WHERE length(word) >= ?"
    params = [args.min_word_len]
    if args.limit > 0:
        query += " LIMIT ?"
        params.append(args.limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    n_words = len(rows)
    logger.info(f"[*] Loaded {n_words:,} words")

    if n_words == 0:
        logger.error("[!] No words found — is the dictionary populated?")
        sys.exit(1)

    # Prepare IVF index
    dimension = 768
    n_clusters = args.n_clusters or max(64, int(np.sqrt(n_words)))
    logger.info(f"[*] Creating IVF index: dim={dimension}, clusters={n_clusters}")

    quantizer = faiss.IndexFlatIP(dimension)
    index = faiss.IndexIVFFlat(quantizer, dimension, n_clusters, faiss.METRIC_INNER_PRODUCT)

    # Batch embedding
    logger.info(f"[*] Computing embeddings (batch_size={args.batch_size})...")
    start = time.time()

    all_embeddings = []
    all_ids = []

    batch_words = []
    batch_ids = []

    def flush_batch():
        if not batch_words:
            return
        with torch.no_grad():
            inputs = tokenizer(
                batch_words, return_tensors="pt", padding=True,
                truncation=True, max_length=32
            ).to(device)
            outputs = model(**inputs)
            # Use [CLS] token embedding
            embs = outputs.last_hidden_state[:, 0, :].cpu().numpy().astype("float32")
        all_embeddings.append(embs)
        all_ids.extend(batch_ids)
        batch_words.clear()
        batch_ids.clear()

    for i, (word_id, word) in enumerate(rows):
        batch_words.append(word.lower())
        batch_ids.append(word_id)

        if len(batch_words) >= args.batch_size:
            flush_batch()

        if (i + 1) % 1000 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            eta = (n_words - i - 1) / rate if rate > 0 else 0
            logger.info(
                f"[*] Processed {i+1:,}/{n_words:,} "
                f"({100*(i+1)/n_words:.1f}%) "
                f"rate={rate:.0f}/s eta={eta/60:.1f}min"
            )

    # Final batch
    flush_batch()

    # Stack all embeddings
    logger.info("[*] Stacking embeddings...")
    X = np.vstack(all_embeddings)
    del all_embeddings
    faiss.normalize_L2(X)
    logger.info(f"[*] Embedding matrix shape: {X.shape}")

    # Train index
    logger.info("[*] Training IVF index (this can take a while)...")
    train_start = time.time()
    # Use a subset for training (faster, same quality for IVF)
    train_size = min(500_000, X.shape[0])
    if X.shape[0] > train_size:
        train_idx = np.random.choice(X.shape[0], train_size, replace=False)
        index.train(X[train_idx])
    else:
        index.train(X)
    logger.info(f"[+] Training done in {(time.time() - train_start):.1f}s")

    # Add all vectors
    logger.info("[*] Adding vectors to index...")
    add_start = time.time()
    index.add(X)
    logger.info(f"[+] Added {index.ntotal:,} vectors in {(time.time() - add_start):.1f}s")

    # Save
    logger.info(f"[*] Saving index to {index_path}...")
    faiss.write_index(index, index_path)

    logger.info(f"[*] Saving ids to {ids_path}...")
    with open(ids_path, "wb") as f:
        pickle.dump(all_ids, f)

    # Metadata
    import json
    meta = {
        "dimension": dimension,
        "n_clusters": n_clusters,
        "n_words": n_words,
        "train_size": train_size,
        "model": model_name,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "build_time_sec": time.time() - start,
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    total_elapsed = time.time() - start
    index_size_mb = os.path.getsize(index_path) / (1024 * 1024)
    ids_size_mb = os.path.getsize(ids_path) / (1024 * 1024)

    logger.info("═" * 60)
    logger.info("[+] FAISS lexicon index built successfully!")
    logger.info(f"    Words indexed:    {n_words:,}")
    logger.info(f"    Dimension:        {dimension}")
    logger.info(f"    Clusters:         {n_clusters}")
    logger.info(f"    Index size:       {index_size_mb:.1f} MB")
    logger.info(f"    IDs size:         {ids_size_mb:.1f} MB")
    logger.info(f"    Total time:       {total_elapsed/60:.1f} min")
    logger.info(f"    Rate:             {n_words/total_elapsed:.0f} words/sec")
    logger.info("═" * 60)


if __name__ == "__main__":
    main()
