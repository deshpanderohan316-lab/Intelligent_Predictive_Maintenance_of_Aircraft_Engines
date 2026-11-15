"""Central configuration for the N-CMAPSS predictive-maintenance project.

Every path, variable list and preprocessing hyper-parameter lives here so the
pipeline, the training scripts and the Flask API all agree on the same values.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT_DIR / "data_set"                 # original N-CMAPSS .h5 files
INTERIM_DIR = ROOT_DIR / "data" / "interim"     # cycle-level aggregated data
PROCESSED_DIR = ROOT_DIR / "data" / "processed" # model-ready matrices
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
PREPROC_ARTIFACTS = ARTIFACTS_DIR / "preprocessing"  # fitted scaler / baseline model
MODEL_ARTIFACTS = ARTIFACTS_DIR / "models"
REPORTS_DIR = ARTIFACTS_DIR / "reports"
FIGURES_DIR = ARTIFACTS_DIR / "figures"
UI_DIR = ARTIFACTS_DIR / "ui"                   # small JSON files served to the UI

# --------------------------------------------------------------------------- #
# N-CMAPSS variable names (Arias Chao et al., 2021)
# --------------------------------------------------------------------------- #
W_VARS = ["alt", "Mach", "TRA", "T2"]  # flight / operating conditions
XS_VARS = [                             # physical (measured) sensors
    "T24", "T30", "T48", "T50", "P15", "P2", "P21",
    "P24", "Ps30", "P40", "P50", "Nf", "Nc", "Wf",
]
XV_VARS = [                             # virtual (model-estimated) sensors
    "T40", "P30", "P45", "W21", "W22", "W25", "W31",
    "W32", "W48", "W50", "SmFan", "SmLPC", "SmHPC", "phi",
]
THETA_VARS = [                          # true health parameters -> NEVER model inputs
    "fan_eff_mod", "fan_flow_mod", "LPC_eff_mod", "LPC_flow_mod",
    "HPC_eff_mod", "HPC_flow_mod", "HPT_eff_mod", "HPT_flow_mod",
    "LPT_eff_mod", "LPT_flow_mod",
]
A_VARS = ["unit", "cycle", "Fc", "hs"]  # auxiliary: engine id, flight #, flight class, health state

SENSOR_DESCRIPTIONS = {
    "T24": "Total temperature at LPC outlet (°R)",
    "T30": "Total temperature at HPC outlet (°R)",
    "T48": "Total temperature at HPT outlet (°R)",
    "T50": "Total temperature at LPT outlet (°R)",
    "P15": "Total pressure in bypass-duct (psia)",
    "P2": "Total pressure at fan inlet (psia)",
    "P21": "Total pressure at fan outlet (psia)",
    "P24": "Total pressure at LPC outlet (psia)",
    "Ps30": "Static pressure at HPC outlet (psia)",
    "P40": "Total pressure at burner outlet (psia)",
    "P50": "Total pressure at LPT outlet (psia)",
    "Nf": "Physical fan speed (rpm)",
    "Nc": "Physical core speed (rpm)",
    "Wf": "Fuel flow (pps)",
}


# --------------------------------------------------------------------------- #
# Preprocessing hyper-parameters
# --------------------------------------------------------------------------- #
@dataclass
class PreprocessConfig:
    # Which files to process (name fragment after "N-CMAPSS_"). DS02 is the
    # reference sub-dataset used in the NASA paper and example notebook.
    datasets: list[str] = field(default_factory=lambda: ["DS02-006"])

    # Read the 1 Hz HDF5 data in slices so 3-4 GB files never sit in RAM at once.
    chunk_size: int = 500_000

    # Use virtual sensors as extra inputs? They are model estimates, not real
    # measurements, so they are off by default (more realistic deployment).
    use_virtual_sensors: bool = False

    # Operating-condition normalisation (sensor residuals vs. a healthy baseline)
    baseline_poly_degree: int = 3
    baseline_ridge_alpha: float = 1e-3
    baseline_max_samples: int = 400_000   # healthy rows sampled to fit the baseline
    min_altitude_ft: float = 0.0          # drop ground-idle samples below this altitude

    # Cycle-level outlier handling (winsorising with train-set percentiles)
    clip_quantiles: tuple[float, float] = (0.005, 0.995)

    # RUL labelling: piece-wise linear target. None = keep raw RUL.
    rul_cap: int | None = None

    # Time-series feature engineering (all causal: use past cycles only)
    rolling_window: int = 5
    slope_window: int = 10
    ewm_alpha: float = 0.3
    baseline_cycles: int = 5              # first k cycles define each engine's own baseline

    # Feature selection (fit on training data only)
    variance_threshold: float = 1e-8
    correlation_threshold: float = 0.95
    max_features: int = 40

    random_state: int = 42

    @property
    def sensor_vars(self) -> list[str]:
        return XS_VARS + (XV_VARS if self.use_virtual_sensors else [])


def ensure_dirs() -> None:
    for d in (INTERIM_DIR, PROCESSED_DIR, PREPROC_ARTIFACTS, MODEL_ARTIFACTS,
              REPORTS_DIR, FIGURES_DIR, UI_DIR):
        d.mkdir(parents=True, exist_ok=True)
