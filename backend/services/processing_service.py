import os
import sys
import tempfile
import csv
from typing import Dict, Any, Optional

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import numpy as np
from baselines.common.bvh_io import parse_bvh, write_bvh
from baselines.denoising.baseline_denoising import denoise_motion_data, run_denoising
from baselines.gap_filling.baseline_gap_filling import inpaint_gap, detect_gap_interval, run_gap_filling
from baselines.retargeting.baseline_retargeting import retarget_motion, TARGET_CONFIGS
from baselines.common.skeleton_utils import CANONICAL_31_JOINTS
from evaluation.task_evaluator import evaluate_task1, evaluate_task2, evaluate_task3
from backend.services.motion_service import motion_service

DATASET_DIR = os.path.join(WORKSPACE_ROOT, "MOTIONFORGE_DATASET")
GAP_META_PATH = os.path.join(DATASET_DIR, "metadata", "gap_metadata.csv")

class ProcessingService:
    def __init__(self):
        self._gap_meta_cache = None

    def get_gap_metadata(self) -> Dict[str, Dict[str, Any]]:
        if self._gap_meta_cache is not None:
            return self._gap_meta_cache

        gaps = {}
        if os.path.exists(GAP_META_PATH):
            with open(GAP_META_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    gaps[row["gap_id"]] = {
                        "motion_id": row["motion_id"],
                        "gap_id": row["gap_id"],
                        "joint_name": row["joint_name"],
                        "start_frame": int(row["start_frame"]),
                        "end_frame": int(row["end_frame"]),
                        "gap_length": int(row["gap_length"]),
                        "gap_type": row["gap_type"],
                        "output_file": row["output_file"]
                    }
        self._gap_meta_cache = gaps
        return gaps

    def process_denoising(
        self,
        motion_id: str,
        noise_level: str = "MEDIUM",
        window_length: Optional[int] = None,
        polyorder: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Runs real baseline denoising on public noisy motion or custom filtered.
        Evaluates with Phase 4 evaluate_task1 against clean ground truth.
        """
        lvl = noise_level.upper()
        clean_path = motion_service.get_bvh_file_path(motion_id, variant="clean")
        noisy_path = motion_service.get_bvh_file_path(motion_id, variant="denoising", subvariant=lvl)

        if not clean_path or not os.path.exists(clean_path):
            raise FileNotFoundError(f"Clean ground truth BVH not found for {motion_id}")
        if not noisy_path or not os.path.exists(noisy_path):
            raise FileNotFoundError(f"Noisy input BVH not found for {motion_id} level {lvl}")

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as tmp_out:
            tmp_out_path = tmp_out.name

        try:
            # Execute actual denoising
            run_denoising(noisy_path, tmp_out_path, noise_level=lvl)

            # Evaluate with Phase 4 Evaluator
            eval_result = evaluate_task1(
                pred_path=tmp_out_path,
                gt_path=clean_path,
                noisy_path=noisy_path
            )

            # Read result BVH text
            with open(tmp_out_path, "r", encoding="utf-8") as f:
                processed_bvh = f.read()

            with open(noisy_path, "r", encoding="utf-8") as f:
                input_bvh = f.read()

            return {
                "task": "denoising",
                "motion_id": motion_id,
                "noise_level": lvl,
                "metrics": eval_result.get("metrics", {}),
                "score": round(eval_result.get("score") or 0.0, 2),
                "task_score": round(eval_result.get("score") or 0.0, 2),
                "status": eval_result.get("status", "ERROR"),
                "detail": eval_result.get("detail", {}),
                "input_bvh": input_bvh,
                "processed_bvh": processed_bvh
            }
        finally:
            if os.path.exists(tmp_out_path):
                os.remove(tmp_out_path)

    def process_gap_filling(
        self,
        motion_id: str,
        gap_type: str = "MEDIUM",
        custom_joint: Optional[str] = None,
        custom_start: Optional[int] = None,
        custom_end: Optional[int] = None,
        method: str = "cubic"
    ) -> Dict[str, Any]:
        """
        Runs real baseline gap-filling on gapped motion.
        Evaluates with Phase 4 evaluate_task2.
        """
        clean_path = motion_service.get_bvh_file_path(motion_id, variant="clean")
        if not clean_path or not os.path.exists(clean_path):
            raise FileNotFoundError(f"Clean ground truth BVH not found for {motion_id}")

        gaps = self.get_gap_metadata()
        gap_id = f"{motion_id}_{gap_type.lower()}"
        gap_info = gaps.get(gap_id)

        if gap_info:
            joint_name = custom_joint or gap_info["joint_name"]
            start_frame = custom_start if custom_start is not None else gap_info["start_frame"]
            end_frame = custom_end if custom_end is not None else gap_info["end_frame"]
            input_path = os.path.join(DATASET_DIR, gap_info["output_file"])
        else:
            joint_name = custom_joint or "Head"
            start_frame = custom_start or 30
            end_frame = custom_end or 60
            input_path = motion_service.get_bvh_file_path(motion_id, variant="gap_filling", subvariant=gap_type)

        if not input_path or not os.path.exists(input_path):
            # Fallback to standard gap path
            input_path = os.path.join(DATASET_DIR, "public", "gap_filling", f"{motion_id}_{gap_type.lower()}.bvh")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Gapped input BVH not found: {input_path}")

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as tmp_out:
            tmp_out_path = tmp_out.name

        try:
            # Execute actual gap filling
            run_gap_filling(
                input_bvh=input_path,
                output_bvh=tmp_out_path,
                start_frame=start_frame,
                end_frame=end_frame,
                joint_name=joint_name,
                method=method
            )

            # Evaluate with Phase 4 Evaluator
            eval_result = evaluate_task2(
                pred_path=tmp_out_path,
                gt_path=clean_path,
                joint_name=joint_name,
                start_frame=start_frame,
                end_frame=end_frame
            )

            with open(tmp_out_path, "r", encoding="utf-8") as f:
                processed_bvh = f.read()

            with open(input_path, "r", encoding="utf-8") as f:
                input_bvh = f.read()

            return {
                "task": "gap_filling",
                "motion_id": motion_id,
                "gap_type": gap_type,
                "gap_info": {
                    "joint_name": joint_name,
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    "length": end_frame - start_frame,
                    "method": method
                },
                "metrics": eval_result.get("metrics", {}),
                "score": round(eval_result.get("score") or 0.0, 2),
                "task_score": round(eval_result.get("score") or 0.0, 2),
                "status": eval_result.get("status", "ERROR"),
                "detail": eval_result.get("detail", {}),
                "input_bvh": input_bvh,
                "processed_bvh": processed_bvh
            }
        finally:
            if os.path.exists(tmp_out_path):
                os.remove(tmp_out_path)

    def process_retargeting(
        self,
        motion_id: str,
        target_type: str = "target_medium"
    ) -> Dict[str, Any]:
        """
        Runs real baseline motion retargeting to target avatar morphology.
        Evaluates with Phase 4 evaluate_task3.
        """
        clean_path = motion_service.get_bvh_file_path(motion_id, variant="clean")
        if not clean_path or not os.path.exists(clean_path):
            raise FileNotFoundError(f"Source clean BVH not found for {motion_id}")

        tgt = target_type.lower()
        if not tgt.startswith("target_"):
            tgt = f"target_{tgt}"
        clean_target = tgt.replace("target_", "")

        with tempfile.NamedTemporaryFile(suffix=".bvh", delete=False) as tmp_out:
            tmp_out_path = tmp_out.name

        try:
            # Execute actual retargeting
            retarget_motion(
                source_bvh_path=clean_path,
                output_bvh_path=tmp_out_path,
                target_type=tgt
            )

            # Evaluate with Phase 4 Evaluator
            eval_result = evaluate_task3(
                pred_path=tmp_out_path,
                src_path=clean_path,
                target_type=clean_target
            )

            with open(tmp_out_path, "r", encoding="utf-8") as f:
                processed_bvh = f.read()

            with open(clean_path, "r", encoding="utf-8") as f:
                input_bvh = f.read()

            return {
                "task": "retargeting",
                "motion_id": motion_id,
                "target_type": tgt,
                "target_config": TARGET_CONFIGS.get(tgt, {}),
                "metrics": eval_result.get("metrics", {}),
                "score": round(eval_result.get("score") or 0.0, 2),
                "task_score": round(eval_result.get("score") or 0.0, 2),
                "status": eval_result.get("status", "ERROR"),
                "detail": eval_result.get("detail", {}),
                "input_bvh": input_bvh,
                "processed_bvh": processed_bvh
            }
        finally:
            if os.path.exists(tmp_out_path):
                os.remove(tmp_out_path)

processing_service = ProcessingService()
