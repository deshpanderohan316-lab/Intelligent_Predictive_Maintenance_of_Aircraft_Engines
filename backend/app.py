"""Flask API server for the predictive-maintenance dashboard.

Run from the project root (either works):
    python -m backend.app            # http://localhost:5000
    python backend/app.py

Production (Docker / Render): gunicorn serves this app, and if the exported
Next.js site exists (frontend/out, or $FRONTEND_DIR) Flask serves it too, so the
website and the /api endpoints share one URL and one port.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running this file directly (VS Code "Run" button / `python backend/app.py`)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flask import Flask, abort, jsonify, send_from_directory  # noqa: E402
from flask_cors import CORS  # noqa: E402

from backend.api.routes import api  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = Path(os.environ.get("FRONTEND_DIR", ROOT / "frontend" / "out"))


def create_app() -> Flask:
    app = Flask(__name__)
    origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    CORS(app, resources={r"/api/*": {"origins": origins}})
    app.register_blueprint(api)

    @app.get("/api")
    def api_index():
        return jsonify({
            "service": "Aircraft Engine RUL API",
            "endpoints": [str(r) for r in app.url_map.iter_rules() if str(r).startswith("/api")],
        })

    if (FRONTEND_DIR / "index.html").exists():
        _register_frontend(app, FRONTEND_DIR)
    else:
        @app.get("/")
        def index():
            return api_index()

    return app


def _register_frontend(app: Flask, site: Path) -> None:
    """Serve the static Next.js export (`next build` with output: 'export', trailingSlash)."""

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def frontend(path: str):
        if path.startswith("api/"):
            abort(404)
        target = (site / path).resolve()
        if site.resolve() not in target.parents and target != site.resolve():
            abort(404)  # block ../ path traversal
        if target.is_file():
            return send_from_directory(site, path)
        if (target / "index.html").is_file():
            return send_from_directory(site, f"{path.rstrip('/')}/index.html".lstrip("/"))
        return send_from_directory(site, "404.html"), 404


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
