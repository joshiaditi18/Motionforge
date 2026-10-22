"""
backend/services/accuracy_service.py — Service layer for MOTIONFORGE Accuracy Lab

Provides comparative analysis between Official Baselines and Improved Experimental Algorithms:
- Real-time on-demand side-by-side evaluation
- Per-frame error dynamics curve generation
- Problematic joint & frame diagnostics
- Benchmark suite execution and retrieval
"""

import os
import sys
import time
import tempfile
import json
import csv
from typing import Dict, Any, List, Optional
import numpy as np

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from baselines.common.bvh_io import parse_bvh
from baselines.common.forward_kinematics import compute_forward_kinematics
from baselines.denoising.baseline_denoising import run_denoising
from experiments.denoising_experiments import run_denoising_experiment
from baselines.gap_filling.baseline_gap_filling import run_gap_filling
from experiments.gap_filling_experiments import run_gap_filling_experiment
from baselines.retargeting.baseline_retargeting import retarget_motion
from experiments.retargeting_experiments import run_retargeting_experiment, compute_foot_sliding_diagnostics
from evaluation.task_evaluator import evaluate_task1, evaluate_task2, evaluate_task3
from backend.services.motion_service import motion_service
from backend.services.processing_service import processing_service

BENCHMARK_PATH = os.path.join(WORKSPACE_ROOT, "reports", "benchmark_results.json")
DATASET_DIR = os.path.join(WORKSPACE_ROOT, "MOTIONFORGE_DATASET")

