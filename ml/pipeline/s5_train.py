"""Main risk model: compare model sizes by grouped cross-validation, then fit the best one.

    python -m pipeline.s5_train               # CV comparison, final fit, scores_main.csv, models/
    python -m pipeline.s5_train --sagemaker   # additionally run the final fit as a SageMaker job

Cross-validation keeps each institution's rows in a single fold, is repeated over several fold
assignments, and reports AUC with a 95% interval from an institution-level bootstrap. With only a
couple of dozen positive rows, the interval says more than the point estimate.
"""
import argparse
import json
import os
import time

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import OUT_DIR, REPO

MODELS_DIR = REPO / "models"
REPEATS, FOLDS, BOOTSTRAPS = 5, 5, 1000
BASELINE = "past penalties only (no model)"


def xgb_params(pos_weight: float, depth: int, trees: int) -> dict:
    return dict(objective="binary:logistic", max_depth=depth, n_estimators=trees, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8, min_child_weight=2, reg_lambda=5.0,
                scale_pos_weight=pos_weight, tree_method="hist", n_jobs=4)


def candidates(pos_weight: float) -> dict:
    """Increasing capacity, from a linear model to depth-4 boosted trees."""
    models = {"logistic L2": lambda: make_pipeline(
        SimpleImputer(strategy="median"), StandardScaler(),
        LogisticRegression(C=0.1, class_weight="balanced", max_iter=5000))}
    for depth, trees in ((1, 100), (2, 200), (3, 200), (4, 400)):
        models[f"xgb depth {depth} × {trees}"] = (
            lambda d=depth, t=trees: xgb.XGBClassifier(**xgb_params(pos_weight, d, t)))
    return models


def out_of_fold(make_model, X, y, groups) -> np.ndarray:
    """Out-of-fold probability per row, averaged over REPEATS grouped fold assignments."""
    preds = np.zeros((REPEATS, len(y)))
    for r in range(REPEATS):
        for train, test in StratifiedGroupKFold(FOLDS, shuffle=True, random_state=r).split(X, y, groups):
            preds[r, test] = make_model().fit(X.iloc[train], y.iloc[train]).predict_proba(X.iloc[test])[:, 1]
    return preds.mean(axis=0)


def bootstrap_auc(y: np.ndarray, score: np.ndarray, groups: np.ndarray) -> tuple[float, float]:
    """95% interval for AUC, resampling institutions rather than rows."""
    rng = np.random.default_rng(0)
    ids = np.unique(groups)
    rows_of = {g: np.flatnonzero(groups == g) for g in ids}
    aucs = []
    for _ in range(BOOTSTRAPS):
        rows = np.concatenate([rows_of[g] for g in rng.choice(ids, len(ids))])
        if 0 < y[rows].sum() < len(rows):
            aucs.append(roc_auc_score(y[rows], score[rows]))
    return float(np.percentile(aucs, 2.5)), float(np.percentile(aucs, 97.5))


def n_parameters(model) -> int:
    if isinstance(model, xgb.XGBClassifier):
        return len(model.get_booster().trees_to_dataframe())  # split + leaf nodes
    return model[-1].coef_.size + 1


def evaluate(name, score, y, groups, seconds, size) -> dict:
    low, high = bootstrap_auc(y, score, groups)
    return dict(model=name, auc=round(roc_auc_score(y, score), 3), ci_low=round(low, 3), ci_high=round(high, 3),
                pr_auc=round(average_precision_score(y, score), 3), cv_seconds=round(seconds, 1), n_parameters=size)


def contributions(model, X: pd.DataFrame) -> np.ndarray:
    """Per-row, per-feature contribution to the score: SHAP for trees, coefficient × z for the linear model."""
    if isinstance(model, xgb.XGBClassifier):
        return model.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)[:, :-1]
    imputer, scaler, linear = model
    return scaler.transform(imputer.transform(X)) * linear.coef_[0]


