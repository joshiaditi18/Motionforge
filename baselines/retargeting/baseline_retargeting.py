import os
import sys
import argparse
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "common")))
from bvh_io import parse_bvh, write_bvh

"""
MOTIONFORGE — baselines/retargeting/baseline_retargeting.py
Baseline motion retargeting algorithm adapting clean source kinematics to
non-uniform target avatar morphologies (target_small, target_medium, target_tall).
"""

TARGET_CONFIGS = {
    "target_small": {
        "torso_scale": 0.82,
        "upper_arm_scale": 0.80,
        "forearm_scale": 0.82,
        "thigh_scale": 0.78,
        "shin_scale": 0.76,
        "foot_scale": 0.85
    },
    "target_medium": {
        "torso_scale": 0.95,
        "upper_arm_scale": 1.12,
        "forearm_scale": 1.15,
        "thigh_scale": 1.08,
        "shin_scale": 1.10,
        "foot_scale": 1.02
    },
    "target_tall": {
        "torso_scale": 1.25,
        "upper_arm_scale": 1.22,
        "forearm_scale": 1.28,
        "thigh_scale": 1.32,
        "shin_scale": 1.35,
        "foot_scale": 1.15
    }
}

TORSO_JOINTS = {'lowerback', 'spine', 'spine1', 'neck', 'neck1', 'head'}
UPPER_ARM_JOINTS = {'leftarm', 'rightarm', 'larm', 'rarm', 'leftshoulder', 'rightshoulder'}
FOREARM_JOINTS = {'leftforearm', 'rightforearm', 'lforearm', 'rforearm'}
THIGH_JOINTS = {'leftupleg', 'rightupleg', 'lupleg', 'rupleg'}
SHIN_JOINTS = {'leftleg', 'rightleg', 'lleg', 'rleg'}
FOOT_JOINTS = {'leftfoot', 'rightfoot', 'lefttoebase', 'righttoebase'}

def classify_joint(joint_name):
    j = joint_name.lower()
    if j in TORSO_JOINTS: return 'torso'
    elif j in UPPER_ARM_JOINTS: return 'upper_arm'
    elif j in FOREARM_JOINTS: return 'forearm'
    elif j in THIGH_JOINTS: return 'thigh'
    elif j in SHIN_JOINTS: return 'shin'
    elif j in FOOT_JOINTS: return 'foot'
    return 'other'

def retarget_hierarchy_offsets(bvh_struct, config):
    """
    Modifies local bone offset vectors according to non-uniform body proportion factors.
    """
    new_headers = []
    current_node = None

    for line in bvh_struct.raw_header_lines:
        parts = line.strip().split()
        if not parts:
            new_headers.append(line)
            continue
        token = parts[0]
        if token in ['ROOT', 'JOINT']:
            current_node = parts[1]
            new_headers.append(line)
        elif token == 'OFFSET':
            if current_node is None:
                new_headers.append(line)
                continue
            cat = classify_joint(current_node)
            scale = 1.0
            if cat == 'torso': scale = config['torso_scale']
            elif cat == 'upper_arm': scale = config['upper_arm_scale']
            elif cat == 'forearm': scale = config['forearm_scale']
            elif cat == 'thigh': scale = config['thigh_scale']
            elif cat == 'shin': scale = config['shin_scale']
            elif cat == 'foot': scale = config['foot_scale']

            ox, oy, oz = float(parts[1]), float(parts[2]), float(parts[3])
            nox, noy, noz = ox * scale, oy * scale, oz * scale

            indent = line[:len(line) - len(line.lstrip())]
            new_headers.append(f"{indent}OFFSET {nox:.5f} {noy:.5f} {noz:.5f}")
        else:
            new_headers.append(line)

    return new_headers

def retarget_motion(source_bvh_path, output_bvh_path, target_type="target_medium"):
    """
    Executes proportional motion retargeting from source BVH to target configuration.
    """
    if target_type not in TARGET_CONFIGS:
        raise ValueError(f"Unknown target type: {target_type}")

    cfg = TARGET_CONFIGS[target_type]
    bvh = parse_bvh(source_bvh_path)

    # 1. Update skeleton bone offsets in hierarchy
    retargeted_headers = retarget_hierarchy_offsets(bvh, cfg)

    # 2. Transfer rotation trajectories and adjust root height for leg length change
    retargeted_motion = bvh.motion_data.copy()
    leg_scale = (cfg['thigh_scale'] + cfg['shin_scale']) / 2.0
    # Channel 1 is Root Yposition
    retargeted_motion[:, 1] = retargeted_motion[:, 1] * leg_scale

    write_bvh(output_bvh_path, retargeted_headers, bvh.frame_time, retargeted_motion)
    return output_bvh_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MOTIONFORGE Baseline Motion Retargeting")
    parser.add_argument("--source", required=True, help="Path to source clean BVH")
    parser.add_argument("--output", required=True, help="Path to output retargeted BVH")
    parser.add_argument("--target", default="target_medium", choices=["target_small", "target_medium", "target_tall"])
    args = parser.parse_args()

    retarget_motion(args.source, args.output, args.target)
    print(f"Successfully generated retargeted motion: {args.output}")
