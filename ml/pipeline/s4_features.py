"""Main-model table -> data/processed/model_table.csv, train.csv (SageMaker), features.json

One row per (institution, period t). Features use only what is known at the end of t; the label
says whether the institution was penalised during t+1.
    市立幼兒園  period = fiscal (calendar) year, from the 決算書
    非營利園    period = 學年度, from the 財務報告
The two groups come from different documents, so accounts are mapped onto shared concepts and the
key ratios are also expressed as z-scores within (group, period): each institution is compared with
its own peers, never across document types.

    python -m pipeline.s4_features
"""
import datetime
import json
import urllib.request

import numpy as np
import pandas as pd

from .common.roc import ROC_OFFSET
from .common.roster import CITY, nonprofit_core, nonprofit_roster
from .common.vocab import CITY as CITY_VOCAB
from .config import CACHE_DIR, OUT_DIR

# Shared concept -> (市立 決算書 accounts, 非營利 收支餘絀表 accounts); budget and actual are summed.
CONCEPTS = {
    "personnel": (["用人費用"], ["人事費"]),
    "services": (["服務費用"], ["業務費"]),
    "materials": (["材料及用品費"], ["材料費"]),
    "maintenance": (["修理保養及保固費"], ["維護費", "修繕購置費"]),
    "utilities": (["水電費"], []),
    "other": (["其他", "會費", "捐助、補助與獎助", "補貼、獎勵、慰問、照護", "稅捐及規費"],
              ["雜支", "其他支出", "公共事務管理費", "行政管理費"]),
    "expense": (["基金用途"], ["支出合計"]),
    "revenue": (["基金來源"], ["收入合計"]),
    "tuition": (["學雜費收入"], ["教保費收入"]),
}
REVENUE_CONCEPTS = {"revenue", "tuition"}
SPENDING = ["personnel", "services", "materials", "maintenance", "utilities", "other"]
Z_FEATURES = ["exec_personnel", "exec_maintenance", "exec_expense", "share_personnel",
              "share_maintenance", "surplus_ratio", "abs_var_share", "expense_per_child"]
BENFORD = np.log10(1 + 1 / np.arange(1, 10))
CITY_PARENTS = {parent for parent, _ in CITY_VOCAB.values()} | {"基金用途", "學前教育計畫"}


def load_city() -> pd.DataFrame:
    df = pd.read_csv(OUT_DIR / "city_fin.csv", dtype={"inst_id": str})
    df = df.rename(columns={"fiscal_year": "period"}).assign(group="市立")
    df["leaf"] = df["table"].eq("用途") & df["kind"].eq("exp") & ~df["account"].isin(CITY_PARENTS)
    return df[["group", "inst_id", "inst", "period", "table", "account", "budget", "actual", "leaf"]]


def load_nonprofit() -> pd.DataFrame:
    rows = pd.read_csv(OUT_DIR / "nonprofit_fin.csv", dtype={"inst_id": str})
    pages = pd.read_csv(OUT_DIR / "nonprofit_pages.csv", dtype={"inst_id": str})
    # Each 學年度 is printed twice: in its own report and as the comparison column of the next one.
    # Prefer a page whose totals reconcile (OCR read every row), then the report's own year.
    pages["own_year"] = pages["report_year"] == pages["academic_year"]
    pages["reconciled"] = pages["rev_total_ok"] & pages["exp_total_ok"]
    best = (pages.sort_values(["reconciled", "own_year"], ascending=False)
            .drop_duplicates(["inst_id", "academic_year"])[["inst_id", "report_year", "page"]])
    rows = rows.merge(best, on=["inst_id", "report_year", "page"])
    rows = rows[rows["account"].fillna("").ne("")]
    rows = (rows.groupby(["inst_id", "inst", "academic_year", "account", "kind"], as_index=False)[["budget", "actual"]]
            .sum(min_count=1))  # 其他收入 can appear on two lines
    rows = rows.rename(columns={"academic_year": "period"}).assign(group="非營利", table="")
    rows["leaf"] = rows["kind"].eq("exp")
    return rows[["group", "inst_id", "inst", "period", "table", "account", "budget", "actual", "leaf"]]


def digit_forensics(amounts: pd.Series) -> tuple[float, float, int]:
    """(share of round thousands, Benford first-digit MAD, number of line items)."""
    a = amounts[amounts > 0].astype("int64")
    if len(a) < 5:
        return np.nan, np.nan, len(a)
    leading = a.astype(str).str[0].astype(int).to_numpy()
    observed = np.bincount(leading, minlength=10)[1:] / len(a)
    mad = float(np.abs(observed - BENFORD).mean()) if len(a) >= 10 else np.nan
    return float((a % 1000 == 0).mean()), mad, len(a)


