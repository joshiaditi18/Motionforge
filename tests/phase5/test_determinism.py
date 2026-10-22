"""
test_determinism.py — Unit & integration tests verifying validator determinism
"""

import os
import copy
import zipfile
import pytest

from validator.validator import validate_submission
from validator.validation_result import ValidationStatus

_CLEAN_BVH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh"
)


def _create_test_zip(zip_path, valid=True):
    with open(_CLEAN_BVH, "r") as f:
        bvh_content = f.read()
    
    if not valid:
        # Invalidate frame time
        bvh_content = bvh_content.replace("Frame Time: 0.0083333", "Frame Time: 0.0500000")

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("denoising/MF001_low.bvh", bvh_content)


def test_validator_determinism_valid_submission(tmp_path):
    zip_path = tmp_path / "det_valid.zip"
    _create_test_zip(zip_path, valid=True)

    res1 = validate_submission(str(zip_path), task="denoising", motion_ids=["MF001"])
    res2 = validate_submission(str(zip_path), task="denoising", motion_ids=["MF001"])

    assert res1.status == res2.status == ValidationStatus.VALID
    assert res1.get_exit_code() == res2.get_exit_code() == 0
    assert len(res1.errors) == len(res2.errors) == 0
    assert res1.checks == res2.checks
    assert res1.file_summary == res2.file_summary
    assert res1.warnings == res2.warnings


def test_validator_determinism_invalid_submission(tmp_path):
    zip_path = tmp_path / "det_invalid.zip"
    _create_test_zip(zip_path, valid=False)

    res1 = validate_submission(str(zip_path), task="denoising", motion_ids=["MF001"])
    res2 = validate_submission(str(zip_path), task="denoising", motion_ids=["MF001"])

    assert res1.status == res2.status == ValidationStatus.REJECTED
    assert res1.get_exit_code() == res2.get_exit_code() == 1
    assert [e.code for e in res1.errors] == [e.code for e in res2.errors]
    assert [e.message for e in res1.errors] == [e.message for e in res2.errors]
    assert res1.checks == res2.checks
    assert res1.file_summary == res2.file_summary
