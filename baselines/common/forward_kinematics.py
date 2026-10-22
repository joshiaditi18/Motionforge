import numpy as np

"""
MOTIONFORGE — baselines/common/forward_kinematics.py
Computes forward kinematics (FK) for the 31-joint MOTIONFORGE hierarchy.
Transforms local Z-Y-X Euler angles and translations into global 3D coordinates.
"""

def euler_zyx_to_matrix(z_deg, y_deg, x_deg):
    """
    Computes 3x3 rotation matrix for Z-Y-X intrinsic Euler angles (degrees).
    R = Rz(z) * Ry(y) * Rx(x)
    """
    zr = np.radians(z_deg)
    yr = np.radians(y_deg)
    xr = np.radians(x_deg)

    cz, sz = np.cos(zr), np.sin(zr)
    cy, sy = np.cos(yr), np.sin(yr)
    cx, sx = np.cos(xr), np.sin(xr)

    # Rz * Ry * Rx
    # Row-column expanded product:
    R = np.array([
        [cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
        [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
        [-sy,     cy * sx,                cy * cx]
    ], dtype=np.float64)
    return R

def compute_forward_kinematics(bvh_struct, include_end_sites=False):
    """
    Computes global 3D positions for all joints across all frames.
    Args:
        bvh_struct: Parsed BVHStructure instance
        include_end_sites: Whether to include the 7 terminal End Sites
    Returns:
        positions: np.ndarray shape (N, num_joints, 3)
        joint_names: List of joint names corresponding to axis 1
    """
    motion = bvh_struct.motion_data
    num_frames = motion.shape[0]

    nodes_to_eval = bvh_struct.nodes if include_end_sites else [n for n in bvh_struct.nodes if not n.is_end_site]
    joint_names = [n.name for n in nodes_to_eval]
    num_joints = len(joint_names)

    # Output array: (N, J, 3)
    positions = np.zeros((num_frames, num_joints, 3), dtype=np.float64)

    # Pre-index nodes
    node_to_idx = {n.name: i for i, n in enumerate(nodes_to_eval)}

    # Batch process frames
    for t in range(num_frames):
        frame_vals = motion[t]

        # Cache global transform per node: {node_name: (global_R, global_pos)}
        transforms = {}

        for node in bvh_struct.nodes:
            if node.is_root:
                # 6 channels: Xpos Ypos Zpos Zrot Yrot Xrot
                c = node.channel_indices
                pos = frame_vals[c[0]:c[3]]
                z, y, x = frame_vals[c[3]], frame_vals[c[4]], frame_vals[c[5]]
                R = euler_zyx_to_matrix(z, y, x)
                transforms[node.name] = (R, pos)
                if node.name in node_to_idx:
                    positions[t, node_to_idx[node.name]] = pos
            elif node.is_end_site:
                parent_R, parent_pos = transforms[node.parent.name]
                pos = parent_pos + parent_R.dot(node.offset)
                transforms[node.name] = (parent_R, pos)
                if include_end_sites and node.name in node_to_idx:
                    positions[t, node_to_idx[node.name]] = pos
            else:
                parent_R, parent_pos = transforms[node.parent.name]
                c = node.channel_indices
                z, y, x = frame_vals[c[0]], frame_vals[c[1]], frame_vals[c[2]]
                local_R = euler_zyx_to_matrix(z, y, x)
                global_R = parent_R.dot(local_R)
                global_pos = parent_pos + parent_R.dot(node.offset)
                transforms[node.name] = (global_R, global_pos)
                if node.name in node_to_idx:
                    positions[t, node_to_idx[node.name]] = global_pos

    return positions, joint_names
