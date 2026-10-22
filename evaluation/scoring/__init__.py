"""
evaluation/scoring/__init__.py
"""

from .normalization import (
    load_calibration,
    get_task_calibration,
    normalize_weighted_exponential,
    check_anti_degeneracy,
    MOTION_PRESERVATION_MIN,
    MOTION_PRESERVATION_MAX,
)
from .task_scoring import score_denoising, score_gap_filling, score_retargeting
from .overall_scoring import (
    compute_overall_score,
    TASK_WEIGHT_DENOISING,
    TASK_WEIGHT_GAP_FILLING,
    TASK_WEIGHT_RETARGETING,
)

__all__ = [
    # normalization
    "load_calibration",
    "get_task_calibration",
    "normalize_weighted_exponential",
    "check_anti_degeneracy",
    "MOTION_PRESERVATION_MIN",
    "MOTION_PRESERVATION_MAX",
    # task scoring
    "score_denoising",
    "score_gap_filling",
    "score_retargeting",
    # overall
    "compute_overall_score",
    "TASK_WEIGHT_DENOISING",
    "TASK_WEIGHT_GAP_FILLING",
    "TASK_WEIGHT_RETARGETING",
]
