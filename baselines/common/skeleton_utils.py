import numpy as np

"""
MOTIONFORGE — baselines/common/skeleton_utils.py
Utilities for skeleton topology, bone-length extraction, joint mapping,
and end-effector identification across the canonical 31-joint hierarchy.
"""

CANONICAL_31_JOINTS = [
    'Hips', 'LHipJoint', 'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase',
    'RHipJoint', 'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase',
    'LowerBack', 'Spine', 'Spine1', 'Neck', 'Neck1', 'Head',
    'LeftShoulder', 'LeftArm', 'LeftForeArm', 'LeftHand', 'LeftFingerBase', 'LeftHandIndex1', 'LThumb',
    'RightShoulder', 'RightArm', 'RightForeArm', 'RightHand', 'RightFingerBase', 'RightHandIndex1', 'RThumb'
]

END_EFFECTOR_JOINTS = {
    'head': 'Head',
    'left_hand': 'LeftHandIndex1',
    'right_hand': 'RightHandIndex1',
    'left_foot': 'LeftToeBase',
    'right_foot': 'RightToeBase'
}

def get_bone_lengths(bvh_struct):
    """
    Computes static rest bone lengths from hierarchical offset vectors.
    Returns:
        dict: {joint_name: float_length}
    """
    lengths = {}
    for node in bvh_struct.nodes:
        if node.is_root:
            lengths[node.name] = 0.0
        else:
            lengths[node.name] = float(np.linalg.norm(node.offset))
    return lengths

def validate_skeleton_hierarchy(bvh_struct):
    """
    Verifies that a BVHStructure matches the canonical 31-joint MOTIONFORGE skeleton.
    Returns:
        (bool, list_of_errors)
    """
    errors = []
    if bvh_struct.root.name != 'Hips':
        errors.append(f"Root joint is '{bvh_struct.root.name}', expected 'Hips'")

    if len(bvh_struct.joint_names) != 31:
        errors.append(f"Joint count is {len(bvh_struct.joint_names)}, expected 31")

    for i, expected in enumerate(CANONICAL_31_JOINTS):
        if i >= len(bvh_struct.joint_names):
            errors.append(f"Missing expected joint: {expected}")
        elif bvh_struct.joint_names[i] != expected:
            errors.append(f"Joint mismatch at index {i}: found '{bvh_struct.joint_names[i]}', expected '{expected}'")

    if bvh_struct.num_channels != 96:
        errors.append(f"Total channel count is {bvh_struct.num_channels}, expected 96")

    return (len(errors) == 0), errors

def get_end_effector_indices(joint_names):
    """
    Returns dict mapping end-effector semantic names to array indices in joint_names list.
    """
    name_to_idx = {name: i for i, name in enumerate(joint_names)}
    ee_indices = {}
    for sem_name, j_name in END_EFFECTOR_JOINTS.items():
        if j_name in name_to_idx:
            ee_indices[sem_name] = name_to_idx[j_name]
    return ee_indices
