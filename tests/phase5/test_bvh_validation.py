"""
test_bvh_validation.py — Unit tests for bvh_validator.py
"""

import os
import pytest

from validator.bvh_validator import validate_bvh_syntax_and_headers
from validator.error_codes import ErrorCode

_CLEAN_BVH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh"
)


def test_valid_bvh_passes():
    assert os.path.isfile(_CLEAN_BVH)
    ok, errors, bvh = validate_bvh_syntax_and_headers(_CLEAN_BVH)
    assert ok is True
    assert len(errors) == 0
    assert bvh is not None
    assert bvh.frame_count > 0


def test_missing_hierarchy_header(tmp_path):
    with open(_CLEAN_BVH, "r") as f:
        content = f.read()
    
    # Remove HIERARCHY
    bad_content = content.replace("HIERARCHY", "# COMMENT")
    bad_file = tmp_path / "no_hierarchy.bvh"
    bad_file.write_text(bad_content)

    ok, errors, _ = validate_bvh_syntax_and_headers(str(bad_file))
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_BVH_HEADER.value for e in errors)


def test_missing_motion_divider(tmp_path):
    with open(_CLEAN_BVH, "r") as f:
        content = f.read()
    
    bad_content = content.replace("MOTION", "NO_MOTION_HERE")
    bad_file = tmp_path / "no_motion.bvh"
    bad_file.write_text(bad_content)

    ok, errors, _ = validate_bvh_syntax_and_headers(str(bad_file))
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_BVH.value for e in errors)


def test_invalid_frame_time_fps(tmp_path):
    with open(_CLEAN_BVH, "r") as f:
        content = f.read()
    
    # Change to 60 FPS (0.0166667)
    bad_content = content.replace("Frame Time: 0.0083333", "Frame Time: 0.0166667")
    bad_file = tmp_path / "bad_fps.bvh"
    bad_file.write_text(bad_content)

    ok, errors, _ = validate_bvh_syntax_and_headers(str(bad_file))
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_FRAME_TIME.value for e in errors)


def test_invalid_zero_frames(tmp_path):
    with open(_CLEAN_BVH, "r") as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if line.startswith("Frames:"):
            new_lines.append("Frames: 0\n")
        else:
            new_lines.append(line)
    
    bad_file = tmp_path / "zero_frames.bvh"
    bad_file.write_text("".join(new_lines))

    ok, errors, _ = validate_bvh_syntax_and_headers(str(bad_file))
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_FRAME_COUNT.value for e in errors)


def test_nan_token_in_motion_data(tmp_path):
    with open(_CLEAN_BVH, "r") as f:
        lines = f.readlines()
    
    # Inject NaN into the first motion row
    for i in range(len(lines)):
        if lines[i].startswith("Frame Time:"):
            # Next non-empty line is motion data
            target_idx = i + 1
            while not lines[target_idx].strip():
                target_idx += 1
            tokens = lines[target_idx].split()
            tokens[5] = "NaN"
            lines[target_idx] = " ".join(tokens) + "\n"
            break

    bad_file = tmp_path / "nan_data.bvh"
    bad_file.write_text("".join(lines))

    ok, errors, _ = validate_bvh_syntax_and_headers(str(bad_file))
    assert ok is False
    assert any(e.code == ErrorCode.NAN_DETECTED.value for e in errors)


def test_inf_token_in_motion_data(tmp_path):
    with open(_CLEAN_BVH, "r") as f:
        lines = f.readlines()
    
    for i in range(len(lines)):
        if lines[i].startswith("Frame Time:"):
            target_idx = i + 1
            while not lines[target_idx].strip():
                target_idx += 1
            tokens = lines[target_idx].split()
            tokens[3] = "Infinity"
            lines[target_idx] = " ".join(tokens) + "\n"
            break

    bad_file = tmp_path / "inf_data.bvh"
    bad_file.write_text("".join(lines))

    ok, errors, _ = validate_bvh_syntax_and_headers(str(bad_file))
    assert ok is False
    assert any(e.code == ErrorCode.INF_DETECTED.value for e in errors)
