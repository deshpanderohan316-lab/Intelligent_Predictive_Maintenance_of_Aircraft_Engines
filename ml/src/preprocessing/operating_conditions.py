"""Step 3 - Operating-condition normalisation (healthy-baseline residuals).

Why this step matters for N-CMAPSS
----------------------------------
Raw sensor values are dominated by *where the aircraft is flying*
(altitude, Mach number, throttle angle, inlet temperature), not by engine
health.  A 1 % efficiency loss changes T48 by a few degrees, while a climb from
sea level to cruise changes it by hundreds.

We therefore learn what a *healthy* engine reads under every flight condition:

    x_hat = f(alt, Mach, TRA, T2)        (fitted on hs == 1 data only)

and keep the standardised residual

    r = (x - x_hat) / sigma_healthy

which is ~0 for a healthy engine in any flight condition and drifts away from
0 as the engine degrades.  ``f`` is a cubic polynomial ridge regression - fast
enough to apply to millions of 1 Hz rows and accurate (R² > 0.99 on most
sensors).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from ..config import W_VARS


class HealthyBaselineModel:
    def __init__(self, sensors: list[str], degree: int = 3, alpha: float = 1e-3, random_state: int = 42):
        self.sensors = sensors
        self.degree = degree
        self.alpha = alpha
        self.random_state = random_state
        self.model_: Pipeline | None = None
        self.sigma_: np.ndarray | None = None
        self.r2_: dict[str, float] = {}

    # ------------------------------------------------------------------ #
    def fit(self, healthy: pd.DataFrame) -> "HealthyBaselineModel":
        W = healthy[W_VARS].to_numpy(np.float64)
        X = healthy[self.sensors].to_numpy(np.float64)
        W_tr, W_va, X_tr, X_va = train_test_split(W, X, test_size=0.2, random_state=self.random_state)

        self.model_ = make_pipeline(
            StandardScaler(),
            PolynomialFeatures(degree=self.degree, include_bias=False),
            Ridge(alpha=self.alpha),
        )
        self.model_.fit(W_tr, X_tr)

        pred_va = self.model_.predict(W_va)
        self.r2_ = {s: float(r2_score(X_va[:, i], pred_va[:, i])) for i, s in enumerate(self.sensors)}
        # Residual spread of a healthy engine -> unit used to standardise residuals
        self.sigma_ = (X_va - pred_va).std(axis=0)
        self.sigma_[self.sigma_ == 0] = 1.0
        return self

    # ------------------------------------------------------------------ #
    def residuals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return standardised residuals ``r_<sensor>`` for every row of ``df``."""
        W = df[W_VARS].to_numpy(np.float64)
        X = df[self.sensors].to_numpy(np.float64)
        R = (X - self.model_.predict(W)) / self.sigma_
        return pd.DataFrame(R.astype(np.float32), columns=[f"r_{s}" for s in self.sensors], index=df.index)

    def summary(self) -> dict:
        return {
            "model": f"StandardScaler -> PolynomialFeatures(degree={self.degree}) -> Ridge(alpha={self.alpha})",
            "inputs": W_VARS,
            "outputs": self.sensors,
            "r2_healthy_holdout": {k: round(v, 5) for k, v in self.r2_.items()},
            "residual_sigma": {s: float(v) for s, v in zip(self.sensors, self.sigma_)},
        }
