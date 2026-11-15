"""Candidate regression models compared in the project."""
from __future__ import annotations

from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.svm import SVR


def get_models(random_state: int = 42) -> dict:
    models = {
        "Linear Regression": LinearRegression(),
        "Ridge Regression": Ridge(alpha=1.0),
        "K-Nearest Neighbours": KNeighborsRegressor(n_neighbors=7, weights="distance"),
        "Support Vector Regression": SVR(C=30, epsilon=1.0, gamma="scale"),
        "Random Forest": RandomForestRegressor(n_estimators=400, min_samples_leaf=3, n_jobs=-1,
                                               random_state=random_state),
        "Extra Trees": ExtraTreesRegressor(n_estimators=400, min_samples_leaf=3, n_jobs=-1,
                                           random_state=random_state),
        "Gradient Boosting": HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05,
                                                           max_leaf_nodes=15, l2_regularization=1.0,
                                                           random_state=random_state),
        "MLP Neural Network": MLPRegressor(hidden_layer_sizes=(64, 32), alpha=1e-3, max_iter=2000,
                                           early_stopping=True, random_state=random_state),
    }
    try:
        from lightgbm import LGBMRegressor
        models["LightGBM"] = LGBMRegressor(n_estimators=500, learning_rate=0.03, num_leaves=15,
                                           min_child_samples=10, subsample=0.8, subsample_freq=1,
                                           colsample_bytree=0.8, random_state=random_state, verbose=-1)
    except ImportError:
        pass
    return models
