"""Memory-safe loading of N-CMAPSS HDF5 files.

Each file stores ~5-10 million rows sampled at 1 Hz, split into a
development set (``*_dev``) and a test set (``*_test``).  Loading a whole file
with ``np.array(hdf.get(...))`` (as the NASA example notebook does) needs 3-4 GB
of RAM per file, so here we stream it in row slices and down-cast to float32.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import h5py
import numpy as np
import pandas as pd

from ..config import A_VARS, RAW_DIR, THETA_VARS, W_VARS, XS_VARS, XV_VARS

log = logging.getLogger(__name__)

SPLITS = ("dev", "test")


@dataclass
class DatasetFile:
    name: str   # e.g. "DS02-006"
    path: Path

    @property
    def short(self) -> str:  # "DS02"
        return self.name.split("-")[0]


def find_dataset(name: str, raw_dir: Path = RAW_DIR) -> DatasetFile:
    path = raw_dir / f"N-CMAPSS_{name}.h5"
    if not path.exists():
        matches = sorted(raw_dir.glob(f"N-CMAPSS_{name}*.h5"))
        if not matches:
            raise FileNotFoundError(f"No N-CMAPSS file matching '{name}' in {raw_dir}")
        path = matches[0]
    return DatasetFile(name=path.stem.replace("N-CMAPSS_", ""), path=path)


def list_datasets(raw_dir: Path = RAW_DIR) -> list[dict]:
    """Return every .h5 file with its row counts, flagging unreadable files."""
    out = []
    for path in sorted(raw_dir.glob("N-CMAPSS_*.h5")):
        info = {"name": path.stem.replace("N-CMAPSS_", ""), "size_gb": round(path.stat().st_size / 1e9, 2)}
        try:
            with h5py.File(path, "r") as h:
                info["rows_dev"] = int(h["W_dev"].shape[0])
                info["rows_test"] = int(h["W_test"].shape[0])
                info["ok"] = True
        except OSError as exc:  # e.g. truncated download
            info["ok"] = False
            info["error"] = str(exc).split("(")[-1].rstrip(")")
        out.append(info)
    return out


def _sensor_columns(use_virtual: bool) -> list[str]:
    return XS_VARS + (XV_VARS if use_virtual else [])


def n_rows(ds: DatasetFile, split: str) -> int:
    with h5py.File(ds.path, "r") as h:
        return int(h[f"W_{split}"].shape[0])


def iter_chunks(
    ds: DatasetFile,
    split: str,
    chunk_size: int = 500_000,
    use_virtual: bool = False,
    include_theta: bool = True,
) -> Iterator[pd.DataFrame]:
    """Yield the 1 Hz data of one split as float32 DataFrames of ``chunk_size`` rows.

    Columns: W_VARS + sensors + [theta] + A_VARS + ["RUL"].
    """
    assert split in SPLITS
    sensors = _sensor_columns(use_virtual)
    with h5py.File(ds.path, "r") as h:
        total = h[f"W_{split}"].shape[0]
        for start in range(0, total, chunk_size):
            stop = min(start + chunk_size, total)
            parts = [
                pd.DataFrame(h[f"W_{split}"][start:stop].astype(np.float32), columns=W_VARS),
                pd.DataFrame(h[f"X_s_{split}"][start:stop].astype(np.float32), columns=XS_VARS),
            ]
            if use_virtual:
                parts.append(pd.DataFrame(h[f"X_v_{split}"][start:stop].astype(np.float32), columns=XV_VARS))
            if include_theta:
                parts.append(pd.DataFrame(h[f"T_{split}"][start:stop].astype(np.float32), columns=THETA_VARS))
            a = h[f"A_{split}"][start:stop]
            parts.append(pd.DataFrame(a.astype(np.int32), columns=A_VARS))
            parts.append(pd.DataFrame({"RUL": h[f"Y_{split}"][start:stop, 0].astype(np.int32)}))
            df = pd.concat(parts, axis=1)
            df.insert(0, "split", split)
            df.insert(0, "dataset", ds.short)
            yield df
    log.debug("finished streaming %s/%s (%d rows)", ds.name, split, total)


def sample_rows(
    ds: DatasetFile,
    split: str,
    n: int,
    use_virtual: bool = False,
) -> pd.DataFrame:
    """Systematically sample ~``n`` rows (every k-th second) from a split.

    Strided slicing is orders of magnitude faster in h5py than random fancy
    indexing, and at 1 Hz a fixed stride is effectively a random sample.
    """
    total = n_rows(ds, split)
    step = max(1, total // n)
    idx = slice(0, total, step)
    sensors = _sensor_columns(use_virtual)
    with h5py.File(ds.path, "r") as h:
        cols = [
            pd.DataFrame(h[f"W_{split}"][idx].astype(np.float32), columns=W_VARS),
            pd.DataFrame(h[f"X_s_{split}"][idx].astype(np.float32), columns=XS_VARS),
        ]
        if use_virtual:
            cols.append(pd.DataFrame(h[f"X_v_{split}"][idx].astype(np.float32), columns=XV_VARS))
        cols.append(pd.DataFrame(h[f"A_{split}"][idx].astype(np.int32), columns=A_VARS))
        cols.append(pd.DataFrame({"RUL": h[f"Y_{split}"][idx, 0].astype(np.int32)}))
    df = pd.concat(cols, axis=1)
    df["dataset"] = ds.short
    df["split"] = split
    return df[["dataset", "split"] + W_VARS + sensors + A_VARS + ["RUL"]]
