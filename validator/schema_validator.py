"""
schema_validator.py — MOTIONFORGE Phase 5 Submission Schema & File Layout Validator

Validates directory layout and required output files against DATA_CONTRACT.md §3.1:
- Required top-level task directories (denoising, gap_filling, retargeting)
- Optional submission metadata (metadata.json / submission.json)
- Correct file naming conventions and extensions (.bvh)
- Expected challenge file counts for evaluated motion IDs
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Tuple, Any, Optional, Set

from validator.error_codes import ErrorCode
from validator.validation_result import ValidationError

# Standard evaluation motions (9 hidden evaluation motions from Phase 1/2)
DEFAULT_EVALUATION_MOTIONS = [
    "MF002", "MF006", "MF007", "MF014",
    "MF020", "MF021", "MF025", "MF026", "MF027"
]

TASK_DIR_ALIASES = {
    "denoising": ["denoising", "task1"],
    "gap_filling": ["gap_filling", "task2"],
    "retargeting": ["retargeting", "task3"],
}

NOISE_LEVELS = ["low", "medium", "high", "LOW", "MEDIUM", "HIGH"]
GAP_TYPES = ["short", "medium", "long", "SHORT", "MEDIUM", "LONG"]
TARGET_TYPES = ["target_small", "target_medium", "target_tall", "small", "medium", "tall"]


def locate_task_directory(submission_dir: str, task_name: str) -> Optional[str]:
    """Find directory corresponding to task_name considering aliases."""
    aliases = TASK_DIR_ALIASES.get(task_name, [task_name])
    for alias in aliases:
        candidate = os.path.join(submission_dir, alias)
        if os.path.isdir(candidate):
            return candidate
    return None


def validate_submission_metadata(metadata_path: str) -> Tuple[bool, List[ValidationError]]:
    """Validate optional submission metadata JSON file."""
    errors: List[ValidationError] = []
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            errors.append(ValidationError(
                code=ErrorCode.INVALID_METADATA.value,
                message="Submission metadata root must be a JSON object",
                file=metadata_path
            ))
            return False, errors

        # Validate fields if present
        if "submission_id" in data and not isinstance(data["submission_id"], str):
            errors.append(ValidationError(
                code=ErrorCode.INVALID_METADATA.value,
                message="Field 'submission_id' in metadata must be a string",
                file=metadata_path
            ))

        if "tasks" in data:
            if not isinstance(data["tasks"], list):
                errors.append(ValidationError(
                    code=ErrorCode.INVALID_METADATA.value,
                    message="Field 'tasks' in metadata must be a list of task names",
                    file=metadata_path
                ))
            else:
                valid_tasks = {"denoising", "gap_filling", "retargeting", "task1", "task2", "task3"}
                for t in data["tasks"]:
                    if str(t).lower() not in valid_tasks:
                        errors.append(ValidationError(
                            code=ErrorCode.INVALID_TASK.value,
                            message=f"Unknown task identifier in metadata: '{t}'",
                            file=metadata_path
                        ))

    except json.JSONDecodeError as e:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_METADATA.value,
            message=f"Malformed metadata JSON syntax: {e}",
            file=metadata_path
        ))
    except Exception as e:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_METADATA.value,
            message=f"Error reading submission metadata: {e}",
            file=metadata_path
        ))

    return (len(errors) == 0), errors


def validate_submission_schema(
    submission_dir: str,
    target_task: Optional[str] = None,
    motion_ids: Optional[List[str]] = None
) -> Tuple[bool, List[ValidationError], List[str], Dict[str, Any], Dict[str, List[str]]]:
    """
    Validate submission folder layout and catalog task output files.

    Returns:
        (is_valid, errors, warnings, file_summary, task_files_map)
    """
    errors: List[ValidationError] = []
    warnings: List[str] = []
    eval_motions = motion_ids or DEFAULT_EVALUATION_MOTIONS

    tasks_to_validate = (
        [target_task.lower()] if target_task and target_task.lower() in TASK_DIR_ALIASES
        else ["denoising", "gap_filling", "retargeting"]
    )

    # 1. Check metadata file if present
    for meta_candidate in ["metadata.json", "submission.json"]:
        meta_file = os.path.join(submission_dir, meta_candidate)
        if os.path.isfile(meta_file):
            ok_meta, meta_errs = validate_submission_metadata(meta_file)
            if not ok_meta:
                errors.extend(meta_errs)

    file_summary: Dict[str, Any] = {
        "total_files_found": 0,
        "total_files_expected": 0,
        "denoising_files": 0,
        "gap_filling_files": 0,
        "retargeting_files": 0,
    }
    task_files_map: Dict[str, List[str]] = {
        "denoising": [],
        "gap_filling": [],
        "retargeting": []
    }

    # 2. Check each required task directory
    for t_name in tasks_to_validate:
        task_dir = locate_task_directory(submission_dir, t_name)
        if not task_dir:
            errors.append(ValidationError(
                code=ErrorCode.MISSING_REQUIRED_DIRECTORY.value,
                message=f"Missing required task directory '{t_name}/' in submission"
            ))
            continue

        # Inspect files in task directory
        try:
            entries = os.listdir(task_dir)
        except OSError as e:
            errors.append(ValidationError(
                code=ErrorCode.INTERNAL_VALIDATION_ERROR.value,
                message=f"Cannot list directory '{t_name}/': {e}"
            ))
            continue

        bvh_files = []
        for entry in entries:
            full_path = os.path.join(task_dir, entry)
            if os.path.isdir(full_path):
                warnings.append(f"Unexpected subdirectory inside task folder: '{t_name}/{entry}'")
                continue
            if not entry.lower().endswith(".bvh"):
                errors.append(ValidationError(
                    code=ErrorCode.UNEXPECTED_FILE.value,
                    message=f"Unexpected non-BVH file found in task directory: '{t_name}/{entry}'",
                    file=full_path
                ))
            else:
                bvh_files.append(full_path)

        task_files_map[t_name] = bvh_files
        count = len(bvh_files)

        if t_name == "denoising":
            file_summary["denoising_files"] = count
        elif t_name == "gap_filling":
            file_summary["gap_filling_files"] = count
        elif t_name == "retargeting":
            file_summary["retargeting_files"] = count

        file_summary["total_files_found"] += count

        # Check required files for evaluation motions
        # A valid submission must contain outputs for each requested evaluation motion
        found_basenames = [os.path.basename(f) for f in bvh_files]
        for mid in eval_motions:
            # Check if at least one file matches this motion_id
            motion_matches = [f for f in found_basenames if f.startswith(f"{mid}_") or f.startswith(f"{mid}.")]
            if not motion_matches:
                errors.append(ValidationError(
                    code=ErrorCode.MISSING_REQUIRED_FILE.value,
                    message=f"Missing required output for motion '{mid}' in task '{t_name}'"
                ))

    # Expected file calculation:
    # Each task expects at least 1 output per motion
    file_summary["total_files_expected"] = len(tasks_to_validate) * len(eval_motions)

    return (len(errors) == 0), errors, warnings, file_summary, task_files_map
