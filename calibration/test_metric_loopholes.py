import os
import sys
import numpy as np
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from baselines.common.bvh_io import parse_bvh, write_bvh
from baselines.common.forward_kinematics import compute_forward_kinematics
from baselines.common.motion_utils import (
    calculate_mpjpe,
    calculate_velocity_error,
    calculate_jitter_error,
    compute_velocities
)

"""
MOTIONFORGE — calibration/test_metric_loopholes.py
Tests potential metric exploits, loopholes, and failure modes:
1. Identity Copy (raw corrupted input submitted without processing)
2. Constant / Flatline Pose (repeating initial static T-pose to minimize jitter)
3. Excessive Over-smoothing (extreme lowpass filtering to eliminate jitter at expense of dynamics)
4. Uniform Scaling Trick for Retargeting (attempting uniform scaling rather than morphology re-weighting)
"""

def evaluate_denoising_sample(pred_bvh, gt_bvh):
    pos_gt, _ = compute_forward_kinematics(gt_bvh, include_end_sites=False)
    pos_pred, _ = compute_forward_kinematics(pred_bvh, include_end_sites=False)

    mpjpe = calculate_mpjpe(pos_pred, pos_gt)
    jve = calculate_velocity_error(pos_pred, pos_gt, gt_bvh.frame_time)
    jitter = calculate_jitter_error(pos_pred, pos_gt, gt_bvh.frame_time)

    v_gt = compute_velocities(pos_gt, gt_bvh.frame_time)
    v_pred = compute_velocities(pos_pred, gt_bvh.frame_time)
    e_gt = float(np.sum(np.linalg.norm(v_gt, axis=-1) ** 2))
    e_pred = float(np.sum(np.linalg.norm(v_pred, axis=-1) ** 2))
    pres_ratio = e_pred / max(1e-6, e_gt)

    return {
        'mpjpe': round(mpjpe, 4),
        'jve': round(jve, 4),
        'jitter': round(jitter, 2),
        'pres_ratio': round(pres_ratio, 4)
    }

def run_exploit_tests():
    print("=" * 80)
    print("MOTIONFORGE — PHASE 3: TESTING METRIC EXPLOITS AND CORNER CASES")
    print("=" * 80)

    clean_file = os.path.join(BASE_DIR, "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh")
    noisy_file = os.path.join(BASE_DIR, "MOTIONFORGE_DATASET", "public", "denoising", "MF001_medium.bvh")

    bvh_gt = parse_bvh(clean_file)
    bvh_noisy = parse_bvh(noisy_file)

    # 1. Baseline submission
    from baselines.denoising.baseline_denoising import denoise_motion_data
    bvh_base = parse_bvh(noisy_file)
    bvh_base.motion_data = denoise_motion_data(bvh_noisy.motion_data, "MEDIUM")
    m_base = evaluate_denoising_sample(bvh_base, bvh_gt)

    # 2. Exploit A: Identity Copy (No cleaning)
    m_raw = evaluate_denoising_sample(bvh_noisy, bvh_gt)

    # 3. Exploit B: Static Flatline Pose (Repeats Frame 0)
    bvh_flat = parse_bvh(noisy_file)
    bvh_flat.motion_data = np.repeat(bvh_noisy.motion_data[:1], bvh_noisy.frame_count, axis=0)
    m_flat = evaluate_denoising_sample(bvh_flat, bvh_gt)

    # 4. Exploit C: Extreme Over-smoothing (101-frame window polynomial filter)
    from scipy.signal import savgol_filter
    from baselines.common.motion_utils import unwrap_euler_degrees, wrap_euler_degrees
    bvh_over = parse_bvh(noisy_file)
    over_data = bvh_over.motion_data.copy()
    for c in range(3):
        over_data[:, c] = savgol_filter(over_data[:, c], 101, 1)
    unwr = unwrap_euler_degrees(over_data[:, 3:])
    for c in range(unwr.shape[1]):
        unwr[:, c] = savgol_filter(unwr[:, c], 101, 1)
    over_data[:, 3:] = wrap_euler_degrees(unwr)
    bvh_over.motion_data = over_data
    m_over = evaluate_denoising_sample(bvh_over, bvh_gt)

    # Print results comparison
    print(f"\nExploit Comparison on MF001 (MEDIUM Noise):")
    print(f"{'Method / Exploit':<30} | {'MPJPE':<10} | {'JVE':<10} | {'Jitter':<10} | {'Preservation Ratio':<18}")
    print("-" * 88)
    print(f"{'Calibrated Baseline':<30} | {m_base['mpjpe']:<10} | {m_base['jve']:<10} | {m_base['jitter']:<10} | {m_base['pres_ratio']:<18}")
    print(f"{'Exploit A: Raw Corrupted Copy':<30} | {m_raw['mpjpe']:<10} | {m_raw['jve']:<10} | {m_raw['jitter']:<10} | {m_raw['pres_ratio']:<18}")
    print(f"{'Exploit B: Flatline T-Pose':<30} | {m_flat['mpjpe']:<10} | {m_flat['jve']:<10} | {m_flat['jitter']:<10} | {m_flat['pres_ratio']:<18}")
    print(f"{'Exploit C: Extreme Oversmoothing':<30} | {m_over['mpjpe']:<10} | {m_over['jve']:<10} | {m_over['jitter']:<10} | {m_over['pres_ratio']:<18}")

    return {
        'baseline': m_base,
        'raw_copy': m_raw,
        'flatline': m_flat,
        'oversmoothing': m_over
    }

if __name__ == "__main__":
    run_exploit_tests()
