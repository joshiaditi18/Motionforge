"""
result_writer.py — MOTIONFORGE Phase 6 Runner Result Artifact Writer

Builds standardized JSON result artifacts matching Phase 2/4 data contracts,
with atomic writing semantics to prevent partial/corrupted output files.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Dict, Any, Optional

from runner.job_manager import Job, JobStatus
from runner.runner_config import RunnerConfig


def build_runner_result(
    job: Job,
    config: RunnerConfig,
    runtime_seconds: float,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Construct canonical machine-readable JSON result object for a competition run.
    Follows DATA_CONTRACT.md §6.1 conventions.
    """
    val = job.validation_result
    eval_res = job.evaluation_result

    val_status_str = val.status.value if val else None
    val_errors = [e.to_dict() for e in val.errors] if val else []
    val_checks = dict(val.checks) if val else {}

    # Extract evaluation scores and metrics if evaluated
    overall_score = None
    task_scores = {"denoising": None, "gap_filling": None, "retargeting": None}
    metrics: Dict[str, Any] = {}

    if eval_res:
        overall_score = eval_res.get("overall_score")
        raw_ts = eval_res.get("task_scores", {})
        task_scores = {
            "denoising": raw_ts.get("denoising"),
            "gap_filling": raw_ts.get("gap_filling"),
            "retargeting": raw_ts.get("retargeting"),
        }
        metrics = eval_res.get("metrics", {})

    err_msg = None
    if job.status == JobStatus.REJECTED:
        if val and val.errors:
            err_msg = f"Submission rejected by validator: {val.errors[0].message}"
        else:
            err_msg = "Submission rejected by validator"
    elif job.status in {JobStatus.VALIDATION_ERROR, JobStatus.FAILED}:
        if job.errors:
            err_msg = "; ".join(job.errors)
        elif eval_res and eval_res.get("error_message"):
            err_msg = eval_res.get("error_message")

    result: Dict[str, Any] = {
        "schema_version": "1.0",
        "competition": config.competition_name,
        "runner_version": config.runner_version,
        "evaluator_version": config.evaluator_version,
        "validator_version": config.validator_version,
        "contract_version": config.contract_version,
        "calibration_version": config.calibration_version,
        "job_id": job.job_id,
        "submission_id": job.submission_id,
        "job_status": job.status.value,
        "validation_status": val_status_str,
        "overall_score": overall_score,
        "task_scores": task_scores,
        "scoring_weights": dict(config.scoring_weights),
        "metrics": metrics,
        "validation_errors": val_errors,
        "validation_checks": val_checks,
        "error_message": err_msg,
        "runtime_seconds": round(float(runtime_seconds), 4),
        "timestamps": {
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        },
        "status_history": job.status_history,
        "warnings": list(job.warnings),
    }

    if extra:
        result.update(extra)

    return result


def write_runner_result(result_dict: Dict[str, Any], output_path: str) -> None:
    """
    Atomically writes result_dict to output_path using temporary file + rename.
    Guarantees no partial or corrupted JSON remains on disk if writing is interrupted.
    """
    abs_path = os.path.abspath(output_path)
    dir_name = os.path.dirname(abs_path)
    os.makedirs(dir_name, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp.json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, abs_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def format_runner_summary(result_dict: Dict[str, Any]) -> str:
    """Formats human-readable summary of the competition run for terminal output."""
    jid = result_dict.get("job_id", "?")
    sid = result_dict.get("submission_id", "?")
    status = result_dict.get("job_status", "?")
    overall = result_dict.get("overall_score")
    ts = result_dict.get("task_scores", {})
    runtime = result_dict.get("runtime_seconds", 0.0)

    lines = [
        "=" * 60,
        "MOTIONFORGE LOCAL COMPETITION RUNNER RESULT",
        "=" * 60,
        f"  Job ID        : {jid}",
        f"  Submission ID : {sid}",
        f"  Final Status  : {status}",
        f"  Runtime       : {runtime:.2f}s",
        "-" * 60,
    ]

    val_status = result_dict.get("validation_status")
    if val_status:
        lines.append(f"  Validator Status: {val_status}")

    if overall is not None:
        lines.append(f"  Overall Score : {overall:.2f} / 100.00")
        lines.append("  Task Breakdown:")
        for t, s in ts.items():
            val_str = f"{s:.2f}" if s is not None else "N/A"
            lines.append(f"    - {t:<15}: {val_str}")
    else:
        lines.append("  Overall Score : N/A (Not Scored)")

    err = result_dict.get("error_message")
    if err:
        lines.append(f"  Error Details : {err}")

    val_errs = result_dict.get("validation_errors", [])
    if val_errs:
        lines.append("  Validation Errors:")
        for e in val_errs[:5]:
            lines.append(f"    * [{e.get('code')}]: {e.get('message')}")
        if len(val_errs) > 5:
            lines.append(f"    ... and {len(val_errs) - 5} more error(s)")

    lines.append("=" * 60)
    return "\n".join(lines)
