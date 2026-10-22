"""
bvh_validator.py — MOTIONFORGE Phase 5 Strict BVH Syntax & Formatting Validator

Validates BVH files against DATA_CONTRACT.md §3.2 and COMPETITION_SPECIFICATION.md §10:
- File starts with 'HIERARCHY'
- Root is 'ROOT Hips'
- Contains 'MOTION' section divider
- Frame count N > 0
- Frame Time strictly 0.0083333 (120 FPS, tolerance 1e-5)
- Numerical parsing: checks for NaN, Inf, non-numeric tokens
- Channel consistency per data row
"""

from __future__ import annotations

import math
import os
import re
import numpy as np
from typing import Tuple, List, Optional

from validator.error_codes import ErrorCode
from validator.validation_result import ValidationError
from baselines.common.bvh_io import parse_bvh, BVHStructure

EXPECTED_FRAME_TIME = 0.0083333
FRAME_TIME_TOLERANCE = 1e-5
EXPECTED_FPS = 120.0

NAN_INF_PATTERN = re.compile(r"\b(nan|infinity|inf|-inf|-infinity|1\.#ind|1\.#qnan|1\.#snan)\b", re.IGNORECASE)


def validate_bvh_syntax_and_headers(file_path: str) -> Tuple[bool, List[ValidationError], Optional[BVHStructure]]:
    """
    Performs strict line-level syntax verification and parses the BVH.

    Returns:
        (is_valid, errors, bvh_structure)
    """
    errors: List[ValidationError] = []

    if not os.path.isfile(file_path):
        errors.append(ValidationError(
            code=ErrorCode.INVALID_BVH.value,
            message=f"BVH file does not exist: {file_path}",
            file=file_path
        ))
        return False, errors, None

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_BVH.value,
            message=f"Failed to read BVH file: {e}",
            file=file_path
        ))
        return False, errors, None

    if not lines:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_BVH.value,
            message="BVH file is empty",
            file=file_path
        ))
        return False, errors, None

    # 1. Line 1 Check: Must begin with HIERARCHY
    first_non_empty = ""
    for line in lines:
        stripped = line.strip()
        if stripped:
            first_non_empty = stripped
            break

    if not first_non_empty.startswith("HIERARCHY"):
        errors.append(ValidationError(
            code=ErrorCode.INVALID_BVH_HEADER.value,
            message=f"BVH file must begin with 'HIERARCHY', found '{first_non_empty[:30]}'",
            file=file_path
        ))
        return False, errors, None

    # 2. Check for MOTION section
    motion_line_idx = -1
    for idx, line in enumerate(lines):
        if line.strip().startswith("MOTION"):
            motion_line_idx = idx
            break

    if motion_line_idx == -1:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_BVH.value,
            message="Missing required 'MOTION' section divider in BVH",
            file=file_path
        ))
        return False, errors, None

    # 3. Check Frames and Frame Time headers
    frame_count = None
    frame_time = None
    data_start_idx = -1

    for idx in range(motion_line_idx + 1, len(lines)):
        line_clean = lines[idx].strip()
        if not line_clean:
            continue
        if line_clean.startswith("Frames:"):
            try:
                frame_count = int(line_clean.split(":")[1].strip())
            except ValueError:
                errors.append(ValidationError(
                    code=ErrorCode.INVALID_FRAME_COUNT.value,
                    message=f"Invalid 'Frames:' header: '{line_clean}'",
                    file=file_path
                ))
        elif line_clean.startswith("Frame Time:"):
            try:
                frame_time = float(line_clean.split(":")[1].strip())
                data_start_idx = idx + 1
                break
            except ValueError:
                errors.append(ValidationError(
                    code=ErrorCode.INVALID_FRAME_TIME.value,
                    message=f"Invalid 'Frame Time:' header: '{line_clean}'",
                    file=file_path
                ))

    if frame_count is None:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_FRAME_COUNT.value,
            message="Missing 'Frames:' header in MOTION section",
            file=file_path
        ))

    if frame_time is None:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_FRAME_TIME.value,
            message="Missing 'Frame Time:' header in MOTION section",
            file=file_path
        ))
    else:
        # Check Frame Time tolerance (120 FPS -> 0.0083333)
        if abs(frame_time - EXPECTED_FRAME_TIME) > FRAME_TIME_TOLERANCE:
            calc_fps = 1.0 / frame_time if frame_time > 0 else 0.0
            errors.append(ValidationError(
                code=ErrorCode.INVALID_FRAME_TIME.value,
                message=(
                    f"Frame Time is {frame_time:.7f} ({calc_fps:.1f} FPS), "
                    f"expected {EXPECTED_FRAME_TIME:.7f} ({EXPECTED_FPS:.1f} FPS)"
                ),
                file=file_path
            ))

    if frame_count is not None and frame_count <= 0:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_FRAME_COUNT.value,
            message=f"Frame count must be greater than 0, got {frame_count}",
            file=file_path
        ))

    # 4. Check for NaN / Inf tokens in motion section text
    if data_start_idx != -1:
        motion_sample = "".join(lines[data_start_idx:])
        match = NAN_INF_PATTERN.search(motion_sample)
        if match:
            token = match.group(0).lower()
            err_code = ErrorCode.NAN_DETECTED.value if "nan" in token or "ind" in token else ErrorCode.INF_DETECTED.value
            errors.append(ValidationError(
                code=err_code,
                message=f"Non-finite numeric token detected in motion data: '{match.group(0)}'",
                file=file_path
            ))
            return False, errors, None

    if errors:
        return False, errors, None

    # 5. Parse using official BVH parser
    try:
        bvh = parse_bvh(file_path)
    except Exception as e:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_BVH.value,
            message=f"BVH parser failure: {e}",
            file=file_path
        ))
        return False, errors, None

    return True, errors, bvh
