"""
experiments/denoising_experiments.py — MOTIONFORGE Denoising Algorithms & Benchmarking

Implements:
1. Baseline: Fixed-window Savitzky-Golay with phase unwrapping
2. Alternative: 2nd-order zero-phase Butterworth IIR lowpass filter
3. Alternative: Gaussian kernel smoothing filter
4. Improved/Adaptive: Velocity-adaptive Savitzky-Golay with dynamic windowing and edge-reflection padding
"""

import numpy as np
from scipy.signal import savgol_filter, butter, filtfilt
from scipy.ndimage import gaussian_filter1d
from baselines.common.bvh_io import parse_bvh, write_bvh
from baselines.common.motion_utils import unwrap_euler_degrees, wrap_euler_degrees

def denoise_butterworth(motion_data, noise_level="MEDIUM", sampling_rate=120.0):
    """
    Zero-phase forward-backward Butterworth lowpass filter.
    Cutoff frequencies selected based on noise level:
      LOW:    12.0 Hz cutoff (gentle noise reduction)
      MEDIUM:  8.0 Hz cutoff (standard motion passband)
      HIGH:    5.0 Hz cutoff (aggressive jitter attenuation)
    """
    cutoff_map = {"LOW": 12.0, "MEDIUM": 8.0, "HIGH": 5.0}
    cutoff = cutoff_map.get(noise_level.upper(), 8.0)
    nyquist = sampling_rate / 2.0
    normalized_cutoff = min(0.95, max(0.01, cutoff / nyquist))

    b, a = butter(N=2, Wn=normalized_cutoff, btype='low', analog=False)
    denoised = motion_data.copy()

    # Root translation
    for c in range(3):
        denoised[:, c] = filtfilt(b, a, motion_data[:, c])

    # Rotational channels with phase unwrapping
    rot_unwrapped = unwrap_euler_degrees(motion_data[:, 3:])
    for c in range(rot_unwrapped.shape[1]):
        rot_unwrapped[:, c] = filtfilt(b, a, rot_unwrapped[:, c])

    denoised[:, 3:] = wrap_euler_degrees(rot_unwrapped)
    return denoised

def denoise_gaussian(motion_data, noise_level="MEDIUM"):
    """
    1D Gaussian kernel smoothing across temporal dimension.
    Standard deviation sigma calibrated per noise level:
      LOW:    sigma = 1.0 (approx 8.3 ms kernel)
      MEDIUM: sigma = 1.8 (approx 15 ms kernel)
      HIGH:   sigma = 2.8 (approx 23 ms kernel)
    """
    sigma_map = {"LOW": 1.0, "MEDIUM": 1.8, "HIGH": 2.8}
    sigma = sigma_map.get(noise_level.upper(), 1.8)

    denoised = motion_data.copy()

    for c in range(3):
        denoised[:, c] = gaussian_filter1d(motion_data[:, c], sigma=sigma, mode='nearest')

    rot_unwrapped = unwrap_euler_degrees(motion_data[:, 3:])
    for c in range(rot_unwrapped.shape[1]):
        rot_unwrapped[:, c] = gaussian_filter1d(rot_unwrapped[:, c], sigma=sigma, mode='nearest')

    denoised[:, 3:] = wrap_euler_degrees(rot_unwrapped)
    return denoised

def denoise_adaptive_savgol(motion_data, noise_level="MEDIUM"):
    """
    Velocity-adaptive Savitzky-Golay with edge-reflection padding.
    Adapts smoothing intensity:
    - High velocity / rapid inflection segments use tighter window to preserve peak kinetics.
    - Low velocity / steady-state segments use calibrated window to maximize jitter elimination.
    - Uses mode='mirror' padding to eliminate Runge boundary distortions at sequence edges.
    """
    num_frames, num_channels = motion_data.shape
    denoised = motion_data.copy()

    # Base parameters per noise level
    if noise_level.upper() == "LOW":
        w_base = 7
        w_tight = 5
        poly = 2
    elif noise_level.upper() == "HIGH":
        w_base = 19
        w_tight = 11
        poly = 2
    else:  # MEDIUM
        w_base = 13
        w_tight = 7
        poly = 2

    # Clamp window size to sequence length
    if w_base >= num_frames:
        w_base = max(3, (num_frames // 2) * 2 - 1)
    if w_tight >= num_frames:
        w_tight = max(3, (num_frames // 2) * 2 - 1)

    # 1. Root translation
    for c in range(3):
        denoised[:, c] = savgol_filter(motion_data[:, c], window_length=w_base, polyorder=poly, mode='mirror')

    # 2. Rotations
    rot_unwrapped = unwrap_euler_degrees(motion_data[:, 3:])

    # Compute angular velocity magnitude across channels to detect high-dynamic regions
    if num_frames > 2:
        diffs = np.diff(rot_unwrapped, axis=0)
        vel_mag = np.linalg.norm(diffs, axis=1)  # (N-1,)
        vel_mag = np.pad(vel_mag, (0, 1), mode='edge')
        # Dynamic threshold (75th percentile of angular velocity)
        thresh = np.percentile(vel_mag, 75)
        # Weight mask: 0 (steady) to 1 (high dynamic)
        alpha = np.clip((vel_mag - thresh) / max(1e-5, thresh * 0.5), 0.0, 1.0)[:, None]
    else:
        alpha = np.zeros((num_frames, 1))

    # Compute base filtered and tight filtered
    for c in range(rot_unwrapped.shape[1]):
        ch_data = rot_unwrapped[:, c]
        f_base = savgol_filter(ch_data, window_length=w_base, polyorder=poly, mode='mirror')
        f_tight = savgol_filter(ch_data, window_length=w_tight, polyorder=poly, mode='mirror')
        # Blend: preserve tight features during high-velocity bursts
        rot_unwrapped[:, c] = (1.0 - alpha[:, 0]) * f_base + alpha[:, 0] * f_tight

    denoised[:, 3:] = wrap_euler_degrees(rot_unwrapped)
    return denoised

def run_denoising_experiment(input_bvh, output_bvh, noise_level="MEDIUM", method="adaptive_savgol"):
    """
    Executes specified denoising method on an input BVH file.
    """
    bvh = parse_bvh(input_bvh)

    if method == "baseline_savgol":
        from baselines.denoising.baseline_denoising import denoise_motion_data
        bvh.motion_data = denoise_motion_data(bvh.motion_data, noise_level=noise_level)
    elif method == "butterworth":
        bvh.motion_data = denoise_butterworth(bvh.motion_data, noise_level=noise_level)
    elif method == "gaussian":
        bvh.motion_data = denoise_gaussian(bvh.motion_data, noise_level=noise_level)
    elif method == "adaptive_savgol":
        bvh.motion_data = denoise_adaptive_savgol(bvh.motion_data, noise_level=noise_level)
    else:
        raise ValueError(f"Unknown denoising method: {method}")

    write_bvh(output_bvh, bvh)
    return output_bvh