def concept_totals(fin: pd.DataFrame, doc: int) -> pd.DataFrame:
    """Budget/actual per concept for every (institution, period). doc: 0 = 決算書, 1 = 財報."""
    records = []
    for (group, inst_id, inst, period), rows in fin.groupby(["group", "inst_id", "inst", "period"]):
        rec = dict(group=group, inst_id=inst_id, inst=inst, period=period)
        for concept, accounts in CONCEPTS.items():
            sel = rows[rows["account"].isin(accounts[doc])]
            if doc == 0:
                sel = sel[sel["table"].eq("來源" if concept in REVENUE_CONCEPTS else "用途")]
            rec[f"{concept}_budget"] = sel["budget"].sum(min_count=1)
            rec[f"{concept}_actual"] = sel["actual"].sum(min_count=1)
        rec["round_share"], rec["benford_mad"], rec["n_line_items"] = digit_forensics(rows.loc[rows["leaf"], "actual"].dropna())
        records.append(rec)
    return pd.DataFrame(records)


def ratio_features(c: pd.DataFrame) -> pd.DataFrame:
    f = c[["group", "inst_id", "inst", "period", "round_share", "benford_mad", "n_line_items"]].copy()
    for k in SPENDING + ["expense"]:
        f[f"exec_{k}"] = c[f"{k}_actual"] / c[f"{k}_budget"].where(c[f"{k}_budget"] > 0)
    for k in SPENDING:
        f[f"share_{k}"] = c[f"{k}_actual"] / c["expense_actual"]
    f["surplus_ratio"] = (c["revenue_actual"] - c["expense_actual"]) / c["expense_actual"]
    f["tuition_share"] = c["tuition_actual"] / c["revenue_actual"]
    deviation = pd.concat([(c[f"{k}_actual"] - c[f"{k}_budget"]).abs() for k in SPENDING], axis=1)
    f["abs_var_share"] = deviation.sum(axis=1, min_count=1) / c[[f"{k}_budget" for k in SPENDING]].sum(axis=1, min_count=1)
    f["n_over_20pct"] = sum(((f[f"exec_{k}"] - 1).abs() > 0.2).astype(int) for k in SPENDING)
    f["hhi"] = (f[[f"share_{k}" for k in SPENDING]] ** 2).sum(axis=1, min_count=1)
    f["expense_actual"] = c["expense_actual"]
    f["log_expense"] = np.log(c["expense_actual"].where(c["expense_actual"] > 0))
    return f


def roster_properties() -> list[dict]:
    """新北 entries of the 全國教保資訊網 roster (kiang mirror snapshot, cached in CACHE_DIR)."""
    path = CACHE_DIR / "preschools.json"
    if not path.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request("https://kiang.github.io/ap.ece.moe.edu.tw/preschools.json",
                                         headers={"User-Agent": "ntpc-hackathon-pipeline"})
        path.write_bytes(urllib.request.urlopen(request, timeout=60).read())
    return [f["properties"] for f in json.loads(path.read_text(encoding="utf-8"))["features"]
            if f["properties"].get("city") == "新北市"]


def load_meta() -> pd.DataFrame:
    """Capacity, fee, age and after-care from the 全國教保資訊網 roster (a current snapshot, not per year)."""
    np_roster, rows = nonprofit_roster(), []
    for p in roster_properties():
        title = p["title"]
        if (core := nonprofit_core(title)) in np_roster:
            group, inst_id = "非營利", np_roster[core]
        elif title.startswith("新北市立") and (name := title[4:].split("幼兒園")[0]) in CITY:
            group, inst_id = "市立", CITY[name]
        else:
            continue
        reg_year = pd.to_numeric(p.get("reg_date", "")[:4], errors="coerce")
        rows.append(dict(group=group, inst_id=inst_id,
                         capacity=pd.to_numeric(p.get("count_approved"), errors="coerce"),
                         monthly_fee=pd.to_numeric(p.get("monthly"), errors="coerce"),
                         reg_year=reg_year if reg_year > 1970 else np.nan,  # 1970/01/01 is a placeholder
                         has_after_care=int(p.get("is_after", "") not in ("", "無"))))
    meta = pd.DataFrame(rows)
    # 市立 分班 are separate entries that the 決算書 reports under their parent, so capacities add up;
    # a 非營利園 listed twice is the same site under two operators, so they do not.
    agg = lambda cap: dict(capacity=("capacity", cap), monthly_fee=("monthly_fee", "max"),
                           reg_year=("reg_year", "min"), has_after_care=("has_after_care", "max"))
    return pd.concat([meta[meta.group == "市立"].groupby("inst_id").agg(**agg("sum")),
                      meta[meta.group == "非營利"].groupby("inst_id").agg(**agg("max"))]).reset_index()


