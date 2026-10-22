"""
evaluation_runner.py — MOTIONFORGE Phase 4 CLI Evaluation Runner

Usage:

  Single-task mode:
    python -m evaluation.runners.evaluation_runner \\
        --task {1|2|3} \\
        --input <noisy_or_gap_or_source.bvh> \\
        --prediction <predicted.bvh> \\
        --ground-truth <gt_clean.bvh> \\
        --output <result.json> \\
        [--joint JOINT_NAME --gap-start N --gap-end N] \\
        [--target-type {small|medium|tall}]

  Batch submission mode:
    python -m evaluation.runners.evaluation_runner \\
        --submission <submission_dir> \\
        --output <result.json> \\
        [--submission-id <id>] \\
        [--motion-ids MF001 MF002 ...] \\
        [--tasks 1 2 3]

Exit codes:
    0 — VALID
    1 — REJECTED
    2 — ERROR
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from evaluation.task_evaluator import evaluate_task1, evaluate_task2, evaluate_task3
from evaluation.evaluator import evaluate_submission
from evaluation.io.evaluation_schema import (
    SubmissionStatus,
    build_evaluation_result,
    get_exit_code,
)
from evaluation.io.result_writer import write_result, format_result_summary
from evaluation import (
    MOTIONFORGE_EVALUATOR_VERSION,
    MOTIONFORGE_METRIC_VERSION,
    MOTIONFORGE_CALIBRATION_VERSION,
)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m evaluation.runners.evaluation_runner",
        description="MOTIONFORGE Official Evaluation Runner v" + MOTIONFORGE_EVALUATOR_VERSION,
    )

    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--task", type=int, choices=[1, 2, 3],
        help="Run single-task evaluation (must also provide --prediction and --ground-truth).",
    )
    mode.add_argument(
        "--submission", metavar="DIR",
        help="Run full batch submission evaluation from a submission directory.",
    )

    # Single-task arguments
    p.add_argument("--input",        metavar="FILE", help="Input BVH (noisy / gap / source).")
    p.add_argument("--prediction",   metavar="FILE", help="Predicted BVH from participant.")
    p.add_argument("--ground-truth", metavar="FILE", dest="ground_truth",
                   help="Ground-truth clean BVH.")

    # Task 2 specifics
    p.add_argument("--joint",     metavar="JOINT", help="(Task 2) Joint name that was filled.")
    p.add_argument("--gap-start", type=int, metavar="N", dest="gap_start",
                   help="(Task 2) First frame of gap (inclusive).")
    p.add_argument("--gap-end",   type=int, metavar="N", dest="gap_end",
                   help="(Task 2) Last frame of gap (inclusive).")

    # Task 3 specifics
    p.add_argument("--target-type", choices=["small", "medium", "tall"], dest="target_type",
                   help="(Task 3) Target avatar size.")

    # Batch arguments
    p.add_argument("--submission-id", metavar="ID", dest="submission_id",
                   help="(Batch) Unique submission ID.")
    p.add_argument("--motion-ids", nargs="+", metavar="MFxxx", dest="motion_ids",
                   help="(Batch) Motion IDs to evaluate (default: hidden set).")
    p.add_argument("--tasks", nargs="+", type=int, choices=[1, 2, 3], metavar="N", dest="tasks",
                   help="(Batch) Task numbers to run (default: 1 2 3).")

    # Output
    p.add_argument("--output", metavar="FILE", default="evaluation_result.json",
                   help="Output JSON result file (default: evaluation_result.json).")

    # Flags
    p.add_argument("--quiet",   action="store_true", help="Suppress stdout summary.")
    p.add_argument("--version", action="version",
                   version=f"MOTIONFORGE Evaluator {MOTIONFORGE_EVALUATOR_VERSION}")

    return p


# ---------------------------------------------------------------------------
# Single-task dispatch
# ---------------------------------------------------------------------------

def run_single_task(args: argparse.Namespace) -> Dict:  # type: ignore[name-defined]
    task = args.task

    if not args.prediction:
        print("ERROR: --prediction is required for single-task mode.", file=sys.stderr)
        sys.exit(2)
    if not args.ground_truth:
        print("ERROR: --ground-truth is required for single-task mode.", file=sys.stderr)
        sys.exit(2)

    if task == 1:
        result_raw = evaluate_task1(
            pred_path=args.prediction,
            gt_path=args.ground_truth,
            noisy_path=args.input,
        )
    elif task == 2:
        if not args.joint or args.gap_start is None or args.gap_end is None:
            print("ERROR: --joint, --gap-start, --gap-end required for Task 2.", file=sys.stderr)
            sys.exit(2)
        result_raw = evaluate_task2(
            pred_path=args.prediction,
            gt_path=args.ground_truth,
            joint_name=args.joint,
            start_frame=args.gap_start,
            end_frame=args.gap_end,
        )
    else:  # task == 3
        if not args.target_type:
            print("ERROR: --target-type required for Task 3.", file=sys.stderr)
            sys.exit(2)
        result_raw = evaluate_task3(
            pred_path=args.prediction,
            src_path=args.ground_truth,
            target_type=args.target_type,
        )

    status = SubmissionStatus(result_raw["status"])
    score  = result_raw.get("score")

    task_name = {1: "denoising", 2: "gap_filling", 3: "retargeting"}[task]
    result = build_evaluation_result(
        submission_id=f"single_task{task}",
        status=status,
        overall_score=score,
        task_scores={
            "denoising":   score if task == 1 else None,
            "gap_filling": score if task == 2 else None,
            "retargeting": score if task == 3 else None,
        },
        metrics={task_name: result_raw.get("metrics", {})},
        runtime_seconds=result_raw.get("runtime_seconds", 0.0),
        error_message=result_raw.get("error_message"),
        evaluator_version=MOTIONFORGE_EVALUATOR_VERSION,
        metric_version=MOTIONFORGE_METRIC_VERSION,
        calibration_version=MOTIONFORGE_CALIBRATION_VERSION,
        extra={"detail": result_raw.get("detail", {})},
    )
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = build_parser()
    args   = parser.parse_args()

    if args.submission:
        # Batch mode
        result = evaluate_submission(
            submission_dir=args.submission,
            submission_id=args.submission_id,
            motion_ids=args.motion_ids,
            evaluate_tasks=args.tasks,
        )
    else:
        # Single-task mode
        result = run_single_task(args)

    # Write output
    write_result(result, args.output, validate=True)

    if not args.quiet:
        print(format_result_summary(result))
        print(f"\nResult saved to: {os.path.abspath(args.output)}")

    return get_exit_code(result)


if __name__ == "__main__":
    sys.exit(main())
