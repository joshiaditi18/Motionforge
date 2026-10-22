"""
task_validator.py — MOTIONFORGE Phase 5 Task-Specific Contract Validator

Validates task-specific invariants defined in docs/COMPETITION_SPECIFICATION.md §3:
- Task 1 (Denoising): Frame count matching, no quality gating (poor motion is VALID)
- Task 2 (Gap Filling): Contract invariant: unoccluded observed frames outside [start_frame, end_frame]
                       must remain strictly unmodified (L_inf <= 1e-6)
- Task 3 (Retargeting): Target morphology validity (target_small, target_medium, target_tall),
                       and bone-length adherence to assigned target proportions
"""

from __future__ import annotations

import numpy as np
from typing import Tuple, List, Optional, Dict, Any

from validator.error_codes import ErrorCode
from validator.validation_result import ValidationError
from baselines.common.bvh_io import BVHStructure
from baselines.common.skeleton_utils import get_bone_lengths
from baselines.retargeting.baseline_retargeting import TARGET_CONFIGS, classify_joint

OBSERVED_FRAME_TOLERANCE = 1e-6
BONE_LENGTH_TOLERANCE = 0.05  # inches tolerance for target rest bone scaling


def validate_task1_denoising(
    bvh_pred: BVHStructure,
    bvh_ref: Optional[BVHStructure] = None,
    file_path: Optional[str] = None
) -> Tuple[bool, List[ValidationError]]:
    """
    Validate Task 1 (Motion Denoising) specific contract requirements.
    Note: Does NOT evaluate reconstruction quality (MPJPE/velocity).
    """
    errors: List[ValidationError] = []

    if bvh_ref is not None:
        if bvh_pred.frame_count != bvh_ref.frame_count:
            errors.append(ValidationError(
                code=ErrorCode.INVALID_FRAME_COUNT.value,
                message=(
                    f"Task 1 frame count mismatch: output has {bvh_pred.frame_count} frames, "
                    f"reference has {bvh_ref.frame_count} frames"
                ),
                file=file_path
            ))

    return (len(errors) == 0), errors


def validate_task2_gap_filling(
    bvh_pred: BVHStructure,
    bvh_ref: Optional[BVHStructure] = None,
    start_frame: Optional[int] = None,
    end_frame: Optional[int] = None,
    file_path: Optional[str] = None
) -> Tuple[bool, List[ValidationError]]:
    """
    Validate Task 2 (Motion Gap Filling) specific contract requirements.
    Enforces contract invariant: observed frames outside [start_frame, end_frame]
    must remain strictly unmodified.
    """
    errors: List[ValidationError] = []

    if bvh_ref is not None:
        if bvh_pred.frame_count != bvh_ref.frame_count:
            errors.append(ValidationError(
                code=ErrorCode.INVALID_FRAME_COUNT.value,
                message=(
                    f"Task 2 frame count mismatch: output has {bvh_pred.frame_count} frames, "
                    f"reference has {bvh_ref.frame_count} frames"
                ),
                file=file_path
            ))
            return False, errors

        # Verify untouched observed frames invariant if interval is specified
        if start_frame is not None and end_frame is not None:
            num_frames = bvh_ref.frame_count
            mask_outside = np.ones(num_frames, dtype=bool)
            s_f = max(0, int(start_frame))
            e_f = min(num_frames - 1, int(end_frame))
            mask_outside[s_f:e_f + 1] = False

            if np.any(mask_outside):
                diff = np.abs(bvh_pred.motion_data[mask_outside] - bvh_ref.motion_data[mask_outside])
                max_diff = float(np.max(diff))
                if max_diff > OBSERVED_FRAME_TOLERANCE:
                    errors.append(ValidationError(
                        code=ErrorCode.OBSERVED_FRAME_MODIFIED.value,
                        message=(
                            f"Task 2 contract invariant violated: frames outside gap [{s_f}, {e_f}] "
                            f"were modified (max absolute difference = {max_diff:.6f} > {OBSERVED_FRAME_TOLERANCE})"
                        ),
                        file=file_path
                    ))

    return (len(errors) == 0), errors


def validate_task3_retargeting(
    bvh_pred: BVHStructure,
    target_type: str,
    bvh_src: Optional[BVHStructure] = None,
    file_path: Optional[str] = None
) -> Tuple[bool, List[ValidationError]]:
    """
    Validate Task 3 (Motion Retargeting) specific contract requirements:
    - Target morphology profile validity (target_small, target_medium, target_tall)
    - Target rest bone length scaling adherence in BVH header offsets
    - Frame count matching source motion
    """
    errors: List[ValidationError] = []

    # Normalize target type name
    canonical_target = target_type.lower()
    if not canonical_target.startswith("target_"):
        canonical_target = f"target_{canonical_target}"

    if canonical_target not in TARGET_CONFIGS:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_TARGET.value,
            message=f"Unknown target avatar morphology '{target_type}'. Expected one of: {list(TARGET_CONFIGS.keys())}",
            file=file_path
        ))
        return False, errors

    # Check frame count matches source
    if bvh_src is not None:
        if bvh_pred.frame_count != bvh_src.frame_count:
            errors.append(ValidationError(
                code=ErrorCode.INVALID_FRAME_COUNT.value,
                message=(
                    f"Task 3 frame count mismatch: retargeted motion has {bvh_pred.frame_count} frames, "
                    f"source motion has {bvh_src.frame_count} frames"
                ),
                file=file_path
            ))

        # Check bone lengths in retargeted header against assigned target configuration
        cfg = TARGET_CONFIGS[canonical_target]
        pred_bone_lens = get_bone_lengths(bvh_pred)

        for node in bvh_src.nodes:
            if not node.is_root and not node.is_end_site:
                cat = classify_joint(node.name)
                scale = 1.0
                if cat == "torso": scale = cfg["torso_scale"]
                elif cat == "upper_arm": scale = cfg["upper_arm_scale"]
                elif cat == "forearm": scale = cfg["forearm_scale"]
                elif cat == "thigh": scale = cfg["thigh_scale"]
                elif cat == "shin": scale = cfg["shin_scale"]
                elif cat == "foot": scale = cfg["foot_scale"]

                expected_len = float(np.linalg.norm(node.offset * scale))
                actual_len = pred_bone_lens.get(node.name, 0.0)
                dev = abs(actual_len - expected_len)
                if dev > BONE_LENGTH_TOLERANCE:
                    errors.append(ValidationError(
                        code=ErrorCode.BONE_LENGTH_VIOLATION.value,
                        message=(
                            f"Rest bone length for joint '{node.name}' ({actual_len:.3f}) "
                            f"violates target proportions ({expected_len:.3f}, diff={dev:.3f} > {BONE_LENGTH_TOLERANCE})"
                        ),
                        file=file_path
                    ))
                    break  # report first major bone violation to prevent error spam

    return (len(errors) == 0), errors
