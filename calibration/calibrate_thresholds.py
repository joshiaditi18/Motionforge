import os
import sys
import json
import yaml
import numpy as np
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

"""
MOTIONFORGE — calibration/calibrate_thresholds.py
Computes calibrated exponential decay normalizers (tau) and weights based on
the empirical distributions of baseline algorithms across the 21 training motions.
Outputs:
- calibration/metric_calibration.json
- calibration/calibration_config.yaml
"""

def main():
    print("=" * 80)
    print("MOTIONFORGE — PHASE 3: CALIBRATE METRIC THRESHOLDS & NORMALIZERS")
    print("=" * 80)

    res_dir = os.path.join(BASE_DIR, "calibration", "results")
    denoise_path = os.path.join(res_dir, "denoising_metrics.csv")
    gap_path = os.path.join(res_dir, "gap_filling_metrics.csv")
    retarget_path = os.path.join(res_dir, "retargeting_metrics.csv")
    runtime_path = os.path.join(res_dir, "runtime_profiles.csv")
    foot_path = os.path.join(BASE_DIR, "calibration", "foot_contact_analysis.csv")

    df_d = pd.read_csv(denoise_path)
    df_g = pd.read_csv(gap_path)
    df_r = pd.read_csv(retarget_path)
    df_rt = pd.read_csv(runtime_path) if os.path.exists(runtime_path) else None

    # 1. Denoising Calibrations
    # Baseline on MEDIUM noise provides the canonical reference baseline level
    d_med = df_d[df_d['level'] == 'MEDIUM']
    # Setting tau to P75 of baseline error gives exp(-E/tau) ~ 0.50 - 0.65 for typical submissions
    tau_mpjpe = float(round(np.percentile(d_med['mpjpe_baseline'], 75), 4))
    tau_vel = float(round(np.percentile(d_med['jve_baseline'], 75), 4))
    tau_jitter = float(round(np.percentile(d_med['jitter_baseline'], 75), 2))

    # 2. Gap Filling Calibrations
    g_med = df_g[df_g['gap_type'] == 'MEDIUM']
    tau_inp = float(round(np.percentile(g_med['inpainting_mpjpe'], 75), 4))
    tau_bound = float(round(np.percentile(g_med['boundary_error'], 75), 4))
    tau_v_bound = float(round(np.percentile(g_med['v_boundary_error'], 75), 4))

    # Stance contact velocity threshold
    df_foot = pd.read_csv(foot_path) if os.path.exists(foot_path) else None
    contact_v_th = 0.85 # default inches/s if not present
    if df_foot is not None:
        p10_mean = float((df_foot['l_toe_p10_horiz_vel'].mean() + df_foot['r_toe_p10_horiz_vel'].mean()) / 2.0)
        contact_v_th = float(round(p10_mean, 3))

    # 3. Retargeting Calibrations
    # Small and tall involve major morphological shifts
    tau_ee = float(round(np.percentile(df_r['end_effector_error'], 75), 4))
    tau_ang = 5.0 # 5.0 degrees deviation scale for retargeting rotations
    tau_ground = 0.50 # 0.5 inches floor tolerance

    # 4. Runtime Constraints
    max_single_time = float(df_rt['execution_time_sec'].max()) if df_rt is not None else 10.0
    p95_time = float(np.percentile(df_rt['execution_time_sec'], 95)) if df_rt is not None else 5.0
    max_peak_mem = float(df_rt['memory_peak_mb'].max()) if df_rt is not None else 50.0

    # Recommend timeout = 300 seconds (total pipeline run) and per-motion timeout = 30s
    calibrated_data = {
        "status": "CALIBRATED_PHASE3",
        "dataset_split": {
            "training_count": 21,
            "testing_count": 9,
            "total_motions": 30
        },
        "task_1_denoising": {
            "normalizers": {
                "mpjpe_tau": tau_mpjpe,
                "velocity_tau": tau_vel,
                "jitter_tau": tau_jitter
            },
            "intra_task_weights": {
                "mpjpe": 0.40,
                "velocity": 0.30,
                "jitter": 0.30
            },
            "baseline_median_scores": {
                "LOW": float(round(100 * np.exp(- (0.4 * df_d[df_d['level']=='LOW']['mpjpe_baseline'].median()/tau_mpjpe + 0.3 * df_d[df_d['level']=='LOW']['jve_baseline'].median()/tau_vel + 0.3 * df_d[df_d['level']=='LOW']['jitter_baseline'].median()/tau_jitter)), 2)),
                "MEDIUM": float(round(100 * np.exp(- (0.4 * df_d[df_d['level']=='MEDIUM']['mpjpe_baseline'].median()/tau_mpjpe + 0.3 * df_d[df_d['level']=='MEDIUM']['jve_baseline'].median()/tau_vel + 0.3 * df_d[df_d['level']=='MEDIUM']['jitter_baseline'].median()/tau_jitter)), 2)),
                "HIGH": float(round(100 * np.exp(- (0.4 * df_d[df_d['level']=='HIGH']['mpjpe_baseline'].median()/tau_mpjpe + 0.3 * df_d[df_d['level']=='HIGH']['jve_baseline'].median()/tau_vel + 0.3 * df_d[df_d['level']=='HIGH']['jitter_baseline'].median()/tau_jitter)), 2))
            }
        },
        "task_2_gap_filling": {
            "normalizers": {
                "inpainting_tau": tau_inp,
                "boundary_tau": tau_bound,
                "v_boundary_tau": tau_v_bound,
                "foot_contact_velocity_threshold_inch_per_sec": contact_v_th
            },
            "intra_task_weights": {
                "inpainting_mpjpe": 0.50,
                "boundary_continuity": 0.25,
                "velocity_continuity": 0.25
            },
            "baseline_median_scores": {
                "SHORT": float(round(100 * np.exp(- (0.5 * df_g[df_g['gap_type']=='SHORT']['inpainting_mpjpe'].median()/tau_inp + 0.25 * df_g[df_g['gap_type']=='SHORT']['boundary_error'].median()/tau_bound + 0.25 * df_g[df_g['gap_type']=='SHORT']['v_boundary_error'].median()/tau_v_bound)), 2)),
                "MEDIUM": float(round(100 * np.exp(- (0.5 * df_g[df_g['gap_type']=='MEDIUM']['inpainting_mpjpe'].median()/tau_inp + 0.25 * df_g[df_g['gap_type']=='MEDIUM']['boundary_error'].median()/tau_bound + 0.25 * df_g[df_g['gap_type']=='MEDIUM']['v_boundary_error'].median()/tau_v_bound)), 2)),
                "LONG": float(round(100 * np.exp(- (0.5 * df_g[df_g['gap_type']=='LONG']['inpainting_mpjpe'].median()/tau_inp + 0.25 * df_g[df_g['gap_type']=='LONG']['boundary_error'].median()/tau_bound + 0.25 * df_g[df_g['gap_type']=='LONG']['v_boundary_error'].median()/tau_v_bound)), 2))
            }
        },
        "task_3_retargeting": {
            "normalizers": {
                "end_effector_tau": tau_ee,
                "angular_tau_deg": tau_ang,
                "ground_penetration_tau": tau_ground
            },
            "intra_task_weights": {
                "end_effector": 0.45,
                "angular_fidelity": 0.35,
                "ground_penetration": 0.20
            },
            "baseline_median_scores": {
                "target_small": float(round(100 * np.exp(- (0.45 * df_r[df_r['target_type']=='target_small']['end_effector_error'].median()/tau_ee + 0.35 * df_r[df_r['target_type']=='target_small']['angular_geodesic_error_deg'].median()/tau_ang + 0.20 * df_r[df_r['target_type']=='target_small']['ground_penetration'].median()/tau_ground)), 2)),
                "target_medium": float(round(100 * np.exp(- (0.45 * df_r[df_r['target_type']=='target_medium']['end_effector_error'].median()/tau_ee + 0.35 * df_r[df_r['target_type']=='target_medium']['angular_geodesic_error_deg'].median()/tau_ang + 0.20 * df_r[df_r['target_type']=='target_medium']['ground_penetration'].median()/tau_ground)), 2)),
                "target_tall": float(round(100 * np.exp(- (0.45 * df_r[df_r['target_type']=='target_tall']['end_effector_error'].median()/tau_ee + 0.35 * df_r[df_r['target_type']=='target_tall']['angular_geodesic_error_deg'].median()/tau_ang + 0.20 * df_r[df_r['target_type']=='target_tall']['ground_penetration'].median()/tau_ground)), 2))
            }
        },
        "competition_weights": {
            "task_1_denoising": 0.30,
            "task_2_gap_filling": 0.30,
            "task_3_retargeting": 0.40
        },
        "runtime_constraints": {
            "timeout_seconds": 300,
            "single_file_timeout_seconds": 30,
            "memory_limit_mb": 4096,
            "max_archive_size_mb": 100,
            "observed_max_time_per_file_sec": max_single_time,
            "observed_max_peak_ram_mb": max_peak_mem
        }
    }

    # Write JSON
    json_path = os.path.join(BASE_DIR, "calibration", "metric_calibration.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(calibrated_data, f, indent=2)
    print(f"Saved calibrated metrics to: {json_path}")

    # Write YAML calibration config
    yaml_config = {
        "competition": {
            "name": "MOTIONFORGE",
            "phase": "PHASE_3_CALIBRATED",
            "random_seed": 2026
        },
        "scoring": {
            "weights": {
                "denoising": 0.30,
                "gap_filling": 0.30,
                "retargeting": 0.40
            },
            "normalization": {
                "method": "exponential_decay",
                "mpjpe_tau": tau_mpjpe,
                "velocity_tau": tau_vel,
                "jitter_tau": tau_jitter,
                "inpainting_tau": tau_inp,
                "boundary_tau": tau_bound,
                "v_boundary_tau": tau_v_bound,
                "end_effector_tau": tau_ee,
                "angular_tau": tau_ang,
                "ground_penetration_tau": tau_ground,
                "foot_contact_velocity_threshold": contact_v_th
            }
        },
        "runtime": {
            "timeout_seconds": 300,
            "memory_limit_mb": 4096,
            "max_archive_size_mb": 100,
            "network_access": False,
            "sandboxed": True
        },
        "submission": {
            "max_daily_attempts": 5,
            "leaderboard_selection": "BEST"
        }
    }

    yaml_path = os.path.join(BASE_DIR, "calibration", "calibration_config.yaml")
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_config, f, default_flow_style=False, sort_keys=False)
    print(f"Saved calibration config YAML to: {yaml_path}")

    print("\n--- Summary of Calibrated Normalizers (Tau) ---")
    print(f"  MPJPE Tau             : {tau_mpjpe:.4f} (inches)")
    print(f"  Velocity Tau          : {tau_vel:.4f} (in/s)")
    print(f"  Jitter Tau            : {tau_jitter:.2f} (in/s^2)")
    print(f"  Inpainting Tau        : {tau_inp:.4f} (inches)")
    print(f"  Boundary Continuity   : {tau_bound:.4f} (inches)")
    print(f"  Velocity Continuity   : {tau_v_bound:.4f} (in/s)")
    print(f"  Foot Contact Velocity : {contact_v_th:.3f} (in/s)")
    print(f"  End-Effector Tau      : {tau_ee:.4f} (normalized ratio)")
    print(f"  Angular Tau           : {tau_ang:.2f} (degrees)")

if __name__ == "__main__":
    main()
