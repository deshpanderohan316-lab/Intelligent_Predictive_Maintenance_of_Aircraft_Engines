# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Aircraft Engine RUL dashboard: one image, one port.
#   Stage 1 (node):   build the Next.js UI as a static site  -> /app/frontend/out
#   Stage 2 (python): gunicorn runs Flask, which serves the UI and the live /api
# ---------------------------------------------------------------------------

# ---------- Stage 1: build the frontend ----------
FROM node:20-bookworm-slim AS frontend
WORKDIR /app/frontend
ENV NEXT_TELEMETRY_DISABLED=1

# install dependencies first (cached unless package*.json changes)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
# export mode -> plain HTML/JS in ./out; live API on the same origin (not the Vercel static-JSON mode)
ENV NEXT_OUTPUT=export \
    NEXT_PUBLIC_STATIC_DATA=0
RUN npm run build


# ---------- Stage 2: Python runtime ----------
FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=10000 \
    FRONTEND_DIR=/app/frontend/out

# libgomp1: OpenMP runtime required by LightGBM / scikit-learn
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --upgrade pip && pip install -r backend/requirements.txt

# application code + the trained model and results it serves
COPY backend/ backend/
COPY artifacts/models/best_model.joblib artifacts/models/best_model.joblib
COPY artifacts/reports/ artifacts/reports/
COPY artifacts/ui/ artifacts/ui/
COPY artifacts/figures/ artifacts/figures/
COPY data/processed/train.parquet data/processed/test.parquet data/processed/
COPY --from=frontend /app/frontend/out frontend/out

# run as an unprivileged user
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/health')" || exit 1

# Render injects $PORT. 1 worker x 4 threads keeps memory low (free plan = 512 MB).
CMD gunicorn backend.app:app --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120 --access-logfile -
