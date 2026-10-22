"""
baselines/generate_outputs.py — Generates Phase 3 baseline reference outputs
for regression testing and verification.
"""
import os
import sys
import csv

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from baselines.denoising.baseline_denoising import run_denoising
from baselines.gap_filling.baseline_gap_filling import run_gap_filling
from baselines.retargeting.baseline_retargeting import retarget_motion

def generate_baseline_outputs(motion_id="MF001"):
    out_dir = os.path.join(WORKSPACE_ROOT, "baselines", "outputs")
    os.makedirs(os.path.join(out_dir, "denoising"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "gap_filling"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "retargeting"), exist_ok=True)

    # 1. Task 1: Denoising
    for lvl in ["LOW", "MEDIUM", "HIGH"]:
        inp = os.path.join(WORKSPACE_ROOT, "MOTIONFORGE_DATASET", "public", "denoising", f"{motion_id}_{lvl}.bvh")
        out = os.path.join(out_dir, "denoising", f"{motion_id}_{lvl}_denoised.bvh")
        if os.path.exists(inp):
            run_denoising(inp, out, lvl)

    # 2. Task 2: Gap Filling
    meta_path = os.path.join(WORKSPACE_ROOT, "MOTIONFORGE_DATASET", "metadata", "gap_metadata.csv")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["motion_id"] == motion_id:
                    inp = os.path.join(WORKSPACE_ROOT, "MOTIONFORGE_DATASET", row["output_file"])
                    gid = row["gap_id"]
                    out = os.path.join(out_dir, "gap_filling", f"{gid}_filled.bvh")
                    if os.path.exists(inp):
                        run_gap_filling(
                            inp,
                            out,
                            int(row["start_frame"]),
                            int(row["end_frame"]),
                            joint_name=row["joint_name"],
                            method="cubic"
                        )

    # 3. Task 3: Retargeting
    src = os.path.join(WORKSPACE_ROOT, "MOTIONFORGE_DATASET", "clean", "bvh", f"{motion_id}_clean.bvh")
    if os.path.exists(src):
        for tgt in ["small", "medium", "tall"]:
            out = os.path.join(out_dir, "retargeting", f"{motion_id}_{tgt}_retargeted.bvh")
            retarget_motion(src, out, f"target_{tgt}")

    print(f"Baseline outputs generated for {motion_id} in {out_dir}")

if __name__ == "__main__":
    generate_baseline_outputs()
