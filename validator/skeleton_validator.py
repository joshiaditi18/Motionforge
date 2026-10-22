"""
skeleton_validator.py — MOTIONFORGE Phase 5 Standardized Skeleton Validator

Validates BVH skeleton topology against DATA_CONTRACT.md §3.2 and Phase 1/2 standards:
- Root node is strictly 'Hips'
- Exactly 31 functional anatomical joints in canonical order
- Exactly 7 terminal End Sites
- Exactly 96 motion channels
- Canonical channel order:
    Root: Xposition, Yposition, Zposition, Zrotation, Yrotation, Xrotation
    Joints: Zrotation, Yrotation, Xrotation (Z-Y-X Euler angles)
- Valid parent-child anatomical hierarchy
- Rest offset vector validity (no NaN / Inf)
"""

from __future__ import annotations

import numpy as np
from typing import List, Tuple, Dict, Optional

from validator.error_codes import ErrorCode
from validator.validation_result import ValidationError
from baselines.common.skeleton_utils import CANONICAL_31_JOINTS
from baselines.common.bvh_io import BVHStructure

ROOT_CHANNELS = ["Xposition", "Yposition", "Zposition", "Zrotation", "Yrotation", "Xrotation"]
JOINT_CHANNELS = ["Zrotation", "Yrotation", "Xrotation"]

CANONICAL_PARENT_MAP: Dict[str, Optional[str]] = {
    "Hips": None,
    "LHipJoint": "Hips",
    "LeftUpLeg": "LHipJoint",
    "LeftLeg": "LeftUpLeg",
    "LeftFoot": "LeftLeg",
    "LeftToeBase": "LeftFoot",
    "RHipJoint": "Hips",
    "RightUpLeg": "RHipJoint",
    "RightLeg": "RightUpLeg",
    "RightFoot": "RightLeg",
    "RightToeBase": "RightFoot",
    "LowerBack": "Hips",
    "Spine": "LowerBack",
    "Spine1": "Spine",
    "Neck": "Spine1",
    "Neck1": "Neck",
    "Head": "Neck1",
    "LeftShoulder": "Spine1",
    "LeftArm": "LeftShoulder",
    "LeftForeArm": "LeftArm",
    "LeftHand": "LeftForeArm",
    "LeftFingerBase": "LeftHand",
    "LeftHandIndex1": "LeftFingerBase",
    "LThumb": "LeftHand",
    "RightShoulder": "Spine1",
    "RightArm": "RightShoulder",
    "RightForeArm": "RightArm",
    "RightHand": "RightForeArm",
    "RightFingerBase": "RightHand",
    "RightHandIndex1": "RightFingerBase",
    "RThumb": "RightHand"
}

CANONICAL_END_SITE_PARENTS = {
    "LeftToeBase", "RightToeBase", "Head",
    "LeftHandIndex1", "LThumb", "RightHandIndex1", "RThumb"
}


def validate_skeleton(bvh: BVHStructure, file_path: Optional[str] = None) -> Tuple[bool, List[ValidationError]]:
    """
    Validates that a BVH structure complies with the standardized 31-joint,
    96-channel MOTIONFORGE competition hierarchy.

    Returns:
        (is_valid, errors)
    """
    errors: List[ValidationError] = []

    # 1. Root joint validation
    if not bvh.root or bvh.root.name != "Hips":
        found_root = bvh.root.name if bvh.root else "None"
        errors.append(ValidationError(
            code=ErrorCode.INVALID_ROOT_JOINT.value,
            message=f"Root joint is '{found_root}', expected 'Hips'",
            file=file_path
        ))

    # 2. Functional joint count validation
    if len(bvh.joint_names) != 31:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_JOINT_COUNT.value,
            message=f"Joint count is {len(bvh.joint_names)}, expected exactly 31 functional joints",
            file=file_path
        ))

    # 3. Functional joint names and order validation
    for idx, expected_name in enumerate(CANONICAL_31_JOINTS):
        if idx >= len(bvh.joint_names):
            errors.append(ValidationError(
                code=ErrorCode.INVALID_JOINT_NAMES.value,
                message=f"Missing canonical joint at index {idx}: '{expected_name}'",
                file=file_path
            ))
        elif bvh.joint_names[idx] != expected_name:
            errors.append(ValidationError(
                code=ErrorCode.INVALID_JOINT_ORDER.value,
                message=(
                    f"Joint mismatch at index {idx}: found '{bvh.joint_names[idx]}', "
                    f"expected '{expected_name}'"
                ),
                file=file_path
            ))

    # 4. End Site count and parent validation
    end_sites = [n for n in bvh.nodes if n.is_end_site]
    if len(end_sites) != 7:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_END_SITE.value,
            message=f"End Site count is {len(end_sites)}, expected exactly 7 terminal End Sites",
            file=file_path
        ))
    else:
        end_site_parents = {n.parent.name for n in end_sites if n.parent}
        if end_site_parents != CANONICAL_END_SITE_PARENTS:
            diff = end_site_parents.symmetric_difference(CANONICAL_END_SITE_PARENTS)
            errors.append(ValidationError(
                code=ErrorCode.INVALID_END_SITE.value,
                message=f"End Site parent mismatch for joints: {diff}",
                file=file_path
            ))

    # 5. Channel count validation
    if bvh.num_channels != 96:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_CHANNEL_COUNT.value,
            message=f"Total channel count is {bvh.num_channels}, expected exactly 96",
            file=file_path
        ))

    # 6. Channel order validation
    if bvh.root and bvh.root.channels != ROOT_CHANNELS:
        errors.append(ValidationError(
            code=ErrorCode.INVALID_CHANNEL_ORDER.value,
            message=f"Root channel order is {bvh.root.channels}, expected {ROOT_CHANNELS}",
            file=file_path
        ))

    for node in bvh.nodes:
        if not node.is_root and not node.is_end_site:
            if node.channels != JOINT_CHANNELS:
                errors.append(ValidationError(
                    code=ErrorCode.INVALID_CHANNEL_ORDER.value,
                    message=f"Joint '{node.name}' channel order is {node.channels}, expected {JOINT_CHANNELS}",
                    file=file_path
                ))

    # 7. Parent-child hierarchy validation
    for node_name, expected_parent in CANONICAL_PARENT_MAP.items():
        if node_name in bvh.node_by_name:
            actual_node = bvh.node_by_name[node_name]
            actual_parent = actual_node.parent.name if actual_node.parent else None
            if actual_parent != expected_parent:
                errors.append(ValidationError(
                    code=ErrorCode.INVALID_HIERARCHY.value,
                    message=(
                        f"Hierarchy error for '{node_name}': parent is '{actual_parent}', "
                        f"expected '{expected_parent}'"
                    ),
                    file=file_path
                ))

    # 8. Offset vectors validity (check NaN / Inf in static offsets)
    for node in bvh.nodes:
        if np.isnan(node.offset).any() or np.isinf(node.offset).any():
            errors.append(ValidationError(
                code=ErrorCode.NAN_DETECTED.value,
                message=f"Non-finite offset values detected in node '{node.name}': {node.offset}",
                file=file_path
            ))

    return (len(errors) == 0), errors
