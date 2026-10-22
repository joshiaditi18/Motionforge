import os
import sys
import csv
import copy
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RANDOM_SEED = 2026

ELIGIBLE_JOINTS = [
    'LeftArm',
    'RightArm',
    'LeftForeArm',
    'RightForeArm',
    'LeftLeg',
    'RightLeg',
    'LeftFoot',
    'RightFoot',
    'Head'
]

def parse_bvh_with_joint_channels(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    header_lines = []
    motion_line_idx = -1
    for idx, line in enumerate(lines):
        if line.strip().startswith('MOTION'):
            motion_line_idx = idx
            break
        header_lines.append(line.rstrip('\r\n'))

    # Map each joint to channel slice
    joint_channels = {}
    current_joint = None
    channel_cursor = 0

    for line in header_lines:
        parts = line.strip().split()
        if not parts:
            continue
        token = parts[0]
        if token in ['ROOT', 'JOINT']:
            current_joint = parts[1]
        elif token == 'CHANNELS':
            cnt = int(parts[1])
            joint_channels[current_joint] = (channel_cursor, channel_cursor + cnt)
            channel_cursor += cnt

    frame_time = 0.0
    idx = motion_line_idx + 1
    while idx < len(lines):
        line = lines[idx].strip()
        idx += 1
        if line.startswith('Frame Time:'):
            frame_time = float(line.split(':')[1].strip())
            break

    motion_data = []
    while idx < len(lines):
        line = lines[idx].strip()
        idx += 1
        if not line:
            continue
        vals = [float(x) for x in line.split()]
        motion_data.append(vals)

    return header_lines, frame_time, np.array(motion_data, dtype=np.float64), joint_channels

def write_bvh(out_path, header_lines, frame_time, motion_array):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        indent = 0
        for line in header_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped == '}':
                indent = max(0, indent - 1)
            f.write(('\t' * indent) + stripped + '\n')
            if stripped == '{':
                indent += 1

        f.write('MOTION\n')
        f.write(f'Frames: {len(motion_array)}\n')
        f.write(f'Frame Time: {frame_time:.7f}\n')

        for frame in motion_array:
            formatted = " ".join(f"{v:.4f}" for v in frame)
            f.write(formatted + '\n')

def introduce_gap(motion_data, joint_name, joint_channels, gap_type, rng):
    """
    Simulates optical marker occlusion / tracking loss for a joint.
    During the gap interval [start_frame, end_frame], tracking values
    drop out (held frozen at occlusion boundary or zeroed).
    """
    gapped = motion_data.copy()
    num_frames = gapped.shape[0]

    if gap_type == "SHORT":
        gap_len = rng.randint(3, 11)   # 3-10 frames
    elif gap_type == "MEDIUM":
        gap_len = rng.randint(11, 31)  # 11-30 frames
    elif gap_type == "LONG":
        gap_len = rng.randint(31, 61)  # 31-60 frames
    else:
        raise ValueError(f"Unknown gap type: {gap_type}")

    # Ensure gap fits within available frames (leave margin at start and end)
    max_start = max(1, num_frames - gap_len - 5)
    start_frame = rng.randint(5, max_start)
    end_frame = start_frame + gap_len

    c_start, c_end = joint_channels[joint_name]

    # Tracking dropout: hold the pre-dropout boundary pose (typical occlusion artifact)
    freeze_pose = gapped[start_frame - 1, c_start:c_end]
    gapped[start_frame:end_frame, c_start:c_end] = freeze_pose

    return gapped, start_frame, end_frame, gap_len

def generate_all_gaps():
    print("=" * 70)
    print("MOTIONFORGE — STAGE 6B: GENERATE GAP-FILLING / OCCLUSION BENCHMARK")
    print("=" * 70)

    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    clean_dir = os.path.join(workspace_root, "clean", "bvh")
    gap_dir = os.path.join(workspace_root, "public", "gap_filling")
    metadata_dir = os.path.join(workspace_root, "metadata")
    os.makedirs(gap_dir, exist_ok=True)

    rng = np.random.RandomState(RANDOM_SEED)

    metadata_records = []
    gap_types = ["SHORT", "MEDIUM", "LONG"]

    for i in range(1, 31):
        motion_id = f"MF{i:03d}"
        clean_file = f"{motion_id}_clean.bvh"
        clean_path = os.path.join(clean_dir, clean_file)

        headers, frame_time, motion_data, joint_channels = parse_bvh_with_joint_channels(clean_path)

        for gap_type in gap_types:
            gap_id = f"{motion_id}_{gap_type.lower()}"
            out_file = f"{gap_id}.bvh"
            out_path = os.path.join(gap_dir, out_file)

            # Randomly select realistic joint (excluding root)
            selected_joint = rng.choice(ELIGIBLE_JOINTS)
            gapped_data, s_frame, e_frame, g_len = introduce_gap(
                motion_data, selected_joint, joint_channels, gap_type, rng
            )

            write_bvh(out_path, headers, frame_time, gapped_data)

            metadata_records.append({
                'motion_id': motion_id,
                'gap_id': gap_id,
                'joint_name': selected_joint,
                'start_frame': s_frame,
                'end_frame': e_frame,
                'gap_length': g_len,
                'gap_type': gap_type,
                'source_clean_file': os.path.relpath(clean_path, workspace_root),
                'output_file': os.path.relpath(out_path, workspace_root),
                'random_seed': RANDOM_SEED
            })

        print(f"  [OK] Generated SHORT, MEDIUM, LONG gap benchmarks for {motion_id}")

    # Write metadata
    out_csv = os.path.join(metadata_dir, "gap_metadata.csv")
    fieldnames = [
        'motion_id',
        'gap_id',
        'joint_name',
        'start_frame',
        'end_frame',
        'gap_length',
        'gap_type',
        'source_clean_file',
        'output_file',
        'random_seed'
    ]
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in metadata_records:
            writer.writerow(r)

    print(f"\nSaved gap metadata to {out_csv} ({len(metadata_records)} files generated)")
    return True

if __name__ == "__main__":
    generate_all_gaps()
