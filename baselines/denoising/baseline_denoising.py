import os
import sys
import argparse
import numpy as np
from scipy.signal import savgol_filter

# Ensure common utilities can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "common")))
from bvh_io import parse_bvh, write_bvh
from motion_utils import unwrap_euler_degrees, wrap_euler_degrees

"""
MOTIONFORGE — baselines/denoising/baseline_denoising.py
Baseline motion denoising algorithm using phase-unwrapped Savitzky-Golay polynomial filtering.
Removes high-frequency jitter while preserving low-frequency deliberate motion dynamics.
"""

def denoise_motion_data(motion_data, noise_level="MEDIUM"):
    """
    Applies calibrated temporal smoothing to motion channels.
    Args:
        motion_data: np.ndarray shape (N, 96)
        noise_level: 'LOW', 'MEDIUM', or 'HIGH'
    Returns:
        denoised_data: np.ndarray shape (N, 96)
    """
    num_frames, num_channels = motion_data.shape
    denoised = motion_data.copy()

    # Determine filter window based on noise level
    # 120 FPS: 9 frames = 75ms window; 15 frames = 125ms; 21 frames = 175ms
    if noise_level.upper() == "LOW":
        window_length = 7
        polyorder = 2
    elif noise_level.upper() == "MEDIUM":
        window_length = 13
        polyorder = 2
    elif noise_level.upper() == "HIGH":
        window_length = 19
        polyorder = 2
    else:
        window_length = 13
        polyorder = 2

    # Window length must be odd and less than number of frames
    if window_length >= num_frames:
        window_length = max(3, (num_frames // 2) * 2 - 1)

    if window_length <= polyorder:
        polyorder = max(1, window_length - 1)

    # 1. Denoise root translation (channels 0, 1, 2)
    for c in range(3):
        denoised[:, c] = savgol_filter(motion_data[:, c], window_length=window_length, polyorder=polyorder)

    # 2. Denoise rotational channels (channels 3 to 95) with phase unwrapping
    # Crucial: Unwrapping eliminates false jumps at +/- 180 degree gimbal boundaries
    rot_channels = motion_data[:, 3:]
    unwrapped_rot = unwrap_euler_degrees(rot_channels)

    for c in range(unwrapped_rot.shape[1]):
        unwrapped_rot[:, c] = savgol_filter(unwrapped_rot[:, c], window_length=window_length, polyorder=polyorder)

    # Wrap back to [-180, 180]
    denoised[:, 3:] = wrap_euler_degrees(unwrapped_rot)

    return denoised

def run_denoising(input_bvh, output_bvh, noise_level="MEDIUM"):
    bvh = parse_bvh(input_bvh)
    denoised_motion = denoise_motion_data(bvh.motion_data, noise_level)
    bvh.motion_data = denoised_motion
    write_bvh(output_bvh, bvh)
    return output_bvh

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MOTIONFORGE Baseline Motion Denoising")
    parser.add_argument("--input", required=True, help="Path to input noisy BVH")
    parser.add_argument("--output", required=True, help="Path to output denoised BVH")
    parser.add_argument("--level", default="MEDIUM", choices=["LOW", "MEDIUM", "HIGH"], help="Noise difficulty level")
    args = parser.parse_args()

    run_denoising(args.input, args.output, args.level)
    print(f"Successfully generated denoised motion: {args.output}")
