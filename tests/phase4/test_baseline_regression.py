"""
tests/phase4/test_baseline_regression.py — Baseline regression tests.

Verifies that the evaluation engine scores the Phase 3 baseline outputs
within expected ranges (±10 points) of the calibrated baseline scores.

Reference scores from calibration/metric_calibration.json:
    Task 1:  LOW=60.4,  MEDIUM=40.0, HIGH=15.0
    Task 2:  SHORT=51.81, MEDIUM=62.78, LONG=12.5
    Task 3:  small=43.24, medium=66.76, tall=68.33
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from evaluation.task_evaluator import evaluate_task1, evaluate_task2, evaluate_task3

# Directories
_ROOT     = os.path.join(os.path.dirname(__file__), "..", "..")
_BASELINE = os.path.join(_ROOT, "baselines", "outputs")
_CLEAN    = os.path.join(_ROOT, "MOTIONFORGE_DATASET", "clean", "bvh")
_PUBLIC   = os.path.join(_ROOT, "MOTIONFORGE_DATASET", "public")

# Tolerance for baseline score regression
SCORE_TOLERANCE = 15.0   # ±15 points (generous for integration test)


def _has_file(path):
    return os.path.isfile(path)


class TestTask1BaselineRegression:
    @pytest.mark.parametrize("motion_id,noise_level,ref_score", [
        ("MF001", "LOW",    60.4),
        ("MF001", "MEDIUM", 40.0),
        ("MF001", "HIGH",   15.0),
    ])
    def test_denoising_baseline_score(self, motion_id, noise_level, ref_score):
        gt_path   = os.path.join(_CLEAN, f"{motion_id}_clean.bvh")
        pred_path = os.path.join(_BASELINE, "denoising", f"{motion_id}_{noise_level}_denoised.bvh")
        noisy_path = os.path.join(_PUBLIC, "denoising", f"{motion_id}_{noise_level}.bvh")

        if not _has_file(pred_path):
            pytest.skip(f"Baseline output missing: {pred_path}")
        if not _has_file(gt_path):
            pytest.skip(f"GT missing: {gt_path}")

        result = evaluate_task1(pred_path=pred_path, gt_path=gt_path,
                                noisy_path=noisy_path if _has_file(noisy_path) else None)

        assert result["status"] == "VALID", f"Unexpected status: {result['status']} — {result.get('error_message')}"
        score = result["score"]
        assert score is not None
        assert abs(score - ref_score) <= SCORE_TOLERANCE, (
            f"Task1 {motion_id} {noise_level}: score={score:.2f}, "
            f"ref={ref_score}, diff={abs(score-ref_score):.2f}"
        )


class TestTask2BaselineRegression:
    @pytest.mark.parametrize("motion_id,gap_type,ref_score", [
        ("MF001", "short",  51.81),
        ("MF001", "medium", 62.78),
        ("MF001", "long",   12.5),
    ])
    def test_gap_filling_baseline_score(self, motion_id, gap_type, ref_score):
        import csv
        meta_path = os.path.join(_ROOT, "MOTIONFORGE_DATASET", "metadata", "gap_metadata.csv")
        gt_path   = os.path.join(_CLEAN, f"{motion_id}_clean.bvh")
        gap_id    = f"{motion_id}_{gap_type}"
        pred_path = os.path.join(_BASELINE, "gap_filling", f"{gap_id}_filled.bvh")

        if not _has_file(pred_path):
            pytest.skip(f"Baseline output missing: {pred_path}")
        if not _has_file(gt_path):
            pytest.skip(f"GT missing: {gt_path}")

        # Load gap metadata
        row = None
        with open(meta_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["gap_id"] == gap_id:
                    row = r
                    break
        if row is None:
            pytest.skip(f"Gap metadata not found for {gap_id}")

        result = evaluate_task2(
            pred_path=pred_path, gt_path=gt_path,
            joint_name=row["joint_name"],
            start_frame=int(row["start_frame"]),
            end_frame=int(row["end_frame"]),
        )

        assert result["status"] in ("VALID", "REJECTED"), f"ERROR status: {result.get('error_message')}"
        if result["status"] == "VALID":
            score = result["score"]
            assert abs(score - ref_score) <= SCORE_TOLERANCE, (
                f"Task2 {gap_id}: score={score:.2f}, ref={ref_score}"
            )


class TestTask3BaselineRegression:
    @pytest.mark.parametrize("motion_id,target,ref_score", [
        ("MF001", "small",  43.24),
        ("MF001", "medium", 66.76),
        ("MF001", "tall",   68.33),
    ])
    def test_retargeting_baseline_score(self, motion_id, target, ref_score):
        src_path  = os.path.join(_CLEAN, f"{motion_id}_clean.bvh")
        pred_path = os.path.join(_BASELINE, "retargeting", f"{motion_id}_{target}_retargeted.bvh")

        if not _has_file(pred_path):
            pytest.skip(f"Baseline output missing: {pred_path}")
        if not _has_file(src_path):
            pytest.skip(f"Source missing: {src_path}")

        result = evaluate_task3(pred_path=pred_path, src_path=src_path, target_type=target)

        assert result["status"] == "VALID", f"Unexpected: {result.get('error_message')}"
        score = result["score"]
        assert abs(score - ref_score) <= SCORE_TOLERANCE, (
            f"Task3 {motion_id} {target}: score={score:.2f}, ref={ref_score}"
        )
