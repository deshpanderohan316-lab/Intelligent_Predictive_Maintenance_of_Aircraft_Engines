"""Regression metrics for RUL estimation."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def nasa_score(y_true, y_pred) -> float:
    """PHM08 asymmetric score: late predictions (over-estimating RUL) are
    penalised more than early ones because they risk in-flight failure."""
    d = np.asarray(y_pred) - np.asarray(y_true)
    return float(np.sum(np.where(d < 0, np.exp(-d / 13) - 1, np.exp(d / 10) - 1)))


def regression_report(y_true, y_pred) -> dict:
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    return {
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 3),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 3),
        "R2": round(float(r2_score(y_true, y_pred)), 4),
        "NASA_score": round(nasa_score(y_true, y_pred), 2),
    }