def load_penalty_periods() -> pd.DataFrame:
    p = pd.read_csv(OUT_DIR / "penalties.csv", dtype={"inst_id": str})
    p["period"] = np.where(p["group"].eq("市立"), p["calendar_year"] - ROC_OFFSET, p["academic_year"])
    return p[["inst_id", "period"]]


def last_complete_period(today: datetime.date) -> dict[str, int]:
    return {"市立": today.year - 1 - ROC_OFFSET,
            "非營利": today.year - ROC_OFFSET - (1 if today.month >= 8 else 2)}


def build(today: datetime.date | None = None) -> tuple[pd.DataFrame, list[str]]:
    today = today or datetime.date.today()
    fin = pd.concat([ratio_features(concept_totals(load_city(), 0)),
                     ratio_features(concept_totals(load_nonprofit(), 1))], ignore_index=True)
    t = fin.merge(load_meta(), on="inst_id", how="left")
    t["expense_per_child"] = t["expense_actual"] / t["capacity"]
    t["years_since_reg"] = t["period"] + ROC_OFFSET - t["reg_year"]
    t["is_nonprofit"] = t["group"].eq("非營利").astype(int)

    penalties = load_penalty_periods().groupby("inst_id")["period"].apply(list).to_dict()
    past = [penalties.get(i, []) for i in t["inst_id"]]
    t["prior_penalties"] = [sum(p <= period for p in ps) for ps, period in zip(past, t["period"])]
    t["penalized_next"] = [float(any(p == period + 1 for p in ps)) for ps, period in zip(past, t["period"])]
    t["label_available"] = t["period"] + 1 <= t["group"].map(last_complete_period(today))
    t.loc[~t["label_available"], "penalized_next"] = np.nan

    t = t.sort_values(["inst_id", "period"]).reset_index(drop=True)
    by_inst = t.groupby("inst_id")
    consecutive = by_inst["period"].shift(1) == t["period"] - 1
    for col in ("exec_personnel", "share_personnel", "exec_expense"):
        t[f"d_{col}"] = (t[col] - by_inst[col].shift(1)).where(consecutive)
    t["expense_growth"] = (t["expense_actual"] / by_inst["expense_actual"].shift(1) - 1).where(consecutive)
    for col in Z_FEATURES:
        peers = t.groupby(["group", "period"])[col]
        t[f"z_{col}"] = (t[col] - peers.transform("mean")) / peers.transform("std")

    opinion = OUT_DIR / "opinion_features.csv"  # produced by the 輿情 model, when available
    opinion_cols = []
    if opinion.exists():
        op = pd.read_csv(opinion, dtype={"inst_id": str})
        opinion_cols = [c for c in op.columns if c not in ("inst_id", "period")]
        t = t.merge(op, on=["inst_id", "period"], how="left")
        if "opinion_docs" in t:
            t["opinion_docs"] = t["opinion_docs"].fillna(0)  # no documents: zero coverage, not zero risk

    features = ([f"exec_{k}" for k in SPENDING + ["expense"]] + [f"share_{k}" for k in SPENDING]
                + ["surplus_ratio", "tuition_share", "abs_var_share", "n_over_20pct", "hhi", "log_expense",
                   "round_share", "benford_mad", "n_line_items",
                   "capacity", "monthly_fee", "years_since_reg", "has_after_care", "expense_per_child",
                   "is_nonprofit", "prior_penalties",
                   "d_exec_personnel", "d_share_personnel", "d_exec_expense", "expense_growth"]
                + [f"z_{c}" for c in Z_FEATURES] + opinion_cols)
    return t, features


def main():
    table, features = build()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    keys = ["group", "inst_id", "inst", "period", "label_available", "penalized_next"]
    table[keys + features].to_csv(OUT_DIR / "model_table.csv", index=False)
    train = table[table["label_available"]]
    # SageMaker built-in XGBoost: headerless CSV, label in the first column, empty field = missing
    train[["penalized_next"] + features].to_csv(OUT_DIR / "train.csv", header=False, index=False, na_rep="")
    (OUT_DIR / "features.json").write_text(json.dumps(
        {"label": "penalized_next", "group_column": "inst_id", "features": features,
         "note": "capacity/monthly_fee/years_since_reg come from a current roster snapshot, not per period"},
        ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"model_table.csv: {len(table)} rows × {len(features)} features")
    summary = table.groupby(["group", "period"]).agg(rows=("inst_id", "size"),
                                                     labelled=("label_available", "sum"),
                                                     positives=("penalized_next", "sum"))
    print(summary.to_string())
    print(f"train.csv: {len(train)} labelled rows, {int(train['penalized_next'].sum())} positive "
          f"({train['penalized_next'].mean():.1%}), {train['inst_id'].nunique()} institutions")
    missing = table[features].isna().mean().sort_values(ascending=False)
    print("most-missing features:", {k: f"{v:.0%}" for k, v in missing.head(8).items()})


if __name__ == "__main__":
    main()
