"""
job_manager.py — MOTIONFORGE Phase 6 Local Competition Job Lifecycle Manager

Defines explicit job lifecycle states, enforces permitted transitions,
and maintains run metadata, timestamps, and workspace state.
"""

from __future__ import annotations

import datetime
import os
import shutil
import uuid
from enum import Enum
from typing import Dict, List, Any, Optional, Set

from validator.validation_result import ValidationResult


class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    REJECTED = "REJECTED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


ALLOWED_TRANSITIONS: Dict[JobStatus, Set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.VALIDATING, JobStatus.FAILED},
    JobStatus.VALIDATING: {
        JobStatus.REJECTED,
        JobStatus.VALIDATION_ERROR,
        JobStatus.EVALUATING,
        JobStatus.FAILED,
    },
    JobStatus.REJECTED: set(),            # Terminal state
    JobStatus.VALIDATION_ERROR: set(),    # Terminal state
    JobStatus.EVALUATING: {JobStatus.COMPLETED, JobStatus.FAILED},
    JobStatus.COMPLETED: set(),           # Terminal state
    JobStatus.FAILED: set(),              # Terminal state
}


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal job lifecycle state transition is attempted."""
    pass


class Job:
    """Represents a competition run job tracking lifecycle state, artifacts, and logs."""

    def __init__(
        self,
        submission_path: str,
        submission_id: Optional[str] = None,
        job_id: Optional[str] = None,
        created_at: Optional[str] = None,
    ):
        self.submission_path = submission_path
        self.submission_id = submission_id or os.path.splitext(os.path.basename(submission_path))[0]
        self.job_id = job_id or str(uuid.uuid4())

        now = created_at or datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.created_at = now
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None

        self.status = JobStatus.QUEUED
        self.status_history: List[Dict[str, Any]] = [
            {
                "from_status": None,
                "to_status": self.status.value,
                "timestamp": now,
                "reason": "Job initialized and queued",
            }
        ]

        self.validation_result: Optional[ValidationResult] = None
        self.evaluation_result: Optional[Dict[str, Any]] = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.workspace_dir: Optional[str] = None

    def transition_to(
        self,
        new_status: JobStatus,
        reason: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> None:
        """
        Transition job to new status according to state machine rules.
        Raises InvalidStateTransitionError if transition is disallowed.
        """
        allowed = ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal job status transition from '{self.status.value}' to '{new_status.value}'. "
                f"Allowed target states: {[s.value for s in allowed]}"
            )

        ts = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()

        if self.started_at is None and new_status == JobStatus.VALIDATING:
            self.started_at = ts

        if new_status in {JobStatus.COMPLETED, JobStatus.REJECTED, JobStatus.VALIDATION_ERROR, JobStatus.FAILED}:
            self.completed_at = ts

        self.status_history.append({
            "from_status": self.status.value,
            "to_status": new_status.value,
            "timestamp": ts,
            "reason": reason or f"Transitioned to {new_status.value}",
        })
        self.status = new_status

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def cleanup(self) -> None:
        """Safely clean up temporary workspace directory."""
        if self.workspace_dir and os.path.isdir(self.workspace_dir):
            try:
                shutil.rmtree(self.workspace_dir, ignore_errors=True)
            except Exception:
                pass
            self.workspace_dir = None
