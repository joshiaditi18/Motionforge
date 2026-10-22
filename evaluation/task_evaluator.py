"""
task_evaluator.py — MOTIONFORGE Phase 4 Per-Task Evaluation

High-level evaluation for a single task submission.
Performs:
    1. Structural BVH validation (hierarchy, frames, FPS, channels, NaN/Inf)
    2. Metric computation (delegating to evaluation/metrics/)
    3. Score computation (delegating to evaluation/scoring/)
    4. Result packaging

Returns a dict with status VALID / REJECTED / ERROR.
"""

from __future__ import annotations

import sys
import os
import time
import traceback
from typing import Optional, Dict, Any, Tuple

# Path setup: ensure project root is on sys.path
_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from baselines.common.bvh_io import parse_bvh
from baselines.common.forward_kinematics import compute_forward_kinematics
from baselines.common.skeleton_utils import CANONICAL_31_JOINTS

from evaluation.metrics.common_metrics import validate_motion_array
from evaluation.metrics.denoising_metrics import evaluate_denoising
from evaluation.metrics.gap_filling_metrics import evaluate_gap_filling, DEFAULT_FOOT_CONTACT_VELOCITY_THRESHOLD
from evaluation.metrics.retargeting_metrics import evaluate_retargeting

from evaluation.scoring.task_scoring import score_denoising, score_gap_filling, score_retargeting
from evaluation.io.evaluation_schema import SubmissionStatus

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPECTED_FPS        = 120.0
EXPECTED_FRAME_TIME = 1.0 / EXPECTED_FPS     # 0.008333...
FRAME_TIME_TOLERANCE = 1e-4                  # ±0.1 ms
EXPECTED_CHANNELS   = 96
EXPECTED_JOINT_COUNT = 31


# ---------------------------------------------------------------------------
# Structural validation helpers
# ---------------------------------------------------------------------------

def _validate_bvh_structure(
    bvh_pred,
    bvh_gt,
    task: int,
) -> Tuple[bool, str]:
    """
    Validate that the predicted BVH matches the ground-truth structure.

    Returns (ok, rejection_reason).
    """
    # Frame count must match exactly
    if bvh_pred.frame_count != bvh_gt.frame_count:
        return False, (
            f"Frame count mismatch: predicted {bvh_pred.frame_count} "
            f"vs ground-truth {bvh_gt.frame_count}"
        )

    # Frame time must match within tolerance
    pred_ft = float(bvh_pred.frame_time)
    gt_ft   = float(bvh_gt.frame_time)
    if abs(pred_ft - gt_ft) > FRAME_TIME_TOLERANCE:
        return False, (
            f"Frame time mismatch: predicted {pred_ft:.6f}s "
            f"vs ground-truth {gt_ft:.6f}s"
        )

    # Channel count must match
    if bvh_pred.num_channels != bvh_gt.num_channels:
        return False, (
            f"Channel count mismatch: predicted {bvh_pred.num_channels} "
            f"vs ground-truth {bvh_gt.num_channels}"
        )

    # Joint names must match (order-sensitive for channel alignment)
    pred_joints = [n.name for n in bvh_pred.nodes if not n.is_end_site]
    gt_joints   = [n.name for n in bvh_gt.nodes   if not n.is_end_site]
    if pred_joints != gt_joints:
        # Collect diff for reporting
        missing  = [j for j in gt_joints   if j not in pred_joints]
        extra    = [j for j in pred_joints if j not in gt_joints]
        msg = "Joint hierarchy mismatch."
        if missing:
            msg += f" Missing: {missing[:5]}"
        if extra:
            msg += f" Extra: {extra[:5]}"
        return False, msg

    # NaN / Inf check
    ok, nan_msg = validate_motion_array(bvh_pred.motion_data)
    if not ok:
        return False, nan_msg

    return True, ""


# ---------------------------------------------------------------------------
# Public per-task evaluators
# ---------------------------------------------------------------------------

