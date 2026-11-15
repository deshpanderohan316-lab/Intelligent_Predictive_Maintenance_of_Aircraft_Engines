"""Step 2 - Data quality checks and cleaning.

Two levels of cleaning are applied:

* **1 Hz level** (inside the streaming loop): remove rows with missing /
  infinite values and physically impossible readings (non-positive pressure,
  temperature, speed or fuel flow), optionally drop ground-idle samples.
* **Cycle level** (after aggregation): detect duplicated (engine, cycle) keys,
  drop constant columns, and winsorise outliers with train-set percentiles.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# Every physical sensor in N-CMAPSS is a temperature, pressure, speed or flow.
# All of them must be strictly positive in a running engine.
POSITIVE_PREFIXES = ("T", "P", "N", "W")


@dataclass
class QualityCounter:
    """Accumulates data-quality statistics across streamed chunks."""

    rows_in: int = 0
    rows_out: int = 0
    nan_rows: int = 0
    inf_rows: int = 0
    non_physical_rows: int = 0
    low_altitude_rows: int = 0
    nan_per_column: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "rows_in": self.rows_in,
            "rows_out": self.rows_out,
            "rows_removed": self.rows_in - self.rows_out,
            "removed_pct": round(100 * (self.rows_in - self.rows_out) / max(self.rows_in, 1), 4),
            "nan_rows": self.nan_rows,
            "inf_rows": self.inf_rows,
            "non_physical_rows": self.non_physical_rows,
            "low_altitude_rows": self.low_altitude_rows,
            "nan_per_column": {k: v for k, v in self.nan_per_column.items() if v},
        }


def clean_chunk(
    df: pd.DataFrame,
    numeric_cols: list[str],
    sensor_cols: list[str],
    counter: QualityCounter,
    min_altitude_ft: float = 0.0,
) -> pd.DataFrame:
    """Clean a 1 Hz chunk in place-free fashion and update ``counter``."""
    counter.rows_in += len(df)
    values = df[numeric_cols].to_numpy()

    nan_mask = np.isnan(values)
    for col, n in zip(numeric_cols, nan_mask.sum(axis=0)):
        counter.nan_per_column[col] = counter.nan_per_column.get(col, 0) + int(n)
    nan_rows = nan_mask.any(axis=1)
    inf_rows = np.isinf(values).any(axis=1)

    positive_cols = [c for c in sensor_cols if c.startswith(POSITIVE_PREFIXES)]
    non_physical = (df[positive_cols].to_numpy() <= 0).any(axis=1)

    low_alt = (df["alt"].to_numpy() < min_altitude_ft) if min_altitude_ft > 0 else np.zeros(len(df), bool)

    counter.nan_rows += int(nan_rows.sum())
    counter.inf_rows += int(inf_rows.sum())
    counter.non_physical_rows += int((non_physical & ~nan_rows & ~inf_rows).sum())
    counter.low_altitude_rows += int(low_alt.sum())

    keep = ~(nan_rows | inf_rows | non_physical | low_alt)
    out = df.loc[keep]
    counter.rows_out += len(out)
    return out


# --------------------------------------------------------------------------- #
# Cycle-level cleaning
# --------------------------------------------------------------------------- #
def check_duplicate_keys(df: pd.DataFrame, keys: list[str]) -> int:
    return int(df.duplicated(subset=keys).sum())


def find_constant_columns(df: pd.DataFrame, cols: list[str], tol: float = 1e-10) -> list[str]:
    std = df[cols].std(numeric_only=True)
    return std[std.fillna(0) <= tol].index.tolist()


class Winsorizer:
    """Clip each feature to [q_low, q_high] percentiles learned on training data.

    Fitting on train only prevents information from the test engines leaking
    into the preprocessing.
    """

    def __init__(self, quantiles: tuple[float, float] = (0.005, 0.995)):
        self.quantiles = quantiles
        self.lower_: pd.Series | None = None
        self.upper_: pd.Series | None = None

    def fit(self, X: pd.DataFrame) -> "Winsorizer":
        self.lower_ = X.quantile(self.quantiles[0])
        self.upper_ = X.quantile(self.quantiles[1])
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return X.clip(lower=self.lower_[X.columns], upper=self.upper_[X.columns], axis=1)

    def n_clipped(self, X: pd.DataFrame) -> int:
        lo, hi = self.lower_[X.columns], self.upper_[X.columns]
        return int(((X < lo) | (X > hi)).to_numpy().sum())
