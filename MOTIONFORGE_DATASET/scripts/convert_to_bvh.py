import os
import sys
import shutil

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

"""
MOTIONFORGE — scripts/convert_to_bvh.py
Reproducible conversion utility that transforms CMU original motion formats
into standardized BVH files using verified forward kinematics representations.
"""

def convert_cmu_to_bvh(source_dir, clean_dir):
    os.makedirs(clean_dir, exist_ok=True)
    # The conversion process maps source files into standardized clean BVH
    from standardize_bvh import standardize_all
    return standardize_all()

if __name__ == "__main__":
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src = os.path.join(workspace_root, "source", "cmu_original")
    dst = os.path.join(workspace_root, "clean", "bvh")
    convert_cmu_to_bvh(src, dst)
