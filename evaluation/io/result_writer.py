"""
result_writer.py — MOTIONFORGE Phase 4 Result File Writer

Writes evaluation result dicts to JSON files with atomic write semantics.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Dict, Any

from .evaluation_schema import validate_result_schema


def write_result(result: Dict[str, Any], output_path: str, validate: bool = True) -> None:
    """
    Write an evaluation result dict to a JSON file.

    Uses atomic write (temp file + rename) to avoid partial writes.

    Parameters
    ----------
    result      : Evaluation result dict (from build_evaluation_result)
    output_path : Target .json file path
    validate    : If True, validate schema before writing (raises ValueError on error)
    """
    if validate:
        errors = validate_result_schema(result)
        if errors:
            raise ValueError(
                "Result schema validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Atomic write: write to temp then rename
    dir_ = os.path.dirname(os.path.abspath(output_path))
    fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp.json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, output_path)
    except Exception:
        # Clean up temp on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_result(path: str) -> Dict[str, Any]:
    """Read an evaluation result JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_result_summary(result: Dict[str, Any]) -> str:
    """Return a human-readable single-string summary of an evaluation result."""
    sid   = result.get("submission_id", "?")
    status = result.get("status", "?")
    overall = result.get("overall_score")
    ts = result.get("task_scores", {})

    lines = [
        f"{'='*60}",
        f"MOTIONFORGE Evaluation Result",
        f"  Submission : {sid}",
        f"  Status     : {status}",
        f"  Timestamp  : {result.get('timestamp', '?')}",
        f"  Runtime    : {result.get('runtime_seconds', 0):.2f}s",
        f"{'='*60}",
    ]

    if overall is not None:
        lines.append(f"  Overall Score : {overall:.2f} / 100")
    lines.append(f"  Task Scores:")
    for task, score in ts.items():
        score_str = f"{score:.2f}" if score is not None else "N/A"
        lines.append(f"    {task:<20}: {score_str}")

    err = result.get("error_message")
    if err:
        lines.append(f"  Error: {err}")

    lines.append("=" * 60)
    return "\n".join(lines)
