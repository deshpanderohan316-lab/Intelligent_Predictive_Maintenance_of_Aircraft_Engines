"""End-to-end preprocessing pipeline for N-CMAPSS.

    raw 1 Hz HDF5  ──► 1 inventory ──► 2 clean ──► 3 operating-condition residuals
                   ──► 4 cycle aggregation ──► 5 RUL labels ──► 6 time-series features
                   ──► 7 split ──► 8 winsorise ──► 9 feature selection ──► 10 scaling
                   ──► data/processed/*.parquet + artifacts/preprocessing/*

Every fitted object (baseline model, winsoriser, selector, scaler) is fitted on
the *development* (training) engines only and then applied to the test engines.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from ..config import (
    INTERIM_DIR, PREPROC_ARTIFACTS, PROCESSED_DIR, REPORTS_DIR, THETA_VARS, UI_DIR, W_VARS,
    PreprocessConfig, ensure_dirs,
)
from ..data.loader import find_dataset, iter_chunks, list_datasets, n_rows
from .aggregation import CycleAggregator
from .cleaning import QualityCounter, Winsorizer, check_duplicate_keys, clean_chunk, find_constant_columns
from .feature_engineering import build_features
from .feature_selection import FeatureSelector
from .labeling import add_rul_labels
from .operating_conditions import HealthyBaselineModel
from .report import PipelineReport

log = logging.getLogger(__name__)
META_COLS = ["dataset", "split", "unit", "cycle", "engine_id", "Fc", "hs", "RUL", "RUL_raw", "health_stage"]


def _downsample(df: pd.DataFrame, n: int) -> pd.DataFrame:
    step = max(1, len(df) // n)
    return df.iloc[::step]


def run(cfg: PreprocessConfig) -> dict:
    ensure_dirs()
    report = PipelineReport(asdict(cfg))
    sensors = cfg.sensor_vars
    datasets = [find_dataset(name) for name in cfg.datasets]

    # ------------------------------------------------------------------ 1
    with report.step("inventory", "Data inventory",
                     "Locate HDF5 files, verify they open, count 1 Hz rows per split.") as d:
        inventory = list_datasets()
        d["files"] = inventory
        bad = {f["name"] for f in inventory if not f["ok"]}
        datasets = [ds for ds in datasets if ds.name not in bad]
        if not datasets:
            raise RuntimeError("None of the requested datasets could be opened.")
        d["selected"] = [ds.name for ds in datasets]
        d["rows"] = {ds.name: {s: n_rows(ds, s) for s in ("dev", "test")} for ds in datasets}
        d["variables"] = {"W (flight conditions)": W_VARS, "X_s (sensors)": sensors,
                          "T (health params, EDA only)": THETA_VARS, "A (auxiliary)": ["unit", "cycle", "Fc", "hs"]}

    numeric_cols = W_VARS + sensors

    # ------------------------------------------------------------------ 2+3a
    with report.step("baseline_fit", "Fit healthy-engine baseline",
                     "Stream development data, clean it, sample healthy (hs=1) seconds and fit "
                     "sensor = f(alt, Mach, TRA, T2) so flight-condition effects can be removed.") as d:
        total_dev = sum(n_rows(ds, "dev") for ds in datasets)
        stride = max(1, int(total_dev * 0.75) // cfg.baseline_max_samples)  # ~75 % of dev is healthy
        healthy_parts, counter = [], QualityCounter()
        for ds in datasets:
            for chunk in iter_chunks(ds, "dev", cfg.chunk_size, cfg.use_virtual_sensors, include_theta=False):
                chunk = clean_chunk(chunk, numeric_cols, sensors, counter, cfg.min_altitude_ft)
                healthy_parts.append(chunk.loc[chunk["hs"] == 1, W_VARS + sensors].iloc[::stride])
        healthy = pd.concat(healthy_parts, ignore_index=True)
        baseline = HealthyBaselineModel(sensors, cfg.baseline_poly_degree, cfg.baseline_ridge_alpha, cfg.random_state)
        baseline.fit(healthy)
        d["healthy_samples_used"] = len(healthy)
        d.update(baseline.summary())
        joblib.dump(baseline, PREPROC_ARTIFACTS / "healthy_baseline.joblib")

    # ------------------------------------------------------------------ 2+3b+4
    with report.step("clean_residual_aggregate", "Clean → residualise → aggregate per flight",
                     "Second streaming pass over dev + test: drop NaN/Inf/non-physical rows, convert "
                     "sensors to healthy-baseline residuals, then compress each flight (1 Hz) to one "
                     "row of cycle statistics using exact chunk-mergeable sufficient statistics.") as d:
        residual_cols = [f"r_{s}" for s in sensors]
        agg = CycleAggregator(residual_cols, sensors, THETA_VARS)
        quality = {}
        flight_trace = None
        for ds in datasets:
            for split in ("dev", "test"):
                counter = QualityCounter()
                for chunk in iter_chunks(ds, split, cfg.chunk_size, cfg.use_virtual_sensors, include_theta=True):
                    chunk = clean_chunk(chunk, numeric_cols, sensors, counter, cfg.min_altitude_ft)
                    chunk = pd.concat([chunk, baseline.residuals(chunk)], axis=1)
                    if flight_trace is None:  # keep one raw flight for the UI "before/after" view
                        first = chunk[(chunk["unit"] == chunk["unit"].iloc[0]) & (chunk["cycle"] == chunk["cycle"].iloc[0])]
                        trace = _downsample(first, 400)
                        trace = trace.assign(t=trace.index - first.index[0])  # seconds into the flight
                        flight_trace = trace[["t"] + W_VARS + ["T48", "r_T48", "Nc", "r_Nc", "unit", "cycle"]]
                    agg.update(chunk)
                quality[f"{ds.name}/{split}"] = counter.as_dict()
        cycles = agg.finalize()
        d["quality"] = quality
        d["rows_1hz_in"] = sum(q["rows_in"] for q in quality.values())
        d["rows_cycle_out"] = len(cycles)
        d["compression_ratio"] = round(d["rows_1hz_in"] / max(len(cycles), 1), 1)
        d["duplicate_cycle_keys"] = check_duplicate_keys(cycles, ["dataset", "unit", "cycle"])
        d["preview"] = report.preview(cycles, ["dataset", "split", "unit", "cycle", "op_duration_s",
                                               "op_alt_max", "r_T48_mean", "r_T48_std", "RUL_file"])

    # ------------------------------------------------------------------ 5
    with report.step("labels", "Remaining-Useful-Life labels",
                     "Verify RUL = last cycle − current cycle, apply optional piece-wise cap, "
                     "derive health stages (healthy > 30, warning 11-30, critical ≤ 10 cycles).") as d:
        cycles, info = add_rul_labels(cycles, cfg.rul_cap)
        d.update(info)
        cycles.to_parquet(INTERIM_DIR / "cycles.parquet", index=False)

    # ------------------------------------------------------------------ 6
    with report.step("features", "Time-series feature engineering",
                     "Causal per-engine rolling mean/std, EWMA, rolling slope and drift-from-own-baseline "
                     "on every residual signal.") as d:
        feats, feature_cols = build_features(cycles, cfg)
        const = find_constant_columns(feats[feats["split"] == "dev"], feature_cols)
        feature_cols = [c for c in feature_cols if c not in const]
        d["n_features"] = len(feature_cols)
        d["constant_dropped"] = const
        d["groups"] = {
            "operating_condition": [c for c in feature_cols if c.startswith("op_")],
            "residual_mean": [c for c in feature_cols if c.endswith("_mean") and "__" not in c and c.startswith("r_")],
            "residual_std": [c for c in feature_cols if c.endswith("_std") and "__" not in c],
            "temporal": len([c for c in feature_cols if "__" in c]),
        }

    # ------------------------------------------------------------------ 7
    with report.step("split", "Train / test split by engine",
                     "Use the official N-CMAPSS split: development engines → train, test engines → test. "
                     "Splitting by engine (never by row) prevents leakage between cycles of the same engine.") as d:
        train = feats[feats["split"] == "dev"].reset_index(drop=True)
        test = feats[feats["split"] == "test"].reset_index(drop=True)
        d["train_engines"] = sorted(train["engine_id"].unique().tolist())
        d["test_engines"] = sorted(test["engine_id"].unique().tolist())
        d["train_rows"], d["test_rows"] = len(train), len(test)

    # ------------------------------------------------------------------ 8
    with report.step("winsorize", "Outlier treatment (winsorising)",
                     f"Clip every feature to the training {cfg.clip_quantiles[0]:.1%}–{cfg.clip_quantiles[1]:.1%} "
                     "percentiles; limits are learned on train engines only.") as d:
        wins = Winsorizer(cfg.clip_quantiles).fit(train[feature_cols])
        d["values_clipped_train"] = wins.n_clipped(train[feature_cols])
        d["values_clipped_test"] = wins.n_clipped(test[feature_cols])
        train[feature_cols] = wins.transform(train[feature_cols])
        test[feature_cols] = wins.transform(test[feature_cols])

    # ------------------------------------------------------------------ 9
    with report.step("selection", "Feature selection",
                     "Variance filter → |Spearman| relevance to RUL → drop features with |r| > "
                     f"{cfg.correlation_threshold} to a stronger one → keep top {cfg.max_features}.") as d:
        selector = FeatureSelector(cfg.variance_threshold, cfg.correlation_threshold, cfg.max_features)
        selector.fit(train[feature_cols], train["RUL"])
        d.update(selector.summary())
        selected = selector.selected_

    # ------------------------------------------------------------------ 10
    with report.step("scaling", "Normalisation (z-score)",
                     "StandardScaler fitted on train engines; mean 0 / std 1 per feature for "
                     "distance- and gradient-based models (SVR, KNN, MLP, Ridge).") as d:
        scaler = StandardScaler().fit(train[selected])
        train_s = train[META_COLS].join(pd.DataFrame(scaler.transform(train[selected]), columns=selected))
        test_s = test[META_COLS].join(pd.DataFrame(scaler.transform(test[selected]), columns=selected))
        d["mean_before"] = train[selected].mean().round(4).head(8).to_dict()
        d["std_before"] = train[selected].std().round(4).head(8).to_dict()
        d["preview"] = report.preview(train_s, ["engine_id", "cycle", "RUL"] + selected[:6])

    # ------------------------------------------------------------------ save
    train_s.to_parquet(PROCESSED_DIR / "train.parquet", index=False)
    test_s.to_parquet(PROCESSED_DIR / "test.parquet", index=False)
    joblib.dump({"winsorizer": wins, "selector": selector, "scaler": scaler,
                 "feature_cols": feature_cols, "selected": selected, "config": asdict(cfg)},
                PREPROC_ARTIFACTS / "preprocessor.joblib")
    report.save(REPORTS_DIR / "preprocessing_report.json")

    # Small UI payloads
    flight_trace.round(4).to_json(UI_DIR / "flight_trace.json", orient="records")
    _export_engine_series(cycles, sensors)
    print(f"Saved train {train_s.shape}, test {test_s.shape} -> {PROCESSED_DIR}")
    return {"train_shape": train_s.shape, "test_shape": test_s.shape, "features": selected}


def _export_engine_series(cycles: pd.DataFrame, sensors: list[str]) -> None:
    """Per-engine trajectories: raw cycle mean vs residual (shows why step 3 matters)."""
    keep = ["engine_id", "split", "cycle", "RUL_raw", "hs", "Fc", "op_alt_max", "op_duration_s"]
    keep += [f"raw_{s}_mean" for s in sensors] + [f"r_{s}_mean" for s in sensors]
    keep += [c for c in cycles.columns if c.startswith("theta_")]
    out = {eid: g[keep[1:]].round(5).to_dict(orient="list") for eid, g in cycles[keep].groupby("engine_id")}
    (UI_DIR / "engine_series.json").write_text(json.dumps(out), encoding="utf-8")
