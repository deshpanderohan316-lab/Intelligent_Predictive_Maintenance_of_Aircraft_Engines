"""Exploratory data analysis: static figures for the project report + JSON for the UI.

Run after preprocessing:  python -m ml.scripts.eda
"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ..config import FIGURES_DIR, INTERIM_DIR, PROCESSED_DIR, UI_DIR, W_VARS, XS_VARS, PreprocessConfig  # noqa: E402
from ..data.loader import find_dataset, sample_rows  # noqa: E402

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, MUTED, GRID = "#0b0b0b", "#898781", "#e1e0d9"

plt.rcParams.update({
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "axes.edgecolor": "#c3c2b7",
    "axes.labelcolor": "#52514e", "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "axes.prop_cycle": matplotlib.cycler(color=SERIES), "lines.linewidth": 1.6, "font.size": 10,
    "axes.titlecolor": INK, "axes.titleweight": "bold",
})


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / f"{name}.png", dpi=150)
    plt.close(fig)


def flight_envelope(cfg: PreprocessConfig) -> None:
    ds = find_dataset(cfg.datasets[0])
    df = sample_rows(ds, "dev", 20_000)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for fc, color in zip(sorted(df["Fc"].unique()), SERIES):
        s = df[df["Fc"] == fc]
        axes[0].scatter(s["Mach"], s["alt"], s=3, alpha=0.4, color=color, label=f"Flight class {fc}")
    axes[0].set(xlabel="Mach", ylabel="Altitude (ft)", title="Flight envelope by flight class")
    axes[0].legend(markerscale=4, frameon=False)
    axes[1].hist(df["TRA"], bins=60, color=SERIES[0])
    axes[1].set(xlabel="Throttle resolver angle (%)", ylabel="Seconds", title="Throttle distribution")
    axes[2].scatter(df["alt"], df["T48"], s=3, alpha=0.3, color=SERIES[0])
    axes[2].set(xlabel="Altitude (ft)", ylabel="T48 (°R)", title="Raw T48 is driven by flight condition")
    _save(fig, "01_flight_envelope")

    ui = df.iloc[:: max(1, len(df) // 1500)][["alt", "Mach", "TRA", "T2", "Fc"]].round(4)
    ui.to_json(UI_DIR / "flight_envelope.json", orient="records")


def raw_vs_residual(cycles: pd.DataFrame) -> None:
    """The key preprocessing figure: residualisation reveals degradation."""
    sensors = ["T48", "T50", "Nc", "Wf"]
    engines = sorted(cycles.loc[cycles["split"] == "dev", "engine_id"].unique())[:4]
    fig, axes = plt.subplots(2, len(sensors), figsize=(16, 6.5), sharex=True)
    for j, s in enumerate(sensors):
        for eid, color in zip(engines, SERIES):
            g = cycles[cycles["engine_id"] == eid]
            axes[0, j].plot(g["cycle"], g[f"raw_{s}_mean"], color=color, label=eid)
            axes[1, j].plot(g["cycle"], g[f"r_{s}_mean"], color=color, label=eid)
        axes[0, j].set_title(f"{s} - raw flight mean")
        axes[1, j].set_title(f"{s} - healthy-baseline residual (σ)")
        axes[1, j].set_xlabel("Flight cycle")
    axes[0, 0].legend(frameon=False, fontsize=8)
    _save(fig, "02_raw_vs_residual")


def health_parameters(cycles: pd.DataFrame) -> None:
    theta = [c for c in cycles.columns if c.startswith("theta_") and cycles[c].std() > 1e-6]
    eid = sorted(cycles["engine_id"].unique())[0]
    g = cycles[cycles["engine_id"] == eid]
    fig, ax = plt.subplots(figsize=(8, 4))
    for c, color in zip(theta, SERIES):
        ax.plot(g["cycle"], g[c], color=color, label=c.replace("theta_", ""))
    ax.set(title=f"Ground-truth component degradation ({eid}) - EDA only", xlabel="Flight cycle",
           ylabel="Health-parameter modifier")
    ax.legend(frameon=False, fontsize=8)
    _save(fig, "03_health_parameters")


def rul_and_lifetimes(cycles: pd.DataFrame) -> dict:
    life = cycles.groupby("engine_id").agg(cycles=("cycle", "max"), split=("split", "first"),
                                           onset=("hs", lambda h: int((h == 1).sum())))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    colors = [SERIES[0] if s == "dev" else SERIES[1] for s in life["split"]]
    axes[0].barh(life.index, life["cycles"], color=colors)
    axes[0].barh(life.index, life["onset"], color="#c3c2b7", height=0.35, label="healthy (hs=1) cycles")
    axes[0].set(title="Engine lifetime (blue = train, orange = test)", xlabel="Cycles to failure")
    axes[0].legend(frameon=False)
    axes[1].hist(cycles["RUL_raw"], bins=30, color=SERIES[0])
    axes[1].set(title="RUL label distribution (cycle level)", xlabel="RUL (cycles)", ylabel="Count")
    _save(fig, "04_rul_lifetimes")
    return life.reset_index().to_dict(orient="records")


def correlations(train: pd.DataFrame) -> dict:
    feats = [c for c in train.columns if c not in
             {"dataset", "split", "unit", "cycle", "engine_id", "Fc", "hs", "RUL", "RUL_raw", "health_stage"}]
    corr = train[feats + ["RUL"]].corr(method="spearman")["RUL"].drop("RUL").sort_values(key=abs, ascending=False)
    top = corr.head(15)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(top.index[::-1], top.values[::-1], color=[SERIES[0] if v > 0 else SERIES[1] for v in top.values[::-1]])
    ax.axvline(0, color="#c3c2b7")
    ax.set(title="Top selected features: Spearman ρ with RUL", xlabel="ρ")
    _save(fig, "05_feature_correlation")

    sub = train[top.index[:10]].corr()
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(sub, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(sub)), sub.columns, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(sub)), sub.columns, fontsize=8)
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.8)
    ax.set_title("Correlation between top-10 features")
    _save(fig, "06_feature_heatmap")
    return {k: round(float(v), 4) for k, v in corr.items()}


def run(cfg: PreprocessConfig | None = None) -> None:
    cfg = cfg or PreprocessConfig()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    cycles = pd.read_parquet(INTERIM_DIR / "cycles.parquet")
    train = pd.read_parquet(PROCESSED_DIR / "train.parquet")

    flight_envelope(cfg)
    raw_vs_residual(cycles)
    health_parameters(cycles)
    lifetimes = rul_and_lifetimes(cycles)
    corr = correlations(train)

    summary = {
        "n_engines": int(cycles["engine_id"].nunique()),
        "n_cycles": int(len(cycles)),
        "lifetimes": lifetimes,
        "rul_histogram": np.histogram(cycles["RUL_raw"], bins=20)[0].tolist(),
        "rul_bins": np.histogram(cycles["RUL_raw"], bins=20)[1].round(1).tolist(),
        "feature_rul_spearman": corr,
        "flight_class_counts": cycles["Fc"].value_counts().sort_index().to_dict(),
        "sensors": XS_VARS,
        "conditions": W_VARS,
    }
    (UI_DIR / "eda_summary.json").write_text(json.dumps(summary, default=int), encoding="utf-8")
    print(f"EDA figures -> {FIGURES_DIR}")
