"""Run preprocessing -> EDA -> training in one go.  Usage: python -m ml.scripts.run_all"""
from ml.src.config import PreprocessConfig
from ml.src.eda.eda import run as eda
from ml.src.models.train import run as train
from ml.src.preprocessing.pipeline import run as preprocess

if __name__ == "__main__":
    cfg = PreprocessConfig()
    preprocess(cfg)
    eda(cfg)
    train()
