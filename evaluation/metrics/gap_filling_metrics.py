import os
import sys
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BASE_DIR)

from baselines.common.forward_kinematics import compute_forward_kinematics
from evaluation.metrics.kinematic_metrics import compute_velocities
from evaluation.metrics.common_metrics import validate_motion_array

"""
MOTIONFORGE — evaluation/metrics/gap_filling_metrics.py
Official Task 2 (Motion Gap Filling) metrics evaluation engine.
Implements inpainting MPJPE on distal bone endpoints, boundary position/velocity
continuity, unoccluded frame fidelity check, and foot skating evaluation.
"""

DEFAULT_FOOT_CONTACT_VELOCITY_THRESHOLD = 0.539  # inches / sec (Phase 3 calibrated)

def resolve_distal_joint_endpoint(bvh_struct, joint_name):
    """
    Kinematic Distal Endpoint Resolution (Phase 3 Critical Finding):
    Rotating an internal joint pivot does NOT displace its own pivot center.
    It displaces its distal bone endpoint (child node or terminal end site).
    """
    if joint_name not in bvh_struct.node_by_name:
        raise ValueError(f"Joint '{joint_name}' not found in BVH hierarchy")

    node = bvh_struct.node_by_name[joint_name]
    if len(node.children) > 0:
        return node.children[0].name
    return joint_name

def evaluate_gap_filling(
    bvh_pred,
    bvh_gt,
    target_joint,
    start_frame,
    end_frame,
    contact_velocity_threshold=DEFAULT_FOOT_CONTACT_VELOCITY_THRESHOLD
):
    """
    Computes official Task 2 (Motion Gap Filling) metrics.
    Args:
        bvh_pred: BVHStructure of participant's reconstructed motion
        bvh_gt: BVHStructure of master clean ground truth
        target_joint: Name of the occluded joint (e.g. 'RightArm', 'LeftLeg', 'Head')
        start_frame: Start frame of occlusion interval (0-indexed or 1-indexed)
        end_frame: End frame of occlusion interval (inclusive)
        contact_velocity_threshold: Speed threshold for stance phase (inches/sec)
    Returns:
        dict: Metric dictionary
    """
    is_valid_gt, err_gt = validate_motion_array(bvh_gt.motion_data, expected_channels=96)
    if not is_valid_gt:
        raise ValueError(f"Ground-truth motion array invalid: {err_gt}")

    is_valid_pred, err_pred = validate_motion_array(bvh_pred.motion_data, expected_frames=bvh_gt.frame_count, expected_channels=96)
    if not is_valid_pred:
        raise ValueError(f"Participant motion array invalid: {err_pred}")

    dt = bvh_gt.frame_time if bvh_gt.frame_time > 0 else 0.0083333
    num_frames = bvh_gt.frame_count

    s_f = int(start_frame)
    e_f = int(end_frame)
    if s_f < 0 or e_f >= num_frames or s_f > e_f:
        raise ValueError(f"Invalid gap interval [{s_f}, {e_f}] for {num_frames} frames")

    # 1. Forward Kinematics (include End Sites for distal endpoints like Head tip)
    pos_gt, j_names_gt = compute_forward_kinematics(bvh_gt, include_end_sites=True)
    pos_pred, j_names_pred = compute_forward_kinematics(bvh_pred, include_end_sites=True)

    vel_gt = compute_velocities(pos_gt, dt)
    vel_pred = compute_velocities(pos_pred, dt)

    # 2. Resolve Distal Endpoint
    distal_name = resolve_distal_joint_endpoint(bvh_gt, target_joint)
    distal_idx = j_names_gt.index(distal_name)

    # 3. Inpainting MPJPE: strictly over [s_f, e_f] for the distal endpoint
    gap_pred = pos_pred[s_f:e_f + 1, distal_idx]
    gap_gt = pos_gt[s_f:e_f + 1, distal_idx]
    inp_errs = np.linalg.norm(gap_pred - gap_gt, axis=-1)
    inpainting_mpjpe = float(np.mean(inp_errs))

    # 4. Boundary Position Continuity Error
    # Entry boundary: pred at s_f vs gt at s_f - 1
    p_step_in = float(np.linalg.norm(pos_pred[s_f, distal_idx] - pos_gt[max(0, s_f - 1), distal_idx])) if s_f > 0 else 0.0
    # Exit boundary: pred at e_f vs gt at e_f + 1
    p_step_out = float(np.linalg.norm(pos_pred[e_f, distal_idx] - pos_gt[min(num_frames - 1, e_f + 1), distal_idx])) if e_f < num_frames - 1 else 0.0
    boundary_position_error = p_step_in + p_step_out

    # 5. Boundary Velocity Continuity Error & Discontinuity
    v_step_in = float(np.linalg.norm(vel_pred[s_f, distal_idx] - vel_gt[max(0, s_f - 1), distal_idx])) if 0 < s_f < len(vel_pred) else 0.0
    v_step_out = float(np.linalg.norm(vel_pred[min(len(vel_pred) - 1, e_f), distal_idx] - vel_gt[min(len(vel_gt) - 1, e_f + 1), distal_idx])) if e_f < len(vel_gt) - 1 else 0.0
    boundary_velocity_error = v_step_in + v_step_out

    # 6. Unmodified Frames Fidelity Check (Contract Invariant: L_inf = 0 outside gap)
    mask_outside = np.ones(num_frames, dtype=bool)
    mask_outside[s_f:e_f + 1] = False
    unmodified_max_diff = float(np.max(np.abs(bvh_pred.motion_data[mask_outside] - bvh_gt.motion_data[mask_outside]))) if np.any(mask_outside) else 0.0

    # 7. Foot Skating Penalty (if leg or foot joint was occluded)
    foot_skating = 0.0
    if any(k in target_joint.lower() for k in ['leg', 'foot', 'toe']):
        # Evaluate horizontal speed (X, Z plane) during stance phase
        h_vel = np.linalg.norm(vel_pred[s_f:min(len(vel_pred), e_f + 1), distal_idx, [0, 2]], axis=-1)
        is_contact = h_vel < contact_velocity_threshold
        if np.any(is_contact):
            foot_skating = float(np.mean(h_vel[is_contact]))

    return {
        "inpainting_mpjpe": round(inpainting_mpjpe, 6),
        "boundary_error": round(boundary_position_error, 6),
        "velocity_boundary_error": round(boundary_velocity_error, 6),
        "foot_skating": round(foot_skating, 6),
        "unmodified_max_diff": round(unmodified_max_diff, 8),
        "target_joint": target_joint,
        "distal_evaluated_joint": distal_name,
        "gap_length_frames": e_f - s_f + 1
    }
