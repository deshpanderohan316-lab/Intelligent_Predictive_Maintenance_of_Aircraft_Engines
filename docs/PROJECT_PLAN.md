# Project Plan: Intelligent Predictive Maintenance of Aircraft Engines

**Domain:** Aerospace  **Dataset:** NASA N-CMAPSS (Turbofan Engine Degradation Simulation-2)
**Goal:** Estimate the Remaining Useful Life (RUL, in flight cycles) of turbofan engines from sensor
data and turn it into a maintenance decision.

---

## 1. Problem framing

| Item | Decision |
|---|---|
| Task | Supervised **regression**: target = RUL (remaining flight cycles) per flight |
| Unit of prediction | one engine after one flight (cycle) |
| Inputs | flight conditions **W** (alt, Mach, TRA, T2) + 14 physical sensors **X_s** |
| Not used as inputs | virtual sensors **X_v** (optional flag), true health parameters **θ** (would leak the answer, so they are used for EDA only) |
| Split | official N-CMAPSS dev/test engines; validation = **GroupKFold by engine** |
| Metrics | MAE, RMSE, R² (from the abstract) + NASA asymmetric score (penalises late predictions) |

### Dataset at a glance (DS02, the reference sub-dataset)

| | Development | Test |
|---|---|---|
| Engines | 6 (units 2, 5, 10, 16, 18, 20) | 3 (units 11, 14, 15) |
| 1 Hz rows | 5,263,447 | 1,253,743 |
| Flight cycles | 446 | 202 |
| Lifetime | 63–89 cycles | 59–76 cycles |

Ten sub-datasets (DS01 to DS08d) are in `data_set/`. **`N-CMAPSS_DS08d-010.h5` is truncated** (corrupt
download). The pipeline detects this and skips the file. Re-download it if you need it.

---

## 2. Data preprocessing (main focus)

Code: [`ml/src/preprocessing/`](../ml/src/preprocessing). Orchestrator: [`pipeline.py`](../ml/src/preprocessing/pipeline.py).
Every step writes statistics to `artifacts/reports/preprocessing_report.json`, which drives the
animated pipeline page in the UI.

```
raw HDF5 (1 Hz, ~1 GB per split)
  │ 1  Inventory          verify files, row counts, variable groups
  │ 2  Cleaning           NaN / Inf / non-physical readings removed (streamed, 500k-row chunks)
  │ 3  Op-condition norm. healthy-baseline model  sensor = f(alt, Mach, TRA, T2)  →  residual r
  │ 4  Aggregation        1 Hz → 1 row per flight (exact mean/std from chunk-merged sums)
  │ 5  Labelling          RUL check, optional cap, health stage
  │ 6  Feature eng.       causal rolling mean/std, EWMA, slope, drift-from-own-baseline
  │ 7  Split              by engine (no leakage between cycles of the same engine)
  │ 8  Winsorising        clip to train 0.5–99.5 %
  │ 9  Feature selection  variance → |Spearman| with RUL → drop |r| > 0.95 → top 40
  │ 10 Scaling            StandardScaler (fit on train)
  ▼
data/processed/{train,test}.parquet  +  artifacts/preprocessing/*.joblib
```

### Why each step

1. **Memory-safe loading** ([`loader.py`](../ml/src/data/loader.py)). Each file holds 2.4–3.7 GB of
   float64 data. The NASA example notebook loads everything at once. We stream row slices with
   `h5py` and downcast to float32, so peak RAM stays in the hundreds of MB.
2. **Cleaning** ([`cleaning.py`](../ml/src/preprocessing/cleaning.py)). Rows with missing or infinite
   values are removed. So are physically impossible ones (every N-CMAPSS sensor is a temperature,
   pressure, speed or flow, so each must be > 0). Every removal is counted in the report. On DS02,
   0 rows were removed and 0 duplicate (engine, cycle) keys were found.
3. **Operating-condition normalisation** ([`operating_conditions.py`](../ml/src/preprocessing/operating_conditions.py)).
   This is the most important step. Raw sensor values mostly reflect *how the aircraft is
   flying*: on healthy data, flight conditions explain **> 99.9 %** of sensor variance. We fit a
   cubic polynomial ridge model on healthy (`hs = 1`) seconds and keep the standardised residual
   `r = (x − x̂) / σ_healthy`. A healthy engine reads about 0 in every flight condition, and the
   residual grows as the engine degrades (see `artifacts/figures/02_raw_vs_residual.png`).
4. **Per-flight aggregation** ([`aggregation.py`](../ml/src/preprocessing/aggregation.py)). Degradation
   and RUL change from flight to flight, not second to second. We compress about 10,000 seconds per
   flight into one row: mean and std of each residual, plus flight-profile descriptors (duration,
   max altitude, mean Mach/TRA/T2). We merge count/sum/sum² across chunks, so the statistics are exact
   even when a flight is split between two chunks (this is unit-tested).
