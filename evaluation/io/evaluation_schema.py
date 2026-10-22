"""
evaluation_schema.py — MOTIONFORGE Phase 4 Result Schema

Defines the canonical evaluation result structure matching DATA_CONTRACT.md §6.1.

Status enum:
    VALID    — submission evaluated successfully (exit code 0)
    REJECTED — structural/contract violation (exit code 1)
    ERROR    — internal evaluator error (exit code 2)
"""

from __future__ import annotations

import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class SubmissionStatus(str, Enum):
    VALID    = "VALID"
    REJECTED = "REJECTED"
    ERROR    = "ERROR"


# Exit codes matching DATA_CONTRACT.md §4.2
EXIT_CODE_MAP = {
    SubmissionStatus.VALID:    0,
    SubmissionStatus.REJECTED: 1,
    SubmissionStatus.ERROR:    2,
}


def build_evaluation_result(
    submission_id: str,
    status: SubmissionStatus,
    overall_score: Optional[float],
    task_scores: Dict[str, Optional[float]],
    metrics: Dict[str, Any],
    runtime_seconds: float,
    error_message: Optional[str] = None,
    evaluator_version: str = "0.1.0",
    metric_version: str = "1.0.0",
    calibration_version: str = "phase3_calibrated_2026",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build the canonical evaluation result dict matching DATA_CONTRACT.md §6.1.

    Parameters
    ----------
    submission_id      : Unique identifier for this submission
    status             : SubmissionStatus enum value
    overall_score      : Weighted overall score [0,100] or None if rejected
    task_scores        : { "denoising": score, "gap_filling": score, "retargeting": score }
    metrics            : Nested dict of per-task metric breakdowns
    runtime_seconds    : Wall-clock evaluation time
    error_message      : Human-readable error description (if status != VALID)
    evaluator_version  : Must match evaluation/__init__.py MOTIONFORGE_EVALUATOR_VERSION
    metric_version     : Must match evaluation/__init__.py MOTIONFORGE_METRIC_VERSION
    calibration_version: Must match evaluation/__init__.py MOTIONFORGE_CALIBRATION_VERSION
    extra              : Optional extra fields (non-breaking extensions)

    Returns
    -------
    dict — JSON-serialisable evaluation result
    """
    result: Dict[str, Any] = {
        "schema_version":      "1.0",
        "evaluator_version":   evaluator_version,
        "metric_version":      metric_version,
        "calibration_version": calibration_version,
        "submission_id":       submission_id,
        "status":              status.value,
        "timestamp":           datetime.datetime.utcnow().isoformat() + "Z",
        "runtime_seconds":     round(float(runtime_seconds), 4),
        "overall_score":       (
            round(float(overall_score), 6) if overall_score is not None else None
        ),
        "task_scores": {
            k: (round(float(v), 6) if v is not None else None)
            for k, v in task_scores.items()
        },
        "metrics":       metrics,
        "error_message": error_message,
    }

    if extra:
        result.update(extra)

    return result


def get_exit_code(result: Dict[str, Any]) -> int:
    """Return the process exit code for a result dict."""
    status_str = result.get("status", "ERROR")
    try:
        status = SubmissionStatus(status_str)
    except ValueError:
        status = SubmissionStatus.ERROR
    return EXIT_CODE_MAP[status]


def validate_result_schema(result: Dict[str, Any]) -> List[str]:
    """
    Validate a result dict against required schema fields.
    Returns list of error strings (empty list = valid).
    """
    errors: List[str] = []
    required_fields = [
        "schema_version", "evaluator_version", "metric_version",
        "calibration_version", "submission_id", "status", "timestamp",
        "runtime_seconds", "overall_score", "task_scores", "metrics",
    ]
    for field in required_fields:
        if field not in result:
            errors.append(f"Missing required field: '{field}'")

    status = result.get("status")
    if status not in (s.value for s in SubmissionStatus):
        errors.append(f"Invalid status value: '{status}'")

    task_scores = result.get("task_scores", {})
    for task in ("denoising", "gap_filling", "retargeting"):
        if task not in task_scores:
            errors.append(f"task_scores missing key: '{task}'")

    return errors
