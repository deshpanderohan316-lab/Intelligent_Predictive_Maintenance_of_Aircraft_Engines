"""Unit tests for the preprocessing steps (synthetic data, no HDF5 needed).

Run:  python -m pytest ml/tests -q
"""
import numpy as np
import pandas as pd
import pytest

from ml.src.config import W_VARS, PreprocessConfig
from ml.src.preprocessing.aggregation import CycleAggregator
from ml.src.preprocessing.cleaning import QualityCounter, Winsorizer, clean_chunk
from ml.src.preprocessing.feature_engineering import build_features
from ml.src.preprocessing.feature_selection import FeatureSelector
from ml.src.preprocessing.labeling import add_rul_labels
from ml.src.preprocessing.operating_conditions import HealthyBaselineModel

RNG = np.random.default_rng(0)


def _one_hz(n_units=2, cycles=6, seconds=50):
    rows = []
    for u in range(1, n_units + 1):
        for c in range(1, cycles + 1):
            alt = RNG.uniform(0, 30000, seconds)
            mach = RNG.uniform(0.2, 0.8, seconds)
            df = pd.DataFrame({"alt": alt, "Mach": mach, "TRA": RNG.uniform(20, 90, seconds),
                               "T2": RNG.uniform(450, 520, seconds)})
            df["T48"] = 1500 + 0.002 * alt + 50 * mach + 2.0 * c  # degradation adds 2 per cycle
            df["Nc"] = 8000 + 100 * mach - 1.0 * c
            df["T_mod"] = -0.001 * c
            df["unit"], df["cycle"], df["Fc"] = u, c, 1
            df["hs"] = int(c <= 3)
            df["RUL"] = cycles - c
            df["dataset"], df["split"] = "DSX", "dev"
            rows.append(df)
    return pd.concat(rows, ignore_index=True)


def test_clean_chunk_removes_bad_rows():
    df = _one_hz()
    df.loc[0, "T48"] = np.nan
    df.loc[1, "Nc"] = np.inf
    df.loc[2, "T48"] = -5.0
    counter = QualityCounter()
    out = clean_chunk(df, W_VARS + ["T48", "Nc"], ["T48", "Nc"], counter)
    assert len(out) == len(df) - 3
    assert counter.nan_rows == 1 and counter.inf_rows == 1 and counter.non_physical_rows == 1


def test_baseline_removes_operating_condition_effect():
    df = _one_hz()
    model = HealthyBaselineModel(["T48", "Nc"], degree=2).fit(df[df["hs"] == 1])
    assert model.r2_["T48"] > 0.99
    r = model.residuals(df)
    # residual must increase with cycle (degradation), independent of flight condition
    per_cycle = r.groupby(df["cycle"])["r_T48"].mean()
    assert per_cycle.is_monotonic_increasing


def test_chunked_aggregation_is_exact():
    df = _one_hz()
    df["r_T48"] = df["T48"] - 1500
    full = CycleAggregator(["r_T48"], ["T48"], ["T_mod"])
    full.update(df)
    a = full.finalize()

    chunked = CycleAggregator(["r_T48"], ["T48"], ["T_mod"])
    for part in np.array_split(df, 7):  # chunk borders fall mid-flight
        chunked.update(part)
    b = chunked.finalize()

    pd.testing.assert_frame_equal(a, b, check_exact=False, rtol=1e-6)
    expected_std = df.groupby(["unit", "cycle"])["r_T48"].std(ddof=0).to_numpy()
    np.testing.assert_allclose(a["r_T48_std"].to_numpy(), expected_std, rtol=1e-5)


def _cycles():
    df = _one_hz()
    df["r_T48"] = df["T48"] - 1500
    agg = CycleAggregator(["r_T48"], ["T48"], ["T_mod"])
    agg.update(df)
    return add_rul_labels(agg.finalize())[0]


def test_rul_labels_consistent():
    cycles, info = add_rul_labels(_cycles().rename(columns={"RUL_raw": "RUL_file"}).drop(columns=["RUL", "engine_id", "health_stage"]))
    assert info["label_mismatch_rows"] == 0
    assert (cycles.groupby("engine_id")["RUL"].min() == 0).all()


def test_features_are_causal():
    """Changing a future cycle must not change features of earlier cycles."""
    cfg = PreprocessConfig(rolling_window=3, slope_window=4, baseline_cycles=2)
    cycles = _cycles()
    f1, cols = build_features(cycles, cfg)
    modified = cycles.copy()
    modified.loc[modified["cycle"] == 6, "r_T48_mean"] += 1000
    f2, _ = build_features(modified, cfg)
    early = f1["cycle"] < 6
    pd.testing.assert_frame_equal(f1.loc[early, cols], f2.loc[early, cols])


def test_winsorizer_uses_train_limits_only():
    train = pd.DataFrame({"a": np.arange(100.0)})
    test = pd.DataFrame({"a": [-50.0, 50.0, 500.0]})
    w = Winsorizer((0.01, 0.99)).fit(train)
    out = w.transform(test)
    assert out["a"].min() >= train["a"].quantile(0.01)
    assert out["a"].max() <= train["a"].quantile(0.99)


def test_selector_drops_redundant():
    y = pd.Series(np.arange(200.0))
    X = pd.DataFrame({"good": y + RNG.normal(0, 1, 200), "copy": y * 2 + RNG.normal(0, 1, 200),
                      "noise": RNG.normal(0, 1, 200), "const": 1.0})
    sel = FeatureSelector(correlation_threshold=0.95, max_features=5).fit(X, y)
    assert "const" in sel.dropped_["low_variance"]
    assert ("good" in sel.selected_) != ("copy" in sel.selected_)


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
