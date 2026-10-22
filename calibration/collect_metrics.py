import os
import sys
import numpy as np
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from baselines.common.bvh_io import parse_bvh
from baselines.common.forward_kinematics import compute_forward_kinematics, euler_zyx_to_matrix
from baselines.common.skeleton_utils import CANONICAL_31_JOINTS, END_EFFECTOR_JOINTS, get_bone_lengths
from baselines.common.motion_utils import (
    compute_velocities,
    compute_accelerations,
    calculate_mpjpe,
    calculate_velocity_error,
    calculate_jitter_error
)

"""
MOTIONFORGE — calibration/collect_metrics.py
Extracts kinematic metrics across all baseline outputs on the 21 training motions.
Generates:
- calibration/results/denoising_metrics.csv
- calibration/results/gap_filling_metrics.csv
- calibration/results/retargeting_metrics.csv
- calibration/foot_contact_analysis.csv
"""

def compute_so3_geodesic_degrees(R1, R2):
    """
    Geodesic distance on SO(3) between two 3x3 rotation matrices in degrees.
    theta = arccos(clip((trace(R1 * R2^T) - 1)/2, -1, 1)) * 180 / pi
    """
    # trace(R1 @ R2.T)
    R_rel = np.einsum('nij,nkj->nik', R1, R2)
    traces = np.trace(R_rel, axis1=-2, axis2=-1)
    cos_theta = np.clip((traces - 1.0) / 2.0, -1.0, 1.0)
    theta_rad = np.arccos(cos_theta)
    return np.degrees(theta_rad)

