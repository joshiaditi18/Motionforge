"""
test_result_artifact.py — Unit tests for Phase 6 runner result schema and atomic writing
"""

import json
import os
import pytest

from runner.job_manager import Job, JobStatus
from runner.runner_config import RunnerConfig
from runner.result_writer import (
    build_runner_result,
    write_runner_result,
    format_runner_summary,
)


def test_runner_result_schema_fields():
    config = RunnerConfig()
    job = Job(submission_path="sub.zip", submission_id="cand_1", job_id="job_123")
    job.transition_to(JobStatus.VALIDATING)
    job.transition_to(JobStatus.EVALUATING)
    job.transition_to(JobStatus.COMPLETED)

    res = build_runner_result(job, config, runtime_seconds=1.2345)

    required_keys = [
        "schema_version",
        "competition",
        "runner_version",
        "evaluator_version",
        "validator_version",
        "contract_version",
        "job_id",
        "submission_id",
        "job_status",
        "validation_status",
        "overall_score",
        "task_scores",
        "scoring_weights",
        "metrics",
        "validation_errors",
        "validation_checks",
        "runtime_seconds",
        "timestamps",
        "status_history",
    ]
    for k in required_keys:
        assert k in res, f"Missing required key '{k}' in runner result"

    assert res["schema_version"] == "1.0"
    assert res["job_id"] == "job_123"
    assert res["job_status"] == JobStatus.COMPLETED.value
    assert isinstance(res["task_scores"], dict)
    assert set(res["scoring_weights"].keys()) == {"denoising", "gap_filling", "retargeting"}


def test_atomic_result_writing(tmp_path):
    out_file = tmp_path / "artifacts" / "result.json"
    dummy_result = {"job_id": "test_atomic", "job_status": "COMPLETED"}

    write_runner_result(dummy_result, str(out_file))

    assert out_file.exists()
    with open(out_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["job_id"] == "test_atomic"


def test_atomic_result_writing_overwrites_existing(tmp_path):
    out_file = tmp_path / "result.json"
    out_file.write_text("old content")

    new_result = {"job_id": "updated_id", "job_status": "COMPLETED"}
    write_runner_result(new_result, str(out_file))

    with open(out_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["job_id"] == "updated_id"


def test_format_runner_summary_outputs_clean_text():
    sample = {
        "job_id": "run_999",
        "submission_id": "candidate_xyz",
        "job_status": "COMPLETED",
        "validation_status": "VALID",
        "overall_score": 85.25,
        "task_scores": {"denoising": 90.0, "gap_filling": 80.0, "retargeting": 85.0},
        "runtime_seconds": 2.45,
    }
    summary = format_runner_summary(sample)
    assert "run_999" in summary
    assert "candidate_xyz" in summary
    assert "85.25" in summary
    assert "COMPLETED" in summary
