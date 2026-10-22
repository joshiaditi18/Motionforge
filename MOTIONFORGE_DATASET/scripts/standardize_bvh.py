import os
import sys
import glob
import math
import shutil
import csv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

MOTIONS = [
    (1, 7, 1, "walk"),
    (2, 7, 4, "slow walk"),
    (3, 8, 7, "walk, exaggerated stride"),
    (4, 8, 9, "walk"),
    (5, 9, 1, "run"),
    (6, 9, 5, "run"),
    (7, 16, 1, "jump"),
    (8, 16, 3, "high jump"),
    (9, 16, 5, "forward jump"),
    (10, 16, 8, "run/jog, sudden stop"),
    (11, 16, 11, "walk, veer left"),
    (12, 35, 14, "walk"),
    (13, 35, 33, "walk"),
    (14, 35, 27, "navigate around obstacles"),
    (15, 38, 3, "run around in a circle"),
    (16, 38, 4, "walk around, frequent turns, cyclic walk along a line"),
    (17, 49, 2, "jump up and down, hop on one foot"),
    (18, 49, 4, "run, leap"),
    (19, 49, 6, "cartwheel"),
    (20, 60, 1, "salsa dance"),
    (21, 60, 2, "salsa dance"),
    (22, 75, 1, "run jump"),
    (23, 75, 6, "180 jump"),
    (24, 86, 3, "walking, running, jumping, kicking, and stretching"),
    (25, 86, 6, "walking, running, kicking, punching, knee kicking, and stretching"),
    (26, 103, 3, "charleston_01"),
    (27, 104, 1, "JogThrough"),
    (28, 127, 4, "Walk to Run"),
    (29, 140, 8, "Get Up From Ground Laying on Back"),
    (30, 144, 20, "Punch_Sequence")
]

def parse_bvh(filepath):
    """
    Parses a BVH file, validating its hierarchy, channels, and motion frames.
    Returns:
        header_lines: List of hierarchy lines
        num_channels: Total degrees of freedom across all joints
        declared_frames: Declared frame count
        frame_time: Declared sampling time
        motion_data: 2D list of float values (frames x channels)
        joints: List of joint names in order
        root_name: Name of root joint
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    header_lines = []
    motion_line_idx = -1
    for idx, line in enumerate(lines):
        if line.strip().startswith('MOTION'):
            motion_line_idx = idx
            break
        header_lines.append(line.rstrip('\r\n'))

    if motion_line_idx == -1:
        raise ValueError(f"No MOTION section found in {filepath}")

    # Inspect hierarchy
    joints = []
    root_name = None
    num_channels = 0
    brace_depth = 0

    for line in header_lines:
        parts = line.strip().split()
        if not parts:
            continue
        token = parts[0]
        if token == '{':
            brace_depth += 1
        elif token == '}':
            brace_depth -= 1
        elif token == 'ROOT':
            root_name = parts[1]
            joints.append(parts[1])
        elif token == 'JOINT':
            joints.append(parts[1])
        elif token == 'CHANNELS':
            num_channels += int(parts[1])

    if brace_depth != 0:
        raise ValueError(f"Unmatched braces in hierarchy of {filepath} (depth={brace_depth})")

    # Read MOTION metadata
    declared_frames = 0
    frame_time = 0.0

    idx = motion_line_idx + 1
    while idx < len(lines):
        line = lines[idx].strip()
        idx += 1
        if line.startswith('Frames:'):
            declared_frames = int(line.split(':')[1].strip())
        elif line.startswith('Frame Time:'):
            frame_time = float(line.split(':')[1].strip())
            break

    # Read motion frames
    motion_data = []
    while idx < len(lines):
        line = lines[idx].strip()
        idx += 1
        if not line:
            continue
        vals = [float(x) for x in line.split()]
        if len(vals) != num_channels:
            raise ValueError(f"Frame {len(motion_data)+1} has {len(vals)} channels, expected {num_channels}")
        for v in vals:
            if math.isnan(v) or math.isinf(v):
                raise ValueError(f"NaN or Inf detected in motion data of {filepath}")
        motion_data.append(vals)

    actual_frames = len(motion_data)
    if declared_frames != actual_frames:
        print(f"  Warning: Header declared {declared_frames} frames but found {actual_frames} frames.")

    return header_lines, num_channels, actual_frames, frame_time, motion_data, joints, root_name

def write_standardized_bvh(out_path, header_lines, frame_time, motion_data):
    """Writes standardized BVH with clean indentation and normalized numeric floats."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        # Write clean hierarchy
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

        # Write MOTION header
        f.write('MOTION\n')
        f.write(f'Frames: {len(motion_data)}\n')
        f.write(f'Frame Time: {frame_time:.7f}\n')

        # Write frames
        for frame in motion_data:
            formatted = " ".join(f"{v:.4f}" for v in frame)
            f.write(formatted + '\n')

