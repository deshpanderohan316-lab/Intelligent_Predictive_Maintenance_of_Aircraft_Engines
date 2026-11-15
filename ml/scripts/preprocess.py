"""Run the full preprocessing pipeline.

Usage (from the project root):
    python -m ml.scripts.preprocess                       # DS02 (default)
    python -m ml.scripts.preprocess --datasets DS01-005 DS02-006 --rul-cap 65
"""
import argparse

from ml.src.config import PreprocessConfig
from ml.src.preprocessing.pipeline import run


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--datasets", nargs="+", default=["DS02-006"])
    p.add_argument("--rul-cap", type=int, default=None)
    p.add_argument("--virtual-sensors", action="store_true", help="also use X_v virtual sensors")
    p.add_argument("--chunk-size", type=int, default=500_000)
    p.add_argument("--max-features", type=int, default=40)
    a = p.parse_args()
    cfg = PreprocessConfig(datasets=a.datasets, rul_cap=a.rul_cap, use_virtual_sensors=a.virtual_sensors,
                           chunk_size=a.chunk_size, max_features=a.max_features)
    run(cfg)


if __name__ == "__main__":
    main()
