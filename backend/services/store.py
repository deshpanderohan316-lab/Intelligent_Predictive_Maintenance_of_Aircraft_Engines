"""Read-only access to the artifacts produced by the ML pipeline (cached)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
UI = ARTIFACTS / "ui"
REPORTS = ARTIFACTS / "reports"
FIGURES = ARTIFACTS / "figures"
PROCESSED = ROOT / "data" / "processed"


class ArtifactMissing(FileNotFoundError):
    pass


def _json(path: Path):
    if not path.exists():
        raise ArtifactMissing(f"{path.relative_to(ROOT)} not found - run `python -m ml.scripts.run_all` first")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache
def preprocessing_report() -> dict:
    return _json(REPORTS / "preprocessing_report.json")


@lru_cache
def metrics() -> dict:
    return _json(REPORTS / "metrics.json")


@lru_cache
def eda_summary() -> dict:
    return _json(UI / "eda_summary.json")


@lru_cache
def flight_trace() -> list:
    return _json(UI / "flight_trace.json")


@lru_cache
def flight_envelope() -> list:
    return _json(UI / "flight_envelope.json")


@lru_cache
def engine_series() -> dict:
    return _json(UI / "engine_series.json")


@lru_cache
def predictions() -> dict:
    return _json(UI / "predictions.json")


@lru_cache
def model_bundle() -> dict:
    path = ARTIFACTS / "models" / "best_model.joblib"
    if not path.exists():
        raise ArtifactMissing("best_model.joblib not found - run training first")
    return joblib.load(path)


@lru_cache
def feature_table() -> pd.DataFrame:
    frames = [pd.read_parquet(PROCESSED / f"{s}.parquet") for s in ("train", "test")]
    return pd.concat(frames, ignore_index=True)


def clear_cache() -> None:
    for fn in (preprocessing_report, metrics, eda_summary, flight_trace, flight_envelope,
               engine_series, predictions, model_bundle, feature_table):
        fn.cache_clear()