def evaluate_task1(
    pred_path: str,
    gt_path: str,
    noisy_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate Task 1 — Motion Denoising.

    Parameters
    ----------
    pred_path  : Path to participant's denoised BVH
    gt_path    : Path to ground-truth clean BVH
    noisy_path : (optional) Path to the noisy input BVH for improvement metrics

    Returns
    -------
    dict with keys: status, score, metrics, detail, error_message
    """
    t0 = time.perf_counter()
    try:
        bvh_pred = parse_bvh(pred_path)
        bvh_gt   = parse_bvh(gt_path)
        bvh_noisy = parse_bvh(noisy_path) if noisy_path else None

        ok, reason = _validate_bvh_structure(bvh_pred, bvh_gt, task=1)
        if not ok:
            return {
                "status": SubmissionStatus.REJECTED.value,
                "score": None,
                "metrics": {},
                "detail": {},
                "error_message": f"Structural validation failed: {reason}",
                "runtime_seconds": time.perf_counter() - t0,
            }

        raw_metrics = evaluate_denoising(bvh_pred, bvh_gt, bvh_noisy)
        score, detail = score_denoising(raw_metrics)

        return {
            "status": SubmissionStatus.VALID.value,
            "score": score,
            "metrics": raw_metrics,
            "detail": detail,
            "error_message": None,
            "runtime_seconds": time.perf_counter() - t0,
        }

    except Exception as exc:
        return {
            "status": SubmissionStatus.ERROR.value,
            "score": None,
            "metrics": {},
            "detail": {},
            "error_message": f"Evaluator error (Task 1): {exc}\n{traceback.format_exc()}",
            "runtime_seconds": time.perf_counter() - t0,
        }


def evaluate_task2(
    pred_path: str,
    gt_path: str,
    joint_name: str,
    start_frame: int,
    end_frame: int,
    contact_velocity_threshold: float = DEFAULT_FOOT_CONTACT_VELOCITY_THRESHOLD,
) -> Dict[str, Any]:
    """
    Evaluate Task 2 — Motion Gap Filling.

    Parameters
    ----------
    pred_path                  : Path to participant's gap-filled BVH
    gt_path                    : Path to ground-truth clean BVH
    joint_name                 : Joint whose gap was filled
    start_frame                : First frame of gap (inclusive)
    end_frame                  : Last frame of gap (inclusive)
    contact_velocity_threshold : Foot skating threshold (in/s)

    Returns
    -------
    dict with keys: status, score, metrics, detail, error_message
    """
    t0 = time.perf_counter()
    try:
        bvh_pred = parse_bvh(pred_path)
        bvh_gt   = parse_bvh(gt_path)

        ok, reason = _validate_bvh_structure(bvh_pred, bvh_gt, task=2)
        if not ok:
            return {
                "status": SubmissionStatus.REJECTED.value,
                "score": None,
                "metrics": {},
                "detail": {},
                "error_message": f"Structural validation failed: {reason}",
                "runtime_seconds": time.perf_counter() - t0,
            }

        raw_metrics = evaluate_gap_filling(
            bvh_pred, bvh_gt, joint_name, start_frame, end_frame,
            contact_velocity_threshold=contact_velocity_threshold,
        )

        # Map actual metric dict keys to scorer expected keys
        scorer_metrics = {
            "inpainting_mpjpe":        raw_metrics.get("inpainting_mpjpe", 0.0),
            "boundary_position_error": raw_metrics.get("boundary_error", 0.0),
            "boundary_velocity_error": raw_metrics.get("velocity_boundary_error", 0.0),
            "unmodified_max_diff":     raw_metrics.get("unmodified_max_diff", 0.0),
        }

        # Contract violation check (handled inside score_gap_filling via unmodified_max_diff)
        score, detail = score_gap_filling(scorer_metrics)

        status = (
            SubmissionStatus.REJECTED.value
            if detail.get("degenerate") and "contract violation" in detail.get("degenerate_reason", "")
            else SubmissionStatus.VALID.value
        )

        return {
            "status": status,
            "score": score if status == SubmissionStatus.VALID.value else None,
            "metrics": raw_metrics,
            "detail": detail,
            "error_message": detail.get("degenerate_reason") if detail.get("degenerate") else None,
            "runtime_seconds": time.perf_counter() - t0,
        }

    except Exception as exc:
        return {
            "status": SubmissionStatus.ERROR.value,
            "score": None,
            "metrics": {},
            "detail": {},
            "error_message": f"Evaluator error (Task 2): {exc}\n{traceback.format_exc()}",
            "runtime_seconds": time.perf_counter() - t0,
        }


def evaluate_task3(
    pred_path: str,
    src_path: str,
    target_type: str,
) -> Dict[str, Any]:
    """
    Evaluate Task 3 — Motion Retargeting.

    Parameters
    ----------
    pred_path   : Path to participant's retargeted BVH
    src_path    : Path to source (original) BVH motion
    target_type : One of "small", "medium", "tall"

    Returns
    -------
    dict with keys: status, score, metrics, detail, error_message
    """
    t0 = time.perf_counter()
    try:
        bvh_pred = parse_bvh(pred_path)
        bvh_src  = parse_bvh(src_path)

        # For retargeting, frame count must match source
        if bvh_pred.frame_count != bvh_src.frame_count:
            return {
                "status": SubmissionStatus.REJECTED.value,
                "score": None,
                "metrics": {},
                "detail": {},
                "error_message": (
                    f"Frame count mismatch: predicted {bvh_pred.frame_count} "
                    f"vs source {bvh_src.frame_count}"
                ),
                "runtime_seconds": time.perf_counter() - t0,
            }

        # NaN/Inf check on prediction
        ok, nan_msg = validate_motion_array(bvh_pred.motion_data)
        if not ok:
            return {
                "status": SubmissionStatus.REJECTED.value,
                "score": None,
                "metrics": {},
                "detail": {},
                "error_message": f"Structural validation failed: {nan_msg}",
                "runtime_seconds": time.perf_counter() - t0,
            }

        if target_type not in ("small", "medium", "tall"):
            return {
                "status": SubmissionStatus.REJECTED.value,
                "score": None,
                "metrics": {},
                "detail": {},
                "error_message": f"Unknown target_type '{target_type}'. Must be small/medium/tall.",
                "runtime_seconds": time.perf_counter() - t0,
            }

        # Retargeting metrics module uses TARGET_CONFIGS keys with 'target_' prefix
        internal_target = f"target_{target_type}"

        raw_metrics = evaluate_retargeting(bvh_pred, bvh_src, internal_target)

        # Map actual metric dict keys to scorer expected keys
        scorer_metrics = {
            "end_effector_error":    raw_metrics.get("end_effector_error", 0.0),
            "angular_deviation_deg": raw_metrics.get("angular_geodesic_error", 0.0),
            "ground_penetration_in": raw_metrics.get("ground_penetration_penalty", 0.0),
        }
        score, detail = score_retargeting(scorer_metrics)

        return {
            "status": SubmissionStatus.VALID.value,
            "score": score,
            "metrics": raw_metrics,
            "detail": detail,
            "error_message": None,
            "runtime_seconds": time.perf_counter() - t0,
        }

    except Exception as exc:
        return {
            "status": SubmissionStatus.ERROR.value,
            "score": None,
            "metrics": {},
            "detail": {},
            "error_message": f"Evaluator error (Task 3): {exc}\n{traceback.format_exc()}",
            "runtime_seconds": time.perf_counter() - t0,
        }
