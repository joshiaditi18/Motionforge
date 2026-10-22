import os
import sys
import csv
import math
import copy
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RANDOM_SEED = 2026

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

def add_noise_to_motion(motion_data, level, rng):
    """
    Simulates realistic optical mocap sensor noise:
    - Root position jitter (Gaussian displacement)
    - Joint rotation jitter (small angular deviations)
    - Occasional tracking jump / glitch (sparse impulse noise)
    - High-frequency temporal micro-jitter
    """
    noisy = motion_data.copy()
    num_frames, num_channels = noisy.shape

    if level == "LOW":
        pos_sigma = 0.08      # ~0.08 units position jitter
        rot_sigma = 0.40      # ~0.4 degrees rotational jitter
        glitch_prob = 0.005   # 0.5% probability of glitch
        glitch_scale = 1.5
    elif level == "MEDIUM":
        pos_sigma = 0.25
        rot_sigma = 1.20
        glitch_prob = 0.015
        glitch_scale = 3.5
    elif level == "HIGH":
        pos_sigma = 0.60
        rot_sigma = 2.80
        glitch_prob = 0.035
        glitch_scale = 7.0
    else:
        raise ValueError(f"Unknown noise level: {level}")

    # 1. Root position noise (channels 0, 1, 2)
    pos_noise = rng.normal(0, pos_sigma, size=(num_frames, 3))
    noisy[:, 0:3] += pos_noise

    # 2. Rotational channel noise (channels 3 to num_channels)
    rot_noise = rng.normal(0, rot_sigma, size=(num_frames, num_channels - 3))
    noisy[:, 3:] += rot_noise

    # 3. Occasional sparse sensor glitch (temporary tracking spike)
    glitch_mask = rng.uniform(0, 1, size=(num_frames, num_channels)) < glitch_prob
    glitches = rng.normal(0, glitch_scale, size=(num_frames, num_channels))
    noisy[glitch_mask] += glitches[glitch_mask]

    return noisy, {
        "pos_sigma": pos_sigma,
        "rot_sigma": rot_sigma,
        "glitch_prob": glitch_prob,
        "glitch_scale": glitch_scale
    }

def generate_all_noise():
    print("=" * 70)
    print("MOTIONFORGE — STAGE 6A: GENERATE REALISTIC NOISY DATA")
    print("=" * 70)

    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    clean_dir = os.path.join(workspace_root, "clean", "bvh")
    denoising_dir = os.path.join(workspace_root, "public", "denoising")
    metadata_dir = os.path.join(workspace_root, "metadata")
    os.makedirs(denoising_dir, exist_ok=True)

    rng = np.random.RandomState(RANDOM_SEED)

    metadata_records = []
    noise_levels = ["LOW", "MEDIUM", "HIGH"]

    for i in range(1, 31):
        motion_id = f"MF{i:03d}"
        clean_file = f"{motion_id}_clean.bvh"
        clean_path = os.path.join(clean_dir, clean_file)

        if not os.path.exists(clean_path):
            raise FileNotFoundError(f"Clean file missing: {clean_path}")

        headers, frame_time, motion_data = parse_bvh(clean_path)

        for level in noise_levels:
            out_file = f"{motion_id}_{level.lower()}.bvh"
            out_path = os.path.join(denoising_dir, out_file)

            noisy_data, params = add_noise_to_motion(motion_data, level, rng)
            write_bvh(out_path, headers, frame_time, noisy_data)

            metadata_records.append({
                'motion_id': motion_id,
                'noise_level': level,
                'noise_type': 'optical_mocap_jitter_and_glitch',
                'noise_parameters': str(params),
                'random_seed': RANDOM_SEED,
                'source_clean_file': os.path.relpath(clean_path, workspace_root),
                'output_file': os.path.relpath(out_path, workspace_root)
            })

        print(f"  [OK] Generated LOW, MEDIUM, HIGH noisy sets for {motion_id}")

    # Write metadata
    out_csv = os.path.join(metadata_dir, "noise_metadata.csv")
    fieldnames = [
        'motion_id',
        'noise_level',
        'noise_type',
        'noise_parameters',
        'random_seed',
        'source_clean_file',
        'output_file'
    ]
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in metadata_records:
            writer.writerow(r)

    print(f"\nSaved noise metadata to {out_csv} ({len(metadata_records)} files generated)")
    return True

if __name__ == "__main__":
    generate_all_noise()