def launch_sagemaker(params: dict, suffix: str = "") -> None:
    """Upload train.csv and run the final fit as a SageMaker built-in XGBoost job in us-west-2.

    Needs SAGEMAKER_BUCKET and SAGEMAKER_ROLE_ARN (kiro-sagemaker-execution-role), an AWS profile
    (AWS_PROFILE, default "workshop"), and XGBOOST_IMAGE_URI or the sagemaker SDK to look it up.
    """
    import boto3

    session = boto3.Session(profile_name=os.environ.get("AWS_PROFILE", "workshop"), region_name="us-west-2")
    bucket, role = os.environ["SAGEMAKER_BUCKET"], os.environ["SAGEMAKER_ROLE_ARN"]
    image = os.environ.get("XGBOOST_IMAGE_URI")
    if not image:
        from sagemaker import image_uris
        image = image_uris.retrieve("xgboost", "us-west-2", "1.7-1")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    key = f"curated/train-{stamp}.csv"
    session.client("s3").upload_file(str(OUT_DIR / f"train{suffix}.csv"), bucket, key)
    hyper = dict(objective="binary:logistic", eval_metric="auc", max_depth=params["max_depth"],
                 num_round=params["n_estimators"], eta=params["learning_rate"], subsample=params["subsample"],
                 colsample_bytree=params["colsample_bytree"], min_child_weight=params["min_child_weight"],
                 scale_pos_weight=params["scale_pos_weight"], **{"lambda": params["reg_lambda"]})
    name = f"kiro-xgb-penalty-{stamp}"
    session.client("sagemaker").create_training_job(
        TrainingJobName=name,
        AlgorithmSpecification={"TrainingImage": image, "TrainingInputMode": "File"},
        RoleArn=role,
        InputDataConfig=[{"ChannelName": "train", "ContentType": "text/csv", "DataSource": {"S3DataSource": {
            "S3DataType": "S3Prefix", "S3Uri": f"s3://{bucket}/{key}", "S3DataDistributionType": "FullyReplicated"}}}],
        OutputDataConfig={"S3OutputPath": f"s3://{bucket}/models/"},
        ResourceConfig={"InstanceType": "ml.m5.xlarge", "InstanceCount": 1, "VolumeSizeInGB": 5},
        StoppingCondition={"MaxRuntimeInSeconds": 1800},
        HyperParameters={k: str(v) for k, v in hyper.items()},
    )
    print(f"SageMaker job {name} started; artifact -> s3://{bucket}/models/{name}/output/model.tar.gz")


def main():
    parser = argparse.ArgumentParser(description="Train the main penalty-risk model.")
    parser.add_argument("--sagemaker", action="store_true", help="also run the final fit on SageMaker")
    parser.add_argument("--table", default="", help='model-table suffix, e.g. "_all" for the all-新北 table')
    args = parser.parse_args()
    sfx = args.table

    features = json.loads((OUT_DIR / f"features{sfx}.json").read_text(encoding="utf-8"))["features"]
    table = pd.read_csv(OUT_DIR / f"model_table{sfx}.csv", dtype={"inst_id": str})
    train = table[table["label_available"]].reset_index(drop=True)
    X, y = train[features], train["penalized_next"].astype(int)
    groups = train["inst_id"].to_numpy()
    pos_weight = float((y == 0).sum() / max(int(y.sum()), 1))
    print(f"{len(train)} labelled rows, {int(y.sum())} positive, {len(np.unique(groups))} institutions, "
          f"{len(features)} features\n")

    results = [evaluate(BASELINE, train["prior_penalties"].to_numpy(float), y.to_numpy(), groups, 0.0, 0)]
    models = candidates(pos_weight)
    for name, make in models.items():
        started = time.perf_counter()
        oof = out_of_fold(make, X, y, groups)
        results.append(evaluate(name, oof, y.to_numpy(), groups, time.perf_counter() - started,
                                n_parameters(make().fit(X, y))))
    report = pd.DataFrame(results)
    print(report.to_string(index=False))

    # Best AUC among real models; on ties the smaller model wins.
    best = report[report["model"] != BASELINE].sort_values(["auc", "n_parameters"], ascending=[False, True]).iloc[0]
    print(f"\nchosen: {best['model']} (AUC {best['auc']}, 95% CI {best['ci_low']}–{best['ci_high']})")

    started = time.perf_counter()
    final = models[best["model"]]().fit(X, y)
    fit_seconds = time.perf_counter() - started
    MODELS_DIR.mkdir(exist_ok=True)
    if isinstance(final, xgb.XGBClassifier):
        final.save_model(MODELS_DIR / f"main_model{sfx}.json")
    else:
        joblib.dump(final, MODELS_DIR / f"main_model{sfx}.joblib")

    scores = table[["group", "inst_id", "inst", "period", "label_available", "penalized_next"]].copy()
    scores["p_penalty"] = final.predict_proba(table[features])[:, 1]
    contrib = contributions(final, table[features])
    top = np.argsort(-np.abs(contrib), axis=1)[:, :5]
    scores["top_factors"] = [json.dumps({features[j]: round(float(contrib[i, j]), 4) for j in top[i]},
                                        ensure_ascii=False) for i in range(len(table))]
    scores.to_csv(OUT_DIR / f"scores_main{sfx}.csv", index=False)
    (MODELS_DIR / f"main_metrics{sfx}.json").write_text(json.dumps(
        dict(chosen=best["model"], final_fit_seconds=round(fit_seconds, 2), cv=results, features=features,
             trained_rows=len(train), positives=int(y.sum())), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"final fit {fit_seconds:.2f}s -> models/, scores_main{sfx}.csv ({len(scores)} rows)")

    if args.sagemaker:
        if not isinstance(final, xgb.XGBClassifier):
            raise SystemExit("the chosen model is not XGBoost; SageMaker's built-in XGBoost cannot train it")
        launch_sagemaker(final.get_params(), sfx)


if __name__ == "__main__":
    main()
