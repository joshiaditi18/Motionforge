"""
tests/phase4/test_denoising_metrics.py — Unit tests for evaluation/metrics/denoising_metrics.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import pytest

from baselines.common.bvh_io import parse_bvh
from evaluation.metrics.denoising_metrics import evaluate_denoising

# Use first public training BVH for integration tests
_BVH_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh"
)


def _load_bvh():
    """Load MF001 for use in tests."""
    bvh = parse_bvh(_BVH_PATH)
    return bvh


class TestEvaluateDenoisingIntegration:
    def test_perfect_denoising_gives_zero_mpjpe(self):
        bvh = _load_bvh()
        result = evaluate_denoising(bvh, bvh)   # pred == gt → perfect
        assert result["mpjpe"] < 1e-9, f"Expected ~0 MPJPE, got {result['mpjpe']}"

    def test_perfect_denoising_preservation_near_1(self):
        bvh = _load_bvh()
        result = evaluate_denoising(bvh, bvh)
        assert abs(result["motion_preservation"] - 1.0) < 1e-6

    def test_result_has_required_keys(self):
        bvh = _load_bvh()
        result = evaluate_denoising(bvh, bvh)
        for key in ["mpjpe", "velocity_error", "acceleration_error", "jitter", "motion_preservation"]:
            assert key in result, f"Missing key: {key}"

    def test_all_values_finite(self):
        bvh = _load_bvh()
        result = evaluate_denoising(bvh, bvh)
        for k, v in result.items():
            if isinstance(v, float):
                assert np.isfinite(v), f"Non-finite value for {k}: {v}"

    def test_all_values_nonneg(self):
        bvh = _load_bvh()
        result = evaluate_denoising(bvh, bvh)
        for k, v in result.items():
            if isinstance(v, float) and k != "motion_preservation":
                assert v >= 0.0, f"Negative value for {k}: {v}"

    def test_noisy_comparison_adds_keys(self):
        bvh = _load_bvh()
        result = evaluate_denoising(bvh, bvh, bvh_noisy=bvh)
        for key in ["raw_mpjpe", "raw_jitter", "mpjpe_improvement_pct", "jitter_reduction_pct"]:
            assert key in result, f"Missing key with noisy input: {key}"

    def test_noisy_improvement_is_zero_for_perfect(self):
        bvh = _load_bvh()
        result = evaluate_denoising(bvh, bvh, bvh_noisy=bvh)
        # If pred == gt == noisy, improvement should be ~0
        assert abs(result["mpjpe_improvement_pct"]) < 1e-6
