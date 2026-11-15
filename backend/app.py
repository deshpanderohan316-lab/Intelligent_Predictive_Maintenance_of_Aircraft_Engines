"""Flask API server for the predictive-maintenance dashboard.

Run from the project root (either works):
    python -m backend.app            # http://localhost:5000
    python backend/app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow running this file directly (VS Code "Run" button / `python backend/app.py`)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flask import Flask, jsonify  # noqa: E402
from flask_cors import CORS  # noqa: E402

from backend.api.routes import api  # noqa: E402


def create_app() -> Flask:
    app = Flask(__name__)
    origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    CORS(app, resources={r"/api/*": {"origins": origins}})
    app.register_blueprint(api)

    @app.get("/")
    def index():
        return jsonify({
            "service": "Aircraft Engine RUL API",
            "endpoints": [str(r) for r in app.url_map.iter_rules() if str(r).startswith("/api")],
        })

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
