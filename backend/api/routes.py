"""REST endpoints consumed by the Next.js frontend."""
from __future__ import annotations

from flask import Blueprint, abort, jsonify, request, send_from_directory

from ..services import prediction, store

api = Blueprint("api", __name__, url_prefix="/api")


@api.errorhandler(store.ArtifactMissing)
def _missing(err):
    return jsonify({"error": str(err)}), 503


@api.errorhandler(KeyError)
def _not_found(err):
    return jsonify({"error": err.args[0] if err.args else "not found"}), 404


@api.get("/health")
def health():
    return jsonify({"status": "ok"})


@api.get("/overview")
def overview():
    rep = store.preprocessing_report()
    m = store.metrics()
    steps = {s["key"]: s["details"] for s in rep["steps"]}
    best = next(r for r in m["results"] if r["model"] == m["best_model"])
    return jsonify({
        "datasets": steps["inventory"]["selected"],
        "rows_1hz": steps["clean_residual_aggregate"]["rows_1hz_in"],
        "rows_cycle": steps["clean_residual_aggregate"]["rows_cycle_out"],
        "engines": steps["labels"]["engines"],
        "features_engineered": steps["features"]["n_features"],
        "features_selected": steps["selection"]["n_selected"],
        "best_model": m["best_model"],
        "best_test": best["test"],
        "pipeline_seconds": rep["total_seconds"],
    })


@api.get("/preprocessing")
def preprocessing():
    return jsonify(store.preprocessing_report())


@api.get("/preprocessing/flight-trace")
def flight_trace():
    return jsonify(store.flight_trace())


@api.get("/eda")
def eda():
    return jsonify(store.eda_summary())


@api.get("/eda/envelope")
def envelope():
    return jsonify(store.flight_envelope())


@api.get("/engines")
def engines():
    series = store.engine_series()
    out = [{"engine_id": eid, "split": s["split"][0], "cycles": int(max(s["cycle"]))} for eid, s in series.items()]
    return jsonify(sorted(out, key=lambda e: e["engine_id"]))


@api.get("/engines/<engine_id>")
def engine(engine_id: str):
    series = store.engine_series()
    if engine_id not in series:
        abort(404)
    return jsonify({"engine_id": engine_id, "series": series[engine_id],
                    "predictions": store.predictions().get(engine_id)})


@api.get("/models")
def models():
    return jsonify(store.metrics())


@api.post("/predict")
def predict():
    body = request.get_json(silent=True) or {}
    if "engine_id" not in body:
        return jsonify({"error": "engine_id is required"}), 400
    cycle = body.get("cycle")
    return jsonify(prediction.predict(body["engine_id"], int(cycle) if cycle is not None else None))


@api.get("/figures/<path:name>")
def figure(name: str):
    return send_from_directory(store.FIGURES, name)


@api.post("/reload")
def reload():
    store.clear_cache()
    return jsonify({"reloaded": True})
