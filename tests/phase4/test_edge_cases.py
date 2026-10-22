"""
tests/phase4/test_edge_cases.py — Edge cases and adversarial input tests.

Tests for:
- Empty / single-frame motions
- All-zero motion data
- NaN / Inf detection
- Boundary frame gaps
- Zero-length gaps
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import copy
import numpy as np
import pytest

from baselines.common.bvh_io import parse_bvh
from evaluation.metrics.common_metrics import validate_motion_array
from evaluation.metrics.denoising_metrics import evaluate_denoising
from evaluation.metrics.gap_filling_metrics import evaluate_gap_filling
from evaluation.scoring.task_scoring import score_denoising, score_gap_filling, score_retargeting

_BVH_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh"
)


def _load_bvh():
    return parse_bvh(_BVH_PATH)


def _make_bvh_with_nan(bvh_real):
    """Return a copy of bvh with NaN injected into motion data."""
    import copy
    bvh_copy = copy.copy(bvh_real)
    data = bvh_real.motion_data.copy()
    data[10, 5] = float('nan')
    bvh_copy.motion_data = data
    return bvh_copy


def _make_bvh_with_inf(bvh_real):
    """Return a copy of bvh with Inf injected into motion data."""
    import copy
    bvh_copy = copy.copy(bvh_real)
    data = bvh_real.motion_data.copy()
    data[5, 3] = float('inf')
    bvh_copy.motion_data = data
    return bvh_copy


class TestValidateMotionArray:
    def test_valid_array_passes(self):
        arr = np.ones((100, 96), dtype=np.float64)
        ok, msg = validate_motion_array(arr, expected_channels=96)
        assert ok, f"Valid array rejected: {msg}"

    def test_nan_detected(self):
        arr = np.ones((100, 96), dtype=np.float64)
        arr[5, 3] = float('nan')
        ok, msg = validate_motion_array(arr, expected_channels=96)
        assert not ok
        assert "NaN" in msg or "nan" in msg.lower()

    def test_inf_detected(self):
        arr = np.ones((100, 96), dtype=np.float64)
        arr[10, 2] = float('inf')
        ok, msg = validate_motion_array(arr, expected_channels=96)
        assert not ok
        assert "Inf" in msg or "inf" in msg.lower()

    def test_wrong_shape_detected(self):
        arr = np.ones((100, 50), dtype=np.float64)  # 50 channels != 96
        ok, msg = validate_motion_array(arr, expected_channels=96)
        assert not ok


class TestEdgeCasesDenoising:
    def test_zero_motion_gives_zero_mpjpe(self):
        """Both pred and gt are all zeros → MPJPE should be 0."""
        bvh = _load_bvh()
        import copy
        bvh_zero = copy.copy(bvh)
        bvh_zero.motion_data = np.zeros_like(bvh.motion_data)
        result = evaluate_denoising(bvh_zero, bvh_zero)
        assert result["mpjpe"] < 1e-9


class TestEdgeCasesGapFilling:
    def test_gap_at_start_of_sequence(self):
        """Gap starting at frame 0 should not crash."""
        bvh = _load_bvh()
        result = evaluate_gap_filling(bvh, bvh, "RightArm", 0, 10)
        assert "inpainting_mpjpe" in result

    def test_gap_at_end_of_sequence(self):
        """Gap ending at last frame should not crash."""
        bvh = _load_bvh()
        last = bvh.frame_count - 1
        result = evaluate_gap_filling(bvh, bvh, "RightArm", last - 10, last)
        assert "inpainting_mpjpe" in result


class TestAdversarialScoring:
    def test_score_does_not_reward_cheating_via_degenerate_preservation(self):
        """
        Adversarial submission: claims 0 error but sets motion to constant (near-zero kinetic energy).
        motion_preservation → 0 → degenerate → score=0
        """
        s, d = score_denoising({
            "mpjpe": 0.0, "velocity_error": 0.0, "jitter": 0.0,
            "motion_preservation": 0.001,
        })
        assert s == 0.0 and d["degenerate"] is True

    def test_score_does_not_reward_amplified_motion(self):
        """
        Adversarial submission: amplified (high-energy) output.
        motion_preservation >> 3.0 → degenerate → score=0
        """
        s, d = score_denoising({
            "mpjpe": 0.0, "velocity_error": 0.0, "jitter": 0.0,
            "motion_preservation": 50.0,
        })
        assert s == 0.0 and d["degenerate"] is True

    def test_gap_filling_outside_modification_detected(self):
        """Participant that modifies unmodified frames gets score=0."""
        s, d = score_gap_filling({
            "inpainting_mpjpe": 0.0, "boundary_position_error": 0.0,
            "boundary_velocity_error": 0.0, "unmodified_max_diff": 1.0,
        })
        assert s == 0.0 and d["degenerate"] is True
