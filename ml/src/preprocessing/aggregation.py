"""Step 4 - Temporal aggregation: 1 Hz samples -> one row per flight cycle.

A flight lasts 1-8 hours (thousands of 1 Hz samples) while degradation evolves
from flight to flight.  RUL is also defined per cycle.  We therefore compress
every flight of every engine into a fixed-length feature vector:

* residual mean & std of each sensor  (health signal)
* raw sensor mean                     (kept for EDA / before-after plots)
* flight-profile descriptors          (duration, max altitude, mean Mach, ...)
* labels: RUL, health state hs, flight class Fc
* true health parameters theta        (for EDA only, never model input)

Because the files are streamed in chunks, a flight may be split across two
chunks.  We therefore accumulate *sufficient statistics* (count, sum, sum of
squares, min, max) per chunk and combine them at the end - this gives exact
means / standard deviations with constant memory.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

KEYS = ["dataset", "split", "unit", "cycle"]


class CycleAggregator:
    def __init__(
        self,
        residual_cols: list[str],
        raw_sensor_cols: list[str],
        theta_cols: list[str],
    ):
        self.residual_cols = residual_cols
        self.raw_sensor_cols = raw_sensor_cols
        self.theta_cols = theta_cols
        self.mean_cols = residual_cols + raw_sensor_cols + theta_cols + ["Mach", "TRA", "T2", "alt"]
        self._parts: list[pd.DataFrame] = []

    def update(self, df: pd.DataFrame) -> None:
        g = df.groupby(KEYS, sort=False, observed=True)
        sums = g[self.mean_cols].sum().add_suffix("__sum")
        sq = (df[self.residual_cols] ** 2).groupby([df[k] for k in KEYS], sort=False, observed=True).sum().add_suffix("__sq")
        extra = g.agg(
            n=("alt", "size"),
            alt__max=("alt", "max"),
            Mach__max=("Mach", "max"),
            TRA__max=("TRA", "max"),
            Fc__max=("Fc", "max"),
            hs__min=("hs", "min"),
            RUL__min=("RUL", "min"),
        )
        self._parts.append(pd.concat([sums, sq, extra], axis=1))

    def finalize(self) -> pd.DataFrame:
        parts = pd.concat(self._parts)
        sum_like = [c for c in parts.columns if c.endswith(("__sum", "__sq")) or c == "n"]
        combined = parts.groupby(level=KEYS, sort=True).agg(
            {**{c: "sum" for c in sum_like},
             **{c: ("max" if c.endswith("__max") else "min") for c in parts.columns if c not in sum_like}}
        )
        n = combined["n"]
        out = pd.DataFrame(index=combined.index)
        for c in self.residual_cols:
            mean = combined[f"{c}__sum"] / n
            var = (combined[f"{c}__sq"] / n - mean ** 2).clip(lower=0)
            out[f"{c}_mean"] = mean
            out[f"{c}_std"] = np.sqrt(var)
        for c in self.raw_sensor_cols:
            out[f"raw_{c}_mean"] = combined[f"{c}__sum"] / n
        for c in self.theta_cols:
            out[f"theta_{c}"] = combined[f"{c}__sum"] / n

        # Flight-profile (operating condition) descriptors
        out["op_duration_s"] = n
        out["op_alt_max"] = combined["alt__max"]
        out["op_alt_mean"] = combined["alt__sum"] / n
        out["op_mach_mean"] = combined["Mach__sum"] / n
        out["op_mach_max"] = combined["Mach__max"]
        out["op_tra_mean"] = combined["TRA__sum"] / n
        out["op_tra_max"] = combined["TRA__max"]
        out["op_t2_mean"] = combined["T2__sum"] / n

        out["Fc"] = combined["Fc__max"].astype(int)
        out["hs"] = combined["hs__min"].astype(int)
        out["RUL_file"] = combined["RUL__min"].astype(int)
        self._parts = []
        return out.reset_index()
