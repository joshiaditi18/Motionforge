"""
evaluator.py — MOTIONFORGE Phase 4 Full Submission Evaluator

Reads a participant submission directory and evaluates all tasks against
ground-truth data. Aggregates task scores into an overall competition score.

Submission directory layout (expected):
    submission/
        task1/          # denoising predictions (one .bvh per motion)
        task2/          # gap-filling predictions (one .bvh per gap_id)
        task3/          # retargeting predictions (one .bvh per motion+target)

Ground-truth data is loaded from:
    MOTIONFORGE_DATASET/hidden/ground_truth/    (hidden clean BVHs)
    MOTIONFORGE_DATASET/metadata/gap_metadata.csv
"""

from __future__ import annotations

import csv
import os
import sys
import time
import uuid
from typing import Dict, Any, List, Optional

_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from evaluation.task_evaluator import evaluate_task1, evaluate_task2, evaluate_task3
from evaluation.scoring.overall_scoring import compute_overall_score
from evaluation.io.evaluation_schema import (
    SubmissionStatus,
    build_evaluation_result,
)
from evaluation import (
    MOTIONFORGE_EVALUATOR_VERSION,
    MOTIONFORGE_METRIC_VERSION,
    MOTIONFORGE_CALIBRATION_VERSION,
)

# ---------------------------------------------------------------------------
# Dataset paths
# ---------------------------------------------------------------------------

_DATASET_ROOT = os.path.join(_PROJECT_ROOT, "MOTIONFORGE_DATASET")
_HIDDEN_GT    = os.path.join(_DATASET_ROOT, "hidden", "ground_truth")
_PUBLIC_GT    = os.path.join(_DATASET_ROOT, "clean", "bvh")
_GAP_META     = os.path.join(_DATASET_ROOT, "metadata", "gap_metadata.csv")

# All 9 hidden evaluation motion IDs (Phase 2, frozen)
HIDDEN_MOTION_IDS = [
    "MF002", "MF006", "MF007", "MF014",
    "MF020", "MF021", "MF025", "MF026", "MF027",
]

# All 21 public training motion IDs
PUBLIC_MOTION_IDS = [
    "MF001", "MF003", "MF004", "MF005",
    "MF008", "MF009", "MF010", "MF011", "MF012", "MF013",
    "MF015", "MF016", "MF017", "MF018", "MF019",
    "MF022", "MF023", "MF024",
    "MF028", "MF029", "MF030",
]

RETARGETING_TARGETS = ("small", "medium", "tall")


# ---------------------------------------------------------------------------
# Gap metadata loader
# ---------------------------------------------------------------------------

