# Deploying the dashboard on Vercel

## How it works

Vercel hosts the **Next.js dashboard**. The Python backend (pandas, scikit-learn, LightGBM, …,
about 340 MB of libraries) is too large for a Vercel Python function, so the deployed site uses
**static data** instead:

```
local machine                                         Vercel
─────────────                                         ──────
ML pipeline → artifacts → Flask app ──export──► frontend/public/data/*.json ──► Next.js site
                                (python -m backend.export_static)            (reads /data/*.json)
```

* `backend/export_static.py` calls every Flask endpoint once and saves the answers as JSON. That
  includes a **prediction for every flight of every engine**, so the Predict page works exactly like
  the live API.
* `frontend/.env.production` sets `NEXT_PUBLIC_STATIC_DATA=1`, so **production builds** read
  `/data/*.json`. Local `npm run dev` still uses the live Flask API.

---

## One-time deployment

### 1. (Optional) Choose which results to publish
The exported data comes from whatever model was trained last. To publish the DS02-only results:
```powershell
.venv\Scripts\python -m ml.scripts.run_all
```
(or `python -m ml.scripts.preprocess --datasets DS01-005 DS02-006 DS03-012`, then `eda` and `train`, for the combined model).

### 2. Export the static data
```powershell
.venv\Scripts\python -m backend.export_static
```
This writes about 2–3 MB of JSON to `frontend/public/data/`.

### 3. Test the production build locally (optional but recommended)
```powershell
cd frontend
npm run build
npx next start      # open http://localhost:3000. It works even with Flask stopped
cd ..
```

### 4. Push to GitHub
```powershell
git add .
git commit -m "Add static export for Vercel deployment"
git push
```
`frontend/public/data/` must be committed (it is not git-ignored). The large `.h5` files, `.venv`,
`node_modules` and `project_explained/` stay out of git.

### 5. Create the Vercel project
1. Go to https://vercel.com and **sign in with GitHub**.
2. **Add New… → Project**, then **Import** the repository
   `Intelligent_Predictive_Maintenance_of_Aircraft_Engines`.
   (If it isn't listed: **Adjust GitHub App Permissions** and give Vercel access to the repo.)
3. On the configuration screen:
   * **Root Directory** → click **Edit** → select **`frontend`**. *(This is the important setting:
     the Next.js app is in that sub-folder.)*
   * **Framework Preset:** Next.js (detected automatically).
   * Build / Output / Install commands: leave the defaults.
   * Environment variables: **none needed** (`.env.production` handles it).
4. Click **Deploy**. After ~1–2 minutes you get a URL like
   `https://intelligent-predictive-maintenance.vercel.app`.

### Alternative: deploy from the terminal (Vercel CLI)
```powershell
npm install -g vercel
cd frontend
vercel          # first time: log in, link the project (answer the prompts); creates a preview URL
vercel --prod   # production URL
```

---

## Updating the live site
Every `git push` to `main` redeploys automatically. After retraining:
```powershell
.venv\Scripts\python -m ml.scripts.run_all          # if you changed the model/data
.venv\Scripts\python -m backend.export_static       # refresh the JSON
git add frontend/public/data
git commit -m "Update exported results"
git push
```

## Troubleshooting
| Symptom | Fix |
|---|---|
| Build fails: "No Next.js version detected" | Root Directory isn't set to `frontend` (Project → Settings → General → Root Directory) |
| Page shows "Static data not found …" | `frontend/public/data` wasn't exported or committed; repeat steps 2 and 4 |
| Live site shows old numbers | Re-export (step 2) and push |
| Site shows "Could not reach the Flask API" | The build didn't pick up static mode. Check that `frontend/.env.production` is committed, or add the env var `NEXT_PUBLIC_STATIC_DATA` = `1` in Vercel → Settings → Environment Variables and redeploy |

## Note for the viva
The deployed site shows **pre-computed** model outputs. Live inference is still implemented in the
Flask API (`POST /api/predict`), and you can demonstrate it locally with `start.bat`. To host the
live API as well, deploy `backend/` to a Python host with more room (e.g. Render, Railway, a VM) and
point the frontend's `FLASK_URL` to it with static mode turned off.
