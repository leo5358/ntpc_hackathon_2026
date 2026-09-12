"""Risk-topic classifier for 輿情: CKIP ALBERT-tiny, multi-label, fine-tuned on weakly labelled headlines.

    python -m pipeline.nlp.train

Training labels are the keyword-rule topics from collect.py (weak supervision). Once annotators
have filled rows of data/labels/opinion_gold_todo.csv, the model *and* the rules are scored
against those rows — that is the number to report. Without gold labels only agreement with the
rules on a held-out split is printed, which measures fit to the rules, not accuracy.
CPU training takes a few minutes (measured: ~0.2 s per batch of 16 at 128 tokens).

The base model is GPL-3.0. The fine-tuned weights in models/opinion_topic/ are for local or hosted use
only — never commit or otherwise distribute them (models/ is gitignored). See NOTICE.md.
"""
import csv
import json
import random
import time

import numpy as np
import torch
from sklearn.metrics import f1_score
from transformers import AutoModelForSequenceClassification, BertTokenizerFast

from ..config import OUT_DIR, REPO
from .collect import TOPICS

MODEL_NAME = "ckiplab/albert-tiny-chinese"  # GPL-3.0, 4.1M parameters, ~16 MB saved
MODEL_DIR = REPO / "models" / "opinion_topic"
GOLD = REPO / "data" / "labels" / "opinion_gold_todo.csv"
MAX_LEN, BATCH, EPOCHS, LR, THRESHOLD = 64, 16, 5, 5e-5, 0.5


def multi_hot(topics) -> list[float]:
    return [float(t in topics) for t in TOPICS]


def gold_labels() -> dict[str, list[float]]:
    """id -> multi-hot, for rows an annotator has filled in."""
    if not GOLD.exists():
        return {}
    with open(GOLD, encoding="utf-8") as f:
        return {r["id"]: multi_hot(r["topic"].split("|")) for r in csv.DictReader(f) if r["topic"].strip()}


@torch.no_grad()
def predict(model, encoded) -> np.ndarray:
    model.eval()
    probs = []
    for start in range(0, len(encoded["input_ids"]), 64):
        batch = {k: v[start:start + 64] for k, v in encoded.items()}
        probs.append(torch.sigmoid(model(**batch).logits).numpy())
    return np.concatenate(probs)


def main():
    random.seed(0)
    torch.manual_seed(0)
    docs = [json.loads(line) for line in open(OUT_DIR / "opinion_docs.jsonl", encoding="utf-8")]
    gold = gold_labels()
    y = np.array([multi_hot(d["weak_topics"]) for d in docs], dtype=np.float32)

    # Gold-labelled documents are held out entirely so the score is never on training data.
    pool = [i for i, d in enumerate(docs) if d["id"] not in gold]
    random.shuffle(pool)
    cut = int(0.9 * len(pool))
    train_idx, val_idx = pool[:cut], pool[cut:]

    tokenizer = BertTokenizerFast.from_pretrained("bert-base-chinese")  # CKIP models share this tokenizer
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=len(TOPICS), problem_type="multi_label_classification")
    encoded = tokenizer([d["title"] for d in docs], padding="max_length", truncation=True,
                        max_length=MAX_LEN, return_tensors="pt")
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR)

    started = time.perf_counter()
    for epoch in range(EPOCHS):
        model.train()
        random.shuffle(train_idx)
        for start in range(0, len(train_idx), BATCH):
            ids = train_idx[start:start + BATCH]
            loss = model(input_ids=encoded["input_ids"][ids], attention_mask=encoded["attention_mask"][ids],
                         labels=torch.tensor(y[ids])).loss
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
    minutes = (time.perf_counter() - started) / 60

    probs = predict(model, encoded)
    pred = (probs >= THRESHOLD).astype(int)
    metrics = dict(model=MODEL_NAME, train_docs=len(train_idx), train_minutes=round(minutes, 2),
                   rule_agreement_micro_f1=round(f1_score(y[val_idx], pred[val_idx], average="micro", zero_division=0), 3))
    if gold:
        gi = [i for i, d in enumerate(docs) if d["id"] in gold]
        truth = np.array([gold[docs[i]["id"]] for i in gi])
        for name, guess in (("model", pred[gi]), ("rules", y[gi].astype(int))):
            metrics[f"gold_{name}_micro_f1"] = round(f1_score(truth, guess, average="micro", zero_division=0), 3)
            metrics[f"gold_{name}_macro_f1"] = round(f1_score(truth, guess, average="macro", zero_division=0), 3)
        metrics["gold_docs"] = len(gi)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(MODEL_DIR)
    tokenizer.save_pretrained(MODEL_DIR)
    (MODEL_DIR / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(OUT_DIR / "opinion_predictions.jsonl", "w", encoding="utf-8") as f:
        for d, p in zip(docs, probs):
            f.write(json.dumps(dict(id=d["id"], probs=dict(zip(TOPICS, np.round(p, 4).tolist())),
                                    topics=[t for t, v in zip(TOPICS, p) if v >= THRESHOLD]), ensure_ascii=False) + "\n")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