def run_metric_collection():
    print("=" * 75)
    print("MOTIONFORGE — PHASE 3: COLLECT KINEMATIC METRICS")
    print("=" * 75)

    dataset_root = os.path.join(BASE_DIR, "MOTIONFORGE_DATASET")
    split_csv = os.path.join(dataset_root, "metadata", "dataset_split.csv")
    gap_csv = os.path.join(dataset_root, "metadata", "gap_metadata.csv")

    df_split = pd.read_csv(split_csv)
    training_motions = df_split[df_split['split'] == 'TRAINING']['motion_id'].tolist()
    df_gap = pd.read_csv(gap_csv).set_index('gap_id')

    out_denoise_dir = os.path.join(BASE_DIR, "calibration", "outputs", "denoising")
    out_gap_dir = os.path.join(BASE_DIR, "calibration", "outputs", "gap_filling")
    out_retarget_dir = os.path.join(BASE_DIR, "calibration", "outputs", "retargeting")
    res_dir = os.path.join(BASE_DIR, "calibration", "results")

    os.makedirs(res_dir, exist_ok=True)

    # =========================================================================
    # 1. Foot Contact Velocity Analysis on Clean Motions
    # =========================================================================
    print("\n--- Analyzing Foot Velocities for Stance-Phase Threshold Calibration ---")
    foot_records = []
    all_toe_horizontal_vels = []

    for mid in training_motions:
        clean_path = os.path.join(dataset_root, "clean", "bvh", f"{mid}_clean.bvh")
        bvh = parse_bvh(clean_path)
        pos, j_names = compute_forward_kinematics(bvh, include_end_sites=False)
        vels = compute_velocities(pos, frame_time=bvh.frame_time)  # (N-1, J, 3)

        l_toe_idx = j_names.index('LeftToeBase')
        r_toe_idx = j_names.index('RightToeBase')

        l_vel_horiz = np.linalg.norm(vels[:, l_toe_idx, [0, 2]], axis=-1)  # X, Z plane
        r_vel_horiz = np.linalg.norm(vels[:, r_toe_idx, [0, 2]], axis=-1)

        all_toe_horizontal_vels.extend(l_vel_horiz.tolist())
        all_toe_horizontal_vels.extend(r_vel_horiz.tolist())

        foot_records.append({
            'motion_id': mid,
            'frame_count': bvh.frame_count,
            'l_toe_mean_horiz_vel': float(np.mean(l_vel_horiz)),
            'l_toe_p10_horiz_vel': float(np.percentile(l_vel_horiz, 10)),
            'l_toe_p25_horiz_vel': float(np.percentile(l_vel_horiz, 25)),
            'r_toe_mean_horiz_vel': float(np.mean(r_vel_horiz)),
            'r_toe_p10_horiz_vel': float(np.percentile(r_vel_horiz, 10)),
            'r_toe_p25_horiz_vel': float(np.percentile(r_vel_horiz, 25)),
        })

    foot_df = pd.DataFrame(foot_records)
    foot_csv_path = os.path.join(BASE_DIR, "calibration", "foot_contact_analysis.csv")
    foot_df.to_csv(foot_csv_path, index=False)

    arr_toe = np.array(all_toe_horizontal_vels)
    v_p05 = np.percentile(arr_toe, 5)
    v_p10 = np.percentile(arr_toe, 10)
    v_p15 = np.percentile(arr_toe, 15)
    v_p20 = np.percentile(arr_toe, 20)
    print(f"Foot Velocity Percentiles across all training frames (inches/sec):")
    print(f"  5th: {v_p05:.3f} | 10th: {v_p10:.3f} | 15th: {v_p15:.3f} | 20th: {v_p20:.3f}")
    calibrated_contact_threshold = float(v_p15)
    print(f"Empirically Calibrated Stance Contact Threshold: {calibrated_contact_threshold:.3f} in/s")

    # =========================================================================
    # 2. Task 1: Denoising Metrics Collection
    # =========================================================================
    print("\n--- Collecting Task 1 (Denoising) Metrics ---")
    denoise_records = []
    for mid in training_motions:
        clean_path = os.path.join(dataset_root, "clean", "bvh", f"{mid}_clean.bvh")
        bvh_gt = parse_bvh(clean_path)
        pos_gt, j_names = compute_forward_kinematics(bvh_gt, include_end_sites=False)
        v_gt = compute_velocities(pos_gt, bvh_gt.frame_time)
        gt_vel_energy = float(np.sum(np.linalg.norm(v_gt, axis=-1) ** 2))

        for lvl in ["low", "medium", "high"]:
            pred_path = os.path.join(out_denoise_dir, f"{mid}_{lvl}.bvh")
            raw_path = os.path.join(dataset_root, "public", "denoising", f"{mid}_{lvl}.bvh")

            bvh_pred = parse_bvh(pred_path)
            pos_pred, _ = compute_forward_kinematics(bvh_pred, include_end_sites=False)
            v_pred = compute_velocities(pos_pred, bvh_pred.frame_time)
            pred_vel_energy = float(np.sum(np.linalg.norm(v_pred, axis=-1) ** 2))

            # Raw corrupted metrics for baseline comparison
            bvh_raw = parse_bvh(raw_path)
            pos_raw, _ = compute_forward_kinematics(bvh_raw, include_end_sites=False)

            # Metrics
            mpjpe_pred = calculate_mpjpe(pos_pred, pos_gt)
            mpjpe_raw = calculate_mpjpe(pos_raw, pos_gt)
            jve_pred = calculate_velocity_error(pos_pred, pos_gt, bvh_gt.frame_time)
            jve_raw = calculate_velocity_error(pos_raw, pos_gt, bvh_gt.frame_time)
            jitter_pred = calculate_jitter_error(pos_pred, pos_gt, bvh_gt.frame_time)
            jitter_raw = calculate_jitter_error(pos_raw, pos_gt, bvh_gt.frame_time)
            pres_ratio = pred_vel_energy / max(1e-6, gt_vel_energy)

            denoise_records.append({
                'motion_id': mid,
                'level': lvl.upper(),
                'frames': bvh_gt.frame_count,
                'mpjpe_baseline': round(mpjpe_pred, 4),
                'mpjpe_raw_corrupted': round(mpjpe_raw, 4),
                'jve_baseline': round(jve_pred, 4),
                'jve_raw_corrupted': round(jve_raw, 4),
                'jitter_baseline': round(jitter_pred, 2),
                'jitter_raw_corrupted': round(jitter_raw, 2),
                'motion_preservation_ratio': round(pres_ratio, 4),
                'mpjpe_reduction_pct': round((mpjpe_raw - mpjpe_pred) / mpjpe_raw * 100, 2),
                'jitter_reduction_pct': round((jitter_raw - jitter_pred) / jitter_raw * 100, 2)
            })

    df_denoise = pd.DataFrame(denoise_records)
    denoise_csv_path = os.path.join(res_dir, "denoising_metrics.csv")
    df_denoise.to_csv(denoise_csv_path, index=False)
    print(f"  [OK] Saved {len(df_denoise)} denoising metric records to: {denoise_csv_path}")

    # =========================================================================
    # 3. Task 2: Gap Filling Metrics Collection
    # =========================================================================
    print("\n--- Collecting Task 2 (Gap Filling) Metrics ---")
    gap_records = []
    for mid in training_motions:
        clean_path = os.path.join(dataset_root, "clean", "bvh", f"{mid}_clean.bvh")
        bvh_gt = parse_bvh(clean_path)
        pos_gt, j_names = compute_forward_kinematics(bvh_gt, include_end_sites=True)
        vel_gt = compute_velocities(pos_gt, bvh_gt.frame_time)

        for gt in ["short", "medium", "long"]:
            gap_id = f"{mid}_{gt}"
            pred_path = os.path.join(out_gap_dir, f"{gap_id}.bvh")
            raw_path = os.path.join(dataset_root, "public", "gap_filling", f"{gap_id}.bvh")

            gap_row = df_gap.loc[gap_id]
            target_joint = gap_row['joint_name']
            s_f = int(gap_row['start_frame'])
            e_f = int(gap_row['end_frame'])

            # Kinematic distal endpoint (child node moved by this joint's rotation)
            target_node = bvh_gt.node_by_name[target_joint]
            distal_name = target_node.children[0].name if len(target_node.children) > 0 else target_joint
            distal_idx = j_names.index(distal_name)

            bvh_pred = parse_bvh(pred_path)
            pos_pred, _ = compute_forward_kinematics(bvh_pred, include_end_sites=True)
            vel_pred = compute_velocities(pos_pred, bvh_pred.frame_time)

            bvh_raw = parse_bvh(raw_path)
            pos_raw, _ = compute_forward_kinematics(bvh_raw, include_end_sites=True)

            # 1. Inpainting MPJPE on occluded interval [s_f, e_f]
            gap_pos_pred = pos_pred[s_f:e_f+1, distal_idx]
            gap_pos_gt = pos_gt[s_f:e_f+1, distal_idx]
            gap_pos_raw = pos_raw[s_f:e_f+1, distal_idx]

            inp_mpjpe = float(np.mean(np.linalg.norm(gap_pos_pred - gap_pos_gt, axis=-1)))
            inp_mpjpe_raw = float(np.mean(np.linalg.norm(gap_pos_raw - gap_pos_gt, axis=-1)))

            # 2. Boundary Continuity Error (at s_f and e_f)
            p_step_in = float(np.linalg.norm(pos_pred[s_f, distal_idx] - pos_gt[s_f - 1, distal_idx]))
            p_step_out = float(np.linalg.norm(pos_pred[e_f, distal_idx] - pos_gt[min(len(pos_gt)-1, e_f + 1), distal_idx]))
            bound_err = p_step_in + p_step_out

            # Velocity continuity
            v_step_in = float(np.linalg.norm(vel_pred[s_f, distal_idx] - vel_gt[s_f - 1, distal_idx])) if s_f < len(vel_pred) else 0.0
            v_step_out = float(np.linalg.norm(vel_pred[min(len(vel_pred)-1, e_f), distal_idx] - vel_gt[min(len(vel_gt)-1, e_f + 1), distal_idx]))
            v_bound_err = v_step_in + v_step_out

            # 3. Unmodified Fidelity Check outside gap
            mask_outside = np.ones(bvh_gt.frame_count, dtype=bool)
            mask_outside[s_f:e_f+1] = False
            outside_max_err = float(np.max(np.abs(bvh_pred.motion_data[mask_outside] - bvh_gt.motion_data[mask_outside])))

            # 4. Foot skating (if leg/foot was target)
            foot_skating = 0.0
            if 'Leg' in target_joint or 'Foot' in target_joint:
                # horizontal velocity during contact
                h_vel = np.linalg.norm(vel_pred[s_f:min(len(vel_pred), e_f), distal_idx, [0, 2]], axis=-1)
                is_contact = h_vel < calibrated_contact_threshold
                if np.any(is_contact):
                    foot_skating = float(np.mean(h_vel[is_contact]))

            gap_records.append({
                'motion_id': mid,
                'gap_id': gap_id,
                'gap_type': gt.upper(),
                'target_joint': target_joint,
                'gap_length': e_f - s_f + 1,
                'inpainting_mpjpe': round(inp_mpjpe, 4),
                'inpainting_mpjpe_raw': round(inp_mpjpe_raw, 4),
                'boundary_error': round(bound_err, 4),
                'v_boundary_error': round(v_bound_err, 4),
                'unmodified_max_diff': outside_max_err,
                'foot_skating': round(foot_skating, 4),
                'improvement_pct': round((inp_mpjpe_raw - inp_mpjpe) / max(1e-5, inp_mpjpe_raw) * 100, 2)
            })

    df_gap_res = pd.DataFrame(gap_records)
    gap_csv_path = os.path.join(res_dir, "gap_filling_metrics.csv")
    df_gap_res.to_csv(gap_csv_path, index=False)
    print(f"  [OK] Saved {len(df_gap_res)} gap filling metric records to: {gap_csv_path}")

    # =========================================================================
    # 4. Task 3: Retargeting Metrics Collection
    # =========================================================================
    print("\n--- Collecting Task 3 (Retargeting) Metrics ---")
    retarget_records = []
    ee_names = ['Head', 'LeftHandIndex1', 'RightHandIndex1', 'LeftToeBase', 'RightToeBase']

    for mid in training_motions:
        clean_path = os.path.join(dataset_root, "clean", "bvh", f"{mid}_clean.bvh")
        bvh_src = parse_bvh(clean_path)
        pos_src, j_names_src = compute_forward_kinematics(bvh_src, include_end_sites=False)
        hips_idx = j_names_src.index('Hips')

        # Compute source limb rest lengths
        src_bone_lens = get_bone_lengths(bvh_src)

        for tgt in ["target_small", "target_medium", "target_tall"]:
            pred_path = os.path.join(out_retarget_dir, f"{mid}_{tgt}.bvh")
            bvh_tgt = parse_bvh(pred_path)
            pos_tgt, j_names_tgt = compute_forward_kinematics(bvh_tgt, include_end_sites=False)

            # 1. End-Effector Semantic Error
            ee_errs = []
            for ee in ee_names:
                idx = j_names_src.index(ee)
                # Relative to hips
                rel_src = pos_src[:, idx] - pos_src[:, hips_idx]
                rel_tgt = pos_tgt[:, idx] - pos_tgt[:, hips_idx]

                # Normalize by limb distance from hips in rest pose
                src_rest_dist = max(1.0, float(np.linalg.norm(pos_src[0, idx] - pos_src[0, hips_idx])))
                tgt_rest_dist = max(1.0, float(np.linalg.norm(pos_tgt[0, idx] - pos_tgt[0, hips_idx])))

                norm_src = rel_src / src_rest_dist
                norm_tgt = rel_tgt / tgt_rest_dist

                diff = np.linalg.norm(norm_tgt - norm_src, axis=-1)
                ee_errs.append(np.mean(diff))

            ee_error = float(np.mean(ee_errs))

            # 2. Geodesic Angular Deviation (rotational angles transferred)
            # For baseline, rotational angles are transferred directly, so geodesic dev should be ~ 0
            ang_errs = []
            for n in bvh_src.nodes:
                if not n.is_end_site:
                    c = n.channel_indices
                    z_src, y_src, x_src = bvh_src.motion_data[:, c[-3]], bvh_src.motion_data[:, c[-2]], bvh_src.motion_data[:, c[-1]]
                    z_tgt, y_tgt, x_tgt = bvh_tgt.motion_data[:, c[-3]], bvh_tgt.motion_data[:, c[-2]], bvh_tgt.motion_data[:, c[-1]]

                    # Sample 100 frames to save computation
                    sample_idx = np.linspace(0, bvh_src.frame_count - 1, min(100, bvh_src.frame_count), dtype=int)
                    R_s = np.array([euler_zyx_to_matrix(z_src[t], y_src[t], x_src[t]) for t in sample_idx])
                    R_t = np.array([euler_zyx_to_matrix(z_tgt[t], y_tgt[t], x_tgt[t]) for t in sample_idx])
                    ang_errs.append(np.mean(compute_so3_geodesic_degrees(R_s, R_t)))

            ang_error = float(np.mean(ang_errs))

            # 3. Bone-Length Invariance
            # Check maximum deviation between FK bone length and BVH target offset
            tgt_bone_lens = get_bone_lengths(bvh_tgt)
            max_bone_dev = 0.0
            for node in bvh_tgt.nodes:
                if not node.is_root and not node.is_end_site:
                    p_idx = j_names_tgt.index(node.name)
                    par_idx = j_names_tgt.index(node.parent.name)
                    dyn_lens = np.linalg.norm(pos_tgt[:, p_idx] - pos_tgt[:, par_idx], axis=-1)
                    target_l = tgt_bone_lens[node.name]
                    dev = np.max(np.abs(dyn_lens - target_l))
                    max_bone_dev = max(max_bone_dev, float(dev))

            # 4. Ground Penetration & Minimum Foot Y
            l_toe_idx = j_names_tgt.index('LeftToeBase')
            r_toe_idx = j_names_tgt.index('RightToeBase')
            min_y = float(min(np.min(pos_tgt[:, l_toe_idx, 1]), np.min(pos_tgt[:, r_toe_idx, 1])))
            ground_pen = max(0.0, -min_y)

            retarget_records.append({
                'motion_id': mid,
                'target_type': tgt,
                'frames': bvh_tgt.frame_count,
                'end_effector_error': round(ee_error, 4),
                'angular_geodesic_error_deg': round(ang_error, 4),
                'max_bone_deviation': round(max_bone_dev, 6),
                'min_foot_height_y': round(min_y, 4),
                'ground_penetration': round(ground_pen, 4)
            })

    df_retarget = pd.DataFrame(retarget_records)
    retarget_csv_path = os.path.join(res_dir, "retargeting_metrics.csv")
    df_retarget.to_csv(retarget_csv_path, index=False)
    print(f"  [OK] Saved {len(df_retarget)} retargeting metric records to: {retarget_csv_path}")

    print("\n[COMPLETE] All metric collection finished successfully!")

if __name__ == "__main__":
    run_metric_collection()
