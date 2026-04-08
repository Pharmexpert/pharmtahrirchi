"""
Syntax mBART Fine-Tune Scaffold.

Requires GPU (Colab Pro / RunPod A100 / Kaggle T4).
Estimated training time: 4-6 hours on A100, ~$3-5 cost.

Usage (on GPU machine):
    pip install transformers datasets accelerate sentencepiece
    python syntax_train_mbart.py --epochs 3 --batch-size 8 --output ./mbart-syntax-uz

Output: fine-tuned mBART-50 model ready for deployment.
"""
import os
import sqlite3
import json
import argparse
import logging

log = logging.getLogger("syntax_train_mbart")

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "pharma_editor.db"))


def export_training_dataset(out_path: str = "/tmp/syntax_train.jsonl",
                            min_quality: float = 0.8) -> int:
    """Export synthetic + UD sentences → JSONL for training."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT source_text, target_text, source_db, quality_score
        FROM translation_memory
        WHERE source_db IN ('syntax_synth', 'ud_uzbek_ud', 'tahrirchi_dilmash')
          AND source_lang = 'uz' AND target_lang = 'uz'
          AND quality_score >= ?
    """, (min_quality,))
    rows = cur.fetchall()
    conn.close()

    written = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for src, tgt, db, score in rows:
            if not src or not tgt:
                continue
            record = {
                "input": f"correct: {src}",
                "output": tgt,
                "source": db,
                "quality": score,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
    log.info(f"Exported {written} examples to {out_path}")
    return written


def train_mbart(data_path: str, output_dir: str, epochs: int = 3,
                batch_size: int = 8, lr: float = 5e-5) -> None:
    """
    Main training loop — runs only if transformers is available (GPU env).
    Safe to import on CPU server (wrapped in try).
    """
    try:
        from transformers import (
            MBart50TokenizerFast,
            MBartForConditionalGeneration,
            Seq2SeqTrainingArguments,
            Seq2SeqTrainer,
            DataCollatorForSeq2Seq,
        )
        from datasets import load_dataset
    except ImportError:
        log.error("transformers/datasets not installed. Install on GPU env:")
        log.error("  pip install transformers datasets accelerate sentencepiece torch")
        return

    model_name = "facebook/mbart-large-50"
    tokenizer = MBart50TokenizerFast.from_pretrained(model_name, src_lang="en_XX", tgt_lang="en_XX")
    model = MBartForConditionalGeneration.from_pretrained(model_name)

    dataset = load_dataset("json", data_files=data_path, split="train")
    dataset = dataset.train_test_split(test_size=0.1)

    def preprocess(examples):
        inputs = tokenizer(examples["input"], max_length=256, truncation=True, padding="max_length")
        with tokenizer.as_target_tokenizer():
            labels = tokenizer(examples["output"], max_length=256, truncation=True, padding="max_length")
        inputs["labels"] = labels["input_ids"]
        return inputs

    tokenized = dataset.map(preprocess, batched=True)

    args = Seq2SeqTrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=lr,
        weight_decay=0.01,
        save_total_limit=2,
        predict_with_generate=True,
        fp16=True,
        logging_steps=50,
        eval_strategy="epoch",
        save_strategy="epoch",
    )

    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    trainer = Seq2SeqTrainer(
        model=model,
        args=args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["test"],
        tokenizer=tokenizer,
        data_collator=data_collator,
    )

    trainer.train()
    trainer.save_model(output_dir)
    log.info(f"Model saved to {output_dir}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-only", action="store_true", help="Export JSONL and exit")
    parser.add_argument("--data", default="/tmp/syntax_train.jsonl")
    parser.add_argument("--output", default="./mbart-syntax-uz")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    n = export_training_dataset(args.data)
    if args.export_only or n == 0:
        print(f"Exported {n} examples. Run with --export-only=false to train.")
    else:
        train_mbart(args.data, args.output, args.epochs, args.batch_size)
