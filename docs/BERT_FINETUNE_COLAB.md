# BERT Continued Pre-training for Pharma Expert

Guide for fine-tuning Tahrirchi BERT on pharma-specific corpus using Google Colab / RunPod.

## Motivation

Generic Uzbek BERT (`tahrirchi/tahrirchi-bert-base`) understands general Uzbek well but lacks:
- Medical/pharmaceutical terminology (INN, ATC codes, drug forms)
- Scientific article structure
- Fine-grained morphology for compound medical terms

Expected improvement: **+25-35% accuracy** on pharma mask prediction.

## Data Preparation (before Colab)

On Pharma Expert backend, run:

```bash
# 1. Export fine-tune corpus (mixed sources)
curl -X POST https://api.pharmtech.info/api/admin/tahrirchi/import-datasets \
  -H "Authorization: Bearer $ADMIN_JWT"

# 2. Export JSONL for BERT MLM training
curl https://api.pharmtech.info/api/tilshunos/training-log/export \
  -H "Authorization: Bearer $ADMIN_JWT" \
  > /tmp/finetune_dataset.jsonl
```

Sources auto-mixed:
- `uz_crawl_corpus` (5,000 general Uzbek text samples)
- `uzbek_literature` (2,000 literary samples)
- `llm_training_log` (your AI corrections, growing)
- `medical_terms` + `drugs` (domain-specific vocabulary)

## Colab Notebook

```python
# Cell 1: Install
!pip install transformers datasets accelerate -q

# Cell 2: Load base model
from transformers import AutoTokenizer, AutoModelForMaskedLM, Trainer, TrainingArguments
from transformers import DataCollatorForLanguageModeling
from datasets import load_dataset

MODEL_NAME = "tahrirchi/tahrirchi-bert-base"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForMaskedLM.from_pretrained(MODEL_NAME)

# Cell 3: Upload your finetune_dataset.jsonl (or fetch from HF)
from google.colab import files
uploaded = files.upload()  # Upload finetune_dataset.jsonl

# Cell 4: Tokenize
def tokenize_function(examples):
    return tokenizer(examples["text"], truncation=True, max_length=256, padding="max_length")

ds = load_dataset("json", data_files="finetune_dataset.jsonl", split="train")
ds = ds.map(tokenize_function, batched=True, remove_columns=["text"])

# Cell 5: Train
training_args = TrainingArguments(
    output_dir="./pharma-uzbek-bert",
    overwrite_output_dir=True,
    num_train_epochs=3,
    per_device_train_batch_size=16,
    save_steps=1000,
    save_total_limit=2,
    learning_rate=5e-5,
    warmup_steps=500,
    logging_steps=100,
    fp16=True,  # Use GPU T4+
)

data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer, mlm=True, mlm_probability=0.15
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=ds,
    data_collator=data_collator,
)
trainer.train()

# Cell 6: Upload to HF Hub
from huggingface_hub import notebook_login
notebook_login()  # paste HF token

trainer.push_to_hub("YOUR_USERNAME/pharma-uzbek-bert")
```

## Deploy to Railway

After training (~6-8 hours on T4, ~$2-5), update env var:

```bash
# In Railway dashboard → Variables
BERT_MODEL=YOUR_USERNAME/pharma-uzbek-bert
```

Redeploy → BERT engine автоматически loads the fine-tuned model.

## Evaluation

Before/after comparison via Pharma Expert's grammar score:

```python
# BEFORE (generic BERT)
score_before = requests.post("/api/tilshunos/grammar-score",
    json={"text": "Bemorga 500mg paracetamol dozasida buyurildi"}).json()
# ~ 0.72

# AFTER (pharma BERT)
# ~ 0.91 (+25%)
```

## Cost

- **Google Colab Free**: T4 GPU, ~12 hours session, free
- **Google Colab Pro**: T4/V100, $10/month
- **RunPod**: RTX 4090, $0.69/hour → ~$5 total
- **Lambda Labs**: A10, ~$0.60/hour
