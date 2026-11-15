"""Train, cross-validate and compare RUL regressors.

* Model selection: GroupKFold cross-validation on training engines (an engine's
  cycles never appear in both the fit and validation folds).
* Final evaluation: refit on all training engines, score on held-out test engines.
* Outputs: metrics.json, best_model.joblib, predictions.json (per test engine).
"""
from __future__ import annotations

import json
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GroupKFold

from ..config import MODEL_ARTIFACTS, PREPROC_ARTIFACTS, PROCESSED_DIR, REPORTS_DIR, UI_DIR
from .metrics import regression_report
from .registry import get_models


def _load():
    pre = joblib.load(PREPROC_ARTIFACTS / "preprocessor.joblib")
    train = pd.read_parquet(PROCESSED_DIR / "train.parquet")
    test = pd.read_parquet(PROCESSED_DIR / "test.parquet")
    return pre["selected"], train, test


def run(n_splits: int | None = None) -> dict:
    features, train, test = _load()
    X, y, groups = train[features], train["RUL"], train["engine_id"]
    X_test, y_test = test[features], test["RUL"]
    n_splits = n_splits or min(5, groups.nunique())
    cv = GroupKFold(n_splits=n_splits)

    results, preds = [], {}
    for name, model in get_models().items():
        t0 = time.time()
        oof = np.zeros(len(y))
        for tr, va in cv.split(X, y, groups):
            m = clone(model).fit(X.iloc[tr], y.iloc[tr])
            oof[va] = m.predict(X.iloc[va])
        oof = np.clip(oof, 0, None)
        final = clone(model).fit(X, y)
        p = np.clip(final.predict(X_test), 0, None)
        preds[name] = (final, p)
        res = {"model": name, "cv": regression_report(y, oof), "test": regression_report(y_test, p),
               "train_seconds": round(time.time() - t0, 2)}
        results.append(res)
        print(f"{name:<28s} CV RMSE {res['cv']['RMSE']:>7.2f} | test RMSE {res['test']['RMSE']:>7.2f} "
              f"MAE {res['test']['MAE']:>6.2f} R² {res['test']['R2']:>6.3f}")

    # Choose by cross-validated RMSE (test set stays untouched for selection)
    best = min(results, key=lambda r: r["cv"]["RMSE"])["model"]
    best_model, best_pred = preds[best]
    MODEL_ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": best_model, "name": best, "features": features}, MODEL_ARTIFACTS / "best_model.joblib")

    importance = _importance(best_model, features)
    payload = {"best_model": best, "cv_folds": n_splits, "selection_metric": "CV RMSE",
               "n_train_rows": len(train), "n_test_rows": len(test),
               "results": results, "feature_importance": importance}
    (REPORTS_DIR / "metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    out = test[["engine_id", "cycle", "RUL", "RUL_raw", "health_stage"]].copy()
    out["pred"] = best_pred.round(2)
    for name, (_, p) in preds.items():
        out[f"pred::{name}"] = p.round(2)
    per_engine = {eid: g.drop(columns="engine_id").to_dict(orient="list") for eid, g in out.groupby("engine_id")}
    (UI_DIR / "predictions.json").write_text(json.dumps(per_engine), encoding="utf-8")
    print(f"Best model (CV RMSE): {best}")
    return payload


def _importance(model, features) -> list[dict]:
    imp = getattr(model, "feature_importances_", None)
    if imp is None and hasattr(model, "coef_"):
        imp = np.abs(np.ravel(model.coef_))
    if imp is None:
        return []
    imp = np.asarray(imp, float)
    imp = imp / imp.sum() if imp.sum() else imp
    order = np.argsort(imp)[::-1][:20]
    return [{"feature": features[i], "importance": round(float(imp[i]), 4)} for i in order]
