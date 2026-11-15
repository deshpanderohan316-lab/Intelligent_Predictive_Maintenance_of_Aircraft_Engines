"""Step 6 - Time-series feature engineering on the cycle-level data.

All features are **causal**: the value at cycle *t* only uses cycles <= t of the
same engine, so the model can be deployed on a live engine.

For every residual-mean sensor signal ``x`` we add
* ``roll_mean``  - rolling mean over the last ``rolling_window`` cycles (denoising)
* ``roll_std``   - rolling standard deviation (instability)
* ``ewm``        - exponentially weighted mean (recent cycles weigh more)
* ``slope``      - least-squares slope over the last ``slope_window`` cycles (degradation rate)
* ``delta``      - drift from the engine's own baseline = mean of its first
                   ``baseline_cycles`` cycles (removes engine-to-engine offsets)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import PreprocessConfig

ENGINE = "engine_id"


def _rolling_slope(x: pd.Series, window: int) -> pd.Series:
    t = pd.Series(np.arange(len(x), dtype=float), index=x.index)
    cov = x.rolling(window, min_periods=2).cov(t)
    var = t.rolling(window, min_periods=2).var()
    return (cov / var).fillna(0.0)


def _engine_features(g: pd.DataFrame, cols: list[str], cfg: PreprocessConfig) -> pd.DataFrame:
    g = g.sort_values("cycle")
    feats = {}
    for c in cols:
        x = g[c]
        feats[f"{c}__roll_mean"] = x.rolling(cfg.rolling_window, min_periods=1).mean()
        feats[f"{c}__roll_std"] = x.rolling(cfg.rolling_window, min_periods=2).std().fillna(0.0)
        feats[f"{c}__ewm"] = x.ewm(alpha=cfg.ewm_alpha, adjust=False).mean()
        feats[f"{c}__slope"] = _rolling_slope(x, cfg.slope_window)
        # causal baseline: expanding mean until baseline_cycles are available, then frozen
        base = x.expanding().mean()
        frozen = base.iloc[min(cfg.baseline_cycles, len(x)) - 1]
        base.iloc[cfg.baseline_cycles:] = frozen
        feats[f"{c}__delta"] = x - base
    return pd.DataFrame(feats, index=g.index)


def build_features(df: pd.DataFrame, cfg: PreprocessConfig) -> tuple[pd.DataFrame, list[str]]:
    resid_mean_cols = [c for c in df.columns if c.startswith("r_") and c.endswith("_mean")]
    resid_std_cols = [c for c in df.columns if c.startswith("r_") and c.endswith("_std")]
    op_cols = [c for c in df.columns if c.startswith("op_")]

    df = df.sort_values([ENGINE, "cycle"]).copy()
    ts = pd.concat([_engine_features(g, resid_mean_cols, cfg) for _, g in df.groupby(ENGINE, sort=False)])
    df = df.join(ts)
    df["age_cycles"] = df["cycle"].astype(float)  # flights flown so far (known in service)

    ts_cols = ts.columns.tolist()
    feature_cols = ["age_cycles"] + op_cols + resid_mean_cols + resid_std_cols + ts_cols
    return df, feature_cols
