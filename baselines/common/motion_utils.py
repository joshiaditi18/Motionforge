import numpy as np

"""
MOTIONFORGE — baselines/common/motion_utils.py
Kinematic motion utilities: velocities, accelerations, jitter,
Euler angle unwrapping/wrapping, and geodesic distance metrics.
"""

def unwrap_euler_degrees(angles_deg):
    """
    Unwraps time-series Euler angle trajectories to prevent 360-degree phase wrap discontinuities.
    Args:
        angles_deg: np.ndarray shape (N, C) in degrees
    Returns:
        unwrapped_deg: np.ndarray shape (N, C) continuous angles
    """
    rad = np.radians(angles_deg)
    unwrapped_rad = np.unwrap(rad, axis=0)
    return np.degrees(unwrapped_rad)

def wrap_euler_degrees(angles_deg):
    """
    Wraps continuous Euler angles back into canonical range [-180, 180] degrees.
    """
    return (angles_deg + 180.0) % 360.0 - 180.0

def compute_velocities(positions, frame_time=0.0083333):
    """
    Computes first-order temporal forward difference velocities.
    positions: shape (N, J, 3)
    Returns: velocities shape (N-1, J, 3)
    """
    return (positions[1:] - positions[:-1]) / frame_time

def compute_accelerations(positions, frame_time=0.0083333):
    """
    Computes central difference accelerations.
    positions: shape (N, J, 3)
    Returns: accelerations shape (N-2, J, 3)
    """
    # a_t = (p_{t+1} - 2*p_t + p_{t-1}) / dt^2
    return (positions[2:] - 2 * positions[1:-1] + positions[:-2]) / (frame_time ** 2)

def calculate_mpjpe(pos_pred, pos_gt):
    """
    Mean Per-Joint Position Error across all frames and joints.
    pos_pred, pos_gt: shape (N, J, 3)
    """
    assert pos_pred.shape == pos_gt.shape, "Shape mismatch between prediction and ground truth"
    diff = pos_pred - pos_gt
    per_joint_err = np.linalg.norm(diff, axis=-1)  # shape (N, J)
    return float(np.mean(per_joint_err))

def calculate_velocity_error(pos_pred, pos_gt, frame_time=0.0083333):
    """
    Joint Velocity Error (JVE).
    """
    v_pred = compute_velocities(pos_pred, frame_time)
    v_gt = compute_velocities(pos_gt, frame_time)
    diff = v_pred - v_gt
    return float(np.mean(np.linalg.norm(diff, axis=-1)))

def calculate_jitter_error(pos_pred, pos_gt, frame_time=0.0083333):
    """
    Acceleration jitter deviation between predicted and ground-truth motion.
    """
    a_pred = compute_accelerations(pos_pred, frame_time)
    a_gt = compute_accelerations(pos_gt, frame_time)
    diff = a_pred - a_gt
    return float(np.mean(np.linalg.norm(diff, axis=-1)))
