"""Collects a step-by-step log of the preprocessing pipeline.

The resulting ``preprocessing_report.json`` drives the animated pipeline view
of the web UI and doubles as documentation for the project report.
"""
from __future__ import annotations

import json
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd


def _jsonable(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o))


class PipelineReport:
    def __init__(self, config: dict):
        self.config = config
        self.steps: list[dict] = []
        self.started = time.time()
        if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    @contextmanager
    def step(self, key: str, title: str, description: str):
        entry = {"key": key, "title": title, "description": description, "details": {}}
        t0 = time.time()
        yield entry["details"]
        entry["seconds"] = round(time.time() - t0, 2)
        self.steps.append(entry)
        print(f"[{len(self.steps):02d}] {title:<45s} {entry['seconds']:>8.1f}s")

    @staticmethod
    def preview(df: pd.DataFrame, cols: list[str] | None = None, n: int = 5) -> dict:
        sub = df[cols] if cols else df
        sub = sub.head(n)
        return {"columns": list(sub.columns), "rows": sub.round(4).astype(object).where(sub.notna(), None).values.tolist()}

    def save(self, path: Path) -> None:
        payload = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_seconds": round(time.time() - self.started, 1),
            "config": self.config,
            "steps": self.steps,
        }
        path.write_text(json.dumps(payload, indent=2, default=_jsonable), encoding="utf-8")
