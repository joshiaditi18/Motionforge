"""
tests/phase4/test_scoring.py — Unit tests for task scoring + overall scoring
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from evaluation.scoring.task_scoring import score_denoising, score_gap_filling, score_retargeting
from evaluation.scoring.overall_scoring import compute_overall_score, TASK_WEIGHT_DENOISING, TASK_WEIGHT_GAP_FILLING, TASK_WEIGHT_RETARGETING


class TestScoreDenoising:
    def test_returns_tuple(self):
        s, d = score_denoising({"mpjpe": 0.1, "velocity_error": 5.0, "jitter": 100.0, "motion_preservation": 1.0})
        assert isinstance(s, float)
        assert isinstance(d, dict)

    def test_score_in_range(self):
        for pres in [0.5, 1.0, 2.0]:
            s, _ = score_denoising({"mpjpe": 0.1, "velocity_error": 5.0, "jitter": 100.0, "motion_preservation": pres})
            assert 0.0 <= s <= 100.0

    def test_degenerate_low_preservation(self):
        s, d = score_denoising({"mpjpe": 0.0, "velocity_error": 0.0, "jitter": 0.0, "motion_preservation": 0.1})
        assert s == 0.0
        assert d["degenerate"] is True

    def test_degenerate_high_preservation(self):
        s, d = score_denoising({"mpjpe": 0.0, "velocity_error": 0.0, "jitter": 0.0, "motion_preservation": 10.0})
        assert s == 0.0
        assert d["degenerate"] is True

    def test_better_metrics_give_higher_score(self):
        s_good, _ = score_denoising({"mpjpe": 0.01, "velocity_error": 0.5, "jitter": 10.0, "motion_preservation": 1.0})
        s_bad,  _ = score_denoising({"mpjpe": 1.0,  "velocity_error": 50.0, "jitter": 5000.0, "motion_preservation": 1.0})
        assert s_good > s_bad

    def test_zero_error_gives_100(self):
        s, _ = score_denoising({"mpjpe": 0.0, "velocity_error": 0.0, "jitter": 0.0, "motion_preservation": 1.0})
        assert abs(s - 100.0) < 1e-6

    def test_detail_keys_present(self):
        _, d = score_denoising({"mpjpe": 0.1, "velocity_error": 5.0, "jitter": 100.0, "motion_preservation": 1.0})
        for key in ["task", "score", "degenerate", "metrics_used", "tau_values", "weights"]:
            assert key in d


class TestScoreGapFilling:
    def test_returns_tuple(self):
        s, d = score_gap_filling({"inpainting_mpjpe": 0.05, "boundary_position_error": 0.2, "boundary_velocity_error": 2.0, "unmodified_max_diff": 0.0})
        assert isinstance(s, float)
        assert isinstance(d, dict)

    def test_score_in_range(self):
        s, _ = score_gap_filling({"inpainting_mpjpe": 0.05, "boundary_position_error": 0.2, "boundary_velocity_error": 2.0, "unmodified_max_diff": 0.0})
        assert 0.0 <= s <= 100.0

    def test_contract_violation_gives_zero(self):
        s, d = score_gap_filling({"inpainting_mpjpe": 0.0, "boundary_position_error": 0.0, "boundary_velocity_error": 0.0, "unmodified_max_diff": 0.01})
        assert s == 0.0
        assert d["degenerate"] is True
        assert "contract violation" in d["degenerate_reason"]

    def test_no_violation_with_tiny_diff(self):
        # diff <= 1e-6 should NOT trigger violation
        s, d = score_gap_filling({"inpainting_mpjpe": 0.05, "boundary_position_error": 0.2, "boundary_velocity_error": 2.0, "unmodified_max_diff": 1e-7})
        assert d["degenerate"] is False

    def test_zero_error_gives_100(self):
        s, _ = score_gap_filling({"inpainting_mpjpe": 0.0, "boundary_position_error": 0.0, "boundary_velocity_error": 0.0, "unmodified_max_diff": 0.0})
        assert abs(s - 100.0) < 1e-6


class TestScoreRetargeting:
    def test_returns_tuple(self):
        s, d = score_retargeting({"end_effector_error": 0.02, "angular_deviation_deg": 3.0, "ground_penetration_in": 0.3})
        assert isinstance(s, float)
        assert isinstance(d, dict)

    def test_score_in_range(self):
        s, _ = score_retargeting({"end_effector_error": 0.02, "angular_deviation_deg": 3.0, "ground_penetration_in": 0.3})
        assert 0.0 <= s <= 100.0

    def test_zero_error_gives_100(self):
        s, _ = score_retargeting({"end_effector_error": 0.0, "angular_deviation_deg": 0.0, "ground_penetration_in": 0.0})
        assert abs(s - 100.0) < 1e-6

    def test_better_metrics_give_higher_score(self):
        s_good, _ = score_retargeting({"end_effector_error": 0.001, "angular_deviation_deg": 0.1, "ground_penetration_in": 0.01})
        s_bad,  _ = score_retargeting({"end_effector_error": 0.1,   "angular_deviation_deg": 15.0, "ground_penetration_in": 2.0})
        assert s_good > s_bad


class TestOverallScoring:
    def test_all_tasks_present(self):
        result = compute_overall_score(70.0, 80.0, 60.0)
        expected = 0.30 * 70.0 + 0.30 * 80.0 + 0.40 * 60.0
        assert abs(result["overall_score"] - expected) < 1e-6

    def test_missing_task_redistributes(self):
        # Only tasks 1 and 2 (weights should be 0.30 and 0.30 → normalized to 0.5/0.5)
        result = compute_overall_score(80.0, 60.0, None)
        expected = 0.5 * 80.0 + 0.5 * 60.0
        assert abs(result["overall_score"] - expected) < 1e-6

    def test_all_none_returns_none(self):
        result = compute_overall_score(None, None, None)
        assert result["overall_score"] is None
        assert result["tasks_evaluated"] == []

    def test_official_weights_defined(self):
        assert TASK_WEIGHT_DENOISING   == 0.30
        assert TASK_WEIGHT_GAP_FILLING == 0.30
        assert TASK_WEIGHT_RETARGETING == 0.40

    def test_overall_bounded(self):
        result = compute_overall_score(100.0, 100.0, 100.0)
        assert result["overall_score"] <= 100.0
        result2 = compute_overall_score(0.0, 0.0, 0.0)
        assert result2["overall_score"] >= 0.0
