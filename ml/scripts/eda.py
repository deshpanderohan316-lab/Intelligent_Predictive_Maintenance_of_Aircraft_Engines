"""Generate EDA figures (artifacts/figures) and UI summaries.  Usage: python -m ml.scripts.eda"""
import argparse

from ml.src.config import PreprocessConfig
from ml.src.eda.eda import run

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--datasets", nargs="+", default=["DS02-006"])
    run(PreprocessConfig(datasets=p.parse_args().datasets))
