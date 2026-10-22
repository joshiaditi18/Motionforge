"""
test_motion_validation.py — Unit tests for motion_validator.py
"""

import os
import copy
import numpy as np
import pytest

from validator.motion_validator import validate_motion
from validator.error_codes import ErrorCode
from baselines.common.bvh_io import parse_bvh

_CLEAN_BVH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh"
)


def _get_bvh():
    return parse_bvh(_CLEAN_BVH)


def test_valid_motion_passes():
    bvh = _get_bvh()
    ok, errors = validate_motion(bvh, expected_frame_count=bvh.frame_count)
    assert ok is True
    assert len(errors) == 0


def test_empty_motion_data():
    bvh = _get_bvh()
    bvh.motion_data = np.zeros((0, 96), dtype=np.float64)
    bvh.frame_count = 0
    ok, errors = validate_motion(bvh)
    assert ok is False
    assert any(e.code == ErrorCode.EMPTY_MOTION_DATA.value for e in errors)


def test_invalid_motion_shape_dimension():
    bvh = _get_bvh()
    bvh.motion_data = np.zeros((10, 96, 1), dtype=np.float64)
    ok, errors = validate_motion(bvh)
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_MOTION_SHAPE.value for e in errors)


def test_invalid_channel_count_in_array():
    bvh = _get_bvh()
    bvh.motion_data = np.zeros((10, 80), dtype=np.float64)
    ok, errors = validate_motion(bvh)
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_CHANNEL_COUNT.value for e in errors)


def test_mismatched_reference_frame_count():
    bvh = _get_bvh()
    ok, errors = validate_motion(bvh, expected_frame_count=bvh.frame_count + 50)
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_FRAME_COUNT.value for e in errors)


def test_nan_in_motion_data():
    bvh = _get_bvh()
    bvh.motion_data[5, 10] = float("nan")
    ok, errors = validate_motion(bvh)
    assert ok is False
    assert any(e.code == ErrorCode.NAN_DETECTED.value for e in errors)


def test_inf_in_motion_data():
    bvh = _get_bvh()
    bvh.motion_data[12, 4] = float("inf")
    ok, errors = validate_motion(bvh)
    assert ok is False
    assert any(e.code == ErrorCode.INF_DETECTED.value for e in errors)
