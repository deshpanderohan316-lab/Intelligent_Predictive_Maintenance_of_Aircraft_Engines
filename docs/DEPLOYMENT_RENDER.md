# Deploying on Render (Docker)

## How it works

One Docker image runs the whole project as **one Render web service**:

```
Dockerfile
 ├─ Stage 1 (node:20)      npm ci → next build (NEXT_OUTPUT=export) → static site in frontend/out
 └─ Stage 2 (python:3.10)  pip install backend/requirements.txt
                           + backend code + trained model + processed data + the static site
                           gunicorn → Flask on $PORT
                               ├─ /api/*          live API (real model predictions)
                               └─ everything else the dashboard pages
```

Because the site and the API share one URL, there's no proxy and no CORS to configure. The
deployed site uses the **live Flask API**, including real-time predictions.

| File | Purpose |
|---|---|
| `Dockerfile` | multi-stage build described above |
| `.dockerignore` | keeps the 28 GB dataset, `.venv`, `node_modules` etc. out of the image |
| `render.yaml` | Render Blueprint: creates the web service automatically |
| `backend/requirements.txt` | runtime libraries, **pinned to the versions the model was trained with** |
| `backend/app.py` | serves `frontend/out` when it exists, plus the `/api` routes |

The image needs the trained model and processed data, so these files are committed to git
(un-ignored in `.gitignore`):
`artifacts/models/best_model.joblib` (~26 MB), `data/processed/train.parquet`,
`data/processed/test.parquet`, plus `artifacts/reports/`, `artifacts/ui/`, `artifacts/figures/`.

---

## Steps

### 1. (Optional) Choose which model to publish
The image ships whatever model was trained last (currently DS01 + DS02 + DS03, Extra Trees).
For the DS02-only results used in the study notes:
```powershell
.venv\Scripts\python -m ml.scripts.run_all
```

### 2. Push to GitHub
```powershell
git add .
git commit -m "Add Docker and Render deployment"
git push
```
Check that the model was included:
```powershell
git ls-files artifacts/models data/processed
```
It should list `best_model.joblib`, `train.parquet` and `test.parquet`.

### 3. Create the service on Render

**Option A: Blueprint (uses `render.yaml`, easiest)**
1. Go to https://dashboard.render.com and sign in with GitHub.
2. **New + → Blueprint**, then select the repository.
3. Render reads `render.yaml` and shows the service **turbo-rul** (Docker, free plan). Click **Apply**.

**Option B: Manual web service**
1. **New + → Web Service**, then select the repository.
2. **Language / Runtime:** `Docker` (Render detects the `Dockerfile`).
3. **Branch:** `main` · **Root Directory:** *leave empty* · **Instance type:** Free.
4. **Advanced → Health Check Path:** `/api/health`.
5. No environment variables are needed (Render sets `PORT` itself).
6. Click **Create Web Service**.

### 4. Wait for the first build (~5–10 minutes)
The log shows the Node stage (`npm ci`, `next build`), then the Python stage (`pip install`), then
`Listening at: http://0.0.0.0:10000`. The service then goes **Live** and the URL looks like
`https://turbo-rul.onrender.com`.

### 5. Check it
* `https://<your-app>.onrender.com/`: the dashboard
* `https://<your-app>.onrender.com/api`: list of API endpoints
* `https://<your-app>.onrender.com/api/health` should return `{"status":"ok"}`

---

## Updating
Every push to `main` rebuilds and redeploys (`autoDeploy: true`). After retraining:
```powershell
.venv\Scripts\python -m ml.scripts.run_all
git add artifacts data/processed
git commit -m "Retrained model"
git push
```
If you upgrade scikit-learn / LightGBM / pandas locally before retraining, update the pins in
`backend/requirements.txt` to match (`.venv\Scripts\pip freeze`). Otherwise the saved model may not
load in the container.

## Run the same image on your own machine (optional, needs Docker Desktop)
```powershell
docker build -t turbo-rul .
docker run -p 10000:10000 turbo-rul
# open http://localhost:10000
```

## Free-plan notes
* The service **sleeps after ~15 minutes without traffic**. The first visit afterwards takes
  ~30–60 s to wake up. Open the URL a minute before a demo.
* 512 MB RAM: gunicorn runs 1 worker × 4 threads to stay well inside it.

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| Build fails at `COPY artifacts/models/best_model.joblib` | The model isn't on GitHub. Run the step 2 checks, then `git add -f artifacts/models/best_model.joblib` |
| Build fails at `npm ci` | `frontend/package-lock.json` is missing from git; commit it |
| Deploy fails health check / "No open ports detected" | Look at the log for a Python error at startup (usually the model failing to load: version pins, see above) |
| Pages load but say "Flask API is not running" | The frontend was built without `NEXT_OUTPUT=export`; make sure you deploy with this `Dockerfile` |
| `/api/...` returns 503 "not found - run …" | `artifacts/reports` or `artifacts/ui` JSON files are missing from git |
| Out of memory | Upgrade the instance, or train a smaller model (fewer trees) |
