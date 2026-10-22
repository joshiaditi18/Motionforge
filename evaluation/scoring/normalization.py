"""
normalization.py — MOTIONFORGE Phase 4 Metric Normalization

Implements the official score formula from COMPETITION_SPECIFICATION.md §9.1:

    S_task = 100 * exp( -sum_k( w_k * E_k / tau_k ) )

τ values are loaded exclusively from calibration/metric_calibration.json.
NO τ constants are hardcoded here.

Anti-degeneracy guard:
    If motion_preservation < 0.35 or > 3.0 → score = 0.0 (degenerate submission)
"""

from __future__ import annotations

import json
import math
import os
from typing import Dict, Any

# ---------------------------------------------------------------------------
# Calibration loader
# ---------------------------------------------------------------------------

_CALIBRATION_CACHE: Dict[str, Any] | None = None
_CALIBRATION_PATH = os.path.join(
    os.path.dirname(__file__),  # evaluation/scoring/
    "..",  # evaluation/
    "..",  # project root
    "calibration",
    "metric_calibration.json",
)


def load_calibration() -> Dict[str, Any]:
    """Load and cache the Phase 3 calibration JSON."""
    global _CALIBRATION_CACHE
    if _CALIBRATION_CACHE is not None:
        return _CALIBRATION_CACHE

    path = os.path.normpath(_CALIBRATION_PATH)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Calibration file not found: {path}\n"
            "Run Phase 3 calibration scripts to generate it."
        )

    with open(path, "r", encoding="utf-8") as f:
        _CALIBRATION_CACHE = json.load(f)
    return _CALIBRATION_CACHE


def get_task_calibration(task: int) -> Dict[str, Any]:
    """
    Return a flattened calibration dict for a task (1, 2, or 3).

    The JSON uses the schema:
        task_1_denoising / task_2_gap_filling / task_3_retargeting
          normalizers         : { tau keys }
          intra_task_weights  : { metric keys }
          baseline_median_scores : { ... }

    This function flattens normalizers + intra_task_weights into a single dict
    for easy access by task_scoring.py.
    """
    cal = load_calibration()
    task_keys = {
        1: "task_1_denoising",
        2: "task_2_gap_filling",
        3: "task_3_retargeting",
    }
    key = task_keys.get(task)
    if key is None:
        raise ValueError(f"Unknown task: {task}. Must be 1, 2, or 3.")
    if key not in cal:
        raise KeyError(f"Key '{key}' missing from metric_calibration.json.")

    raw = cal[key]
    # Flatten normalizers and intra_task_weights to top-level for convenience
    flat: Dict[str, Any] = {}
    flat.update(raw.get("normalizers", {}))
    flat["intra_task_weights"] = raw.get("intra_task_weights", {})
    flat["baseline_median_scores"] = raw.get("baseline_median_scores", {})
    return flat


# ---------------------------------------------------------------------------
# Core normalization
# ---------------------------------------------------------------------------

# Anti-degeneracy bounds for motion preservation ratio (Task 1 denoising)
MOTION_PRESERVATION_MIN = 0.35
MOTION_PRESERVATION_MAX = 3.00


def normalize_weighted_exponential(
    metric_weights: Dict[str, float],
    metric_values: Dict[str, float],
    tau_values: Dict[str, float],
) -> float:
    """
    Compute the normalized score using the official formula:

        S = 100 * exp( -sum_k( w_k * E_k / tau_k ) )

    Parameters
    ----------
    metric_weights : dict
        { metric_name: weight }   — must sum to ≈ 1.0
    metric_values : dict
        { metric_name: raw_error_value }
    tau_values : dict
        { metric_name: tau }   — loaded from calibration JSON

    Returns
    -------
    float in [0.0, 100.0]
    """
    exponent = 0.0
    for name, weight in metric_weights.items():
        error = float(metric_values.get(name, 0.0))
        tau = float(tau_values.get(name))
        if tau <= 0:
            raise ValueError(f"τ for '{name}' must be positive, got {tau}.")
        # Clamp error to non-negative (errors are magnitudes)
        error = max(error, 0.0)
        exponent += weight * error / tau

    raw = 100.0 * math.exp(-exponent)
    return float(max(0.0, min(100.0, raw)))


def check_anti_degeneracy(motion_preservation: float) -> bool:
    """
    Returns True if the submission passes the anti-degeneracy check.
    Returns False (degenerate) if motion_preservation is out of [0.35, 3.0].
    """
    return MOTION_PRESERVATION_MIN <= motion_preservation <= MOTION_PRESERVATION_MAX
