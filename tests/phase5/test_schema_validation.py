"""
test_schema_validation.py — Unit tests for schema_validator.py
"""

import os
import json
import pytest

from validator.schema_validator import (
    validate_submission_schema,
    validate_submission_metadata,
)
from validator.error_codes import ErrorCode


def test_missing_required_directory(tmp_path):
    # Only create denoising/, missing gap_filling/ and retargeting/
    sub_dir = tmp_path / "submission"
    os.makedirs(sub_dir / "denoising", exist_ok=True)
    
    ok, errors, _, _, _ = validate_submission_schema(str(sub_dir))
    assert ok is False
    assert any(e.code == ErrorCode.MISSING_REQUIRED_DIRECTORY.value for e in errors)


def test_missing_required_file_for_motion(tmp_path):
    sub_dir = tmp_path / "submission"
    os.makedirs(sub_dir / "denoising", exist_ok=True)
    # Only MF002 present, MF006, MF007 etc missing
    (sub_dir / "denoising" / "MF002_low.bvh").write_text("HIERARCHY\n")
    
    ok, errors, _, _, _ = validate_submission_schema(
        str(sub_dir),
        target_task="denoising",
        motion_ids=["MF002", "MF006"]
    )
    assert ok is False
    assert any(e.code == ErrorCode.MISSING_REQUIRED_FILE.value and "MF006" in e.message for e in errors)


def test_unexpected_file_in_task_dir(tmp_path):
    sub_dir = tmp_path / "submission"
    os.makedirs(sub_dir / "denoising", exist_ok=True)
    (sub_dir / "denoising" / "MF002_low.bvh").write_text("HIERARCHY\n")
    (sub_dir / "denoising" / "notes.txt").write_text("my notes")
    
    ok, errors, _, _, _ = validate_submission_schema(
        str(sub_dir),
        target_task="denoising",
        motion_ids=["MF002"]
    )
    assert ok is False
    assert any(e.code == ErrorCode.UNEXPECTED_FILE.value for e in errors)


def test_invalid_metadata_json(tmp_path):
    meta_path = tmp_path / "metadata.json"
    meta_path.write_text("{ malformed json: true ")
    
    ok, errors = validate_submission_metadata(str(meta_path))
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_METADATA.value for e in errors)


def test_invalid_metadata_field_type(tmp_path):
    meta_path = tmp_path / "metadata.json"
    meta_path.write_text(json.dumps({"submission_id": 12345, "tasks": "denoising"}))
    
    ok, errors = validate_submission_metadata(str(meta_path))
    assert ok is False
    assert any(e.code == ErrorCode.INVALID_METADATA.value for e in errors)


def test_valid_schema_single_task(tmp_path):
    sub_dir = tmp_path / "submission"
    os.makedirs(sub_dir / "denoising", exist_ok=True)
    (sub_dir / "denoising" / "MF002_low.bvh").write_text("HIERARCHY\n")
    (sub_dir / "denoising" / "MF006_low.bvh").write_text("HIERARCHY\n")
    
    ok, errors, _, summary, task_files = validate_submission_schema(
        str(sub_dir),
        target_task="denoising",
        motion_ids=["MF002", "MF006"]
    )
    assert ok is True
    assert len(errors) == 0
    assert summary["denoising_files"] == 2
    assert summary["total_files_found"] == 2
