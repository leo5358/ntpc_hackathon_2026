"""All-新北 model table -> data/processed/model_table_all.csv, train_all.csv, features_all.json

One row per (kindergarten, calendar year t) for every 新北 園 in the 全國教保資訊網 roster, from its
registration year (2018 at the earliest) to the last complete year. The label is whether the 園 was
penalised in t+1; rows for the last complete year have no label yet and are only scored.

These features need no financial statement, so every 園 gets a row: penalty history up to t plus
roster attributes. Financial and 輿情 features exist only for the 60 公共化園 and showed no signal
(see s5_train on model_table.csv), so they are not joined here.

The roster is a current snapshot, so its attributes describe the 園 today, not at t. `is_active` is
deliberately left out: a 園 that closed after being penalised would leak its future into the past.

    python -m pipeline.s4b_features_all
"""
import datetime
import json

import numpy as np
import pandas as pd

from .config import OUT_DIR
from .s4_features import roster_properties

FIRST_YEAR = 2018
FEATURES = ["prior_penalties", "penalized_this_year", "years_since_penalty", "capacity", "monthly_fee",
            "age", "private", "nonprofit", "after_care", "pre_public"]


def build(today: datetime.date | None = None) -> pd.DataFrame:
    last_complete = (today or datetime.date.today()).year - 1
    penalty_years = pd.read_csv(OUT_DIR / "penalties_all.csv").groupby("title")["calendar_year"].apply(list).to_dict()
    rows = []
    for p in roster_properties():
        reg = pd.to_numeric(p.get("reg_date", "")[:4], errors="coerce")
        reg = reg if reg > 1970 else np.nan  # 1970/01/01 is a placeholder
        years = penalty_years.get(p["title"], [])
        for t in range(FIRST_YEAR if np.isnan(reg) else int(max(reg, FIRST_YEAR)), last_complete + 1):
            prior = [y for y in years if y <= t]
            labelled = t + 1 <= last_complete
            rows.append(dict(
                group=p.get("type"), inst_id=p["title"], inst=p["title"], period=t, label_available=labelled,
                penalized_next=float(t + 1 in years) if labelled else np.nan,
                prior_penalties=len(prior), penalized_this_year=int(t in years),
                years_since_penalty=t - max(prior) if prior else 99,
                capacity=pd.to_numeric(p.get("count_approved"), errors="coerce"),
                monthly_fee=pd.to_numeric(p.get("monthly"), errors="coerce"),
                age=t - reg, private=int(p.get("type") == "私立"), nonprofit=int(p.get("type") == "非營利"),
                after_care=int(p.get("is_after", "") not in ("", "無")),
                pre_public=int(p.get("pre_public", "") not in ("", "無"))))
    return pd.DataFrame(rows)


def main():
    table = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    keys = ["group", "inst_id", "inst", "period", "label_available", "penalized_next"]
    table[keys + FEATURES].to_csv(OUT_DIR / "model_table_all.csv", index=False)
    train = table[table["label_available"]]
    train[["penalized_next"] + FEATURES].to_csv(OUT_DIR / "train_all.csv", header=False, index=False, na_rep="")
    (OUT_DIR / "features_all.json").write_text(json.dumps(
        {"label": "penalized_next", "group_column": "inst_id", "features": FEATURES,
         "note": "roster attributes are a current snapshot; is_active excluded to avoid leakage"},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"model_table_all.csv: {len(table)} rows ({table['inst_id'].nunique()} 園, "
          f"{table['period'].min()}–{table['period'].max()}); labelled {len(train)}, "
          f"positive {int(train['penalized_next'].sum())} ({train['penalized_next'].mean():.1%})")


if __name__ == "__main__":
    main()
