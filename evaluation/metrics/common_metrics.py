import numpy as np

"""
MOTIONFORGE — evaluation/metrics/common_metrics.py
Common mathematical and numerical validation utilities for evaluation engine.
"""

def validate_motion_array(arr, expected_frames=None, expected_channels=96):
    """
    Validates that a motion array is well-formed, non-empty, and free of NaN/Inf.
    Returns: (is_valid, error_msg)
    """
    if arr is None or not isinstance(arr, np.ndarray):
        return False, "Motion data is not a valid numpy ndarray"

    if arr.ndim != 2:
        return False, f"Motion data has {arr.ndim} dimensions, expected 2"

    if arr.shape[0] == 0:
        return False, "Motion data contains 0 frames"

    if arr.shape[1] != expected_channels:
        return False, f"Motion data has {arr.shape[1]} channels, expected {expected_channels}"

    if expected_frames is not None and arr.shape[0] != expected_frames:
        return False, f"Motion data has {arr.shape[0]} frames, expected {expected_frames}"

    if np.isnan(arr).any():
        return False, "Motion data contains NaN values"

    if np.isinf(arr).any():
        return False, "Motion data contains Inf values"

    return True, None

def compute_so3_geodesic_degrees(R1, R2):
    """
    Computes geodesic distance on SO(3) between pairs of 3x3 rotation matrices in degrees.
    Formula: theta = arccos(clip((trace(R1 * R2^T) - 1) / 2, -1, 1)) * 180 / pi
    Args:
        R1, R2: arrays of shape (N, 3, 3) or (3, 3)
    Returns:
        theta: array of shape (N,) or scalar float in degrees
    """
    R_rel = np.einsum('...ij,...kj->...ik', R1, R2)
    traces = np.trace(R_rel, axis1=-2, axis2=-1)
    cos_theta = np.clip((traces - 1.0) / 2.0, -1.0, 1.0)
    theta_rad = np.arccos(cos_theta)
    return np.degrees(theta_rad)
