import os
import sys
import argparse
import numpy as np
from scipy.interpolate import CubicSpline

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "common")))
from bvh_io import parse_bvh, write_bvh
from motion_utils import unwrap_euler_degrees, wrap_euler_degrees

"""
MOTIONFORGE — baselines/gap_filling/baseline_gap_filling.py
Baseline gap-filling algorithm supporting linear interpolation and cubic spline
interpolation over occluded joint intervals while strictly preserving observed frames.
"""

def detect_gap_interval(motion_data, min_length=3):
    """
    Auto-detects frozen channel segment representing marker loss.
    Returns: (joint_channels_slice, start_frame, end_frame)
    """
    num_frames, num_channels = motion_data.shape
    best_joint_slice = None
    best_start = -1
    best_end = -1
    max_len = 0

    # Look across rotational 3-channel blocks (channels 3 to 95)
    for c in range(3, num_channels, 3):
        diffs = np.abs(motion_data[1:, c:c+3] - motion_data[:-1, c:c+3])
        is_frozen = np.all(diffs < 1e-5, axis=1)

        # Find longest continuous frozen run
        run_start = -1
        for t, frozen in enumerate(is_frozen):
            if frozen:
                if run_start == -1:
                    run_start = t
            else:
                if run_start != -1:
                    length = t - run_start + 1
                    if length >= min_length and length > max_len:
                        max_len = length
                        best_joint_slice = (c, c+3)
                        best_start = run_start + 1
                        best_end = t + 1
                    run_start = -1
        if run_start != -1:
            length = len(is_frozen) - run_start + 1
            if length >= min_length and length > max_len:
                max_len = length
                best_joint_slice = (c, c+3)
                best_start = run_start + 1
                best_end = len(is_frozen)

    return best_joint_slice, best_start, best_end

def inpaint_gap(motion_data, start_frame, end_frame, channel_slice, method="cubic"):
    """
    Inpaints the interval [start_frame, end_frame] for specified channel_slice.
    Preserves all observed frames strictly untouched.
    """
    filled = motion_data.copy()
    c_start, c_end = channel_slice
    N = motion_data.shape[0]

    # Pre-gap anchor and Post-gap anchor
    idx_pre = max(0, start_frame - 1)
    idx_post = min(N - 1, end_frame)

    if idx_pre >= idx_post:
        return filled

    # Unwrap angles across anchors
    raw_segment = motion_data[:, c_start:c_end]
    unwrapped = unwrap_euler_degrees(raw_segment)

    gap_indices = np.arange(start_frame, end_frame)
    gap_len = end_frame - start_frame

    # Use linear interpolation for short gaps or fallback
    if method == "linear" or gap_len <= 5 or idx_pre < 2 or idx_post > N - 3:
        for ch in range(c_end - c_start):
            y_pre = unwrapped[idx_pre, ch]
            y_post = unwrapped[idx_post, ch]
            alpha = (gap_indices - idx_pre) / (idx_post - idx_pre)
            unwrapped[gap_indices, ch] = y_pre + alpha * (y_post - y_pre)
    else:
        # Cubic spline interpolation using multiple boundary anchor points for velocity continuity
        anchors_x = np.array([idx_pre - 2, idx_pre - 1, idx_pre, idx_post, idx_post + 1, idx_post + 2])
        anchors_x = np.clip(anchors_x, 0, N - 1)
        anchors_x = np.unique(anchors_x)

        if len(anchors_x) >= 4:
            for ch in range(c_end - c_start):
                anchors_y = unwrapped[anchors_x, ch]
                cs = CubicSpline(anchors_x, anchors_y, bc_type='natural')
                unwrapped[gap_indices, ch] = cs(gap_indices)
        else:
            # Fallback to linear
            for ch in range(c_end - c_start):
                y_pre = unwrapped[idx_pre, ch]
                y_post = unwrapped[idx_post, ch]
                alpha = (gap_indices - idx_pre) / (idx_post - idx_pre)
                unwrapped[gap_indices, ch] = y_pre + alpha * (y_post - y_pre)

    # Re-wrap
    filled[gap_indices, c_start:c_end] = wrap_euler_degrees(unwrapped[gap_indices])
    return filled

def run_gap_filling(input_bvh, output_bvh, start_frame=None, end_frame=None, channel_slice=None, joint_name=None, method="cubic"):
    bvh = parse_bvh(input_bvh)

    if joint_name is not None and channel_slice is None:
        if joint_name in bvh.node_by_name:
            node = bvh.node_by_name[joint_name]
            channel_slice = (node.channel_indices[0], node.channel_indices[-1] + 1)

    if start_frame is None or end_frame is None or channel_slice is None:
        ch_slice, s_f, e_f = detect_gap_interval(bvh.motion_data)
        if ch_slice is None:
            # No gap detected, write original
            write_bvh(output_bvh, bvh)
            return output_bvh
    else:
        ch_slice, s_f, e_f = channel_slice, start_frame, end_frame

    inpainted_motion = inpaint_gap(bvh.motion_data, s_f, e_f, ch_slice, method=method)
    bvh.motion_data = inpainted_motion
    write_bvh(output_bvh, bvh)
    return output_bvh

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MOTIONFORGE Baseline Gap Filling")
    parser.add_argument("--input", required=True, help="Path to input gapped BVH")
    parser.add_argument("--output", required=True, help="Path to output filled BVH")
    parser.add_argument("--method", default="cubic", choices=["linear", "cubic"], help="Interpolation method")
    parser.add_argument("--joint", default=None, help="Target occluded joint name")
    parser.add_argument("--start_frame", type=int, default=None, help="Start frame of gap")
    parser.add_argument("--end_frame", type=int, default=None, help="End frame of gap")
    args = parser.parse_args()

    run_gap_filling(args.input, args.output, args.start_frame, args.end_frame, joint_name=args.joint, method=args.method)
    print(f"Successfully generated gap-filled motion: {args.output}")

