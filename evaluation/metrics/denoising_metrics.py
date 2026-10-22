import os
import sys
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BASE_DIR)

from baselines.common.forward_kinematics import compute_forward_kinematics
from baselines.common.skeleton_utils import CANONICAL_31_JOINTS
from evaluation.metrics.kinematic_metrics import (
    calculate_mpjpe,
    calculate_velocity_error,
    calculate_acceleration_error,
    calculate_jitter_error,
    calculate_motion_preservation_ratio
)
from evaluation.metrics.common_metrics import validate_motion_array

"""
MOTIONFORGE — evaluation/metrics/denoising_metrics.py
Official Task 1 (Motion Denoising) metrics evaluation engine.
Evaluates 3D Forward Kinematics trajectories over the 31 canonical joints:
CANONICAL_31_JOINTS = [
    'Hips', 'LHipJoint', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase',
    'RHipJoint', 'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase',
    'LowerBack', 'Spine', 'Spine1', 'Neck', 'Neck1', 'Head',
    'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand', 'LeftFingerBase', 'LeftHandIndex1', 'LThumb',
    'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand', 'RightFingerBase', 'RightHandIndex1', 'RThumb'
]
"""

def evaluate_denoising(bvh_pred, bvh_gt, bvh_noisy=None):
    """
    Computes official Task 1 (Motion Denoising) metrics.
    Args:
        bvh_pred: BVHStructure of participant's denoised output
        bvh_gt: BVHStructure of master clean ground truth
        bvh_noisy: (Optional) BVHStructure of corrupted challenge input
    Returns:
        dict: Raw metric dictionary with float values
    """
    # 1. Structural and dimension validation
    is_valid_gt, err_gt = validate_motion_array(bvh_gt.motion_data, expected_channels=96)
    if not is_valid_gt:
        raise ValueError(f"Ground-truth motion array invalid: {err_gt}")

    is_valid_pred, err_pred = validate_motion_array(bvh_pred.motion_data, expected_frames=bvh_gt.frame_count, expected_channels=96)
    if not is_valid_pred:
        raise ValueError(f"Participant motion array invalid: {err_pred}")

    dt = bvh_gt.frame_time if bvh_gt.frame_time > 0 else 0.0083333

    # 2. Forward Kinematics
    pos_gt, j_names_gt = compute_forward_kinematics(bvh_gt, include_end_sites=False)
    pos_pred, j_names_pred = compute_forward_kinematics(bvh_pred, include_end_sites=False)

    if pos_pred.shape != pos_gt.shape:
        raise ValueError(f"FK position shape mismatch: pred {pos_pred.shape} vs gt {pos_gt.shape}")

    # 3. Compute Official Metrics
    mpjpe = calculate_mpjpe(pos_pred, pos_gt)
    vel_err = calculate_velocity_error(pos_pred, pos_gt, frame_time=dt)
    acc_err = calculate_acceleration_error(pos_pred, pos_gt, frame_time=dt)
    jitter = calculate_jitter_error(pos_pred, pos_gt, frame_time=dt)
    pres_ratio = calculate_motion_preservation_ratio(pos_pred, pos_gt, frame_time=dt)

    result = {
        "mpjpe": round(mpjpe, 6),
        "velocity_error": round(vel_err, 6),
        "acceleration_error": round(acc_err, 6),
        "jitter": round(jitter, 4),
        "motion_preservation": round(pres_ratio, 6)
    }

    # Optional relative improvement analysis
    if bvh_noisy is not None:
        pos_raw, _ = compute_forward_kinematics(bvh_noisy, include_end_sites=False)
        raw_mpjpe = calculate_mpjpe(pos_raw, pos_gt)
        raw_jitter = calculate_jitter_error(pos_raw, pos_gt, frame_time=dt)
        result["raw_mpjpe"] = round(raw_mpjpe, 6)
        result["raw_jitter"] = round(raw_jitter, 4)
        result["mpjpe_improvement_pct"] = round((raw_mpjpe - mpjpe) / max(1e-6, raw_mpjpe) * 100.0, 2)
        result["jitter_reduction_pct"] = round((raw_jitter - jitter) / max(1e-6, raw_jitter) * 100.0, 2)

    return result