class AccuracyService:
    def get_available_methods(self) -> Dict[str, Any]:
        return {
            "denoising": [
                {"id": "baseline_savgol", "name": "Savitzky-Golay (Official Baseline)", "category": "baseline", "description": "Fixed polynomial window smoothing with phase unwrapping."},
                {"id": "adaptive_savgol", "name": "Velocity-Adaptive Savitzky-Golay (Improved)", "category": "experimental", "description": "Dynamic window adjustment based on angular kinetics with mirror boundary padding."},
                {"id": "butterworth", "name": "Zero-Phase Butterworth Filter", "category": "experimental", "description": "2nd-order bidirectional IIR lowpass filter."},
                {"id": "gaussian", "name": "Gaussian Temporal Filter", "category": "experimental", "description": "1D Gaussian kernel smoothing."}
            ],
            "gap_filling": [
                {"id": "natural_cubic", "name": "Natural Cubic Spline (Official Baseline)", "category": "baseline", "description": "Natural cubic spline across 6 boundary anchor frames."},
                {"id": "pchip", "name": "PCHIP Shape-Preserving Hermite (Improved)", "category": "experimental", "description": "Monotonic piecewise cubic Hermite interpolation; completely eliminates overshoot."},
                {"id": "clamped_hermite", "name": "Velocity-Clamped Hermite (C1 Continuous)", "category": "experimental", "description": "Explicit finite-difference boundary velocity matching."},
                {"id": "linear", "name": "Linear Interpolation", "category": "experimental", "description": "First-order straight trajectory interpolation."}
            ],
            "retargeting": [
                {"id": "baseline", "name": "Proportional Bone Scaling (Official Baseline)", "category": "baseline", "description": "Direct bone offset scaling with (thigh+shin)/2 root translation."},
                {"id": "contact_aware", "name": "Contact-Aware & Anti-Penetration (Improved)", "category": "experimental", "description": "Full kinematic chain rest scaling with dynamic ground-plane clearance clamping."},
                {"id": "full_chain", "name": "Full-Kinematic Chain Leg Scaling", "category": "experimental", "description": "Exact rest height proportion taking thigh, shin, and foot into account."}
            ]
        }

    def compare_denoising(
        self,
        motion_id: str,
        noise_level: str = "MEDIUM",
        method_baseline: str = "baseline_savgol",
        method_experimental: str = "adaptive_savgol"
    ) -> Dict[str, Any]:
        lvl = noise_level.upper()
        clean_path = motion_service.get_bvh_file_path(motion_id, variant="clean")
        noisy_path = motion_service.get_bvh_file_path(motion_id, variant="denoising", subvariant=lvl)

        if not clean_path or not os.path.exists(clean_path):
            raise FileNotFoundError(f"Clean BVH not found for {motion_id}")
        if not noisy_path or not os.path.exists(noisy_path):
            raise FileNotFoundError(f"Noisy BVH not found for {motion_id} at {lvl}")

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as b_tmp, \
             tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as e_tmp:
            b_path = b_tmp.name
            e_path = e_tmp.name

        try:
            # Run baseline
            t0 = time.perf_counter()
            run_denoising_experiment(noisy_path, b_path, noise_level=lvl, method=method_baseline)
            time_b = (time.perf_counter() - t0) * 1000.0

            # Run experimental
            t1 = time.perf_counter()
            run_denoising_experiment(noisy_path, e_path, noise_level=lvl, method=method_experimental)
            time_e = (time.perf_counter() - t1) * 1000.0

            # Evaluate both
            eval_b = evaluate_task1(pred_path=b_path, gt_path=clean_path, noisy_path=noisy_path)
            eval_e = evaluate_task1(pred_path=e_path, gt_path=clean_path, noisy_path=noisy_path)

            # Compute per-frame error dynamics curve
            bvh_gt = parse_bvh(clean_path)
            bvh_b = parse_bvh(b_path)
            bvh_e = parse_bvh(e_path)

            pos_gt, j_names = compute_forward_kinematics(bvh_gt, include_end_sites=False)
            pos_b, _ = compute_forward_kinematics(bvh_b, include_end_sites=False)
            pos_e, _ = compute_forward_kinematics(bvh_e, include_end_sites=False)

            # Frame MPJPE: mean over joints at each frame (in inches)
            err_b_frame = np.mean(np.linalg.norm(pos_b - pos_gt, axis=-1), axis=-1)
            err_e_frame = np.mean(np.linalg.norm(pos_e - pos_gt, axis=-1), axis=-1)

            # Joint MPJPE: mean over frames for each joint
            err_b_joint = np.mean(np.linalg.norm(pos_b - pos_gt, axis=-1), axis=0)
            err_e_joint = np.mean(np.linalg.norm(pos_e - pos_gt, axis=-1), axis=0)

            # Downsample curve for responsive UI chart (max 80 points)
            N = len(err_b_frame)
            step = max(1, N // 80)
            sample_frames = list(range(0, N, step))
            error_curve = [
                {
                    "frame": int(f),
                    "baseline_error": round(float(err_b_frame[f]), 4),
                    "experimental_error": round(float(err_e_frame[f]), 4)
                }
                for f in sample_frames
            ]

            # Peak error frame
            peak_f_b = int(np.argmax(err_b_frame))
            peak_f_e = int(np.argmax(err_e_frame))

            # Worst joint
            worst_j_idx = int(np.argmax(err_b_joint))
            worst_joint_name = j_names[worst_j_idx]

            # BVH contents
            with open(noisy_path, "r", encoding="utf-8") as f:
                input_bvh = f.read()
            with open(b_path, "r", encoding="utf-8") as f:
                baseline_bvh = f.read()
            with open(e_path, "r", encoding="utf-8") as f:
                experimental_bvh = f.read()

            return {
                "task": "denoising",
                "motion_id": motion_id,
                "config": {"noise_level": lvl},
                "method_baseline": method_baseline,
                "method_experimental": method_experimental,
                "score_baseline": round(eval_b.get("score") or 0.0, 2),
                "score_experimental": round(eval_e.get("score") or 0.0, 2),
                "score_delta": round((eval_e.get("score") or 0.0) - (eval_b.get("score") or 0.0), 2),
                "runtime_baseline_ms": round(time_b, 2),
                "runtime_experimental_ms": round(time_e, 2),
                "metrics_baseline": eval_b.get("metrics", {}),
                "metrics_experimental": eval_e.get("metrics", {}),
                "error_curve": error_curve,
                "diagnostics": {
                    "peak_error_frame_baseline": peak_f_b,
                    "peak_error_frame_experimental": peak_f_e,
                    "peak_error_baseline": round(float(err_b_frame[peak_f_b]), 4),
                    "peak_error_experimental": round(float(err_e_frame[peak_f_e]), 4),
                    "worst_joint": worst_joint_name,
                    "worst_joint_baseline_error": round(float(err_b_joint[worst_j_idx]), 4),
                    "worst_joint_experimental_error": round(float(err_e_joint[worst_j_idx]), 4)
                },
                "input_bvh": input_bvh,
                "baseline_bvh": baseline_bvh,
                "experimental_bvh": experimental_bvh
            }
        finally:
            if os.path.exists(b_path):
                os.remove(b_path)
            if os.path.exists(e_path):
                os.remove(e_path)

    def compare_gap_filling(
        self,
        motion_id: str,
        gap_type: str = "MEDIUM",
        method_baseline: str = "natural_cubic",
        method_experimental: str = "pchip"
    ) -> Dict[str, Any]:
        clean_path = motion_service.get_bvh_file_path(motion_id, variant="clean")
        if not clean_path or not os.path.exists(clean_path):
            raise FileNotFoundError(f"Clean BVH not found for {motion_id}")

        gaps = processing_service.get_gap_metadata()
        gap_id = f"{motion_id}_{gap_type.lower()}"
        gap_info = gaps.get(gap_id)
        if not gap_info:
            raise FileNotFoundError(f"Gap metadata not found for {gap_id}")

        input_path = os.path.join(DATASET_DIR, gap_info["output_file"])
        s_f = gap_info["start_frame"]
        e_f = gap_info["end_frame"]
        j_name = gap_info["joint_name"]

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as b_tmp, \
             tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as e_tmp:
            b_path = b_tmp.name
            e_path = e_tmp.name

        try:
            t0 = time.perf_counter()
            run_gap_filling_experiment(input_path, b_path, s_f, e_f, j_name, method=method_baseline)
            time_b = (time.perf_counter() - t0) * 1000.0

            t1 = time.perf_counter()
            run_gap_filling_experiment(input_path, e_path, s_f, e_f, j_name, method=method_experimental)
            time_e = (time.perf_counter() - t1) * 1000.0

            eval_b = evaluate_task2(pred_path=b_path, gt_path=clean_path, joint_name=j_name, start_frame=s_f, end_frame=e_f)
            eval_e = evaluate_task2(pred_path=e_path, gt_path=clean_path, joint_name=j_name, start_frame=s_f, end_frame=e_f)

            # Error curve across gap window
            bvh_gt = parse_bvh(clean_path)
            bvh_b = parse_bvh(b_path)
            bvh_e = parse_bvh(e_path)

            pos_gt, j_names = compute_forward_kinematics(bvh_gt, include_end_sites=True)
            pos_b, _ = compute_forward_kinematics(bvh_b, include_end_sites=True)
            pos_e, _ = compute_forward_kinematics(bvh_e, include_end_sites=True)

            from evaluation.metrics.gap_filling_metrics import resolve_distal_joint_endpoint
            distal_name = resolve_distal_joint_endpoint(bvh_gt, j_name)
            d_idx = j_names.index(distal_name)

            # Window of gap ± 10 frames
            w_start = max(0, s_f - 10)
            w_end = min(bvh_gt.frame_count - 1, e_f + 10)

            error_curve = []
            for f in range(w_start, w_end + 1):
                err_b = float(np.linalg.norm(pos_b[f, d_idx] - pos_gt[f, d_idx]))
                err_e = float(np.linalg.norm(pos_e[f, d_idx] - pos_gt[f, d_idx]))
                error_curve.append({
                    "frame": f,
                    "baseline_error": round(err_b, 4),
                    "experimental_error": round(err_e, 4)
                })

            with open(input_path, "r", encoding="utf-8") as f:
                input_bvh = f.read()
            with open(b_path, "r", encoding="utf-8") as f:
                baseline_bvh = f.read()
            with open(e_path, "r", encoding="utf-8") as f:
                experimental_bvh = f.read()

            return {
                "task": "gap_filling",
                "motion_id": motion_id,
                "config": {"gap_type": gap_type, "joint_name": j_name, "start_frame": s_f, "end_frame": e_f},
                "method_baseline": method_baseline,
                "method_experimental": method_experimental,
                "score_baseline": round(eval_b.get("score") or 0.0, 2),
                "score_experimental": round(eval_e.get("score") or 0.0, 2),
                "score_delta": round((eval_e.get("score") or 0.0) - (eval_b.get("score") or 0.0), 2),
                "runtime_baseline_ms": round(time_b, 2),
                "runtime_experimental_ms": round(time_e, 2),
                "metrics_baseline": eval_b.get("metrics", {}),
                "metrics_experimental": eval_e.get("metrics", {}),
                "error_curve": error_curve,
                "diagnostics": {
                    "occluded_joint": j_name,
                    "distal_evaluated_joint": distal_name,
                    "gap_frame_range": [s_f, e_f],
                    "observed_frame_invariance_baseline": eval_b.get("metrics", {}).get("unmodified_max_diff", 0.0),
                    "observed_frame_invariance_experimental": eval_e.get("metrics", {}).get("unmodified_max_diff", 0.0)
                },
                "input_bvh": input_bvh,
                "baseline_bvh": baseline_bvh,
                "experimental_bvh": experimental_bvh
            }
        finally:
            if os.path.exists(b_path):
                os.remove(b_path)
            if os.path.exists(e_path):
                os.remove(e_path)

    def compare_retargeting(
        self,
        motion_id: str,
        target_type: str = "target_tall",
        method_baseline: str = "baseline",
        method_experimental: str = "contact_aware"
    ) -> Dict[str, Any]:
        clean_path = motion_service.get_bvh_file_path(motion_id, variant="clean")
        if not clean_path or not os.path.exists(clean_path):
            raise FileNotFoundError(f"Clean BVH not found for {motion_id}")

        tgt = target_type.lower()
        if not tgt.startswith("target_"):
            tgt = f"target_{tgt}"
        clean_target = tgt.replace("target_", "")

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as b_tmp, \
             tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as e_tmp:
            b_path = b_tmp.name
            e_path = e_tmp.name

        try:
            t0 = time.perf_counter()
            run_retargeting_experiment(clean_path, b_path, target_type=tgt, method=method_baseline)
            time_b = (time.perf_counter() - t0) * 1000.0

            t1 = time.perf_counter()
            run_retargeting_experiment(clean_path, e_path, target_type=tgt, method=method_experimental)
            time_e = (time.perf_counter() - t1) * 1000.0

            eval_b = evaluate_task3(pred_path=b_path, src_path=clean_path, target_type=clean_target)
            eval_e = evaluate_task3(pred_path=e_path, src_path=clean_path, target_type=clean_target)

            bvh_b = parse_bvh(b_path)
            bvh_e = parse_bvh(e_path)
            diag_b = compute_foot_sliding_diagnostics(bvh_b)
            diag_e = compute_foot_sliding_diagnostics(bvh_e)

            # Error curve across frames (end-effector distance)
            pos_src, j_names = compute_forward_kinematics(parse_bvh(clean_path), include_end_sites=False)
            pos_b, _ = compute_forward_kinematics(bvh_b, include_end_sites=False)
            pos_e, _ = compute_forward_kinematics(bvh_e, include_end_sites=False)

            head_idx = j_names.index('Head')
            step = max(1, len(pos_src) // 80)
            sample_frames = list(range(0, len(pos_src), step))
            error_curve = [
                {
                    "frame": f,
                    "baseline_error": round(float(abs(pos_b[f, head_idx, 1] - pos_src[f, head_idx, 1])), 4),
                    "experimental_error": round(float(abs(pos_e[f, head_idx, 1] - pos_src[f, head_idx, 1])), 4)
                }
                for f in sample_frames
            ]

            with open(clean_path, "r", encoding="utf-8") as f:
                input_bvh = f.read()
            with open(b_path, "r", encoding="utf-8") as f:
                baseline_bvh = f.read()
            with open(e_path, "r", encoding="utf-8") as f:
                experimental_bvh = f.read()

            return {
                "task": "retargeting",
                "motion_id": motion_id,
                "config": {"target_type": tgt},
                "method_baseline": method_baseline,
                "method_experimental": method_experimental,
                "score_baseline": round(eval_b.get("score") or 0.0, 2),
                "score_experimental": round(eval_e.get("score") or 0.0, 2),
                "score_delta": round((eval_e.get("score") or 0.0) - (eval_b.get("score") or 0.0), 2),
                "runtime_baseline_ms": round(time_b, 2),
                "runtime_experimental_ms": round(time_e, 2),
                "metrics_baseline": eval_b.get("metrics", {}),
                "metrics_experimental": eval_e.get("metrics", {}),
                "error_curve": error_curve,
                "diagnostics": {
                    "foot_sliding_baseline": diag_b,
                    "foot_sliding_experimental": diag_e,
                    "ground_penetration_baseline": eval_b.get("metrics", {}).get("ground_penetration_penalty", 0.0),
                    "ground_penetration_experimental": eval_e.get("metrics", {}).get("ground_penetration_penalty", 0.0)
                },
                "input_bvh": input_bvh,
                "baseline_bvh": baseline_bvh,
                "experimental_bvh": experimental_bvh
            }
        finally:
            if os.path.exists(b_path):
                os.remove(b_path)
            if os.path.exists(e_path):
                os.remove(e_path)

    def get_benchmark_results(self) -> Dict[str, Any]:
        if os.path.exists(BENCHMARK_PATH):
            with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"status": "not_run", "message": "Benchmark results not yet generated"}

accuracy_service = AccuracyService()