5. **Labels** ([`labeling.py`](../ml/src/preprocessing/labeling.py)). The pipeline checks that
   `RUL = last cycle − cycle` (0 mismatches). It supports a piece-wise RUL cap (`--rul-cap`) and derives
   health stages: healthy > 30, warning 11–30, critical ≤ 10 cycles.
6. **Time-series features** ([`feature_engineering.py`](../ml/src/preprocessing/feature_engineering.py)).
   For each engine, every residual signal gets a rolling mean (denoising), a rolling std
   (instability), an EWMA (recent trend), a rolling slope (degradation rate) and a drift from the
   engine's own first 5 cycles (removes engine-to-engine offsets). All windows look **backwards only**
   (unit-tested), so the model can run on a live engine. This gives 107 features.
7. **Leakage control.** The baseline model, winsoriser, feature selector and scaler are all fitted
   on training engines only and then applied to test engines.
8. **Selection and scaling** ([`feature_selection.py`](../ml/src/preprocessing/feature_selection.py)).
   Starting from 107 features, 56 are dropped as redundant and 11 more fall beyond the cap, leaving
   40. Z-score scaling is needed for SVR, KNN, MLP and Ridge.

---

## 3. Exploratory data analysis

[`ml/src/eda/eda.py`](../ml/src/eda/eda.py) writes figures to `artifacts/figures/`:
flight envelope by flight class, raw vs residual sensor trends, ground-truth health parameters θ,
engine lifetimes and RUL distribution, and feature/RUL correlations with a heatmap.

## 4. Modelling

[`ml/src/models/`](../ml/src/models). We compare Linear, Ridge, KNN, SVR, Random Forest, Extra Trees,
HistGradientBoosting, MLP and LightGBM. The model is selected on **CV RMSE** (GroupKFold by engine),
and the test engines are scored once.

Results on DS02 (test engines):

| Model | CV RMSE | Test RMSE | Test MAE | Test R² |
|---|---|---|---|---|
| Linear Regression | 10.21 | 14.92 | 13.11 | 0.446 |
| SVR | 10.59 | 13.82 | 11.75 | 0.524 |
| MLP | 9.11 | 9.58 | 7.54 | 0.772 |
| Random Forest | 7.36 | 8.25 | 6.35 | 0.831 |
| Extra Trees | 7.47 | **8.04** | **6.01** | **0.839** |
| LightGBM (selected by CV) | **7.23** | 9.07 | 6.55 | 0.795 |

With DS01 + DS03 combined (more training engines), Extra Trees reaches a test RMSE of 7.88 and an
R² of 0.889.

## 5. Application

* **Flask API** ([`backend/`](../backend)) serves the artifacts and runs inference:
  `/api/overview`, `/api/preprocessing`, `/api/eda`, `/api/engines/<id>`, `/api/models`,
  `POST /api/predict {engine_id, cycle}`.
* **Next.js UI** ([`frontend/`](../frontend)) uses Framer Motion animations and Recharts:
  * *Overview*: animated turbine hero, count-up KPIs, project workflow.
  * *Preprocessing*: an auto-playing 10-step pipeline stepper, a 1 Hz flight trace and an
    interactive raw vs residual comparison.
  * *EDA*: flight envelope, lifetimes, RUL distribution, correlations and θ degradation.
  * *Models*: animated metric switcher, results table and feature importance.
  * *Predict*: an engine selector and cycle slider, an animated RUL gauge, the health status with a
    maintenance action, and predicted vs actual RUL.

---

## 6. Timeline (suggested, 8 weeks)

| Week | Work | Deliverable |
|---|---|---|
| 1 | Literature + dataset study, environment setup | problem statement, data dictionary |
| 2 | Loader, data-quality checks, EDA | EDA figures |
| 3 | Operating-condition normalisation, aggregation | `cycles.parquet`, before/after plots |
| 4 | Labels, feature engineering, selection, scaling | `train/test.parquet`, preprocessing report |
| 5 | Baseline + ensemble models, CV protocol | model comparison table |
| 6 | Tuning, multi-dataset training, error analysis | final model |
| 7 | Flask API + Next.js UI | working demo |
| 8 | Report, slides, testing | final submission |

## 7. Possible extensions

* Hyper-parameter search (Optuna) with GroupKFold.
* Train on all sub-datasets (DS01–DS08c) for better generalisation across failure modes.
* Sequence models (1D-CNN / LSTM) on windows of cycle-level features, compared against these classical models.
* Uncertainty: quantile regression (LightGBM `objective="quantile"`) to give an RUL interval.
* Use `hs` to train a classifier for onset of degradation, then predict RUL only after onset.
