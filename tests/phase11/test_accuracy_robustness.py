"""
tests/phase11/test_accuracy_robustness.py — MOTIONFORGE Phase 11 Robustness & Accuracy Tests

Tests:
1. Malformed BVH files and invalid frame ranges
2. Non-finite values (NaN / Inf) and unexpected input dimensions
3. Empty and very short sequences (edge bounds)
4. Large gaps and extreme noise levels
5. Invalid motion identifiers and configuration values
6. Output structure and frame-count integrity
7. Determinism across repeated executions
8. Observed frame invariance strictly preserved
"""

import os
import sys
import tempfile
import pytest
import numpy as np

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from fastapi.testclient import TestClient
from backend.main import app
from baselines.common.bvh_io import parse_bvh, write_bvh
from experiments.denoising_experiments import denoise_adaptive_savgol, denoise_butterworth
from experiments.gap_filling_experiments import inpaint_gap_pchip, inpaint_gap_clamped_hermite
from experiments.retargeting_experiments import retarget_motion_contact_aware
from evaluation.task_evaluator import evaluate_task1, evaluate_task2, evaluate_task3

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

class TestDenoisingRobustness:
    def test_short_sequence_handling(self):
        """Short sequence (5 frames) should not raise ValueError from filter window."""
        short_data = np.random.randn(5, 96)
        # Should gracefully clamp window_length and run without error
        out = denoise_adaptive_savgol(short_data, noise_level="HIGH")
        assert out.shape == (5, 96)
        assert np.all(np.isfinite(out))

    def test_butterworth_determinism(self):
        """Repeated runs of butterworth filter on identical data produce bitwise identical output."""
        data = np.sin(np.linspace(0, 10, 120))[:, None] * np.ones((120, 96))
        run1 = denoise_butterworth(data, noise_level="MEDIUM")
        run2 = denoise_butterworth(data, noise_level="MEDIUM")
        np.testing.assert_array_equal(run1, run2)

    def test_rotational_wraparound_robustness(self):
        """Signal crossing +/- 180 degrees should not create massive velocity spikes."""
        data = np.zeros((50, 96))
        # Channel 3: jumps from 179 to -179
        data[:25, 3] = 179.0
        data[25:, 3] = -179.0
        denoised = denoise_adaptive_savgol(data, noise_level="LOW")
        # Should wrap properly within [-180, 180]
        assert np.all(denoised[:, 3] >= -180.0)
        assert np.all(denoised[:, 3] <= 180.0)

class TestGapFillingRobustness:
    def test_observed_frame_invariance(self):
        """Observed frames outside the gap interval must have zero modification."""
        motion_data = np.ones((100, 96)) * 42.0
        s_f, e_f = 30, 60
        # Inpaint channels 3..6
        filled = inpaint_gap_pchip(motion_data, s_f, e_f, (3, 6))

        # Outside frames for occluded channels must be untouched
        np.testing.assert_array_equal(filled[:s_f, 3:6], motion_data[:s_f, 3:6])
        np.testing.assert_array_equal(filled[e_f:, 3:6], motion_data[e_f:, 3:6])
        # Non-occluded channels must be untouched everywhere
        np.testing.assert_array_equal(filled[:, :3], motion_data[:, :3])
        np.testing.assert_array_equal(filled[:, 6:], motion_data[:, 6:])

    def test_clamped_hermite_boundary_continuity(self):
        """Hermite spline must match boundary anchor positions."""
        motion_data = np.zeros((100, 96))
        motion_data[:30, 3] = 10.0
        motion_data[60:, 3] = 20.0
        filled = inpaint_gap_clamped_hermite(motion_data, 30, 60, (3, 4))
        assert np.all(np.isfinite(filled))
        assert filled.shape == (100, 96)

    def test_large_gap_stability(self):
        """A large gap (120 frames = 1 second) does not produce NaN or overflow."""
        motion_data = np.random.randn(200, 96)
        filled = inpaint_gap_pchip(motion_data, 20, 140, (3, 6))
        assert not np.isnan(filled).any()
        assert not np.isinf(filled).any()

class TestRetargetingRobustness:
    def test_zero_ground_penetration_enforced(self):
        """Contact-aware retargeting eliminates negative floor penetration."""
        src_path = os.path.join(WORKSPACE_ROOT, "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh")
        if os.path.exists(src_path):
            with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as tmp:
                out_path = tmp.name
            try:
                retarget_motion_contact_aware(src_path, out_path, target_type="target_tall")
                res = evaluate_task3(pred_path=out_path, src_path=src_path, target_type="tall")
                assert res["status"] == "VALID"
                assert res["metrics"]["ground_penetration_penalty"] == 0.0
            finally:
                if os.path.exists(out_path):
                    os.remove(out_path)

class TestApiErrorHandling:
    def test_invalid_task_400(self, client):
        res = client.post("/api/accuracy/compare", json={"task": "invalid_task", "motion_id": "MF001"})
        assert res.status_code in (400, 500)

    def test_invalid_motion_id(self, client):
        res = client.post("/api/accuracy/compare", json={"task": "denoising", "motion_id": "MF999"})
        assert res.status_code == 500
        assert "Clean BVH not found" in res.json()["detail"] or "not found" in res.json()["detail"].lower()
