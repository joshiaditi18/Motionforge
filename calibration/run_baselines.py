import os
import sys
import time
import tracemalloc
import pandas as pd
import numpy as np

# Ensure parent and baselines are in path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from baselines.common.bvh_io import parse_bvh, write_bvh
from baselines.denoising.baseline_denoising import run_denoising
from baselines.gap_filling.baseline_gap_filling import run_gap_filling
from baselines.retargeting.baseline_retargeting import retarget_motion

"""
MOTIONFORGE — calibration/run_baselines.py
Executes deterministic baseline algorithms across all 21 public training motions.
Profiles wall-clock execution time and peak RAM usage per task and variant.
"""

def main():
    print("=" * 75)
    print("MOTIONFORGE — PHASE 3: RUN BASELINE ALGORITHMS")
    print("=" * 75)

    dataset_root = os.path.join(BASE_DIR, "MOTIONFORGE_DATASET")
    split_csv = os.path.join(dataset_root, "metadata", "dataset_split.csv")
    gap_csv = os.path.join(dataset_root, "metadata", "gap_metadata.csv")

    df_split = pd.read_csv(split_csv)
    training_motions = df_split[df_split['split'] == 'TRAINING']['motion_id'].tolist()
    print(f"Loaded {len(training_motions)} public training motions: {training_motions}")

    df_gap = pd.read_csv(gap_csv).set_index('gap_id')

    out_denoise_dir = os.path.join(BASE_DIR, "calibration", "outputs", "denoising")
    out_gap_dir = os.path.join(BASE_DIR, "calibration", "outputs", "gap_filling")
    out_retarget_dir = os.path.join(BASE_DIR, "calibration", "outputs", "retargeting")
    res_dir = os.path.join(BASE_DIR, "calibration", "results")

    os.makedirs(out_denoise_dir, exist_ok=True)
    os.makedirs(out_gap_dir, exist_ok=True)
    os.makedirs(out_retarget_dir, exist_ok=True)
    os.makedirs(res_dir, exist_ok=True)

    runtime_records = []

    # =========================================================================
    # Task 1: Denoising
    # =========================================================================
    print("\n--- Task 1: Running Denoising Baselines (LOW, MEDIUM, HIGH) ---")
    denoise_levels = ["low", "medium", "high"]
    for mid in training_motions:
        for lvl in denoise_levels:
            in_file = os.path.join(dataset_root, "public", "denoising", f"{mid}_{lvl}.bvh")
            out_file = os.path.join(out_denoise_dir, f"{mid}_{lvl}.bvh")

            tracemalloc.start()
            t0 = time.perf_counter()
            run_denoising(in_file, out_file, noise_level=lvl.upper())
            elapsed = time.perf_counter() - t0
            current_mem, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Read frame count
            bvh = parse_bvh(in_file)
            f_count = bvh.frame_count

            runtime_records.append({
                'task': 'denoising',
                'motion_id': mid,
                'variant': lvl.upper(),
                'frame_count': f_count,
                'execution_time_sec': round(elapsed, 4),
                'memory_peak_mb': round(peak_mem / (1024 * 1024), 2)
            })
        print(f"  [Denoising OK] {mid} (3 variants)")

    # =========================================================================
    # Task 2: Gap Filling
    # =========================================================================
    print("\n--- Task 2: Running Gap Filling Baselines (SHORT, MEDIUM, LONG) ---")
    gap_types = ["short", "medium", "long"]
    for mid in training_motions:
        for gt in gap_types:
            gap_id = f"{mid}_{gt}"
            in_file = os.path.join(dataset_root, "public", "gap_filling", f"{gap_id}.bvh")
            out_file = os.path.join(out_gap_dir, f"{gap_id}.bvh")

            gap_row = df_gap.loc[gap_id]
            joint_name = gap_row['joint_name']
            s_f = int(gap_row['start_frame'])
            e_f = int(gap_row['end_frame'])
            method = "linear" if gt == "short" else "cubic"

            tracemalloc.start()
            t0 = time.perf_counter()
            run_gap_filling(in_file, out_file, start_frame=s_f, end_frame=e_f, joint_name=joint_name, method=method)
            elapsed = time.perf_counter() - t0
            current_mem, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            bvh = parse_bvh(in_file)
            f_count = bvh.frame_count

            runtime_records.append({
                'task': 'gap_filling',
                'motion_id': mid,
                'variant': gt.upper(),
                'frame_count': f_count,
                'execution_time_sec': round(elapsed, 4),
                'memory_peak_mb': round(peak_mem / (1024 * 1024), 2)
            })
        print(f"  [Gap Filling OK] {mid} (3 variants)")

    # =========================================================================
    # Task 3: Retargeting
    # =========================================================================
    print("\n--- Task 3: Running Retargeting Baselines (small, medium, tall) ---")
    targets = ["target_small", "target_medium", "target_tall"]
    for mid in training_motions:
        clean_file = os.path.join(dataset_root, "clean", "bvh", f"{mid}_clean.bvh")
        for tgt in targets:
            out_file = os.path.join(out_retarget_dir, f"{mid}_{tgt}.bvh")

            tracemalloc.start()
            t0 = time.perf_counter()
            retarget_motion(clean_file, out_file, target_type=tgt)
            elapsed = time.perf_counter() - t0
            current_mem, peak_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            bvh = parse_bvh(clean_file)
            f_count = bvh.frame_count

            runtime_records.append({
                'task': 'retargeting',
                'motion_id': mid,
                'variant': tgt,
                'frame_count': f_count,
                'execution_time_sec': round(elapsed, 4),
                'memory_peak_mb': round(peak_mem / (1024 * 1024), 2)
            })
        print(f"  [Retargeting OK] {mid} (3 targets)")

    # Save runtime records
    runtime_df = pd.DataFrame(runtime_records)
    runtime_csv_path = os.path.join(res_dir, "runtime_profiles.csv")
    runtime_df.to_csv(runtime_csv_path, index=False)
    print(f"\n[SUCCESS] Saved runtime profiles to: {runtime_csv_path}")
    print(f"Total baseline evaluations performed: {len(runtime_df)}")
    print(f"Total runtime: {runtime_df['execution_time_sec'].sum():.2f} seconds")
    print(f"Max peak RAM: {runtime_df['memory_peak_mb'].max():.2f} MB")

if __name__ == "__main__":
    main()
