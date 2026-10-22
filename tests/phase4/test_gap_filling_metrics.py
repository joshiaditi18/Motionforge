"""
tests/phase4/test_gap_filling_metrics.py — Unit tests for evaluation/metrics/gap_filling_metrics.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import pytest

from baselines.common.bvh_io import parse_bvh
from evaluation.metrics.gap_filling_metrics import (
    evaluate_gap_filling,
    resolve_distal_joint_endpoint,
    DEFAULT_FOOT_CONTACT_VELOCITY_THRESHOLD,
)

_BVH_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh"
)


def _load_bvh():
    return parse_bvh(_BVH_PATH)


class TestResolveDistalJointEndpoint:
    def test_resolves_to_valid_name(self):
        bvh = _load_bvh()
        # RightArm should resolve to its first child (RightForeArm)
        name = resolve_distal_joint_endpoint(bvh, "RightArm")
        assert name is not None
        assert isinstance(name, str)
        assert name != "RightArm"  # should be the child joint

    def test_invalid_joint_raises_valueerror(self):
        bvh = _load_bvh()
        with pytest.raises(ValueError):
            resolve_distal_joint_endpoint(bvh, "FakeJointXYZ")


class TestEvaluateGapFillingIntegration:
    def test_perfect_fill_gives_zero_inpainting_mpjpe(self):
        bvh = _load_bvh()
        # Gap at frames 50-70 on RightArm
        result = evaluate_gap_filling(bvh, bvh, "RightArm", 50, 70)
        assert result["inpainting_mpjpe"] < 1e-9

    def test_perfect_fill_boundary_error_is_finite(self):
        """Boundary error compares pred[s_f] vs gt[s_f-1] (adjacent frames),
        so even a perfect fill gives non-zero boundary error — it measures
        the natural motion step at the gap boundary, not reconstruction accuracy."""
        bvh = _load_bvh()
        result = evaluate_gap_filling(bvh, bvh, "RightArm", 50, 70)
        assert np.isfinite(result["boundary_error"])
        assert result["boundary_error"] >= 0.0
        assert np.isfinite(result["velocity_boundary_error"])
        assert result["velocity_boundary_error"] >= 0.0

    def test_perfect_fill_zero_unmodified_diff(self):
        bvh = _load_bvh()
        result = evaluate_gap_filling(bvh, bvh, "RightArm", 50, 70)
        assert result["unmodified_max_diff"] < 1e-9

    def test_result_has_required_keys(self):
        bvh = _load_bvh()
        result = evaluate_gap_filling(bvh, bvh, "RightArm", 50, 70)
        required = [
            "inpainting_mpjpe", "boundary_error",
            "velocity_boundary_error", "unmodified_max_diff",
        ]
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_all_values_finite(self):
        bvh = _load_bvh()
        result = evaluate_gap_filling(bvh, bvh, "RightArm", 50, 70)
        for k, v in result.items():
            if isinstance(v, float):
                assert np.isfinite(v), f"Non-finite: {k}={v}"

    def test_default_threshold_positive(self):
        assert DEFAULT_FOOT_CONTACT_VELOCITY_THRESHOLD > 0.0
