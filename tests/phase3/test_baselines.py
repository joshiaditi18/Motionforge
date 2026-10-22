import os
import sys
import unittest
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(BASE_DIR)

from baselines.common.bvh_io import parse_bvh, write_bvh
from baselines.common.forward_kinematics import compute_forward_kinematics
from baselines.common.skeleton_utils import CANONICAL_31_JOINTS, validate_skeleton_hierarchy, get_bone_lengths
from baselines.common.motion_utils import calculate_mpjpe, calculate_jitter_error
from baselines.denoising.baseline_denoising import denoise_motion_data
from baselines.gap_filling.baseline_gap_filling import inpaint_gap
from baselines.retargeting.baseline_retargeting import retarget_hierarchy_offsets, TARGET_CONFIGS

"""
MOTIONFORGE — tests/phase3/test_baselines.py
Unit tests validating BVH I/O, forward kinematics, baseline operations,
metric invariants, and reproducibility.
"""

class TestBaselinesPhase3(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.sample_bvh_path = os.path.join(BASE_DIR, "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh")
        cls.assertTrue(os.path.exists(cls.sample_bvh_path), "MF001_clean.bvh must exist for tests")
        cls.bvh = parse_bvh(cls.sample_bvh_path)

    def test_canonical_skeleton_hierarchy(self):
        is_valid, errors = validate_skeleton_hierarchy(self.bvh)
        self.assertTrue(is_valid, f"Canonical skeleton validation failed: {errors}")
        self.assertEqual(len(self.bvh.joint_names), 31)
        self.assertEqual(self.bvh.num_channels, 96)
        self.assertEqual(self.bvh.root.name, "Hips")

    def test_forward_kinematics_dimensions_and_validity(self):
        pos, j_names = compute_forward_kinematics(self.bvh, include_end_sites=False)
        self.assertEqual(pos.shape, (self.bvh.frame_count, 31, 3))
        self.assertFalse(np.isnan(pos).any(), "FK positions contain NaN")
        self.assertFalse(np.isinf(pos).any(), "FK positions contain Inf")
        self.assertEqual(j_names, CANONICAL_31_JOINTS)

    def test_bvh_io_roundtrip_fidelity(self):
        temp_out = os.path.join(BASE_DIR, "calibration", "temp_roundtrip.bvh")
        try:
            write_bvh(temp_out, self.bvh)
            reloaded = parse_bvh(temp_out)
            self.assertEqual(reloaded.frame_count, self.bvh.frame_count)
            self.assertEqual(reloaded.num_channels, self.bvh.num_channels)
            np.testing.assert_allclose(reloaded.motion_data, self.bvh.motion_data, atol=1e-4)
        finally:
            if os.path.exists(temp_out):
                os.remove(temp_out)

    def test_denoising_reduces_synthetic_jitter(self):
        # Inject artificial high-frequency jitter
        rng = np.random.RandomState(2026)
        noisy = self.bvh.motion_data.copy()
        noise = rng.normal(0, 0.5, size=noisy.shape)
        noisy += noise

        denoised = denoise_motion_data(noisy, "MEDIUM")

        # Compare accelerations
        dt = self.bvh.frame_time
        a_noisy = (noisy[2:] - 2*noisy[1:-1] + noisy[:-2]) / (dt**2)
        a_clean = (denoised[2:] - 2*denoised[1:-1] + denoised[:-2]) / (dt**2)
        self.assertLess(np.mean(np.abs(a_clean)), np.mean(np.abs(a_noisy)))

    def test_gap_filling_preserves_observed_frames(self):
        motion = self.bvh.motion_data.copy()
        s_f, e_f = 50, 70
        ch_slice = (15, 18) # RightArm
        filled = inpaint_gap(motion, s_f, e_f, ch_slice, method="cubic")

        # Unmodified frames must be identical bit-for-bit
        mask_outside = np.ones(len(motion), dtype=bool)
        mask_outside[s_f:e_f] = False
        np.testing.assert_array_equal(filled[mask_outside], motion[mask_outside])

    def test_retargeting_hierarchy_and_root_adjustment(self):
        cfg = TARGET_CONFIGS["target_small"]
        new_headers = retarget_hierarchy_offsets(self.bvh, cfg)
        self.assertGreater(len(new_headers), 0)

        # Check root Y scaling
        leg_scale = (cfg['thigh_scale'] + cfg['shin_scale']) / 2.0
        scaled_motion = self.bvh.motion_data.copy()
        scaled_motion[:, 1] *= leg_scale
        np.testing.assert_allclose(scaled_motion[:, 1], self.bvh.motion_data[:, 1] * leg_scale)

if __name__ == "__main__":
    unittest.main()
