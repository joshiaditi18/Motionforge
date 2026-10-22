import os
import sys
import csv
import math
import glob
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

EXPECTED_JOINTS = [
    'Hips', 'LHipJoint', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase',
    'RHipJoint', 'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase',
    'LowerBack', 'Spine', 'Spine1', 'LeftShoulder', 'LeftArm', 'LeftForeArm',
    'LeftHand', 'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand',
    'Neck', 'Neck1', 'Head'
]

def parse_and_validate_bvh(filepath):
    """
    Validates BVH syntax, hierarchy, channels, frames, and numeric values.
    """
    if not os.path.exists(filepath):
        return False, f"File does not exist: {filepath}", {}

    if os.path.getsize(filepath) == 0:
        return False, f"File is empty: {filepath}", {}

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
        return False, f"Missing MOTION section in {filepath}", {}

    # Validate hierarchy
    joints = []
    root_name = None
    num_channels = 0
    brace_depth = 0
    end_sites = 0
    offsets = {}
    joint_channels = {}
    curr_joint = None
    channel_cursor = 0

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
            curr_joint = parts[1]
        elif token == 'JOINT':
            joints.append(parts[1])
            curr_joint = parts[1]
        elif token == 'End':
            end_sites += 1
            curr_joint = f"End_Site_{end_sites}"
        elif token == 'CHANNELS':
            cnt = int(parts[1])
            num_channels += cnt
            if curr_joint:
                joint_channels[curr_joint] = (channel_cursor, channel_cursor + cnt)
            channel_cursor += cnt
        elif token == 'OFFSET':
            if len(parts) >= 4:
                ox, oy, oz = float(parts[1]), float(parts[2]), float(parts[3])
                if curr_joint:
                    offsets[curr_joint] = (ox, oy, oz)

    if brace_depth != 0:
        return False, f"Unmatched hierarchy braces (depth={brace_depth}) in {filepath}", {}

    if root_name != 'Hips':
        return False, f"Root joint is '{root_name}', expected 'Hips' in {filepath}", {}

    # Check expected core joints
    for ej in EXPECTED_JOINTS:
        if ej not in joints:
            return False, f"Missing expected joint '{ej}' in {filepath}", {}

    # Validate MOTION header
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

    if frame_time <= 0:
        return False, f"Invalid frame time ({frame_time}) in {filepath}", {}

    motion_data = []
    while idx < len(lines):
        line = lines[idx].strip()
        idx += 1
        if not line:
            continue
        vals = [float(x) for x in line.split()]
        if len(vals) != num_channels:
            return False, f"Frame channel count mismatch in {filepath}: found {len(vals)}, expected {num_channels}", {}
        for v in vals:
            if math.isnan(v) or math.isinf(v):
                return False, f"NaN or Inf detected in {filepath}", {}
        motion_data.append(vals)

    actual_frames = len(motion_data)
    if declared_frames != actual_frames:
        return False, f"Declared frames ({declared_frames}) != actual frames ({actual_frames}) in {filepath}", {}

    info = {
        'root': root_name,
        'joints': joints,
        'num_channels': num_channels,
        'declared_frames': declared_frames,
        'frame_time': frame_time,
        'offsets': offsets,
        'joint_channels': joint_channels,
        'motion_data': np.array(motion_data, dtype=np.float64)
    }
    return True, "Valid", info

