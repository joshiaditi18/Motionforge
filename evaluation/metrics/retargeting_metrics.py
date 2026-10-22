import os
import sys
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BASE_DIR)

from baselines.common.forward_kinematics import compute_forward_kinematics, euler_zyx_to_matrix
from baselines.common.skeleton_utils import get_bone_lengths, END_EFFECTOR_JOINTS
from baselines.retargeting.baseline_retargeting import TARGET_CONFIGS, retarget_hierarchy_offsets
from evaluation.metrics.kinematic_metrics import compute_velocities
from evaluation.metrics.common_metrics import compute_so3_geodesic_degrees, validate_motion_array

"""
MOTIONFORGE — evaluation/metrics/retargeting_metrics.py
Official Task 3 (Motion Retargeting) metrics evaluation engine.
Evaluates bone-length adherence to target avatar, normalized end-effector semantic error,
geodesic joint angular deviation on SO(3), floor penetration, and temporal consistency.
"""

CANONICAL_END_EFFECTORS = ['Head', 'LeftHandIndex1', 'RightHandIndex1', 'LeftToeBase', 'RightToeBase']

def evaluate_retargeting(bvh_pred, bvh_src, target_type):
    """
    Computes official Task 3 (Motion Retargeting) metrics.
    Args:
        bvh_pred: BVHStructure of participant's retargeted motion
        bvh_src: BVHStructure of clean source motion
        target_type: 'target_small', 'target_medium', or 'target_tall'
    Returns:
        dict: Metric dictionary
    """
    if target_type not in TARGET_CONFIGS:
        raise ValueError(f"Unknown target avatar morphology: '{target_type}'")

    is_valid_src, err_src = validate_motion_array(bvh_src.motion_data, expected_channels=96)
    if not is_valid_src:
        raise ValueError(f"Source motion array invalid: {err_src}")

    is_valid_pred, err_pred = validate_motion_array(bvh_pred.motion_data, expected_frames=bvh_src.frame_count, expected_channels=96)
    if not is_valid_pred:
        raise ValueError(f"Participant retargeted motion array invalid: {err_pred}")

    dt = bvh_src.frame_time if bvh_src.frame_time > 0 else 0.0083333

    # 1. Target Bone-Length Consistency
    # Generate canonical target reference hierarchy from source BVH
    cfg = TARGET_CONFIGS[target_type]
    # Rest bone lengths from candidate BVH header
    pred_bone_lens = get_bone_lengths(bvh_pred)

    # Compute expected target bone lengths by applying config scale
    from baselines.retargeting.baseline_retargeting import classify_joint
    max_bone_dev = 0.0
    for node in bvh_src.nodes:
        if not node.is_root and not node.is_end_site:
            cat = classify_joint(node.name)
            scale = 1.0
            if cat == 'torso': scale = cfg['torso_scale']
            elif cat == 'upper_arm': scale = cfg['upper_arm_scale']
            elif cat == 'forearm': scale = cfg['forearm_scale']
            elif cat == 'thigh': scale = cfg['thigh_scale']
            elif cat == 'shin': scale = cfg['shin_scale']
            elif cat == 'foot': scale = cfg['foot_scale']

            expected_len = float(np.linalg.norm(node.offset * scale))
            actual_len = pred_bone_lens.get(node.name, 0.0)
            dev = abs(actual_len - expected_len)
            max_bone_dev = max(max_bone_dev, dev)

    # 2. Forward Kinematics
    pos_src, j_names_src = compute_forward_kinematics(bvh_src, include_end_sites=False)
    pos_pred, j_names_pred = compute_forward_kinematics(bvh_pred, include_end_sites=False)

    hips_src_idx = j_names_src.index('Hips')
    hips_pred_idx = j_names_pred.index('Hips')

    # 3. End-Effector Semantic Error (normalized relative to Hips by rest limb scale)
    ee_errors = []
    for ee in CANONICAL_END_EFFECTORS:
        idx_s = j_names_src.index(ee)
        idx_p = j_names_pred.index(ee)

        rel_src = pos_src[:, idx_s] - pos_src[:, hips_src_idx]
        rel_pred = pos_pred[:, idx_p] - pos_pred[:, hips_pred_idx]

        src_rest_dist = max(1.0, float(np.linalg.norm(pos_src[0, idx_s] - pos_src[0, hips_src_idx])))
        pred_rest_dist = max(1.0, float(np.linalg.norm(pos_pred[0, idx_p] - pos_pred[0, hips_pred_idx])))

        norm_src = rel_src / src_rest_dist
        norm_pred = rel_pred / pred_rest_dist

        diff = np.linalg.norm(norm_pred - norm_src, axis=-1)
        ee_errors.append(float(np.mean(diff)))

    end_effector_error = float(np.mean(ee_errors))

    # 4. Geodesic Joint Angular Deviation on SO(3)
    sample_indices = np.linspace(0, bvh_src.frame_count - 1, min(100, bvh_src.frame_count), dtype=int)
    ang_errors = []
    for node in bvh_src.nodes:
        if not node.is_end_site:
            c = node.channel_indices
            z_s, y_s, x_s = bvh_src.motion_data[:, c[-3]], bvh_src.motion_data[:, c[-2]], bvh_src.motion_data[:, c[-1]]
            z_p, y_p, x_p = bvh_pred.motion_data[:, c[-3]], bvh_pred.motion_data[:, c[-2]], bvh_pred.motion_data[:, c[-1]]

            R_s = np.array([euler_zyx_to_matrix(z_s[t], y_s[t], x_s[t]) for t in sample_indices])
            R_p = np.array([euler_zyx_to_matrix(z_p[t], y_p[t], x_p[t]) for t in sample_indices])
            ang_errors.append(np.mean(compute_so3_geodesic_degrees(R_s, R_p)))

    angular_geodesic_error = float(np.mean(ang_errors))

    # 5. Ground Penetration & Floating Penalty
    l_toe_idx = j_names_pred.index('LeftToeBase')
    r_toe_idx = j_names_pred.index('RightToeBase')
    min_y = float(min(np.min(pos_pred[:, l_toe_idx, 1]), np.min(pos_pred[:, r_toe_idx, 1])))
    ground_penetration = max(0.0, -min_y)

    # 6. Temporal Consistency
    v_src = compute_velocities(pos_src, dt)
    v_pred = compute_velocities(pos_pred, dt)
    v_src_norm = np.linalg.norm(v_src, axis=-1)
    v_pred_norm = np.linalg.norm(v_pred, axis=-1)
    vel_ratio = float(np.mean(v_pred_norm) / max(1e-6, np.mean(v_src_norm)))

    return {
        "end_effector_error": round(end_effector_error, 6),
        "angular_geodesic_error": round(angular_geodesic_error, 4),
        "bone_length_violation_max": round(max_bone_dev, 6),
        "ground_penetration_penalty": round(ground_penetration, 4),
        "min_foot_height_y": round(min_y, 4),
        "temporal_velocity_ratio": round(vel_ratio, 4),
        "target_avatar": target_type
    }
