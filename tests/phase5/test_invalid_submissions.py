"""
test_invalid_submissions.py — Integration tests verifying invalid submissions return REJECTED and exit code 1
"""

import os
import shutil
import zipfile
import numpy as np
import pytest

from validator.validator import validate_submission
from validator.validation_result import ValidationStatus
from validator.error_codes import ErrorCode
from baselines.common.bvh_io import parse_bvh, write_bvh

_CLEAN_BVH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh"
)


def _make_zip(zip_path, files_dict):
    """Create a zip file from a dictionary of relative_path -> content (str or bytes)."""
    with zipfile.ZipFile(zip_path, "w") as zf:
        for rel_path, content in files_dict.items():
            zf.writestr(rel_path, content)


def test_missing_archive_rejected(tmp_path):
    res = validate_submission(str(tmp_path / "does_not_exist.zip"))
    assert res.status == ValidationStatus.REJECTED
    assert res.get_exit_code() == 1
    assert any(e.code == ErrorCode.ARCHIVE_NOT_FOUND.value for e in errors_of(res))


def test_corrupted_zip_rejected(tmp_path):
    bad_zip = tmp_path / "corrupt.zip"
    bad_zip.write_bytes(b"garbage not zip data")
    res = validate_submission(str(bad_zip))
    assert res.status == ValidationStatus.REJECTED
    assert res.get_exit_code() == 1
    assert any(e.code == ErrorCode.ARCHIVE_CORRUPTED.value for e in errors_of(res))


def test_path_traversal_rejected(tmp_path):
    zip_path = tmp_path / "traversal.zip"
    _make_zip(zip_path, {"../../evil.txt": "payload"})
    res = validate_submission(str(zip_path))
    assert res.status == ValidationStatus.REJECTED
    assert res.get_exit_code() == 1
    assert any(e.code == ErrorCode.PATH_TRAVERSAL.value for e in errors_of(res))


def test_missing_task_directory_rejected(tmp_path):
    zip_path = tmp_path / "missing_dir.zip"
    # Only includes denoising, missing gap_filling and retargeting
    _make_zip(zip_path, {"denoising/MF001_low.bvh": "HIERARCHY\n"})
    res = validate_submission(str(zip_path), motion_ids=["MF001"])
    assert res.status == ValidationStatus.REJECTED
    assert res.get_exit_code() == 1
    assert any(e.code == ErrorCode.MISSING_REQUIRED_DIRECTORY.value for e in errors_of(res))


def test_invalid_bvh_syntax_rejected(tmp_path):
    zip_path = tmp_path / "bad_syntax.zip"
    _make_zip(zip_path, {
        "denoising/MF001_low.bvh": "NOT_A_BVH_FILE\n",
        "gap_filling/MF001_short.bvh": "NOT_A_BVH_FILE\n",
        "retargeting/MF001_target_small.bvh": "NOT_A_BVH_FILE\n",
    })
    res = validate_submission(str(zip_path), motion_ids=["MF001"])
    assert res.status == ValidationStatus.REJECTED
    assert res.get_exit_code() == 1
    assert any(e.code in (ErrorCode.INVALID_BVH.value, ErrorCode.INVALID_BVH_HEADER.value) for e in errors_of(res))


def test_wrong_fps_rejected(tmp_path):
    with open(_CLEAN_BVH, "r") as f:
        content = f.read().replace("Frame Time: 0.0083333", "Frame Time: 0.0333333")

    zip_path = tmp_path / "bad_fps.zip"
    _make_zip(zip_path, {"denoising/MF001_low.bvh": content})
    res = validate_submission(str(zip_path), task="denoising", motion_ids=["MF001"])
    assert res.status == ValidationStatus.REJECTED
    assert res.get_exit_code() == 1
    assert any(e.code == ErrorCode.INVALID_FRAME_TIME.value for e in errors_of(res))


def test_nan_in_submission_rejected(tmp_path):
    bvh = parse_bvh(_CLEAN_BVH)
    bvh.motion_data[2, 3] = float("nan")
    out_bvh = tmp_path / "nan.bvh"
    write_bvh(str(out_bvh), bvh)

    zip_path = tmp_path / "nan_sub.zip"
    with open(out_bvh, "r") as f:
        bvh_str = f.read()
    _make_zip(zip_path, {"denoising/MF001_low.bvh": bvh_str})

    res = validate_submission(str(zip_path), task="denoising", motion_ids=["MF001"])
    assert res.status == ValidationStatus.REJECTED
    assert res.get_exit_code() == 1
    assert any(e.code == ErrorCode.NAN_DETECTED.value for e in errors_of(res))


def test_inf_in_submission_rejected(tmp_path):
    bvh = parse_bvh(_CLEAN_BVH)
    bvh.motion_data[4, 5] = float("inf")
    out_bvh = tmp_path / "inf.bvh"
    write_bvh(str(out_bvh), bvh)

    zip_path = tmp_path / "inf_sub.zip"
    with open(out_bvh, "r") as f:
        bvh_str = f.read()
    _make_zip(zip_path, {"denoising/MF001_low.bvh": bvh_str})

    res = validate_submission(str(zip_path), task="denoising", motion_ids=["MF001"])
    assert res.status == ValidationStatus.REJECTED
    assert res.get_exit_code() == 1
    assert any(e.code == ErrorCode.INF_DETECTED.value for e in errors_of(res))


def test_modified_observed_frames_rejected(tmp_path):
    bvh = parse_bvh(_CLEAN_BVH)
    # Modify frame 1
    bvh.motion_data[1, 0] += 5.0
    out_bvh = tmp_path / "gap_cheat.bvh"
    write_bvh(str(out_bvh), bvh)

    zip_path = tmp_path / "cheat.zip"
    with open(out_bvh, "r") as f:
        bvh_str = f.read()
    _make_zip(zip_path, {"gap_filling/MF001_short.bvh": bvh_str})

    res = validate_submission(str(zip_path), task="gap_filling", motion_ids=["MF001"])
    assert res.status == ValidationStatus.REJECTED
    assert res.get_exit_code() == 1
    assert any(e.code == ErrorCode.OBSERVED_FRAME_MODIFIED.value for e in errors_of(res))


def errors_of(res):
    return res.errors
