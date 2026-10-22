"""
test_task_validation.py — Unit tests for task_validator.py
"""

import os
import copy
import numpy as np
import pytest

from validator.task_validator import (
    validate_task1_denoising,
    validate_task2_gap_filling,
    validate_task3_retargeting,
)
from validator.error_codes import ErrorCode
from baselines.common.bvh_io import parse_bvh
from baselines.retargeting.baseline_retargeting import TARGET_CONFIGS, retarget_hierarchy_offsets

_CLEAN_BVH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh"
)


def _get_bvh():
    return parse_bvh(_CLEAN_BVH)


def test_task1_denoising_valid_even_if_poor():
    bvh = _get_bvh()
    # Modify motion to constant (poor quality denoising, but structurally valid)
    bvh_poor = copy.deepcopy(bvh)
    bvh_poor.motion_data = np.zeros_like(bvh.motion_data)

    ok, errors = validate_task1_denoising(bvh_poor, bvh_ref=bvh)
    assert ok is True
    assert len(errors) == 0


def test_task1_denoising_frame_mismatch():
    bvh = _get_bvh()
    bvh_short = copy.deepcopy(bvh)
    bvh_short.frame_count = bvh.frame_count - 10
    ok, errors = validate_task1_denoising(bvh_short, bvh_ref=bvh)
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_FRAME_COUNT.value for e in errors)


def test_task2_gap_filling_untouched_frames_passes():
    bvh = _get_bvh()
    bvh_filled = copy.deepcopy(bvh)
    # Modify only frames inside gap [50, 70]
    bvh_filled.motion_data[50:71, 10:13] += 5.0

    ok, errors = validate_task2_gap_filling(
        bvh_filled, bvh_ref=bvh, start_frame=50, end_frame=70
    )
    assert ok is True
    assert len(errors) == 0


def test_task2_gap_filling_outside_gap_modified_fails():
    bvh = _get_bvh()
    bvh_filled = copy.deepcopy(bvh)
    # Modify frame 10 (which is outside gap [50, 70])
    bvh_filled.motion_data[10, 0] += 2.0

    ok, errors = validate_task2_gap_filling(
        bvh_filled, bvh_ref=bvh, start_frame=50, end_frame=70
    )
    assert ok is False
    assert any(e.code == ErrorCode.OBSERVED_FRAME_MODIFIED.value for e in errors)


def test_task3_retargeting_valid_target_passes(tmp_path):
    bvh = _get_bvh()
    from baselines.common.bvh_io import write_bvh
    new_headers = retarget_hierarchy_offsets(bvh, TARGET_CONFIGS["target_small"])
    out_file = tmp_path / "retargeted_small.bvh"
    write_bvh(str(out_file), new_headers, bvh.frame_time, bvh.motion_data)
    bvh_retargeted = parse_bvh(str(out_file))

    ok, errors = validate_task3_retargeting(
        bvh_retargeted, target_type="target_small", bvh_src=bvh
    )
    assert ok is True
    assert len(errors) == 0


def test_task3_retargeting_invalid_target_type():
    bvh = _get_bvh()
    ok, errors = validate_task3_retargeting(bvh, target_type="target_colossus")
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_TARGET.value for e in errors)


def test_task3_retargeting_bone_length_violation():
    bvh = _get_bvh()
    # bvh has unscaled bone lengths, but we declare it as target_tall
    ok, errors = validate_task3_retargeting(
        bvh, target_type="target_tall", bvh_src=bvh
    )
    assert ok is False
    assert any(e.code == ErrorCode.BONE_LENGTH_VIOLATION.value for e in errors)
