"""Step 7 - Feature selection (fitted on training engines only).

1. Variance filter       - drop (near) constant features.
2. Relevance ranking     - |Spearman rho| between feature and RUL (monotonic,
                           robust to non-linear sensor responses).
3. Redundancy pruning    - walk features from most to least relevant and drop
                           any whose |Pearson r| with an already-kept feature
                           exceeds ``correlation_threshold``.
4. Cap at ``max_features``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class FeatureSelector:
    def __init__(self, variance_threshold=1e-8, correlation_threshold=0.95, max_features=40):
        self.variance_threshold = variance_threshold
        self.correlation_threshold = correlation_threshold
        self.max_features = max_features
        self.selected_: list[str] = []
        self.relevance_: pd.Series | None = None
        self.dropped_: dict[str, list[str]] = {}

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "FeatureSelector":
        var = X.var()
        low_var = var[var <= self.variance_threshold].index.tolist()
        X = X.drop(columns=low_var)

        relevance = X.corrwith(y, method="spearman").abs().fillna(0).sort_values(ascending=False)
        corr = X.corr().abs()

        kept, redundant = [], []
        for f in relevance.index:
            if any(corr.loc[f, k] > self.correlation_threshold for k in kept):
                redundant.append(f)
            else:
                kept.append(f)
        capped = kept[self.max_features:]
        self.selected_ = kept[: self.max_features]
        self.relevance_ = relevance
        self.dropped_ = {"low_variance": low_var, "redundant": redundant, "over_cap": capped}
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return X[self.selected_]

    def summary(self) -> dict:
        return {
            "n_selected": len(self.selected_),
            "selected": [{"feature": f, "abs_spearman": round(float(self.relevance_[f]), 4)} for f in self.selected_],
            "dropped_counts": {k: len(v) for k, v in self.dropped_.items()},
            "dropped": self.dropped_,
        }
