"""Validate and package the all-新北 risk model.

    python -m pipeline.s6_validate

Outputs: models/risk_model_all.joblib, models/risk_model_all.json (portable parameters),
         models/validation_all.json, data/processed/risk_scores_latest.csv

Two validations, both grouped so no institution is on both sides of a split:
  1. across institutions — 5 folds × 5 repeats, 95% CI from an institution-level bootstrap
  2. forward in time — fit on years ≤ SPLIT_YEAR, test on later years, with the screening threshold
     fixed on the training years only (the test years never influence it)

The shipped model is the logistic regression that won s5_train, plus a Platt mapping fitted on its
out-of-fold scores so the displayed probability matches the observed penalty rate. Its parameters are
also written as plain JSON so the model can be re-implemented anywhere. Two operating points are recorded:
  screen    the score above which 90% of penalties fall — the "do not miss" list (~70% of 園)
  priority  the top 10% of each year's scores — where the model beats simple rules (~2× hit rate)
"""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import OUT_DIR, REPO
from .s5_train import bootstrap_auc, out_of_fold

MODELS_DIR = REPO / "models"
SPLIT_YEAR = 2022
TARGET_RECALL = 0.90
PRIORITY_SHARE = 0.10


def make_model():
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         LogisticRegression(C=0.3, class_weight="balanced", max_iter=5000))


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def threshold_for_recall(y: np.ndarray, score: np.ndarray, recall: float) -> float:
    """Score at or above which `recall` of the positives lie."""
    positives = np.sort(score[y == 1])
    return float(positives[int(np.floor((1 - recall) * len(positives)))])


def top_share(score: np.ndarray, periods, share: float) -> np.ndarray:
    """Flag the top `share` of scores within each period — how an inspector would pick a shortlist."""
    return pd.Series(score).groupby(np.asarray(periods)).rank(ascending=False, pct=True).to_numpy() <= share


def confusion(y: np.ndarray, flag) -> dict:
    flag = np.asarray(flag, dtype=bool)
    tp, fp = int((flag & (y == 1)).sum()), int((flag & (y == 0)).sum())
    fn, tn = int((~flag & (y == 1)).sum()), int((~flag & (y == 0)).sum())
    return dict(tp=tp, fn=fn, fp=fp, tn=tn, recall=round(tp / max(tp + fn, 1), 3),
                precision=round(tp / max(tp + fp, 1), 3), specificity=round(tn / max(tn + fp, 1), 3),
                flagged=round(float(flag.mean()), 3))


def auc_ci(y: np.ndarray, score: np.ndarray, groups: np.ndarray) -> dict:
    low, high = bootstrap_auc(y, score, groups)
    return dict(auc=round(roc_auc_score(y, score), 3), ci_low=round(low, 3), ci_high=round(high, 3))


def by_group_auc(y, score, keys) -> dict:
    keys = np.asarray(keys)
    return {str(k): round(roc_auc_score(y[keys == k], score[keys == k]), 3)
            for k in pd.unique(keys) if len(set(y[keys == k])) == 2}


