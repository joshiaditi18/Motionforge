import os
import sys
import math
import numpy as np

"""
MOTIONFORGE — baselines/common/bvh_io.py
Robust, deterministic parser and serializer for the canonical 31-joint,
96-channel MOTIONFORGE BVH format (120 FPS, Z-Y-X Euler rotations).
"""

class BVHNode:
    def __init__(self, name, is_root=False, is_end_site=False, parent=None):
        self.name = name
        self.is_root = is_root
        self.is_end_site = is_end_site
        self.parent = parent
        self.children = []
        self.offset = np.zeros(3, dtype=np.float64)
        self.channels = []
        self.channel_indices = []

    def add_child(self, child):
        self.children.append(child)

class BVHStructure:
    def __init__(self):
        self.root = None
        self.nodes = []              # In traversal order
        self.joint_names = []        # Excluding End Sites
        self.node_by_name = {}
        self.num_channels = 0
        self.channel_names = []      # (joint_name, channel_type)
        self.frame_count = 0
        self.frame_time = 0.0083333
        self.motion_data = None      # np.ndarray shape (N, 96)
        self.raw_header_lines = []

def parse_bvh(filepath):
    """
    Parses a MOTIONFORGE BVH file into a structured representation.
    Returns:
        bvh: BVHStructure object
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"BVH file does not exist: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    bvh = BVHStructure()
    motion_line_idx = -1
    for idx, line in enumerate(lines):
        if line.strip().startswith('MOTION'):
            motion_line_idx = idx
            break
        bvh.raw_header_lines.append(line.rstrip('\r\n'))

    if motion_line_idx == -1:
        raise ValueError(f"No MOTION section found in BVH: {filepath}")

    # Parse hierarchy
    current_node = None
    channel_cursor = 0
    end_site_counter = 0

    for line in bvh.raw_header_lines:
        parts = line.strip().split()
        if not parts:
            continue
        token = parts[0]
        if token == 'ROOT':
            name = parts[1]
            node = BVHNode(name, is_root=True, parent=None)
            bvh.root = node
            bvh.nodes.append(node)
            bvh.joint_names.append(name)
            bvh.node_by_name[name] = node
            current_node = node
        elif token == 'JOINT':
            name = parts[1]
            node = BVHNode(name, is_root=False, parent=current_node)
            current_node.add_child(node)
            bvh.nodes.append(node)
            bvh.joint_names.append(name)
            bvh.node_by_name[name] = node
            current_node = node
        elif token == 'End':
            end_site_counter += 1
            name = f"End_Site_{end_site_counter}"
            node = BVHNode(name, is_end_site=True, parent=current_node)
            current_node.add_child(node)
            bvh.nodes.append(node)
            bvh.node_by_name[name] = node
            current_node = node
        elif token == '}':
            if current_node and current_node.parent:
                current_node = current_node.parent
        elif token == 'OFFSET':
            if current_node:
                current_node.offset = np.array([float(parts[1]), float(parts[2]), float(parts[3])], dtype=np.float64)
        elif token == 'CHANNELS':
            cnt = int(parts[1])
            ch_names = parts[2:2 + cnt]
            current_node.channels = ch_names
            current_node.channel_indices = list(range(channel_cursor, channel_cursor + cnt))
            for ch in ch_names:
                bvh.channel_names.append((current_node.name, ch))
            channel_cursor += cnt

    bvh.num_channels = channel_cursor

    # Parse MOTION metadata
    idx = motion_line_idx + 1
    while idx < len(lines):
        line = lines[idx].strip()
        idx += 1
        if line.startswith('Frames:'):
            bvh.frame_count = int(line.split(':')[1].strip())
        elif line.startswith('Frame Time:'):
            bvh.frame_time = float(line.split(':')[1].strip())
            break

    # Read frame values
    motion_rows = []
    while idx < len(lines):
        line = lines[idx].strip()
        idx += 1
        if not line:
            continue
        vals = [float(x) for x in line.split()]
        if len(vals) != bvh.num_channels:
            raise ValueError(f"Channel mismatch at frame {len(motion_rows)+1}: expected {bvh.num_channels}, got {len(vals)}")
        motion_rows.append(vals)

    bvh.motion_data = np.array(motion_rows, dtype=np.float64)
    if len(bvh.motion_data) != bvh.frame_count:
        bvh.frame_count = len(bvh.motion_data)

    return bvh

def write_bvh(out_path, bvh_or_headers, frame_time=None, motion_data=None):
    """
    Serializes motion data back into standard compliant BVH.
    Can be called with (out_path, bvh_obj) or (out_path, raw_header_lines, frame_time, motion_data).
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    if isinstance(bvh_or_headers, BVHStructure):
        headers = bvh_or_headers.raw_header_lines
        f_time = bvh_or_headers.frame_time
        data = bvh_or_headers.motion_data
    else:
        headers = bvh_or_headers
        f_time = frame_time if frame_time is not None else 0.0083333
        data = motion_data

    with open(out_path, 'w', encoding='utf-8') as f:
        indent = 0
        for line in headers:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped == '}':
                indent = max(0, indent - 1)
            f.write(('\t' * indent) + stripped + '\n')
            if stripped == '{':
                indent += 1

        f.write('MOTION\n')
        f.write(f'Frames: {len(data)}\n')
        f.write(f'Frame Time: {f_time:.7f}\n')

        for frame in data:
            row_str = " ".join(f"{val:.4f}" for val in frame)
            f.write(row_str + '\n')
