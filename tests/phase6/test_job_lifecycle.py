"""
test_job_lifecycle.py — Unit tests for Phase 6 Job lifecycle and state machine
"""

import os
import tempfile
import pytest

from runner.job_manager import (
    Job,
    JobStatus,
    InvalidStateTransitionError,
    ALLOWED_TRANSITIONS,
)


def test_job_initial_state():
    job = Job(submission_path="dummy.zip", submission_id="test_sub")
    assert job.status == JobStatus.QUEUED
    assert job.submission_id == "test_sub"
    assert len(job.status_history) == 1
    assert job.status_history[0]["to_status"] == JobStatus.QUEUED.value


def test_valid_transitions_pipeline():
    job = Job(submission_path="dummy.zip")
    assert job.status == JobStatus.QUEUED

    job.transition_to(JobStatus.VALIDATING, reason="Starting validation")
    assert job.status == JobStatus.VALIDATING
    assert job.started_at is not None

    job.transition_to(JobStatus.EVALUATING, reason="Validation passed")
    assert job.status == JobStatus.EVALUATING

    job.transition_to(JobStatus.COMPLETED, reason="Evaluation complete")
    assert job.status == JobStatus.COMPLETED
    assert job.completed_at is not None
    assert len(job.status_history) == 4


def test_valid_rejection_transition():
    job = Job(submission_path="dummy.zip")
    job.transition_to(JobStatus.VALIDATING)
    job.transition_to(JobStatus.REJECTED, reason="Altered FPS detected")
    assert job.status == JobStatus.REJECTED
    assert job.completed_at is not None


def test_valid_validation_error_transition():
    job = Job(submission_path="dummy.zip")
    job.transition_to(JobStatus.VALIDATING)
    job.transition_to(JobStatus.VALIDATION_ERROR, reason="Validator internal crash")
    assert job.status == JobStatus.VALIDATION_ERROR
    assert job.completed_at is not None


def test_invalid_transitions_rejected():
    # Attempting to jump directly from QUEUED to EVALUATING
    job = Job(submission_path="dummy.zip")
    with pytest.raises(InvalidStateTransitionError):
        job.transition_to(JobStatus.EVALUATING)

    # Attempting to evaluate a REJECTED job
    job = Job(submission_path="dummy.zip")
    job.transition_to(JobStatus.VALIDATING)
    job.transition_to(JobStatus.REJECTED)
    with pytest.raises(InvalidStateTransitionError):
        job.transition_to(JobStatus.EVALUATING)

    # Attempting to transition from COMPLETED (terminal state)
    job = Job(submission_path="dummy.zip")
    job.transition_to(JobStatus.VALIDATING)
    job.transition_to(JobStatus.EVALUATING)
    job.transition_to(JobStatus.COMPLETED)
    with pytest.raises(InvalidStateTransitionError):
        job.transition_to(JobStatus.VALIDATING)


def test_job_workspace_cleanup(tmp_path):
    job = Job(submission_path="dummy.zip")
    ws = tmp_path / "job_workspace"
    ws.mkdir()
    (ws / "temp_file.txt").write_text("temporary data")
    job.workspace_dir = str(ws)

    assert os.path.isdir(job.workspace_dir)
    job.cleanup()
    assert not os.path.exists(str(ws))
    assert job.workspace_dir is None
