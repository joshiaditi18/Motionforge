"""
test_runner_pipeline.py — Integration tests for Phase 6 competition runner pipeline
"""

import os
import shutil
import zipfile
import pytest

from runner.competition_runner import run_competition, RUNNER_EXIT_CODES
from runner.job_manager import JobStatus
from baselines.retargeting.baseline_retargeting import TARGET_CONFIGS, retarget_hierarchy_offsets
from baselines.common.bvh_io import parse_bvh, write_bvh

_CLEAN_BVH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh"
)


def _build_valid_submission_zip(zip_path: str, motion_id: str = "MF001"):
    """Creates a valid 3-task submission zip for motion_id."""
    bvh = parse_bvh(_CLEAN_BVH)
    staging = os.path.join(os.path.dirname(zip_path), "staging_valid")
    os.makedirs(os.path.join(staging, "denoising"), exist_ok=True)
    os.makedirs(os.path.join(staging, "gap_filling"), exist_ok=True)
    os.makedirs(os.path.join(staging, "retargeting"), exist_ok=True)

    # Denoising
    for lvl in ["low", "medium", "high"]:
        shutil.copyfile(_CLEAN_BVH, os.path.join(staging, "denoising", f"{motion_id}_{lvl}.bvh"))

    # Gap filling
    for gt in ["short", "medium", "long"]:
        shutil.copyfile(_CLEAN_BVH, os.path.join(staging, "gap_filling", f"{motion_id}_{gt}.bvh"))

    # Retargeting
    for tgt in ["target_small", "target_medium", "target_tall"]:
        nh = retarget_hierarchy_offsets(bvh, TARGET_CONFIGS[tgt])
        out_f = os.path.join(staging, "retargeting", f"{motion_id}_{tgt}.bvh")
        write_bvh(out_f, nh, bvh.frame_time, bvh.motion_data)

    with zipfile.ZipFile(zip_path, "w") as zf:
        for root, _, files in os.walk(staging):
            for file in files:
                full_p = os.path.join(root, file)
                rel_p = os.path.relpath(full_p, staging)
                zf.write(full_p, rel_p)

    shutil.rmtree(staging, ignore_errors=True)


def _build_rejected_submission_zip(zip_path: str, motion_id: str = "MF001"):
    """Creates a submission zip with altered FPS (violates 120 FPS contract)."""
    with open(_CLEAN_BVH, "r", encoding="utf-8") as f:
        bad_bvh = f.read().replace("Frame Time: 0.0083333", "Frame Time: 0.0333333")

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(f"denoising/{motion_id}_low.bvh", bad_bvh)
        zf.writestr(f"gap_filling/{motion_id}_short.bvh", bad_bvh)
        zf.writestr(f"retargeting/{motion_id}_target_small.bvh", bad_bvh)


def test_missing_submission_archive_handled(tmp_path):
    missing_path = str(tmp_path / "does_not_exist.zip")
    exit_code, result = run_competition(
        submission_path=missing_path,
        output_dir=str(tmp_path / "results"),
        quiet=True,
    )
    assert exit_code == 2
    assert result["job_status"] == JobStatus.FAILED.value
    assert "not found" in result["error_message"].lower()


def test_rejected_submission_never_evaluated(tmp_path):
    zip_path = str(tmp_path / "rejected_sub.zip")
    _build_rejected_submission_zip(zip_path, motion_id="MF001")

    exit_code, result = run_competition(
        submission_path=zip_path,
        output_dir=str(tmp_path / "results"),
        motion_ids=["MF001"],
        quiet=True,
    )
    assert exit_code == 1
    assert result["job_status"] == JobStatus.REJECTED.value
    assert result["validation_status"] == "REJECTED"
    # Gatekeeping guarantee: NEVER evaluated
    assert result["overall_score"] is None
    assert result["metrics"] == {}
    assert len(result["validation_errors"]) > 0


def test_validator_internal_error_halts_pipeline(tmp_path, monkeypatch):
    zip_path = str(tmp_path / "error_sub.zip")
    _build_valid_submission_zip(zip_path, motion_id="MF001")

    # Mock validate_submission to simulate unexpected validator crash
    import validator
    from validator.validation_result import ValidationResult, ValidationStatus

    def mock_val(*args, **kwargs):
        res = ValidationResult(status=ValidationStatus.ERROR)
        res.add_error("INTERNAL_VALIDATION_ERROR", "Simulated validator panic")
        return res

    monkeypatch.setattr(validator, "validate_submission", mock_val)

    exit_code, result = run_competition(
        submission_path=zip_path,
        output_dir=str(tmp_path / "results"),
        motion_ids=["MF001"],
        quiet=True,
    )
    assert exit_code == 2
    assert result["job_status"] == JobStatus.VALIDATION_ERROR.value
    assert result["overall_score"] is None
    assert result["metrics"] == {}


def test_evaluation_exception_produces_failed_job(tmp_path, monkeypatch):
    zip_path = str(tmp_path / "eval_exc_sub.zip")
    _build_valid_submission_zip(zip_path, motion_id="MF001")

    # Mock evaluate_submission to simulate unhandled evaluator error
    import runner.competition_runner as cr_mod

    def mock_eval(*args, **kwargs):
        raise RuntimeError("Simulated unhandled evaluation calculation crash")

    monkeypatch.setattr(cr_mod, "evaluate_submission", mock_eval)

    exit_code, result = run_competition(
        submission_path=zip_path,
        output_dir=str(tmp_path / "results"),
        motion_ids=["MF001"],
        quiet=True,
    )
    assert exit_code == 2
    assert result["job_status"] == JobStatus.FAILED.value
    assert "Simulated unhandled evaluation" in result["error_message"]


def test_valid_submission_completes_successfully(tmp_path):
    zip_path = str(tmp_path / "valid_sub.zip")
    _build_valid_submission_zip(zip_path, motion_id="MF001")

    out_dir = tmp_path / "results"
    exit_code, result = run_competition(
        submission_path=zip_path,
        submission_id="test_candidate",
        run_id="run_001",
        output_dir=str(out_dir),
        motion_ids=["MF001"],
        quiet=True,
    )

    assert exit_code == 0
    assert result["job_status"] == JobStatus.COMPLETED.value
    assert result["validation_status"] == "VALID"
    assert result["overall_score"] is not None
    assert 0.0 <= result["overall_score"] <= 100.0
    assert result["job_id"] == "run_001"
    assert result["submission_id"] == "test_candidate"


def test_temporary_workspace_cleaned_after_success(tmp_path, monkeypatch):
    zip_path = str(tmp_path / "clean_sub.zip")
    _build_valid_submission_zip(zip_path, motion_id="MF001")

    recorded_workspace = []
    import runner.competition_runner as cr_mod
    orig_eval = cr_mod.evaluate_submission

    def spy_eval(*args, **kwargs):
        recorded_workspace.append(kwargs.get("submission_dir") or args[0])
        return orig_eval(*args, **kwargs)

    monkeypatch.setattr(cr_mod, "evaluate_submission", spy_eval)

    exit_code, result = run_competition(
        submission_path=zip_path,
        output_dir=str(tmp_path / "results"),
        motion_ids=["MF001"],
        quiet=True,
    )
    assert exit_code == 0
    assert len(recorded_workspace) == 1
    # Check that temporary extraction directory was cleaned up
    assert not os.path.exists(recorded_workspace[0])
