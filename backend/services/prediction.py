"""RUL inference + maintenance recommendation for one engine at one cycle."""
from __future__ import annotations

from . import store


def health_status(rul: float) -> dict:
    if rul <= 10:
        return {"stage": "critical", "label": "Critical",
                "action": "Ground the engine and schedule immediate shop visit / borescope inspection."}
    if rul <= 30:
        return {"stage": "warning", "label": "Warning",
                "action": "Plan maintenance within the next maintenance window; increase monitoring."}
    return {"stage": "healthy", "label": "Healthy", "action": "Continue normal operation and routine monitoring."}


def predict(engine_id: str, cycle: int | None = None) -> dict:
    bundle = store.model_bundle()
    table = store.feature_table()
    rows = table[table["engine_id"] == engine_id].sort_values("cycle")
    if rows.empty:
        raise KeyError(f"Unknown engine '{engine_id}'")
    row = rows.iloc[-1] if cycle is None else rows[rows["cycle"] == cycle]
    if cycle is not None:
        if row.empty:
            raise KeyError(f"Engine '{engine_id}' has no cycle {cycle}")
        row = row.iloc[0]

    X = row[bundle["features"]].to_frame().T.astype(float)
    rul = max(0.0, float(bundle["model"].predict(X)[0]))
    return {
        "engine_id": engine_id,
        "cycle": int(row["cycle"]),
        "split": row["split"],
        "predicted_rul": round(rul, 1),
        "true_rul": int(row["RUL_raw"]),
        "max_cycle": int(rows["cycle"].max()),
        "model": bundle["name"],
        "status": health_status(rul),
        "top_inputs": {f: round(float(row[f]), 3) for f in bundle["features"][:8]},
    }
