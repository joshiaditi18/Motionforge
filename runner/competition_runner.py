"""
competition_runner.py — MOTIONFORGE Phase 6 Local Competition Runner

Orchestrates the complete deterministic evaluation pipeline:
    Submission Archive -> Phase 5 Validator -> Phase 4 Evaluator -> Phase 4 Scorer -> Result Artifact
Enforces strict gatekeeping (never evaluates rejected submissions) and guarantees cleanup.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
import traceback
from typing import Dict, Any, Optional, Tuple, List

_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from runner.job_manager import Job, JobStatus
from runner.runner_config import RunnerConfig
from runner.result_writer import build_runner_result, write_runner_result, format_runner_summary
import validator
from validator import ValidationStatus
from validator.security_validator import safe_extract_zip
from evaluation.evaluator import evaluate_submission, HIDDEN_MOTION_IDS, load_gap_metadata
from evaluation.io.evaluation_schema import SubmissionStatus

RUNNER_EXIT_CODES: Dict[JobStatus, int] = {
    JobStatus.COMPLETED: 0,
    JobStatus.REJECTED: 1,
    JobStatus.VALIDATION_ERROR: 2,
    JobStatus.FAILED: 2,
}


def _normalize_workspace_layout(workspace_dir: str) -> str:
    """
    Ensures the extracted workspace contains task1, task2, task3 directories
    with canonical filenames expected by the Phase 4 evaluator, bridging between
    DATA_CONTRACT.md §3.1 layout (denoising/, gap_filling/, retargeting/) and
    evaluator.py batch layout (task1/, task2/, task3/).
    """
    entries = [e for e in os.listdir(workspace_dir) if not e.startswith("__MACOSX")]
    target_root = workspace_dir
    # Handle single wrapper directory if present
    if len(entries) == 1:
        nested = os.path.join(workspace_dir, entries[0])
        if os.path.isdir(nested) and entries[0].lower() not in {"task1", "task2", "task3", "denoising", "gap_filling", "retargeting"}:
            target_root = nested

    # Task mappings (DATA_CONTRACT -> evaluator)
    mapping = [
        ("denoising", "task1"),
        ("gap_filling", "task2"),
        ("retargeting", "task3"),
    ]

    for source_alias, eval_name in mapping:
        src_dir = os.path.join(target_root, source_alias)
        dst_dir = os.path.join(target_root, eval_name)

        if os.path.isdir(src_dir) and not os.path.isdir(dst_dir):
            os.makedirs(dst_dir, exist_ok=True)
            for f in os.listdir(src_dir):
                shutil.copy2(os.path.join(src_dir, f), os.path.join(dst_dir, f))
        elif os.path.isdir(dst_dir) and not os.path.isdir(src_dir):
            os.makedirs(src_dir, exist_ok=True)
            for f in os.listdir(dst_dir):
                shutil.copy2(os.path.join(dst_dir, f), os.path.join(src_dir, f))

    # Normalize file names inside task1
    task1_dir = os.path.join(target_root, "task1")
    if os.path.isdir(task1_dir):
        for fname in list(os.listdir(task1_dir)):
            if fname.lower().endswith(".bvh"):
                mid = fname.split("_")[0] if "_" in fname else fname.split(".")[0]
                canonical_t1 = f"{mid}_denoised.bvh"
                canonical_path = os.path.join(task1_dir, canonical_t1)
                orig_path = os.path.join(task1_dir, fname)
                if not os.path.isfile(canonical_path):
                    shutil.copy2(orig_path, canonical_path)

    # Normalize file names inside task2
    task2_dir = os.path.join(target_root, "task2")
    if os.path.isdir(task2_dir):
        for fname in list(os.listdir(task2_dir)):
            if fname.lower().endswith(".bvh"):
                stem = os.path.splitext(fname)[0]
                # e.g. MF001_short -> MF001_short_filled.bvh
                if not stem.endswith("_filled"):
                    canonical_t2 = f"{stem}_filled.bvh"
                    canonical_path = os.path.join(task2_dir, canonical_t2)
                    orig_path = os.path.join(task2_dir, fname)
                    if not os.path.isfile(canonical_path):
                        shutil.copy2(orig_path, canonical_path)

    # Normalize file names inside task3
    task3_dir = os.path.join(target_root, "task3")
    if os.path.isdir(task3_dir):
        for fname in list(os.listdir(task3_dir)):
            if fname.lower().endswith(".bvh"):
                stem = os.path.splitext(fname)[0]
                # Map target names: target_small -> small, etc.
                for t_name in ["small", "medium", "tall"]:
                    if t_name in stem.lower():
                        mid = stem.split("_")[0]
                        canonical_t3 = f"{mid}_{t_name}_retargeted.bvh"
                        canonical_path = os.path.join(task3_dir, canonical_t3)
                        orig_path = os.path.join(task3_dir, fname)
                        if not os.path.isfile(canonical_path):
                            shutil.copy2(orig_path, canonical_path)

    return target_root


def run_competition(
    submission_path: str,
    submission_id: Optional[str] = None,
    run_id: Optional[str] = None,
    config: Optional[RunnerConfig] = None,
    output_dir: Optional[str] = None,
    output_file: Optional[str] = None,
    tasks: Optional[List[int]] = None,
    motion_ids: Optional[List[str]] = None,
    quiet: bool = False,
) -> Tuple[int, Dict[str, Any]]:
    """
    Execute full competition runner pipeline for a participant submission.

    Returns:
        (exit_code: int, result_dict: Dict[str, Any])
    """
    t0 = time.perf_counter()
    cfg = config or RunnerConfig.load()
    out_directory = output_dir or cfg.output_dir
    os.makedirs(out_directory, exist_ok=True)

    job = Job(
        submission_path=submission_path,
        submission_id=submission_id,
        job_id=run_id,
    )

    eval_motions = motion_ids or cfg.hidden_motion_ids
    result_dict: Dict[str, Any] = {}

    try:
        # ---------------------------------------------------------
        # STAGE 1: Transition to VALIDATING & Validate Submission
        # ---------------------------------------------------------
        job.transition_to(JobStatus.VALIDATING, reason="Initiating Phase 5 validation")

        if not os.path.exists(submission_path):
            job.add_error(f"Submission archive not found: '{submission_path}'")
            job.transition_to(JobStatus.FAILED, reason="Archive file not found")
            runtime = time.perf_counter() - t0
            result_dict = build_runner_result(job, cfg, runtime)
            _finalize_result(result_dict, job, out_directory, output_file, quiet)
            return RUNNER_EXIT_CODES[JobStatus.FAILED], result_dict

        # Execute official Phase 5 Validator
        val_res = validator.validate_submission(
            submission_path=submission_path,
            submission_id=job.submission_id,
            motion_ids=eval_motions,
        )
        job.validation_result = val_res

        # Check validation verdict
        if val_res.status == ValidationStatus.REJECTED:
            # STOP immediately: Never evaluate rejected submissions
            job.transition_to(
                JobStatus.REJECTED,
                reason=f"Validator rejected submission with {len(val_res.errors)} error(s)",
            )
            runtime = time.perf_counter() - t0
            result_dict = build_runner_result(job, cfg, runtime)
            _finalize_result(result_dict, job, out_directory, output_file, quiet)
            return RUNNER_EXIT_CODES[JobStatus.REJECTED], result_dict

        if val_res.status == ValidationStatus.ERROR:
            # STOP immediately on validator internal error
            job.transition_to(
                JobStatus.VALIDATION_ERROR,
                reason="Phase 5 Validator reported an internal execution error",
            )
            runtime = time.perf_counter() - t0
            result_dict = build_runner_result(job, cfg, runtime)
            _finalize_result(result_dict, job, out_directory, output_file, quiet)
            return RUNNER_EXIT_CODES[JobStatus.VALIDATION_ERROR], result_dict

        # ---------------------------------------------------------
        # STAGE 2: Transition to EVALUATING & Prepare Staging Area
        # ---------------------------------------------------------
        job.transition_to(
            JobStatus.EVALUATING,
            reason="Submission validated successfully. Proceeding to Phase 4 evaluation.",
        )

        job.workspace_dir = tempfile.mkdtemp(prefix=f"mf_run_{job.job_id[:8]}_")

        if os.path.isfile(submission_path):
            ok_ext, ext_errs = safe_extract_zip(submission_path, job.workspace_dir)
            if not ok_ext:
                job.add_error(f"Failed extracting submission archive: {ext_errs}")
                job.transition_to(JobStatus.FAILED, reason="Archive extraction failure")
                runtime = time.perf_counter() - t0
                result_dict = build_runner_result(job, cfg, runtime)
                _finalize_result(result_dict, job, out_directory, output_file, quiet)
                return RUNNER_EXIT_CODES[JobStatus.FAILED], result_dict
            eval_workspace = _normalize_workspace_layout(job.workspace_dir)
        else:
            # Uncompressed directory submission
            eval_workspace = _normalize_workspace_layout(submission_path)

        # ---------------------------------------------------------
        # STAGE 3: Invoke Official Phase 4 Evaluation Engine
        # ---------------------------------------------------------
        eval_res = evaluate_submission(
            submission_dir=eval_workspace,
            submission_id=job.submission_id,
            motion_ids=eval_motions,
            evaluate_tasks=tasks or [1, 2, 3],
        )
        job.evaluation_result = eval_res

        # Evaluate outcome
        if eval_res.get("status") == SubmissionStatus.ERROR.value:
            job.add_error(eval_res.get("error_message") or "Evaluator reported ERROR status")
            job.transition_to(JobStatus.FAILED, reason="Evaluation engine failed with ERROR")
            status_key = JobStatus.FAILED
        else:
            job.transition_to(JobStatus.COMPLETED, reason="Evaluation completed successfully")
            status_key = JobStatus.COMPLETED

        runtime = time.perf_counter() - t0
        result_dict = build_runner_result(job, cfg, runtime)
        _finalize_result(result_dict, job, out_directory, output_file, quiet)
        return RUNNER_EXIT_CODES[status_key], result_dict

    except Exception as exc:
        job.add_error(f"Runner execution exception: {exc}\n{traceback.format_exc()}")
        if job.status not in {JobStatus.REJECTED, JobStatus.VALIDATION_ERROR, JobStatus.COMPLETED, JobStatus.FAILED}:
            try:
                job.transition_to(JobStatus.FAILED, reason=f"Unhandled exception: {exc}")
            except Exception:
                job.status = JobStatus.FAILED

        runtime = time.perf_counter() - t0
        result_dict = build_runner_result(job, cfg, runtime)
        _finalize_result(result_dict, job, out_directory, output_file, quiet)
        return RUNNER_EXIT_CODES[JobStatus.FAILED], result_dict

    finally:
        if cfg.cleanup_temp:
            job.cleanup()


def _finalize_result(
    result_dict: Dict[str, Any],
    job: Job,
    output_dir: str,
    output_file: Optional[str],
    quiet: bool,
) -> str:
    """Writes result JSON atomically and prints summary if not quiet."""
    dest_path = output_file or os.path.join(output_dir, f"result_{job.job_id}.json")
    try:
        write_runner_result(result_dict, dest_path)
    except Exception as e:
        print(f"WARNING: Failed to write runner result file '{dest_path}': {e}", file=sys.stderr)

    if not quiet:
        print(format_runner_summary(result_dict))
        print(f"\nArtifact saved: {os.path.abspath(dest_path)}")

    return dest_path


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m runner.competition_runner",
        description="MOTIONFORGE Local Competition Runner v0.1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--submission", "--submission-path",
        dest="submission",
        required=True,
        help="Path to participant submission ZIP archive or directory.",
    )
    parser.add_argument(
        "--submission-id",
        dest="submission_id",
        default=None,
        help="Custom submission identifier (default: archive basename).",
    )
    parser.add_argument(
        "--run-id",
        dest="run_id",
        default=None,
        help="Deterministic run/job identifier (default: auto-generated UUID).",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=None,
        help="Directory to save runner artifacts (default: runner_results/).",
    )
    parser.add_argument(
        "--output", "--output-file",
        dest="output_file",
        default=None,
        help="Specific file path for the output result JSON.",
    )
    parser.add_argument(
        "--motion-ids",
        nargs="+",
        dest="motion_ids",
        default=None,
        help="Motion IDs to evaluate (default: official hidden evaluation set).",
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        type=int,
        choices=[1, 2, 3],
        dest="tasks",
        default=None,
        help="Specific tasks to evaluate [1, 2, 3] (default: all tasks).",
    )
    parser.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Path to competition.yaml configuration file (optional).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress human-readable terminal summary.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="MOTIONFORGE Local Competition Runner v0.1.0 (Contract v1.0.0)",
    )

    args = parser.parse_args()

    cfg = RunnerConfig.load(args.config_path)

    exit_code, _ = run_competition(
        submission_path=args.submission,
        submission_id=args.submission_id,
        run_id=args.run_id,
        config=cfg,
        output_dir=args.output_dir,
        output_file=args.output_file,
        tasks=args.tasks,
        motion_ids=args.motion_ids,
        quiet=args.quiet,
    )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
