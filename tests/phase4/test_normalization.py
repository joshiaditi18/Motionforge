"""
tests/phase4/test_normalization.py — Unit tests for evaluation/scoring/normalization.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import math
import pytest

from evaluation.scoring.normalization import (
    load_calibration,
    get_task_calibration,
    normalize_weighted_exponential,
    check_anti_degeneracy,
    MOTION_PRESERVATION_MIN,
    MOTION_PRESERVATION_MAX,
)


class TestLoadCalibration:
    def test_loads_successfully(self):
        cal = load_calibration()
        assert isinstance(cal, dict)

    def test_has_required_task_keys(self):
        cal = load_calibration()
        for key in ["task_1_denoising", "task_2_gap_filling", "task_3_retargeting"]:
            assert key in cal, f"Missing key: {key}"

    def test_caches_result(self):
        cal1 = load_calibration()
        cal2 = load_calibration()
        assert cal1 is cal2  # same object (cached)

    def test_calibration_status(self):
        cal = load_calibration()
        assert cal["status"] == "CALIBRATED_PHASE3"


class TestGetTaskCalibration:
    def test_task1_has_tau_values(self):
        cal = get_task_calibration(1)
        assert "mpjpe_tau" in cal
        assert "velocity_tau" in cal
        assert "jitter_tau" in cal
        assert cal["mpjpe_tau"] > 0
        assert cal["velocity_tau"] > 0
        assert cal["jitter_tau"] > 0

    def test_task2_has_tau_values(self):
        cal = get_task_calibration(2)
        assert "inpainting_tau" in cal
        assert "boundary_tau" in cal
        assert "v_boundary_tau" in cal

    def test_task3_has_tau_values(self):
        cal = get_task_calibration(3)
        assert "end_effector_tau" in cal
        assert "angular_tau_deg" in cal
        assert "ground_penetration_tau" in cal

    def test_invalid_task_raises(self):
        with pytest.raises(ValueError):
            get_task_calibration(0)
        with pytest.raises(ValueError):
            get_task_calibration(4)

    def test_intra_weights_present(self):
        for task in [1, 2, 3]:
            cal = get_task_calibration(task)
            assert "intra_task_weights" in cal
            w = cal["intra_task_weights"]
            assert isinstance(w, dict)
            total = sum(w.values())
            assert abs(total - 1.0) < 1e-9, f"Task {task} weights don't sum to 1: {total}"


class TestNormalizeWeightedExponential:
    def test_zero_error_gives_100(self):
        score = normalize_weighted_exponential(
            {"a": 0.5, "b": 0.5},
            {"a": 0.0, "b": 0.0},
            {"a": 1.0, "b": 1.0},
        )
        assert abs(score - 100.0) < 1e-9

    def test_large_error_gives_near_zero(self):
        score = normalize_weighted_exponential(
            {"a": 1.0},
            {"a": 1e9},
            {"a": 1.0},
        )
        assert score < 1e-3

    def test_score_bounded_100(self):
        score = normalize_weighted_exponential(
            {"a": 1.0}, {"a": 0.0}, {"a": 1.0}
        )
        assert score <= 100.0

    def test_score_bounded_0(self):
        score = normalize_weighted_exponential(
            {"a": 1.0}, {"a": 1e10}, {"a": 1.0}
        )
        assert score >= 0.0

    def test_formula_correctness(self):
        # S = 100 * exp(-( 0.4*2/1.0 + 0.6*3/2.0 ))
        #   = 100 * exp(-(0.8 + 0.9)) = 100 * exp(-1.7)
        expected = 100.0 * math.exp(-1.7)
        score = normalize_weighted_exponential(
            {"m": 0.4, "v": 0.6},
            {"m": 2.0, "v": 3.0},
            {"m": 1.0, "v": 2.0},
        )
        assert abs(score - expected) < 1e-9

    def test_negative_tau_raises(self):
        with pytest.raises(ValueError):
            normalize_weighted_exponential(
                {"a": 1.0}, {"a": 1.0}, {"a": -1.0}
            )

    def test_negative_error_clamped_to_zero(self):
        # Negative errors (shouldn't happen) should be clamped
        score_neg = normalize_weighted_exponential(
            {"a": 1.0}, {"a": -5.0}, {"a": 1.0}
        )
        score_zero = normalize_weighted_exponential(
            {"a": 1.0}, {"a": 0.0}, {"a": 1.0}
        )
        assert abs(score_neg - score_zero) < 1e-9


class TestAntiDegeneracy:
    def test_normal_range_passes(self):
        assert check_anti_degeneracy(1.0) is True
        assert check_anti_degeneracy(0.35) is True
        assert check_anti_degeneracy(3.0) is True

    def test_below_min_fails(self):
        assert check_anti_degeneracy(0.34) is False
        assert check_anti_degeneracy(0.0) is False

    def test_above_max_fails(self):
        assert check_anti_degeneracy(3.01) is False
        assert check_anti_degeneracy(100.0) is False

    def test_constants_correct(self):
        assert MOTION_PRESERVATION_MIN == 0.35
        assert MOTION_PRESERVATION_MAX == 3.00