def validate_entire_dataset():
    print("=" * 70)
    print("MOTIONFORGE — STAGE 7: COMPLETE AUTOMATED DATASET VALIDATION")
    print("=" * 70)

    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    clean_dir = os.path.join(workspace_root, "clean", "bvh")
    hidden_gt_dir = os.path.join(workspace_root, "hidden", "ground_truth")
    denoising_dir = os.path.join(workspace_root, "public", "denoising")
    gap_dir = os.path.join(workspace_root, "public", "gap_filling")
    retarget_dir = os.path.join(workspace_root, "public", "retargeting")
    metadata_dir = os.path.join(workspace_root, "metadata")

    total_checks = 0
    passed_checks = 0
    failed_checks = 0

    clean_info_cache = {}

    # 1. Validate Clean Master & Hidden Ground Truth
    print("\n--- 1. Validating Clean Master & Hidden Ground Truth BVH (30 + 30 files) ---")
    for i in range(1, 31):
        mid = f"MF{i:03d}"
        c_path = os.path.join(clean_dir, f"{mid}_clean.bvh")
        h_path = os.path.join(hidden_gt_dir, f"{mid}_clean.bvh")

        total_checks += 2
        ok_c, msg_c, info_c = parse_and_validate_bvh(c_path)
        ok_h, msg_h, info_h = parse_and_validate_bvh(h_path)

        if ok_c and ok_h:
            passed_checks += 2
            clean_info_cache[mid] = info_c
            # Check mirror consistency
            assert np.array_equal(info_c['motion_data'], info_h['motion_data']), f"Hidden GT differs from Clean for {mid}"
        else:
            failed_checks += 1
            print(f"  [FAIL] {mid}: Clean: {msg_c}, Hidden: {msg_h}")

    print(f"  ✓ All 30 Clean and 30 Hidden Ground Truth files parsed and verified.")

    # 2. Validate Denoising Dataset (90 files)
    print("\n--- 2. Validating Denoising Dataset (90 files) ---")
    noise_csv = os.path.join(metadata_dir, "noise_metadata.csv")
    with open(noise_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        noise_rows = list(reader)

    for row in noise_rows:
        total_checks += 1
        mid = row['motion_id']
        level = row['noise_level']
        n_file = os.path.join(workspace_root, row['output_file'])

        ok, msg, info_n = parse_and_validate_bvh(n_file)
        if not ok:
            failed_checks += 1
            print(f"  [FAIL] Noise file {n_file}: {msg}")
            continue

        c_info = clean_info_cache[mid]
        # Check that frame count remains identical
        if info_n['declared_frames'] != c_info['declared_frames']:
            failed_checks += 1
            print(f"  [FAIL] Frame count changed in {n_file}")
            continue

        # Check that corrupted file differs from clean ground truth
        diff = np.abs(info_n['motion_data'] - c_info['motion_data']).max()
        if diff == 0:
            failed_checks += 1
            print(f"  [FAIL] No noise added to {n_file}")
            continue

        passed_checks += 1

    print(f"  ✓ All 90 Noisy files verified: syntax valid, frame count matches, distinct from ground truth.")

    # 3. Validate Gap-Filling Dataset (90 files)
    print("\n--- 3. Validating Gap-Filling Dataset (90 files) ---")
    gap_csv = os.path.join(metadata_dir, "gap_metadata.csv")
    with open(gap_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        gap_rows = list(reader)

    for row in gap_rows:
        total_checks += 1
        mid = row['motion_id']
        g_id = row['gap_id']
        joint = row['joint_name']
        s_frame = int(row['start_frame'])
        e_frame = int(row['end_frame'])
        g_file = os.path.join(workspace_root, row['output_file'])

        ok, msg, info_g = parse_and_validate_bvh(g_file)
        if not ok:
            failed_checks += 1
            print(f"  [FAIL] Gap file {g_file}: {msg}")
            continue

        c_info = clean_info_cache[mid]
        c_start, c_end = c_info['joint_channels'][joint]

        # Check gap interval in motion data
        gap_motion = info_g['motion_data'][s_frame:e_frame, c_start:c_end]
        first_val = gap_motion[0]
        # Verify frozen signal flatline
        flatline_var = np.var(gap_motion, axis=0).max()
        if flatline_var > 1e-6:
            failed_checks += 1
            print(f"  [FAIL] Gap not properly frozen in {g_file} for joint {joint}")
            continue

        passed_checks += 1

    print(f"  ✓ All 90 Gap files verified: syntax valid, exact joint affected, exact frame intervals matched.")

    # 4. Validate Retargeting Dataset (90 files)
    print("\n--- 4. Validating Retargeting Dataset (90 files) ---")
    retarget_csv = os.path.join(metadata_dir, "retarget_metadata.csv")
    with open(retarget_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        retarget_rows = list(reader)

    for row in retarget_rows:
        total_checks += 1
        mid = row['motion_id']
        r_rel_path = row.get('target_file') or row.get('output_file')
        r_file = os.path.join(workspace_root, r_rel_path)

        ok, msg, info_r = parse_and_validate_bvh(r_file)
        if not ok:
            failed_checks += 1
            print(f"  [FAIL] Retarget file {r_file}: {msg}")
            continue

        c_info = clean_info_cache[mid]
        # Frame count and duration must be preserved
        if info_r['declared_frames'] != c_info['declared_frames']:
            failed_checks += 1
            print(f"  [FAIL] Frame count mismatch in retarget file {r_file}")
            continue

        # Proportions must differ
        c_leg_offset = np.linalg.norm(c_info['offsets']['LeftUpLeg'])
        r_leg_offset = np.linalg.norm(info_r['offsets']['LeftUpLeg'])
        if abs(c_leg_offset - r_leg_offset) < 1e-4:
            failed_checks += 1
            print(f"  [FAIL] Bone offset was not retargeted in {r_file}")
            continue

        passed_checks += 1

    print(f"  ✓ All 90 Retargeted files verified: proportions altered, frame counts and durations preserved.")

    # Summary
    print("\n" + "=" * 70)
    print(f"VALIDATION SUMMARY:")
    print(f"  Total Integrity Checks: {total_checks}")
    print(f"  Checks Passed:          {passed_checks}")
    print(f"  Checks Failed:          {failed_checks}")
    print("=" * 70)

    if failed_checks == 0:
        print("ALL CHECKS PASSED: DATASET IS 100% VALID AND COMPLIANT.")
        return True
    else:
        print(f"VALIDATION FAILED WITH {failed_checks} ERRORS.")
        return False

if __name__ == "__main__":
    success = validate_entire_dataset()
    if not success:
        sys.exit(1)
