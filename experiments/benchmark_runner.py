"""
experiments/benchmark_runner.py — MOTIONFORGE Reproducible Benchmark Runner

Runs comprehensive comparative benchmarks between Baseline and Experimental algorithms:
- Task 1 (Denoising): Baseline Savitzky-Golay vs Butterworth vs Gaussian vs Adaptive Savitzky-Golay
- Task 2 (Gap Filling): Baseline Linear vs Baseline Natural Cubic vs PCHIP vs Clamped Hermite
- Task 3 (Retargeting): Baseline vs Full-Chain Leg vs Contact-Aware Adaptive

Outputs detailed benchmark summary and saves results to reports/benchmark_results.json.
"""

import os
import sys
import time
import json
import tempfile
import csv
from typing import Dict, Any, List

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from baselines.denoising.baseline_denoising import run_denoising
from experiments.denoising_experiments import run_denoising_experiment
from baselines.gap_filling.baseline_gap_filling import run_gap_filling
from experiments.gap_filling_experiments import run_gap_filling_experiment
from baselines.retargeting.baseline_retargeting import retarget_motion
from experiments.retargeting_experiments import run_retargeting_experiment, compute_foot_sliding_diagnostics
from evaluation.task_evaluator import evaluate_task1, evaluate_task2, evaluate_task3
from baselines.common.bvh_io import parse_bvh

DATASET_DIR = os.path.join(WORKSPACE_ROOT, "MOTIONFORGE_DATASET")
CLEAN_DIR = os.path.join(DATASET_DIR, "clean", "bvh")
GAP_META_PATH = os.path.join(DATASET_DIR, "metadata", "gap_metadata.csv")

def benchmark_task1_denoising(motions: List[str] = ["MF001", "MF002", "MF003"], levels: List[str] = ["LOW", "MEDIUM", "HIGH"]):
    """
    Benchmarks Task 1 algorithms across specified motions and noise levels.
    """
    methods = ["baseline_savgol", "butterworth", "gaussian", "adaptive_savgol"]
    results = {m: [] for m in methods}

    for mid in motions:
        clean_path = os.path.join(CLEAN_DIR, f"{mid}_clean.bvh")
        if not os.path.exists(clean_path):
            continue

        for lvl in levels:
            noisy_path = os.path.join(DATASET_DIR, "public", "denoising", f"{mid}_{lvl}.bvh")
            if not os.path.exists(noisy_path):
                continue

            for method in methods:
                with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as tmp:
                    tmp_out = tmp.name
                try:
                    t0 = time.perf_counter()
                    run_denoising_experiment(noisy_path, tmp_out, noise_level=lvl, method=method)
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0

                    eval_res = evaluate_task1(pred_path=tmp_out, gt_path=clean_path, noisy_path=noisy_path)

                    entry = {
                        "motion_id": mid,
                        "noise_level": lvl,
                        "method": method,
                        "score": round(eval_res.get("score") or 0.0, 2),
                        "status": eval_res.get("status", "ERROR"),
                        "runtime_ms": round(elapsed_ms, 2),
                        "metrics": eval_res.get("metrics", {})
                    }
                    results[method].append(entry)
                finally:
                    if os.path.exists(tmp_out):
                        os.remove(tmp_out)

    return results

