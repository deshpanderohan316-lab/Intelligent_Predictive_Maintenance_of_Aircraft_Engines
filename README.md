# Intelligent Predictive Maintenance of Aircraft Engines

Remaining Useful Life (RUL) estimation for turbofan engines on the **NASA N-CMAPSS** dataset, using
classical machine learning. The project includes a **Flask** API and an animated **Next.js** dashboard.

See **[docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)** for the full plan, a detailed explanation of the
preprocessing, and the results.

**New to the project?** Read **[project_explained/00_START_HERE.md](project_explained/00_START_HERE.md)**.
It covers the domain, the full mathematics, a line-by-line code walkthrough and viva questions.

## Folder structure

```
├── data_set/                    raw N-CMAPSS .h5 files (not in git)
├── data/
│   ├── interim/cycles.parquet   1 row per (engine, flight) after aggregation
│   └── processed/               model-ready train/test matrices
├── ml/
│   ├── src/
│   │   ├── config.py            paths, variable names, all hyper-parameters
│   │   ├── data/loader.py       chunked, memory-safe HDF5 reader
│   │   ├── preprocessing/       ★ cleaning → op-condition residuals → aggregation →
│   │   │                          labels → features → selection → scaling (pipeline.py)
│   │   ├── eda/eda.py           report figures + UI summaries
│   │   └── models/              registry, metrics (MAE/RMSE/R²/NASA), training
│   ├── scripts/                 CLI entry points (preprocess, eda, train, run_all)
│   ├── notebooks/               scratch analysis
│   └── tests/                   unit tests for preprocessing
├── artifacts/
│   ├── preprocessing/           fitted baseline model, scaler, selector
│   ├── models/best_model.joblib
│   ├── reports/                 preprocessing_report.json, metrics.json
│   ├── figures/                 EDA PNGs
│   └── ui/                      small JSON payloads for the dashboard
├── backend/                     Flask API (app.py, api/routes.py, services/)
├── frontend/                    Next.js 14 + Tailwind + Framer Motion + Recharts
└── docs/PROJECT_PLAN.md
```

## Run it

**1. Python environment** (Python 3.10 or newer)

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

**2. ML pipeline** (DS02 takes about 30 s end to end)

```bash
python -m ml.scripts.run_all                      # preprocess → EDA → train
# or step by step / other sub-datasets:
python -m ml.scripts.preprocess --datasets DS01-005 DS02-006 DS03-012 --rul-cap 65
python -m ml.scripts.eda
python -m ml.scripts.train
python -m pytest ml/tests -q
```

**3. Flask API**, served at http://localhost:5000

```bash
python -m backend.app
```

**4. Next.js UI**, served at http://localhost:3000 (requires Node.js 18 or newer)

```bash
cd frontend
npm install
npm run dev
```

The UI proxies `/api/*` to Flask (see `frontend/next.config.mjs`; you can override the address with `FLASK_URL`).

**5. Deploy to Vercel**: see **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**. In short:
`python -m backend.export_static` → push to GitHub → import the repo in Vercel with
**Root Directory = `frontend`**.

## Notes

* `data_set/N-CMAPSS_DS08d-010.h5` is truncated. The pipeline reports it and skips it.
* The health parameters θ (`T_*` in the files) are used **only** for EDA, because they encode the
  ground-truth degradation.
