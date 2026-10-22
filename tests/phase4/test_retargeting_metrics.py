"""
tests/phase4/test_retargeting_metrics.py — Unit tests for evaluation/metrics/retargeting_metrics.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import pytest

from baselines.common.bvh_io import parse_bvh
from evaluation.metrics.retargeting_metrics import evaluate_retargeting

_BVH_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh"
)


def _load_bvh():
    return parse_bvh(_BVH_PATH)


class TestEvaluateRetargetingIntegration:
    """Integration tests using src == pred (identity retargeting) to test zero-error cases."""

    @pytest.mark.parametrize("target", ["target_small", "target_medium", "target_tall"])
    def test_result_has_required_keys(self, target):
        bvh = _load_bvh()
        result = evaluate_retargeting(bvh, bvh, target)
        for key in ["end_effector_error", "angular_geodesic_error", "ground_penetration_penalty"]:
            assert key in result, f"Missing key: {key}"

    @pytest.mark.parametrize("target", ["target_small", "target_medium", "target_tall"])
    def test_all_values_finite(self, target):
        bvh = _load_bvh()
        result = evaluate_retargeting(bvh, bvh, target)
        for k, v in result.items():
            if isinstance(v, float):
                assert np.isfinite(v), f"Non-finite: {k}={v} for target={target}"

    @pytest.mark.parametrize("target", ["target_small", "target_medium", "target_tall"])
    def test_all_values_nonneg(self, target):
        bvh = _load_bvh()
        result = evaluate_retargeting(bvh, bvh, target)
        # min_foot_height_y can legitimately be negative (foot below ground)
        skip_keys = {"min_foot_height_y", "target_avatar"}
        for k, v in result.items():
            if isinstance(v, float) and k not in skip_keys:
                assert v >= 0.0, f"Negative value for {k}={v}, target={target}"

    def test_invalid_target_type_raises(self):
        bvh = _load_bvh()
        with pytest.raises((ValueError, KeyError)):
            evaluate_retargeting(bvh, bvh, "giant")