def load_gap_metadata(motion_ids: Optional[List[str]] = None) -> List[Dict[str, str]]:
    """
    Load gap metadata CSV; optionally filter by motion_ids.
    Returns list of row dicts.
    """
    rows = []
    with open(_GAP_META, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if motion_ids is None or row["motion_id"] in motion_ids:
                rows.append(dict(row))
    return rows


def _resolve_gt_path(motion_id: str) -> str:
    """Return path to ground-truth clean BVH for a motion (hidden preferred)."""
    hidden_path = os.path.join(_HIDDEN_GT, f"{motion_id}_clean.bvh")
    public_path = os.path.join(_PUBLIC_GT, f"{motion_id}_clean.bvh")
    if os.path.isfile(hidden_path):
        return hidden_path
    if os.path.isfile(public_path):
        return public_path
    raise FileNotFoundError(
        f"Ground-truth BVH not found for {motion_id}.\n"
        f"  Tried: {hidden_path}\n"
        f"         {public_path}"
    )


# ---------------------------------------------------------------------------
# Task batch evaluators
# ---------------------------------------------------------------------------

def _evaluate_task1_batch(
    submission_dir: str,
    motion_ids: List[str],
) -> Dict[str, Any]:
    """Evaluate all denoising predictions in submission/task1/."""
    task1_dir = os.path.join(submission_dir, "task1")
    results: Dict[str, Any] = {}

    for mid in motion_ids:
        pred_file = os.path.join(task1_dir, f"{mid}_denoised.bvh")
        if not os.path.isfile(pred_file):
            results[mid] = {
                "status": SubmissionStatus.REJECTED.value,
                "score": None,
                "error_message": f"Missing prediction file: {os.path.basename(pred_file)}",
            }
            continue
        try:
            gt_path = _resolve_gt_path(mid)
        except FileNotFoundError as e:
            results[mid] = {
                "status": SubmissionStatus.ERROR.value,
                "score": None,
                "error_message": str(e),
            }
            continue

        results[mid] = evaluate_task1(pred_path=pred_file, gt_path=gt_path)

    return results


def _evaluate_task2_batch(
    submission_dir: str,
    gap_rows: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Evaluate all gap-filling predictions in submission/task2/."""
    task2_dir = os.path.join(submission_dir, "task2")
    results: Dict[str, Any] = {}

    for row in gap_rows:
        gap_id    = row["gap_id"]
        motion_id = row["motion_id"]
        joint_name = row["joint_name"]
        start_frame = int(row["start_frame"])
        end_frame   = int(row["end_frame"])

        pred_file = os.path.join(task2_dir, f"{gap_id}_filled.bvh")
        if not os.path.isfile(pred_file):
            results[gap_id] = {
                "status": SubmissionStatus.REJECTED.value,
                "score": None,
                "error_message": f"Missing prediction file: {os.path.basename(pred_file)}",
            }
            continue

        try:
            gt_path = _resolve_gt_path(motion_id)
        except FileNotFoundError as e:
            results[gap_id] = {
                "status": SubmissionStatus.ERROR.value,
                "score": None,
                "error_message": str(e),
            }
            continue

        results[gap_id] = evaluate_task2(
            pred_path=pred_file,
            gt_path=gt_path,
            joint_name=joint_name,
            start_frame=start_frame,
            end_frame=end_frame,
        )

    return results


def _evaluate_task3_batch(
    submission_dir: str,
    motion_ids: List[str],
) -> Dict[str, Any]:
    """Evaluate all retargeting predictions in submission/task3/."""
    task3_dir = os.path.join(submission_dir, "task3")
    results: Dict[str, Any] = {}

    for mid in motion_ids:
        for target in RETARGETING_TARGETS:
            key       = f"{mid}_{target}"
            pred_file = os.path.join(task3_dir, f"{key}_retargeted.bvh")

            if not os.path.isfile(pred_file):
                results[key] = {
                    "status": SubmissionStatus.REJECTED.value,
                    "score": None,
                    "error_message": f"Missing prediction file: {os.path.basename(pred_file)}",
                }
                continue

            try:
                src_path = _resolve_gt_path(mid)   # source clean BVH
            except FileNotFoundError as e:
                results[key] = {
                    "status": SubmissionStatus.ERROR.value,
                    "score": None,
                    "error_message": str(e),
                }
                continue

            results[key] = evaluate_task3(
                pred_path=pred_file,
                src_path=src_path,
                target_type=target,
            )

    return results


# ---------------------------------------------------------------------------
# Score aggregation helpers
# ---------------------------------------------------------------------------

def _aggregate_task_score(task_results: Dict[str, Any]) -> Optional[float]:
    """
    Compute mean score across all evaluated submissions for a task.
    Only VALID results with a non-None score contribute.
    Returns None if no valid results.
    """
    scores = [
        r["score"] for r in task_results.values()
        if r.get("status") == SubmissionStatus.VALID.value and r.get("score") is not None
    ]
    if not scores:
        return None
    return sum(scores) / len(scores)


# ---------------------------------------------------------------------------
# Full submission evaluator
# ---------------------------------------------------------------------------

def evaluate_submission(
    submission_dir: str,
    submission_id: Optional[str] = None,
    motion_ids: Optional[List[str]] = None,
    evaluate_tasks: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Evaluate a full participant submission directory.

    Parameters
    ----------
    submission_dir : Path to participant submission folder
    submission_id  : Unique ID (auto-generated if None)
    motion_ids     : List of motion IDs to evaluate (default: HIDDEN_MOTION_IDS)
    evaluate_tasks : Which tasks to run, e.g. [1, 2, 3] (default: all)

    Returns
    -------
    Full evaluation result dict (suitable for write_result / build_evaluation_result).
    """
    t0 = time.perf_counter()

    if submission_id is None:
        submission_id = str(uuid.uuid4())

    if motion_ids is None:
        motion_ids = HIDDEN_MOTION_IDS

    if evaluate_tasks is None:
        evaluate_tasks = [1, 2, 3]

    task1_results: Dict[str, Any] = {}
    task2_results: Dict[str, Any] = {}
    task3_results: Dict[str, Any] = {}

    # --- Task 1 ---
    if 1 in evaluate_tasks:
        task1_results = _evaluate_task1_batch(submission_dir, motion_ids)

    # --- Task 2 ---
    if 2 in evaluate_tasks:
        gap_rows = load_gap_metadata(motion_ids)
        task2_results = _evaluate_task2_batch(submission_dir, gap_rows)

    # --- Task 3 ---
    if 3 in evaluate_tasks:
        task3_results = _evaluate_task3_batch(submission_dir, motion_ids)

    # --- Aggregate task scores ---
    t1_score = _aggregate_task_score(task1_results) if 1 in evaluate_tasks else None
    t2_score = _aggregate_task_score(task2_results) if 2 in evaluate_tasks else None
    t3_score = _aggregate_task_score(task3_results) if 3 in evaluate_tasks else None

    overall_info = compute_overall_score(t1_score, t2_score, t3_score)
    overall_score = overall_info.get("overall_score")

    # Determine top-level status
    any_error    = any(
        r.get("status") == SubmissionStatus.ERROR.value
        for results in [task1_results, task2_results, task3_results]
        for r in results.values()
    )
    any_rejected = any(
        r.get("status") == SubmissionStatus.REJECTED.value
        for results in [task1_results, task2_results, task3_results]
        for r in results.values()
    )

    if any_error:
        top_status = SubmissionStatus.ERROR
    elif any_rejected:
        top_status = SubmissionStatus.REJECTED
    else:
        top_status = SubmissionStatus.VALID

    runtime_seconds = time.perf_counter() - t0

    result = build_evaluation_result(
        submission_id=submission_id,
        status=top_status,
        overall_score=overall_score,
        task_scores={
            "denoising":   t1_score,
            "gap_filling": t2_score,
            "retargeting": t3_score,
        },
        metrics={
            "task1_denoising":   task1_results,
            "task2_gap_filling": task2_results,
            "task3_retargeting": task3_results,
        },
        runtime_seconds=runtime_seconds,
        error_message=None,
        evaluator_version=MOTIONFORGE_EVALUATOR_VERSION,
        metric_version=MOTIONFORGE_METRIC_VERSION,
        calibration_version=MOTIONFORGE_CALIBRATION_VERSION,
        extra={"overall_score_info": overall_info},
    )

    return result
