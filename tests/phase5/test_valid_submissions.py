"""
test_valid_submissions.py — Integration tests verifying valid participant submissions
"""

import os
import shutil
import zipfile
import pytest

from validator.validator import validate_submission
from validator.validation_result import ValidationStatus
from baselines.retargeting.baseline_retargeting import TARGET_CONFIGS, retarget_hierarchy_offsets
from baselines.common.bvh_io import parse_bvh, write_bvh

_CLEAN_BVH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh"
)


def _prepare_valid_submission_zip(zip_path, motion_id="MF001"):
    """Create a fully compliant submission zip archive for MF001."""
    bvh = parse_bvh(_CLEAN_BVH)
    tmp_dir = zip_path.parent / "staging"
    os.makedirs(tmp_dir / "denoising", exist_ok=True)
    os.makedirs(tmp_dir / "gap_filling", exist_ok=True)
    os.makedirs(tmp_dir / "retargeting", exist_ok=True)

    # 1. Denoising files
    for level in ["low", "medium", "high"]:
        shutil.copyfile(_CLEAN_BVH, tmp_dir / "denoising" / f"{motion_id}_{level}.bvh")

    # 2. Gap filling files
    for gtype in ["short", "medium", "long"]:
        shutil.copyfile(_CLEAN_BVH, tmp_dir / "gap_filling" / f"{motion_id}_{gtype}.bvh")

    # 3. Retargeting files
    for target in ["target_small", "target_medium", "target_tall"]:
        new_headers = retarget_hierarchy_offsets(bvh, TARGET_CONFIGS[target])
        out_target = tmp_dir / "retargeting" / f"{motion_id}_{target}.bvh"
        write_bvh(str(out_target), new_headers, bvh.frame_time, bvh.motion_data)

    with zipfile.ZipFile(zip_path, "w") as zf:
        for root, _, files in os.walk(tmp_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, tmp_dir)
                zf.write(full_path, rel_path)

    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_valid_submission_archive_full(tmp_path):
    zip_path = tmp_path / "valid_full_submission.zip"
    _prepare_valid_submission_zip(zip_path, motion_id="MF001")

    result = validate_submission(
        submission_path=str(zip_path),
        motion_ids=["MF001"]
    )

    assert result.status == ValidationStatus.VALID
    assert result.get_exit_code() == 0
    assert len(result.errors) == 0
    assert result.checks["archive"] == "PASS"
    assert result.checks["security"] == "PASS"
    assert result.checks["schema"] == "PASS"
    assert result.checks["bvh"] == "PASS"
    assert result.checks["skeleton"] == "PASS"
    assert result.checks["motion"] == "PASS"
    assert result.checks["task"] == "PASS"
    assert result.file_summary["total_files_found"] == 9


def test_valid_submission_single_task_denoising(tmp_path):
    sub_dir = tmp_path / "denoising_sub"
    os.makedirs(sub_dir / "denoising", exist_ok=True)
    shutil.copyfile(_CLEAN_BVH, sub_dir / "denoising" / "MF001_low.bvh")

    result = validate_submission(
        submission_path=str(sub_dir),
        task="denoising",
        motion_ids=["MF001"]
    )

    assert result.status == ValidationStatus.VALID
    assert result.get_exit_code() == 0
    assert len(result.errors) == 0
