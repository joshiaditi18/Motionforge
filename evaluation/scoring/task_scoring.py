"""
task_scoring.py — MOTIONFORGE Phase 4 Per-Task Scoring

Three public functions:
    score_denoising(metrics_dict)     -> float [0, 100]
    score_gap_filling(metrics_dict)   -> float [0, 100]
    score_retargeting(metrics_dict)   -> float [0, 100]

All τ values loaded from calibration/metric_calibration.json via normalization.py.
Competition weights (0.30 / 0.30 / 0.40) are applied at the overall-score level.
"""

from __future__ import annotations

from typing import Dict, Any, Tuple

from .normalization import (
    normalize_weighted_exponential,
    check_anti_degeneracy,
    get_task_calibration,
)

# ---------------------------------------------------------------------------
# Task 1 — Motion Denoising
# ---------------------------------------------------------------------------

def score_denoising(metrics: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    Score a denoising submission.

    Expected keys in `metrics`:
        mpjpe               — mean per-joint position error (inches)
        velocity_error      — mean joint velocity error (in/s)
        jitter              — mean joint jitter (in/s²)
        motion_preservation — ratio of output/input kinetic energy [dimensionless]

    Returns
    -------
    (score, detail)
        score  : float in [0.0, 100.0]; 0.0 if degenerate
        detail : dict with scoring breakdown
    """
    cal = get_task_calibration(1)

    motion_preservation = float(metrics.get("motion_preservation", 1.0))

    # Anti-degeneracy guard
    if not check_anti_degeneracy(motion_preservation):
        return 0.0, {
            "task": "denoising",
            "score": 0.0,
            "degenerate": True,
            "degenerate_reason": (
                f"motion_preservation={motion_preservation:.4f} outside "
                f"[0.35, 3.0] — submission flagged as degenerate"
            ),
            "metrics_used": {},
        }

    # Extract τ values from flattened calibration
    # JSON keys: mpjpe_tau, velocity_tau, jitter_tau
    tau_values = {
        "mpjpe":          cal["mpjpe_tau"],
        "velocity_error": cal["velocity_tau"],
        "jitter":         cal["jitter_tau"],
    }
    # JSON intra_task_weights keys: mpjpe, velocity, jitter
    raw_w = cal.get("intra_task_weights", {})
    weights = {
        "mpjpe":          raw_w.get("mpjpe", 0.40),
        "velocity_error": raw_w.get("velocity", 0.30),
        "jitter":         raw_w.get("jitter", 0.30),
    }

    metric_values = {
        "mpjpe":          float(metrics.get("mpjpe", 0.0)),
        "velocity_error": float(metrics.get("velocity_error", 0.0)),
        "jitter":         float(metrics.get("jitter", 0.0)),
    }

    score = normalize_weighted_exponential(weights, metric_values, tau_values)

    detail = {
        "task": "denoising",
        "score": score,
        "degenerate": False,
        "metrics_used": metric_values,
        "tau_values": tau_values,
        "weights": weights,
        "motion_preservation": motion_preservation,
    }
    return score, detail


# ---------------------------------------------------------------------------
# Task 2 — Motion Gap Filling
# ---------------------------------------------------------------------------

def score_gap_filling(metrics: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    Score a gap-filling submission.

    Expected keys in `metrics`:
        inpainting_mpjpe       — MPJPE inside gap (inches)
        boundary_position_error — positional continuity at gap boundaries (inches)
        boundary_velocity_error — velocity continuity at gap boundaries (in/s)
        unmodified_max_diff    — L∞ diff outside gap (inches); >1e-6 → REJECTED

    Returns
    -------
    (score, detail)
        score  : float in [0.0, 100.0]; 0.0 if unmodified frames were altered
        detail : dict with scoring breakdown
    """
    cal = get_task_calibration(2)

    # Contract violation: participant must not modify frames outside the gap
    unmodified_max_diff = float(metrics.get("unmodified_max_diff", 0.0))
    if unmodified_max_diff > 1e-6:
        return 0.0, {
            "task": "gap_filling",
            "score": 0.0,
            "degenerate": True,
            "degenerate_reason": (
                f"unmodified_max_diff={unmodified_max_diff:.2e} > 1e-6 "
                "— frames outside gap were modified (contract violation)"
            ),
            "metrics_used": {},
        }

    tau_values = {
        "inpainting_mpjpe":        cal["inpainting_tau"],
        "boundary_position_error": cal["boundary_tau"],
        "boundary_velocity_error": cal["v_boundary_tau"],
    }
    # JSON intra_task_weights keys: inpainting_mpjpe, boundary_continuity, velocity_continuity
    raw_w = cal.get("intra_task_weights", {})
    weights = {
        "inpainting_mpjpe":        raw_w.get("inpainting_mpjpe", 0.50),
        "boundary_position_error": raw_w.get("boundary_continuity", 0.25),
        "boundary_velocity_error": raw_w.get("velocity_continuity", 0.25),
    }

    metric_values = {
        "inpainting_mpjpe":        float(metrics.get("inpainting_mpjpe", 0.0)),
        "boundary_position_error": float(metrics.get("boundary_position_error", 0.0)),
        "boundary_velocity_error": float(metrics.get("boundary_velocity_error", 0.0)),
    }

    score = normalize_weighted_exponential(weights, metric_values, tau_values)

    detail = {
        "task": "gap_filling",
        "score": score,
        "degenerate": False,
        "metrics_used": metric_values,
        "tau_values": tau_values,
        "weights": weights,
        "unmodified_max_diff": unmodified_max_diff,
    }
    return score, detail


# ---------------------------------------------------------------------------
# Task 3 — Motion Retargeting
# ---------------------------------------------------------------------------

def score_retargeting(metrics: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    Score a retargeting submission.

    Expected keys in `metrics`:
        end_effector_error    — normalised end-effector semantic error [0,∞)
        angular_deviation_deg — mean geodesic angular deviation (degrees)
        ground_penetration_in — mean ground penetration depth (inches, ≥0)

    Returns
    -------
    (score, detail)
        score  : float in [0.0, 100.0]
        detail : dict with scoring breakdown
    """
    cal = get_task_calibration(3)

    tau_values = {
        "end_effector_error":    cal["end_effector_tau"],
        "angular_deviation_deg": cal["angular_tau_deg"],
        "ground_penetration_in": cal["ground_penetration_tau"],
    }
    # JSON intra_task_weights keys: end_effector, angular_fidelity, ground_penetration
    raw_w = cal.get("intra_task_weights", {})
    weights = {
        "end_effector_error":    raw_w.get("end_effector", 0.45),
        "angular_deviation_deg": raw_w.get("angular_fidelity", 0.35),
        "ground_penetration_in": raw_w.get("ground_penetration", 0.20),
    }

    metric_values = {
        "end_effector_error":    float(metrics.get("end_effector_error", 0.0)),
        "angular_deviation_deg": float(metrics.get("angular_deviation_deg", 0.0)),
        "ground_penetration_in": float(metrics.get("ground_penetration_in", 0.0)),
    }

    score = normalize_weighted_exponential(weights, metric_values, tau_values)

    detail = {
        "task": "retargeting",
        "score": score,
        "degenerate": False,
        "metrics_used": metric_values,
        "tau_values": tau_values,
        "weights": weights,
    }
    return score, detail
