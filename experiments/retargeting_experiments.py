"""
experiments/retargeting_experiments.py — MOTIONFORGE Retargeting Algorithms & Benchmarking

Implements:
1. Baseline: Proportional bone scaling + average (thigh+shin)/2 root scaling
2. Alternative: Full-Kinematic Chain Leg Height Scaling (exact thigh + shin + foot rest length)
3. Alternative: Ground-Contact Aware Clamping with Foot-Sliding & Penetration Diagnostics
"""

import numpy as np
from baselines.common.bvh_io import parse_bvh, write_bvh
from baselines.common.skeleton_utils import get_bone_lengths
from baselines.common.forward_kinematics import compute_forward_kinematics
from baselines.retargeting.baseline_retargeting import TARGET_CONFIGS, retarget_hierarchy_offsets

def compute_kinematic_leg_scale(bvh_struct, config):
    """
    Computes exact rest leg height ratio between target and source:
      H = L(thigh) + L(shin) + L(foot)
      H_target = s_thigh*L(thigh) + s_shin*L(shin) + s_foot*L(foot)
    """
    bone_lens = get_bone_lengths(bvh_struct)

    # Search for thigh, shin, foot bone names
    l_thigh = bone_lens.get('LeftLeg', bone_lens.get('LeftUpLeg', 17.5))
    l_shin = bone_lens.get('LeftFoot', bone_lens.get('LeftLeg', 16.0))
    l_foot = bone_lens.get('LeftToeBase', 5.0)

    h_src = max(1.0, l_thigh + l_shin + l_foot)
    h_tgt = (
        l_thigh * config['thigh_scale'] +
        l_shin * config['shin_scale'] +
        l_foot * config['foot_scale']
    )
    return float(h_tgt / h_src)

def retarget_motion_full_chain(source_bvh_path, output_bvh_path, target_type="target_medium"):
    """
    Retargets motion using full-kinematic chain leg scaling to preserve ground clearance.
    """
    cfg = TARGET_CONFIGS[target_type]
    bvh = parse_bvh(source_bvh_path)

    # 1. Update hierarchy offsets
    retargeted_headers = retarget_hierarchy_offsets(bvh, cfg)

    # 2. Scale root Y by exact full-chain leg ratio
    leg_scale = compute_kinematic_leg_scale(bvh, cfg)
    retargeted_motion = bvh.motion_data.copy()
    retargeted_motion[:, 1] = retargeted_motion[:, 1] * leg_scale

    write_bvh(output_bvh_path, retargeted_headers, bvh.frame_time, retargeted_motion)
    return output_bvh_path

def retarget_motion_contact_aware(source_bvh_path, output_bvh_path, target_type="target_medium"):
    """
    Retargets motion with full-chain leg scaling AND dynamic ground-penetration clamping.
    Evaluates foot height and shifts root Y if toe/foot drops below the contact floor plane.
    """
    cfg = TARGET_CONFIGS[target_type]
    bvh = parse_bvh(source_bvh_path)

    # 1. Update hierarchy offsets
    retargeted_headers = retarget_hierarchy_offsets(bvh, cfg)

    # 2. Base full-chain scaling
    leg_scale = compute_kinematic_leg_scale(bvh, cfg)
    retargeted_motion = bvh.motion_data.copy()
    retargeted_motion[:, 1] = retargeted_motion[:, 1] * leg_scale

    # Write initial candidate to calculate FK accurately with new hierarchy offsets
    write_bvh(output_bvh_path, retargeted_headers, bvh.frame_time, retargeted_motion)
    bvh_candidate = parse_bvh(output_bvh_path)

    # Compute FK on candidate
    pos_pred, j_names = compute_forward_kinematics(bvh_candidate, include_end_sites=False)
    l_toe_idx = j_names.index('LeftToeBase')
    r_toe_idx = j_names.index('RightToeBase')

    # Find per-frame lowest foot coordinate
    min_foot_y = np.minimum(pos_pred[:, l_toe_idx, 1], pos_pred[:, r_toe_idx, 1])

    # Dynamic floor clamp: if foot goes below 0.0, elevate root smoothly
    floor_penetration = np.maximum(0.0, -min_foot_y)
    if np.any(floor_penetration > 0.0):
        from scipy.ndimage import maximum_filter1d
        smooth_offset = maximum_filter1d(floor_penetration, size=15)
        retargeted_motion[:, 1] += smooth_offset
        write_bvh(output_bvh_path, retargeted_headers, bvh.frame_time, retargeted_motion)

    return output_bvh_path

def compute_foot_sliding_diagnostics(bvh_struct, contact_thresh=0.907):
    """
    Calculates detailed foot contact and sliding diagnostics:
    - Contact ratio (% of frames where foot is grounded)
    - Mean sliding speed during stance phase (in/s)
    - Cumulative sliding distance (inches)
    """
    dt = bvh_struct.frame_time if bvh_struct.frame_time > 0 else 0.0083333
    pos, j_names = compute_forward_kinematics(bvh_struct, include_end_sites=False)

    l_idx = j_names.index('LeftToeBase')
    r_idx = j_names.index('RightToeBase')

    from evaluation.metrics.kinematic_metrics import compute_velocities
    vel = compute_velocities(pos, dt)

    l_hvel = np.linalg.norm(vel[:, l_idx, [0, 2]], axis=-1)
    r_hvel = np.linalg.norm(vel[:, r_idx, [0, 2]], axis=-1)

    l_contact = l_hvel < contact_thresh
    r_contact = r_hvel < contact_thresh

    l_sliding = float(np.mean(l_hvel[l_contact])) if np.any(l_contact) else 0.0
    r_sliding = float(np.mean(r_hvel[r_contact])) if np.any(r_contact) else 0.0

    return {
        "left_foot_contact_ratio": round(float(np.mean(l_contact)), 4),
        "right_foot_contact_ratio": round(float(np.mean(r_contact)), 4),
        "left_foot_sliding_speed": round(l_sliding, 4),
        "right_foot_sliding_speed": round(r_sliding, 4),
        "mean_skating_speed": round((l_sliding + r_sliding) / 2.0, 4)
    }

def run_retargeting_experiment(source_bvh, output_bvh, target_type="target_medium", method="contact_aware"):
    """
    Executes specified retargeting method on source BVH.
    """
    if method == "baseline":
        from baselines.retargeting.baseline_retargeting import retarget_motion
        return retarget_motion(source_bvh, output_bvh, target_type=target_type)
    elif method == "full_chain":
        return retarget_motion_full_chain(source_bvh, output_bvh, target_type=target_type)
    elif method == "contact_aware":
        return retarget_motion_contact_aware(source_bvh, output_bvh, target_type=target_type)
    else:
        raise ValueError(f"Unknown retargeting method: {method}")
