import numpy as np

"""
MOTIONFORGE — evaluation/metrics/kinematic_metrics.py
Authoritative kinematic differential metrics using double precision (float64).
"""

def compute_velocities(positions, frame_time=0.0083333):
    """
    Computes first-order temporal forward difference velocities.
    positions: shape (N, J, 3)
    Returns: velocities shape (N-1, J, 3) in units / second
    """
    pos = np.asarray(positions, dtype=np.float64)
    return (pos[1:] - pos[:-1]) / frame_time

def compute_accelerations(positions, frame_time=0.0083333):
    """
    Computes central difference accelerations.
    positions: shape (N, J, 3)
    Returns: accelerations shape (N-2, J, 3) in units / second^2
    """
    pos = np.asarray(positions, dtype=np.float64)
    return (pos[2:] - 2.0 * pos[1:-1] + pos[:-2]) / (frame_time ** 2)

def calculate_mpjpe(pos_pred, pos_gt):
    """
    Mean Per-Joint Position Error across all frames and joints.
    Formula: (1 / (N * J)) * sum_t sum_j || p_pred - p_gt ||_2
    """
    p1 = np.asarray(pos_pred, dtype=np.float64)
    p2 = np.asarray(pos_gt, dtype=np.float64)
    if p1.shape != p2.shape:
        raise ValueError(f"Shape mismatch in MPJPE: {p1.shape} vs {p2.shape}")
    diff = p1 - p2
    per_joint_err = np.linalg.norm(diff, axis=-1)
    return float(np.mean(per_joint_err))

def calculate_velocity_error(pos_pred, pos_gt, frame_time=0.0083333):
    """
    Joint Velocity Error (JVE).
    Formula: (1 / ((N-1) * J)) * sum_t sum_j || v_pred - v_gt ||_2
    """
    v_pred = compute_velocities(pos_pred, frame_time)
    v_gt = compute_velocities(pos_gt, frame_time)
    diff = v_pred - v_gt
    return float(np.mean(np.linalg.norm(diff, axis=-1)))

def calculate_acceleration_error(pos_pred, pos_gt, frame_time=0.0083333):
    """
    Temporal acceleration error between predicted and ground-truth motion.
    """
    a_pred = compute_accelerations(pos_pred, frame_time)
    a_gt = compute_accelerations(pos_gt, frame_time)
    diff = a_pred - a_gt
    return float(np.mean(np.linalg.norm(diff, axis=-1)))

def calculate_jitter_error(pos_pred, pos_gt, frame_time=0.0083333):
    """
    Acceleration jitter penalty matching Phase 3 calibration metric.
    """
    return calculate_acceleration_error(pos_pred, pos_gt, frame_time)

def calculate_motion_preservation_ratio(pos_pred, pos_gt, frame_time=0.0083333):
    """
    Motion Preservation Ratio: sum ||v_pred||^2 / sum ||v_gt||^2.
    Detects flatlining/over-smoothing (R -> 0) and noise amplification (R >> 1).
    """
    v_pred = compute_velocities(pos_pred, frame_time)
    v_gt = compute_velocities(pos_gt, frame_time)
    e_pred = float(np.sum(np.linalg.norm(v_pred, axis=-1) ** 2))
    e_gt = float(np.sum(np.linalg.norm(v_gt, axis=-1) ** 2))
    return float(e_pred / max(1e-6, e_gt))
