"""
test_skeleton_validation.py — Unit tests for skeleton_validator.py
"""

import os
import copy
import numpy as np
import pytest

from validator.skeleton_validator import validate_skeleton
from validator.error_codes import ErrorCode
from baselines.common.bvh_io import parse_bvh

_CLEAN_BVH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh"
)


def _get_bvh():
    return parse_bvh(_CLEAN_BVH)


def test_canonical_skeleton_passes():
    bvh = _get_bvh()
    ok, errors = validate_skeleton(bvh)
    assert ok is True
    assert len(errors) == 0


def test_invalid_root_joint():
    bvh = _get_bvh()
    bvh.root.name = "Pelvis"
    ok, errors = validate_skeleton(bvh)
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_ROOT_JOINT.value for e in errors)


def test_invalid_joint_count():
    bvh = _get_bvh()
    # Pop one joint from joint_names list
    bvh.joint_names.pop()
    ok, errors = validate_skeleton(bvh)
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_JOINT_COUNT.value for e in errors)


def test_invalid_joint_order():
    bvh = _get_bvh()
    # Swap two joints
    bvh.joint_names[1], bvh.joint_names[2] = bvh.joint_names[2], bvh.joint_names[1]
    ok, errors = validate_skeleton(bvh)
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_JOINT_ORDER.value for e in errors)


def test_invalid_channel_count():
    bvh = _get_bvh()
    bvh.num_channels = 93
    ok, errors = validate_skeleton(bvh)
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_CHANNEL_COUNT.value for e in errors)


def test_invalid_root_channel_order():
    bvh = _get_bvh()
    bvh.root.channels = ["Xposition", "Yposition", "Zposition", "Xrotation", "Yrotation", "Zrotation"]
    ok, errors = validate_skeleton(bvh)
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_CHANNEL_ORDER.value for e in errors)


def test_invalid_joint_hierarchy_parent():
    bvh = _get_bvh()
    # Re-parent Head directly to Hips
    bvh.node_by_name["Head"].parent = bvh.node_by_name["Hips"]
    ok, errors = validate_skeleton(bvh)
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_HIERARCHY.value for e in errors)


def test_nan_in_node_offset():
    bvh = _get_bvh()
    bvh.node_by_name["Head"].offset[1] = float("nan")
    ok, errors = validate_skeleton(bvh)
    assert ok is False
    assert any(e.code == ErrorCode.NAN_DETECTED.value for e in errors)
