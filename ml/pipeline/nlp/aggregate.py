"""Per-(institution, period) 輿情 features for the main model -> data/processed/opinion_features.csv

Uses the topic model's predictions when opinion_predictions.jsonl exists, otherwise the keyword
rules. Periods match the main model: 學年度 for 非營利園, fiscal (calendar) year for 市立幼兒園.
A document only counts toward the period it was published in, so a row for period t never sees
news from t+1. Periods with no documents are left out; s4_features records them as zero coverage.

    python -m pipeline.nlp.aggregate
"""
import json

import pandas as pd

from ..common.roc import ROC_OFFSET, academic_year
from ..config import OUT_DIR


def main():
    docs = [json.loads(line) for line in open(OUT_DIR / "opinion_docs.jsonl", encoding="utf-8")]
    path = OUT_DIR / "opinion_predictions.jsonl"
    predicted = {}
    if path.exists():
        predicted = {p["id"]: p["topics"] for p in map(json.loads, open(path, encoding="utf-8"))}

    rows = []
    for d in docs:
        if d["kind"] != "institution" or not d.get("inst_id"):
            continue
        date = d["published"].replace("-", "/")
        period = academic_year(date) if d["inst_id"].startswith("N") else int(date[:4]) - ROC_OFFSET
        topics = predicted.get(d["id"], d["weak_topics"])
        rows.append(dict(inst_id=d["inst_id"], period=period, negative=d["weak_polarity"] < 0, risk=bool(topics)))

    features = (pd.DataFrame(rows).groupby(["inst_id", "period"])
                .agg(opinion_docs=("negative", "size"), opinion_neg_share=("negative", "mean"),
                     opinion_risk_docs=("risk", "sum"))
                .reset_index())
    features.to_csv(OUT_DIR / "opinion_features.csv", index=False)
    print(f"opinion_features.csv: {len(features)} (institution, period) rows with coverage, "
          f"{features['inst_id'].nunique()} institutions; source: {'model' if predicted else 'keyword rules'}")


if __name__ == "__main__":
    main()
