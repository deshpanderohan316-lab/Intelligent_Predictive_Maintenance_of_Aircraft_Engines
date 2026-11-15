"""Step 5 - Target construction (Remaining Useful Life labels).

N-CMAPSS provides RUL per sample.  After aggregation we:

1. verify it equals ``(last cycle of the engine) - cycle`` (run-to-failure data),
2. optionally cap it (piece-wise linear target) - early in life the engine is
   healthy and the exact RUL is not observable from sensors,
3. derive a maintenance-oriented health stage used by the UI.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ENGINE_KEY = ["dataset", "unit"]


def add_rul_labels(df: pd.DataFrame, rul_cap: int | None = None) -> tuple[pd.DataFrame, dict]:
    df = df.sort_values(ENGINE_KEY + ["cycle"]).copy()
    df["engine_id"] = df["dataset"] + "_u" + df["unit"].astype(str).str.zfill(2)
    eol = df.groupby(ENGINE_KEY)["cycle"].transform("max")
    df["RUL_computed"] = (eol - df["cycle"]).astype(int)
    mismatch = int((df["RUL_computed"] != df["RUL_file"]).sum())

    df["RUL_raw"] = df["RUL_file"]
    df["RUL"] = df["RUL_raw"].clip(upper=rul_cap) if rul_cap else df["RUL_raw"]
    df["health_stage"] = pd.cut(
        df["RUL_raw"], bins=[-1, 10, 30, np.inf], labels=["critical", "warning", "healthy"]
    ).astype(str)

    info = {
        "rul_cap": rul_cap,
        "label_mismatch_rows": mismatch,
        "rul_min": int(df["RUL_raw"].min()),
        "rul_max": int(df["RUL_raw"].max()),
        "rul_mean": round(float(df["RUL_raw"].mean()), 2),
        "engines": int(df["engine_id"].nunique()),
        "cycles_per_engine": df.groupby("engine_id")["cycle"].max().astype(int).to_dict(),
        "health_stage_counts": df["health_stage"].value_counts().to_dict(),
    }
    return df.drop(columns=["RUL_computed", "RUL_file"]), info