def benchmark_task2_gap_filling(motions: List[str] = ["MF001", "MF002", "MF003"], gap_types: List[str] = ["SHORT", "MEDIUM", "LONG"]):
    """
    Benchmarks Task 2 algorithms across specified motions and gap difficulties.
    """
    methods = ["linear", "natural_cubic", "pchip", "clamped_hermite"]
    results = {m: [] for m in methods}

    # Load gap metadata
    meta = {}
    if os.path.exists(GAP_META_PATH):
        with open(GAP_META_PATH, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                meta[row["gap_id"]] = row

    for mid in motions:
        clean_path = os.path.join(CLEAN_DIR, f"{mid}_clean.bvh")
        if not os.path.exists(clean_path):
            continue

        for gt in gap_types:
            gap_id = f"{mid}_{gt.lower()}"
            row = meta.get(gap_id)
            if not row:
                continue

            input_path = os.path.join(DATASET_DIR, row["output_file"])
            if not os.path.exists(input_path):
                continue

            s_f = int(row["start_frame"])
            e_f = int(row["end_frame"])
            j_name = row["joint_name"]

            for method in methods:
                with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as tmp:
                    tmp_out = tmp.name
                try:
                    t0 = time.perf_counter()
                    run_gap_filling_experiment(input_path, tmp_out, s_f, e_f, j_name, method=method)
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0

                    eval_res = evaluate_task2(
                        pred_path=tmp_out,
                        gt_path=clean_path,
                        joint_name=j_name,
                        start_frame=s_f,
                        end_frame=e_f
                    )

                    entry = {
                        "motion_id": mid,
                        "gap_type": gt,
                        "gap_id": gap_id,
                        "joint_name": j_name,
                        "method": method,
                        "score": round(eval_res.get("score") or 0.0, 2),
                        "status": eval_res.get("status", "ERROR"),
                        "runtime_ms": round(elapsed_ms, 2),
                        "metrics": eval_res.get("metrics", {})
                    }
                    results[method].append(entry)
                finally:
                    if os.path.exists(tmp_out):
                        os.remove(tmp_out)

    return results

def benchmark_task3_retargeting(motions: List[str] = ["MF001", "MF002", "MF003"], targets: List[str] = ["small", "medium", "tall"]):
    """
    Benchmarks Task 3 algorithms across specified motions and target avatar morphologies.
    """
    methods = ["baseline", "full_chain", "contact_aware"]
    results = {m: [] for m in methods}

    for mid in motions:
        clean_path = os.path.join(CLEAN_DIR, f"{mid}_clean.bvh")
        if not os.path.exists(clean_path):
            continue

        for tgt in targets:
            full_tgt = f"target_{tgt}"
            for method in methods:
                with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as tmp:
                    tmp_out = tmp.name
                try:
                    t0 = time.perf_counter()
                    run_retargeting_experiment(clean_path, tmp_out, target_type=full_tgt, method=method)
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0

                    eval_res = evaluate_task3(pred_path=tmp_out, src_path=clean_path, target_type=tgt)

                    # Diagnostic foot sliding
                    bvh_out = parse_bvh(tmp_out)
                    diagnostics = compute_foot_sliding_diagnostics(bvh_out)

                    entry = {
                        "motion_id": mid,
                        "target_type": full_tgt,
                        "method": method,
                        "score": round(eval_res.get("score") or 0.0, 2),
                        "status": eval_res.get("status", "ERROR"),
                        "runtime_ms": round(elapsed_ms, 2),
                        "metrics": eval_res.get("metrics", {}),
                        "diagnostics": diagnostics
                    }
                    results[method].append(entry)
                finally:
                    if os.path.exists(tmp_out):
                        os.remove(tmp_out)

    return results

def run_full_benchmark(motions: List[str] = ["MF001", "MF002", "MF003"]):
    """
    Runs complete suite across all 3 tasks and saves benchmark JSON.
    """
    print(f"Running MOTIONFORGE Comprehensive Benchmark across motions: {motions}...")
    t_start = time.perf_counter()

    t1_res = benchmark_task1_denoising(motions)
    t2_res = benchmark_task2_gap_filling(motions)
    t3_res = benchmark_task3_retargeting(motions)

    total_time = time.perf_counter() - t_start

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "benchmark_duration_seconds": round(total_time, 2),
        "motions_evaluated": motions,
        "task1_denoising": t1_res,
        "task2_gap_filling": t2_res,
        "task3_retargeting": t3_res
    }

    out_file = os.path.join(WORKSPACE_ROOT, "reports", "benchmark_results.json")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Benchmark completed in {total_time:.2f}s. Saved to {out_file}")
    return summary

if __name__ == "__main__":
    run_full_benchmark()