def main():
    features = json.loads((OUT_DIR / "features_all.json").read_text(encoding="utf-8"))["features"]
    table = pd.read_csv(OUT_DIR / "model_table_all.csv")
    lab = table[table["label_available"]].reset_index(drop=True)
    y, groups = lab["penalized_next"].astype(int).to_numpy(), lab["inst_id"].to_numpy()
    base_rate = float(y.mean())
    report = dict(rows=len(lab), positives=int(y.sum()), base_rate=round(base_rate, 3),
                  institutions=int(lab["inst_id"].nunique()),
                  years=[int(lab["period"].min()), int(lab["period"].max())], features=features)

    # 1. across institutions
    oof = out_of_fold(make_model, lab[features], lab["penalized_next"].astype(int), groups)
    screen_cv = threshold_for_recall(y, oof, TARGET_RECALL)
    report["cross_validation"] = dict(
        **auc_ci(y, oof, groups), auc_by_year=by_group_auc(y, oof, lab["period"]),
        auc_by_type=by_group_auc(y, oof, lab["group"]),
        screen=confusion(y, oof >= screen_cv), priority=confusion(y, top_share(oof, lab["period"], PRIORITY_SHARE)),
        rule_every_private=confusion(y, lab["group"].eq("私立")))

    # 2. forward in time
    past, future = lab[lab["period"] <= SPLIT_YEAR], lab[lab["period"] > SPLIT_YEAR]
    y_past, y_future = past["penalized_next"].astype(int), future["penalized_next"].astype(int).to_numpy()
    screen_past = threshold_for_recall(y_past.to_numpy(), out_of_fold(make_model, past[features], y_past,
                                                                      past["inst_id"].to_numpy()), TARGET_RECALL)
    forward = make_model().fit(past[features], y_past).predict_proba(future[features])[:, 1]
    report["forward"] = dict(
        train_years=[int(past["period"].min()), SPLIT_YEAR], test_years=[SPLIT_YEAR + 1, int(future["period"].max())],
        test_rows=len(future), test_positives=int(y_future.sum()),
        **auc_ci(y_future, forward, future["inst_id"].to_numpy()), auc_by_year=by_group_auc(y_future, forward, future["period"]),
        screen=confusion(y_future, forward >= screen_past),
        priority=confusion(y_future, top_share(forward, future["period"], PRIORITY_SHARE)),
        rule_every_private=confusion(y_future, future["group"].eq("私立")),
        rule_penalised_before=confusion(y_future, future["prior_penalties"].gt(0)))

    # 3. ship: the ranker orders and flags; a Platt mapping fitted on its out-of-fold scores turns the
    #    class-weighted (hence inflated) output into a probability that matches the penalty rate
    ranker = make_model().fit(lab[features], y)
    platt = LogisticRegression(C=1e6).fit(logit(oof).reshape(-1, 1), y)
    a, b = float(platt.coef_[0][0]), float(platt.intercept_[0])

    def calibrate(p):
        return 1 / (1 + np.exp(-(a * logit(p) + b)))

    imputer, scaler, linear = ranker
    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(dict(ranker=ranker, platt=(a, b), features=features, screen_threshold=screen_cv,
                     priority_share=PRIORITY_SHARE), MODELS_DIR / "risk_model_all.joblib")
    (MODELS_DIR / "risk_model_all.json").write_text(json.dumps(dict(
        features=features, impute_median=imputer.statistics_.round(6).tolist(),
        mean=scaler.mean_.round(6).tolist(), scale=scaler.scale_.round(6).tolist(),
        coef=linear.coef_[0].round(6).tolist(), intercept=round(float(linear.intercept_[0]), 6),
        platt=dict(a=round(a, 6), b=round(b, 6)), screen_threshold=round(screen_cv, 6), priority_share=PRIORITY_SHARE,
        formula=("x = features, missing values replaced by impute_median; z = (x - mean) / scale; "
                 "rank_score = sigmoid(intercept + coef · z); probability = sigmoid(platt.a * logit(rank_score) + platt.b); "
                 "screen_flag = rank_score >= screen_threshold; priority_flag = rank_score in the year's top priority_share")),
        ensure_ascii=False, indent=2), encoding="utf-8")
    report["coefficients"] = {f: round(float(c), 3) for f, c in
                              sorted(zip(features, linear.coef_[0]), key=lambda fc: -abs(fc[1]))}

    latest = table[~table["label_available"]].reset_index(drop=True)
    score = ranker.predict_proba(latest[features])[:, 1]
    contrib = scaler.transform(imputer.transform(latest[features])) * linear.coef_[0]
    top = np.argsort(-contrib, axis=1)[:, :3]  # the factors pushing risk up the most
    scores = latest[["group", "inst", "period"]].assign(
        predicts_year=latest["period"] + 1,
        risk_probability=calibrate(score).round(4),
        percentile=pd.Series(score).rank(pct=True).round(3),
        screen_flag=score >= screen_cv,
        priority_flag=top_share(score, latest["period"], PRIORITY_SHARE),
        top_factors=[", ".join(features[j] for j in row if contrib[i, j] > 0) for i, row in enumerate(top)])
    scores.sort_values("risk_probability", ascending=False).to_csv(OUT_DIR / "risk_scores_latest.csv", index=False)
    report["latest_scoring"] = dict(year=int(latest["period"].max()) + 1, institutions=len(scores),
                                    screen_flagged=int(scores["screen_flag"].sum()),
                                    priority_flagged=int(scores["priority_flag"].sum()),
                                    mean_probability=round(float(scores["risk_probability"].mean()), 3))
    (MODELS_DIR / "validation_all.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "features"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
