"""Export every API response as static JSON so the dashboard can be hosted on Vercel
without a Python server.

The Flask app itself produces the files (through its test client), so the static
data is exactly what the live API would return.

Run from the project root after training:
    python -m backend.export_static
Output: frontend/public/data/**.json  (commit this folder, then deploy)
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app import create_app  # noqa: E402
from backend.services import store  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "frontend" / "public" / "data"


def _save(client, api_path: str, method: str = "get", body: dict | None = None):
    res = client.post(api_path, json=body) if method == "post" else client.get(api_path)
    if res.status_code != 200:
        raise RuntimeError(f"{api_path} returned {res.status_code}: {res.get_data(as_text=True)[:200]}")
    return res.get_json()


def _write(rel: str, payload) -> None:
    path = OUT / f"{rel}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    store.clear_cache()
    client = create_app().test_client()
    if OUT.exists():
        shutil.rmtree(OUT)

    # Simple GET endpoints: /api/<x>  ->  /data/<x>.json
    for rel in ["overview", "preprocessing", "preprocessing/flight-trace", "eda", "eda/envelope", "models", "engines"]:
        _write(rel, _save(client, f"/api/{rel}"))

    # Per-engine series + predictions for every flight of every engine
    engines = _save(client, "/api/engines")
    n_pred = 0
    for e in engines:
        eid = e["engine_id"]
        _write(f"engines/{eid}", _save(client, f"/api/engines/{eid}"))
        cycles = store.feature_table().query("engine_id == @eid")["cycle"].astype(int).tolist()
        preds = {str(c): _save(client, "/api/predict", "post", {"engine_id": eid, "cycle": c}) for c in cycles}
        _write(f"predict/{eid}", preds)
        n_pred += len(preds)

    size_mb = sum(p.stat().st_size for p in OUT.rglob("*.json")) / 1e6
    print(f"Exported {len(engines)} engines, {n_pred} predictions -> {OUT} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
