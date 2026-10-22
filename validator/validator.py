"""
validator.py — MOTIONFORGE Phase 5 Official Submission Validator Orchestrator & CLI

Integrates all validation stages:
    Archive -> Security -> Schema -> BVH -> Skeleton -> Motion -> Task
Returns exactly one of: VALID, REJECTED, ERROR.
Exit codes: 0 (VALID), 1 (REJECTED), 2 (ERROR).
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
import traceback
from typing import Optional, Dict, Any, List

_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from validator.error_codes import ErrorCode
from validator.validation_result import ValidationResult, ValidationStatus, ValidationError
from validator.archive_validator import validate_archive
from validator.security_validator import safe_extract_zip
from validator.schema_validator import validate_submission_schema, locate_task_directory
from validator.bvh_validator import validate_bvh_syntax_and_headers
from validator.skeleton_validator import validate_skeleton
from validator.motion_validator import validate_motion
from validator.task_validator import (
    validate_task1_denoising,
    validate_task2_gap_filling,
    validate_task3_retargeting,
)
from baselines.common.bvh_io import parse_bvh

_DATASET_ROOT = os.path.join(_PROJECT_ROOT, "MOTIONFORGE_DATASET")
_CLEAN_BVH_DIR = os.path.join(_DATASET_ROOT, "clean", "bvh")
_HIDDEN_GT_DIR = os.path.join(_DATASET_ROOT, "hidden", "ground_truth")
_GAP_META_PATH = os.path.join(_DATASET_ROOT, "metadata", "gap_metadata.csv")


def _load_gap_metadata_map() -> Dict[str, Dict[str, Any]]:
    """Loads gap intervals from gap_metadata.csv indexed by gap_id."""
    mapping = {}
    if os.path.isfile(_GAP_META_PATH):
        import csv
        try:
            with open(_GAP_META_PATH, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    gap_id = row.get("gap_id", "").lower()
                    if gap_id:
                        mapping[gap_id] = {
                            "start_frame": int(row["start_frame"]),
                            "end_frame": int(row["end_frame"]),
                            "joint_name": row["joint_name"],
                        }
        except Exception:
            pass
    return mapping


def _find_clean_reference(motion_id: str) -> Optional[str]:
    """Find corresponding clean BVH from hidden or clean directory if available."""
    hidden_candidate = os.path.join(_HIDDEN_GT_DIR, f"{motion_id}_clean.bvh")
    if os.path.isfile(hidden_candidate):
        return hidden_candidate
    clean_candidate = os.path.join(_CLEAN_BVH_DIR, f"{motion_id}_clean.bvh")
    if os.path.isfile(clean_candidate):
        return clean_candidate
    return None


def validate_submission(
    submission_path: str,
    task: Optional[str] = None,
    submission_id: Optional[str] = None,
    output_path: Optional[str] = None,
    motion_ids: Optional[List[str]] = None,
) -> ValidationResult:
    """
    Main validation pipeline executing all validation stages deterministically.

    Parameters:
        submission_path: Path to participant .zip archive or extracted directory
        task: Optional task filter ('denoising', 'gap_filling', 'retargeting', or None for all)
        submission_id: Optional custom identifier
        output_path: Optional path to save result JSON
        motion_ids: Optional list of evaluation motion IDs

    Returns:
        ValidationResult object
    """
    t0 = time.perf_counter()
    sub_id = submission_id or os.path.splitext(os.path.basename(submission_path))[0]
    result = ValidationResult(submission_id=sub_id, task=task)

    temp_dir: Optional[str] = None
    try:
        working_dir = submission_path

        # -------------------------------------------------------------
        # STAGE 1: Archive & Security Validation (if ZIP file)
        # -------------------------------------------------------------
        if os.path.isfile(submission_path) or submission_path.lower().endswith(".zip"):
            ok_arc, arc_errs, arc_warns = validate_archive(submission_path)
            for w in arc_warns:
                result.add_warning(w)

            if not ok_arc:
                result.set_check("archive", "FAIL")
                for err in arc_errs:
                    result.add_error(err.code, err.message, err.file)
                return result
            result.set_check("archive", "PASS")

            # Extract archive to safe temporary directory
            temp_dir = tempfile.mkdtemp(prefix="mf_val_")
            ok_extract, ext_errs = safe_extract_zip(submission_path, temp_dir)
            if not ok_extract:
                result.set_check("security", "FAIL")
                for err in ext_errs:
                    result.add_error(err.code, err.message, err.file)
                return result
            result.set_check("security", "PASS")
            working_dir = temp_dir
        else:
            if not os.path.isdir(submission_path):
                result.set_check("archive", "FAIL")
                result.add_error(
                    ErrorCode.ARCHIVE_NOT_FOUND,
                    f"Submission path does not exist: '{submission_path}'"
                )
                return result
            result.set_check("archive", "SKIP")
            result.set_check("security", "PASS")

        # Handle nested root folder in archive (e.g. submission/ inside zip)
        extracted_entries = [e for e in os.listdir(working_dir) if not e.startswith("__MACOSX")]
        known_task_dirs = {"denoising", "gap_filling", "retargeting", "task1", "task2", "task3"}
        if len(extracted_entries) == 1 and extracted_entries[0].lower() not in known_task_dirs:
            nested_candidate = os.path.join(working_dir, extracted_entries[0])
            if os.path.isdir(nested_candidate):
                working_dir = nested_candidate

        # -------------------------------------------------------------
        # STAGE 2: Schema Validation (Directory layout & required files)
        # -------------------------------------------------------------
        ok_schema, schema_errs, schema_warns, file_summary, task_files_map = validate_submission_schema(
            submission_dir=working_dir,
            target_task=task,
            motion_ids=motion_ids
        )
        result.file_summary = file_summary
        for w in schema_warns:
            result.add_warning(w)

        if not ok_schema:
            result.set_check("schema", "FAIL")
            for err in schema_errs:
                result.add_error(err.code, err.message, err.file)
            # If critical schema errors (e.g. missing folder), return early
            if any(e.code == ErrorCode.MISSING_REQUIRED_DIRECTORY.value for e in schema_errs):
                return result
        else:
            result.set_check("schema", "PASS")

        # -------------------------------------------------------------
        # STAGE 3, 4, 5, 6: BVH, Skeleton, Motion & Task Validation
        # -------------------------------------------------------------
        bvh_failed = False
        skeleton_failed = False
        motion_failed = False
        task_failed = False
        gap_map = _load_gap_metadata_map()

        # Gather all BVH files from task_files_map
        for task_name, bvh_paths in task_files_map.items():
            for bvh_path in bvh_paths:
                file_rel = os.path.relpath(bvh_path, working_dir)

                # 3. BVH Syntax & Headers
                ok_bvh, bvh_errs, bvh_struct = validate_bvh_syntax_and_headers(bvh_path)
                if not ok_bvh or bvh_struct is None:
                    bvh_failed = True
                    for err in bvh_errs:
                        result.add_error(err.code, err.message, file_rel)
                    continue

                # 4. Skeleton Validation
                ok_skel, skel_errs = validate_skeleton(bvh_struct, file_path=file_rel)
                if not ok_skel:
                    skeleton_failed = True
                    for err in skel_errs:
                        result.add_error(err.code, err.message, file_rel)

                # Extract motion_id from filename (e.g. MF004 from MF004_low.bvh or MF004_denoised.bvh)
                basename = os.path.basename(bvh_path)
                motion_id = basename.split("_")[0] if "_" in basename else basename.split(".")[0]

                clean_ref_path = _find_clean_reference(motion_id)
                ref_struct: Optional[Any] = None
                expected_frames: Optional[int] = None
                if clean_ref_path and os.path.isfile(clean_ref_path):
                    try:
                        ref_struct = parse_bvh(clean_ref_path)
                        expected_frames = ref_struct.frame_count
                    except Exception:
                        pass

                # 5. Motion Matrix & Numerical Validity
                ok_mot, mot_errs = validate_motion(
                    bvh_struct,
                    expected_frame_count=expected_frames,
                    file_path=file_rel
                )
                if not ok_mot:
                    motion_failed = True
                    for err in mot_errs:
                        result.add_error(err.code, err.message, file_rel)

                # 6. Task-Specific Invariants
                if task_name == "denoising":
                    ok_t1, t1_errs = validate_task1_denoising(bvh_struct, ref_struct, file_path=file_rel)
                    if not ok_t1:
                        task_failed = True
                        for err in t1_errs:
                            result.add_error(err.code, err.message, file_rel)

                elif task_name == "gap_filling":
                    gap_info = None
                    gap_stem = os.path.splitext(basename)[0].lower()
                    for gid, info in gap_map.items():
                        if gid in gap_stem:
                            gap_info = info
                            break

                    start_f = gap_info["start_frame"] if gap_info else None
                    end_f = gap_info["end_frame"] if gap_info else None

                    # Task 2 requires untouched observed frames check
                    ok_t2, t2_errs = validate_task2_gap_filling(
                        bvh_struct,
                        bvh_ref=ref_struct,
                        start_frame=start_f,
                        end_frame=end_f,
                        file_path=file_rel
                    )
                    if not ok_t2:
                        task_failed = True
                        for err in t2_errs:
                            result.add_error(err.code, err.message, file_rel)

                elif task_name == "retargeting":
                    # Determine target type from filename (e.g. MF004_target_small.bvh -> target_small)
                    target_candidate = "target_medium"
                    for t_opt in ["target_small", "target_tall", "target_medium", "small", "tall", "medium"]:
                        if t_opt in basename.lower():
                            target_candidate = t_opt
                            break

                    ok_t3, t3_errs = validate_task3_retargeting(
                        bvh_struct,
                        target_type=target_candidate,
                        bvh_src=ref_struct,
                        file_path=file_rel
                    )
                    if not ok_t3:
                        task_failed = True
                        for err in t3_errs:
                            result.add_error(err.code, err.message, file_rel)

        result.set_check("bvh", "FAIL" if bvh_failed else "PASS")
        result.set_check("skeleton", "FAIL" if skeleton_failed else "PASS")
        result.set_check("motion", "FAIL" if motion_failed else "PASS")
        result.set_check("task", "FAIL" if task_failed else "PASS")

    except Exception as exc:
        result.status = ValidationStatus.ERROR
        result.add_error(
            ErrorCode.INTERNAL_VALIDATION_ERROR,
            f"Internal validator failure: {exc}\n{traceback.format_exc()}"
        )
    finally:
        # Safe cleanup of temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    result.runtime_seconds = time.perf_counter() - t0

    # Write output JSON if requested
    if output_path:
        try:
            out_dir = os.path.dirname(os.path.abspath(output_path))
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.to_json(indent=2))
        except Exception as e:
            result.add_warning(f"Failed to write output report to '{output_path}': {e}")

    return result


def format_validation_summary(result: ValidationResult) -> str:
    """Format human-readable CLI summary matching prompt §25."""
    lines = [
        "=" * 50,
        "MOTIONFORGE SUBMISSION VALIDATION",
        "=" * 50,
        f"Submission ID : {result.submission_id}",
        f"Task          : {result.task or 'all'}",
        f"Runtime       : {result.runtime_seconds:.4f}s",
        "",
        "Validation Checks:",
    ]
    for check_name, status in result.checks.items():
        dots = "." * max(2, 20 - len(check_name))
        lines.append(f"  {check_name.capitalize()} {dots} {status}")

    lines.append("")
    lines.append(f"Files Found   : {result.file_summary.get('total_files_found', 0)}")
    lines.append(f"STATUS        : {result.status.value}")
    lines.append(f"EXIT CODE     : {result.get_exit_code()}")

    if result.errors:
        lines.append("")
        lines.append("ERRORS:")
        for err in result.errors[:10]:
            loc = f" [{err.file}]" if err.file else ""
            lines.append(f"  - {err.code}: {err.message}{loc}")
        if len(result.errors) > 10:
            lines.append(f"  ... and {len(result.errors) - 10} more error(s)")

    if result.warnings:
        lines.append("")
        lines.append("WARNINGS:")
        for w in result.warnings[:5]:
            lines.append(f"  - {w}")

    lines.append("=" * 50)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="MOTIONFORGE Official Submission Validator v0.1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # Support both --submission (prompt §25) and --submission_path (DATA_CONTRACT §4.1)
    parser.add_argument(
        "--submission", "--submission_path",
        dest="submission",
        required=True,
        help="Path to submission archive (.zip) or uncompressed directory."
    )
    parser.add_argument(
        "--task",
        choices=["denoising", "gap_filling", "retargeting", "all"],
        default=None,
        help="Target task to validate (default: validate all)."
    )
    parser.add_argument(
        "--submission-id", "--submission_id",
        dest="submission_id",
        default=None,
        help="Unique identifier for the submission."
    )
    parser.add_argument(
        "--output", "--output_report",
        dest="output",
        default=None,
        help="Path to save validation result JSON file."
    )
    parser.add_argument(
        "--manifest-path", "--manifest_path",
        dest="manifest_path",
        default=None,
        help="Path to dataset manifest JSON (optional)."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress human-readable summary output to stdout."
    )
    parser.add_argument(
        "--version",
        action="version",
        version="MOTIONFORGE Validator v0.1.0 (Contract v1.0.0)"
    )

    args = parser.parse_args()

    result = validate_submission(
        submission_path=args.submission,
        task=args.task if args.task != "all" else None,
        submission_id=args.submission_id,
        output_path=args.output,
    )

    if not args.quiet:
        print(format_validation_summary(result))

    sys.exit(result.get_exit_code())


if __name__ == "__main__":
    main()
