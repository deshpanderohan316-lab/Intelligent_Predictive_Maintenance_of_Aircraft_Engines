"""Train and compare RUL models.  Usage: python -m ml.scripts.train"""
import sys

from ml.src.models.train import run

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    run()
