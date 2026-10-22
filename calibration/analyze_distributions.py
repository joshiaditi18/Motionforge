import os
import sys
import numpy as np
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

"""
MOTIONFORGE — calibration/analyze_distributions.py
Performs statistical distribution analysis across all collected metric CSVs.
Computes mean, std, median, p25, p75, p90, p95, min, max across difficulty levels.
"""

def summarize_series(s):
    return {
        'mean': float(s.mean()),
        'std': float(s.std()),
        'median': float(s.median()),
        'p25': float(np.percentile(s, 25)),
        'p75': float(np.percentile(s, 75)),
        'p90': float(np.percentile(s, 90)),
        'p95': float(np.percentile(s, 95)),
        'min': float(s.min()),
        'max': float(s.max())
    }

def main():
    res_dir = os.path.join(BASE_DIR, "calibration", "results")
    denoise_path = os.path.join(res_dir, "denoising_metrics.csv")
    gap_path = os.path.join(res_dir, "gap_filling_metrics.csv")
    retarget_path = os.path.join(res_dir, "retargeting_metrics.csv")
    runtime_path = os.path.join(res_dir, "runtime_profiles.csv")

    print("=" * 80)
    print("MOTIONFORGE — PHASE 3: METRIC DISTRIBUTION ANALYSIS")
    print("=" * 80)

    # 1. Denoising Distributions
    if os.path.exists(denoise_path):
        df_d = pd.read_csv(denoise_path)
        print("\n" + "=" * 40)
        print("TASK 1: MOTION DENOISING METRIC DISTRIBUTIONS")
        print("=" * 40)
        for lvl in ["LOW", "MEDIUM", "HIGH"]:
            sub = df_d[df_d['level'] == lvl]
            print(f"\n--- Noise Level: {lvl} (N={len(sub)}) ---")
            for col in ['mpjpe_baseline', 'mpjpe_raw_corrupted', 'jve_baseline', 'jitter_baseline', 'motion_preservation_ratio', 'jitter_reduction_pct']:
                st = summarize_series(sub[col])
                print(f"  {col:<26}: Mean={st['mean']:>8.3f} | Median={st['median']:>8.3f} | P75={st['p75']:>8.3f} | P90={st['p90']:>8.3f} | Max={st['max']:>8.3f}")

    # 2. Gap Filling Distributions
    if os.path.exists(gap_path):
        df_g = pd.read_csv(gap_path)
        print("\n" + "=" * 40)
        print("TASK 2: MOTION GAP FILLING METRIC DISTRIBUTIONS")
        print("=" * 40)
        for gt in ["SHORT", "MEDIUM", "LONG"]:
            sub = df_g[df_g['gap_type'] == gt]
            print(f"\n--- Gap Regime: {gt} (N={len(sub)}) ---")
            for col in ['inpainting_mpjpe', 'inpainting_mpjpe_raw', 'boundary_error', 'v_boundary_error', 'improvement_pct']:
                st = summarize_series(sub[col])
                print(f"  {col:<26}: Mean={st['mean']:>8.3f} | Median={st['median']:>8.3f} | P75={st['p75']:>8.3f} | P90={st['p90']:>8.3f} | Max={st['max']:>8.3f}")

    # 3. Retargeting Distributions
    if os.path.exists(retarget_path):
        df_r = pd.read_csv(retarget_path)
        print("\n" + "=" * 40)
        print("TASK 3: MOTION RETARGETING METRIC DISTRIBUTIONS")
        print("=" * 40)
        for tgt in ["target_small", "target_medium", "target_tall"]:
            sub = df_r[df_r['target_type'] == tgt]
            print(f"\n--- Target Avatar: {tgt} (N={len(sub)}) ---")
            for col in ['end_effector_error', 'angular_geodesic_error_deg', 'max_bone_deviation', 'ground_penetration']:
                st = summarize_series(sub[col])
                print(f"  {col:<26}: Mean={st['mean']:>8.4f} | Median={st['median']:>8.4f} | P75={st['p75']:>8.4f} | P90={st['p90']:>8.4f} | Max={st['max']:>8.4f}")

    # 4. Runtime & Resource Profiles
    if os.path.exists(runtime_path):
        df_rt = pd.read_csv(runtime_path)
        print("\n" + "=" * 40)
        print("RESOURCE PROFILING (RUNTIME & RAM)")
        print("=" * 40)
        for task in ['denoising', 'gap_filling', 'retargeting']:
            sub = df_rt[df_rt['task'] == task]
            t_st = summarize_series(sub['execution_time_sec'])
            m_st = summarize_series(sub['memory_peak_mb'])
            print(f"\n--- Task: {task.upper()} (N={len(sub)}) ---")
            print(f"  Execution Time (s)        : Mean={t_st['mean']:>6.3f} | Median={t_st['median']:>6.3f} | P90={t_st['p90']:>6.3f} | Max={t_st['max']:>6.3f} | Total={sub['execution_time_sec'].sum():>6.2f}s")
            print(f"  Peak Memory (MB)          : Mean={m_st['mean']:>6.2f} | Median={m_st['median']:>6.2f} | P90={m_st['p90']:>6.2f} | Max={m_st['max']:>6.2f}")

if __name__ == "__main__":
    main()
