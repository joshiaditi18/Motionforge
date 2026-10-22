"""
motion_validator.py — MOTIONFORGE Phase 5 Motion Matrix & Numerical Validator

Validates motion array dimensions, frame properties, and floating-point validity:
- Array shape (N, 96)
- Frame count N > 0
- Non-empty motion data
- Floating point validity (strictly no NaN, Inf, -Inf)
- Frame count adherence to ground truth / reference sequence
"""

from __future__ import annotations

import numpy as np
from typing import Tuple, List, Optional

from validator.error_codes import ErrorCode
from validator.validation_result import ValidationError
from baselines.common.bvh_io import BVHStructure

EXPECTED_CHANNELS = 96


def validate_motion(
    bvh: BVHStructure,
    expected_frame_count: Optional[int] = None,
    file_path: Optional[str] = None
) -> Tuple[bool, List[ValidationError]]:
    """
    Validates that a BVH structure contains well-formed, non-empty, finite motion data
    matching expected dimensions and frame counts.

    Returns:
        (is_valid, errors)
    """
    errors: List[ValidationError] = []

    # 1. Existence of motion data
    if bvh.motion_data is None or not isinstance(bvh.motion_data, np.ndarray):
        errors.append(ValidationError(
            code=ErrorCode.EMPTY_MOTION_DATA.value,
            message="BVH motion data array is missing or not a numpy ndarray",
            file=file_path
        ))
        return False, errors

    # 2. Dimensions and shape
    if bvh.motion_data.ndim != 2:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_MOTION_SHAPE.value,
            message=f"Motion array has {bvh.motion_data.ndim} dimensions, expected exactly 2",
            file=file_path
        ))
        return False, errors

    frames, channels = bvh.motion_data.shape

    if frames == 0:
        errors.append(ValidationError(
            code=ErrorCode.EMPTY_MOTION_DATA.value,
            message="Motion array contains 0 frames",
            file=file_path
        ))
        return False, errors

    if channels != EXPECTED_CHANNELS:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_CHANNEL_COUNT.value,
            message=f"Motion data has {channels} channels per frame, expected {EXPECTED_CHANNELS}",
            file=file_path
        ))

    # Consistency with bvh.frame_count
    if frames != bvh.frame_count:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_FRAME_COUNT.value,
            message=(
                f"Motion array row count ({frames}) does not match "
                f"BVH header 'Frames:' ({bvh.frame_count})"
            ),
            file=file_path
        ))

    # Consistency with reference frame count if provided
    if expected_frame_count is not None and frames != expected_frame_count:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_FRAME_COUNT.value,
            message=(
                f"Motion frame count ({frames}) does not match expected "
                f"reference frame count ({expected_frame_count})"
            ),
            file=file_path
        ))

    # 3. Finite numerical check (strictly no NaN or Inf)
    if np.isnan(bvh.motion_data).any():
        nan_indices = np.argwhere(np.isnan(bvh.motion_data))
        sample_loc = nan_indices[0].tolist() if len(nan_indices) > 0 else []
        errors.append(ValidationError(
            code=ErrorCode.NAN_DETECTED.value,
            message=f"Motion data contains {len(nan_indices)} NaN value(s), first at frame {sample_loc[0]} channel {sample_loc[1]}",
            file=file_path
        ))

    if np.isinf(bvh.motion_data).any():
        inf_indices = np.argwhere(np.isinf(bvh.motion_data))
        sample_loc = inf_indices[0].tolist() if len(inf_indices) > 0 else []
        errors.append(ValidationError(
            code=ErrorCode.INF_DETECTED.value,
            message=f"Motion data contains {len(inf_indices)} Inf value(s), first at frame {sample_loc[0]} channel {sample_loc[1]}",
            file=file_path
        ))

    return (len(errors) == 0), errors