def standardize_all():
    print("=" * 70)
    print("MOTIONFORGE — STAGE 4: STANDARDIZE BVH & CREATE MASTER GROUND TRUTH")
    print("=" * 70)

    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    source_dir = os.path.join(workspace_root, "source", "cmu_original")
    clean_dir = os.path.join(workspace_root, "clean", "bvh")
    hidden_dir = os.path.join(workspace_root, "hidden", "ground_truth")
    metadata_dir = os.path.join(workspace_root, "metadata")

    os.makedirs(clean_dir, exist_ok=True)
    os.makedirs(hidden_dir, exist_ok=True)
    os.makedirs(metadata_dir, exist_ok=True)

    motions_metadata = []

    for idx, s, t, desc in MOTIONS:
        motion_id = f"MF{idx:03d}"
        in_bvh_path = os.path.join(source_dir, f"subject_{s:02d}_trial_{t:02d}", f"{s:02d}_{t:02d}.bvh")
        clean_bvh_name = f"{motion_id}_clean.bvh"
        clean_bvh_path = os.path.join(clean_dir, clean_bvh_name)
        hidden_bvh_path = os.path.join(hidden_dir, clean_bvh_name)

        print(f"Standardizing [{idx}/30] {motion_id} (Subject {s}, Trial {t}: '{desc}')...")

        if not os.path.exists(in_bvh_path):
            raise FileNotFoundError(f"Source file not found: {in_bvh_path}")

        headers, num_channels, frames, f_time, motion_data, joints, root_name = parse_bvh(in_bvh_path)
        fps = round(1.0 / f_time)
        duration = round(frames * f_time, 3)

        # Write standardized clean BVH
        write_standardized_bvh(clean_bvh_path, headers, f_time, motion_data)

        # Mirror securely to hidden ground truth
        shutil.copy2(clean_bvh_path, hidden_bvh_path)

        motions_metadata.append({
            'motion_id': motion_id,
            'cmu_subject': s,
            'cmu_trial': t,
            'description': desc,
            'fps': fps,
            'frame_count': frames,
            'duration_seconds': duration,
            'joint_count': len(joints),
            'root_joint': root_name,
            'source_format': 'BVH (from CMU ASF/AMC)',
            'source_path': os.path.relpath(in_bvh_path, workspace_root),
            'clean_bvh_path': os.path.relpath(clean_bvh_path, workspace_root)
        })

        print(f"  [OK] Standardized: {frames} frames, {fps} FPS, {len(joints)} joints, {num_channels} channels -> {clean_bvh_name}")

    # Write metadata/motions.csv
    out_csv = os.path.join(metadata_dir, "motions.csv")
    fieldnames = [
        'motion_id',
        'cmu_subject',
        'cmu_trial',
        'description',
        'fps',
        'frame_count',
        'duration_seconds',
        'joint_count',
        'root_joint',
        'source_format',
        'source_path',
        'clean_bvh_path'
    ]
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in motions_metadata:
            writer.writerow(r)
    print(f"\nSaved master clean inventory to {out_csv}")

    # Also write to top-level metadata if different
    top_metadata_csv = os.path.join(workspace_root, "..", "metadata", "motions.csv")
    os.makedirs(os.path.dirname(top_metadata_csv), exist_ok=True)
    shutil.copy2(out_csv, top_metadata_csv)

    print("-" * 70)
    print(f"STAGE 4 COMPLETE: 30 master clean BVH files created and validated.")
    print(f"Master files stored in clean/bvh/ and mirrored to hidden/ground_truth/.")
    print("-" * 70)
    return True

if __name__ == "__main__":
    success = standardize_all()
    if not success:
        sys.exit(1)
