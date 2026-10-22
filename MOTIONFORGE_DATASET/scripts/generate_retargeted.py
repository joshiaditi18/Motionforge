import os
import sys
import csv
import copy
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TARGET_CONFIGS = {
    "target_small": {
        "torso_scale": 0.82,
        "upper_arm_scale": 0.80,
        "forearm_scale": 0.82,
        "thigh_scale": 0.78,
        "shin_scale": 0.76,
        "foot_scale": 0.85
    },
    "target_medium": {
        "torso_scale": 0.95,
        "upper_arm_scale": 1.12,
        "forearm_scale": 1.15,
        "thigh_scale": 1.08,
        "shin_scale": 1.10,
        "foot_scale": 1.02
    },
    "target_tall": {
        "torso_scale": 1.25,
        "upper_arm_scale": 1.22,
        "forearm_scale": 1.28,
        "thigh_scale": 1.32,
        "shin_scale": 1.35,
        "foot_scale": 1.15
    }
}

TORSO_JOINTS = {'lowerback', 'spine', 'spine1', 'neck', 'neck1', 'head'}
UPPER_ARM_JOINTS = {'leftarm', 'rightarm', 'larm', 'rarm', 'leftshoulder', 'rightshoulder'}
FOREARM_JOINTS = {'leftforearm', 'rightforearm', 'lforearm', 'rforearm'}
THIGH_JOINTS = {'leftupleg', 'rightupleg', 'lupleg', 'rupleg'}
SHIN_JOINTS = {'leftleg', 'rightleg', 'lleg', 'rleg'}
FOOT_JOINTS = {'leftfoot', 'rightfoot', 'lefttoebase', 'righttoebase', 'lfoot', 'rfoot'}

def classify_joint(joint_name):
    j = joint_name.lower()
    if j in TORSO_JOINTS:
        return 'torso'
    elif j in UPPER_ARM_JOINTS:
        return 'upper_arm'
    elif j in FOREARM_JOINTS:
        return 'forearm'
    elif j in THIGH_JOINTS:
        return 'thigh'
    elif j in SHIN_JOINTS:
        return 'shin'
    elif j in FOOT_JOINTS:
        return 'foot'
    return 'other'

def retarget_hierarchy(header_lines, config):
    """
    Modifies OFFSET vectors in the BVH hierarchy according to body proportion scaling factors.
    """
    new_headers = []
    current_joint = None

    for line in header_lines:
        parts = line.strip().split()
        if not parts:
            new_headers.append(line)
            continue

        token = parts[0]
        if token in ['ROOT', 'JOINT']:
            current_joint = parts[1]
            new_headers.append(line)
        elif token == 'OFFSET':
            if current_joint is None:
                new_headers.append(line)
                continue

            part_type = classify_joint(current_joint)
            scale = 1.0
            if part_type == 'torso':
                scale = config['torso_scale']
            elif part_type == 'upper_arm':
                scale = config['upper_arm_scale']
            elif part_type == 'forearm':
                scale = config['forearm_scale']
            elif part_type == 'thigh':
                scale = config['thigh_scale']
            elif part_type == 'shin':
                scale = config['shin_scale']
            elif part_type == 'foot':
                scale = config['foot_scale']

            ox, oy, oz = float(parts[1]), float(parts[2]), float(parts[3])
            nox, noy, noz = ox * scale, oy * scale, oz * scale

            # Reconstruct indentation
            indent_count = len(line) - len(line.lstrip())
            indent_str = line[:indent_count]
            new_headers.append(f"{indent_str}OFFSET {nox:.5f} {noy:.5f} {noz:.5f}")
        else:
            new_headers.append(line)

    return new_headers

def parse_bvh(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    header_lines = []
    motion_line_idx = -1
    for idx, line in enumerate(lines):
        if line.strip().startswith('MOTION'):
            motion_line_idx = idx
            break
        header_lines.append(line.rstrip('\r\n'))

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

    return header_lines, frame_time, np.array(motion_data, dtype=np.float64)

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

def generate_all_retargeted():
    print("=" * 70)
    print("MOTIONFORGE — STAGE 6C: GENERATE RETARGETED MOTIONS (BODY PROPORTIONS)")
    print("=" * 70)

    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    clean_dir = os.path.join(workspace_root, "clean", "bvh")
    retarget_dir = os.path.join(workspace_root, "public", "retargeting")
    metadata_dir = os.path.join(workspace_root, "metadata")
    os.makedirs(retarget_dir, exist_ok=True)

    metadata_records = []

    for i in range(1, 31):
        motion_id = f"MF{i:03d}"
        clean_file = f"{motion_id}_clean.bvh"
        clean_path = os.path.join(clean_dir, clean_file)

        headers, frame_time, motion_data = parse_bvh(clean_path)

        for target_type, cfg in TARGET_CONFIGS.items():
            out_file = f"{motion_id}_{target_type}.bvh"
            out_path = os.path.join(retarget_dir, out_file)

            # 1. Adapt skeletal bone offsets to new body proportions
            new_headers = retarget_hierarchy(headers, cfg)

            # 2. Adjust root translation height to match leg scale
            leg_scale = (cfg['thigh_scale'] + cfg['shin_scale']) / 2.0
            retargeted_motion = motion_data.copy()
            # Root Y position is channel 1
            retargeted_motion[:, 1] = retargeted_motion[:, 1] * leg_scale

            write_bvh(out_path, new_headers, frame_time, retargeted_motion)

            metadata_records.append({
                'motion_id': motion_id,
                'target_type': target_type,
                'torso_scale': cfg['torso_scale'],
                'upper_arm_scale': cfg['upper_arm_scale'],
                'forearm_scale': cfg['forearm_scale'],
                'thigh_scale': cfg['thigh_scale'],
                'shin_scale': cfg['shin_scale'],
                'foot_scale': cfg['foot_scale'],
                'source_file': os.path.relpath(clean_path, workspace_root),
                'target_file': os.path.relpath(out_path, workspace_root)
            })

        print(f"  [OK] Generated target_small, target_medium, target_tall for {motion_id}")

    # Write metadata
    out_csv = os.path.join(metadata_dir, "retarget_metadata.csv")
    fieldnames = [
        'motion_id',
        'target_type',
        'torso_scale',
        'upper_arm_scale',
        'forearm_scale',
        'thigh_scale',
        'shin_scale',
        'foot_scale',
        'source_file',
        'target_file'
    ]
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in metadata_records:
            writer.writerow(r)

    print(f"\nSaved retarget metadata to {out_csv} ({len(metadata_records)} files generated)")
    return True

if __name__ == "__main__":
    generate_all_retargeted()
