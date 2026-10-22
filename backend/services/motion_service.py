import os
import csv
import glob
from typing import List, Dict, Any, Optional
import numpy as np

# Path configurations relative to workspace root
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATASET_DIR = os.path.join(WORKSPACE_ROOT, "MOTIONFORGE_DATASET")
METADATA_CSV = os.path.join(WORKSPACE_ROOT, "metadata", "motions.csv")

class MotionService:
    def __init__(self):
        self._motions_cache: Optional[List[Dict[str, Any]]] = None

    def get_all_motions(self) -> List[Dict[str, Any]]:
        """
        Reads motions metadata from metadata/motions.csv.
        Returns a rich list of motion descriptors.
        """
        if self._motions_cache is not None:
            return self._motions_cache

        motions = []
        if os.path.exists(METADATA_CSV):
            with open(METADATA_CSV, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    motion_id = row["motion_id"]
                    # Check available files in dataset
                    clean_bvh = os.path.join(DATASET_DIR, "clean", "bvh", f"{motion_id}_clean.bvh")
                    has_clean = os.path.exists(clean_bvh)

                    # Public denoised, gap, retargeted files
                    denoising_files = {
                        "LOW": os.path.exists(os.path.join(DATASET_DIR, "public", "denoising", f"{motion_id}_low.bvh")),
                        "MEDIUM": os.path.exists(os.path.join(DATASET_DIR, "public", "denoising", f"{motion_id}_medium.bvh")),
                        "HIGH": os.path.exists(os.path.join(DATASET_DIR, "public", "denoising", f"{motion_id}_high.bvh"))
                    }

                    gap_files = {
                        "SHORT": os.path.exists(os.path.join(DATASET_DIR, "public", "gap_filling", f"{motion_id}_short.bvh")),
                        "MEDIUM": os.path.exists(os.path.join(DATASET_DIR, "public", "gap_filling", f"{motion_id}_medium.bvh")),
                        "LONG": os.path.exists(os.path.join(DATASET_DIR, "public", "gap_filling", f"{motion_id}_long.bvh"))
                    }

                    retarget_files = {
                        "target_small": os.path.exists(os.path.join(DATASET_DIR, "public", "retargeting", f"{motion_id}_target_small.bvh")),
                        "target_medium": os.path.exists(os.path.join(DATASET_DIR, "public", "retargeting", f"{motion_id}_target_medium.bvh")),
                        "target_tall": os.path.exists(os.path.join(DATASET_DIR, "public", "retargeting", f"{motion_id}_target_tall.bvh"))
                    }

                    category = self._categorize_motion(row["description"])

                    motions.append({
                        "motion_id": motion_id,
                        "description": row["description"],
                        "category": category,
                        "fps": float(row["fps"]),
                        "frame_count": int(row["frame_count"]),
                        "duration_seconds": float(row["duration_seconds"]),
                        "joint_count": int(row["joint_count"]),
                        "root_joint": row["root_joint"],
                        "has_clean": has_clean,
                        "available_tasks": {
                            "denoising": denoising_files,
                            "gap_filling": gap_files,
                            "retargeting": retarget_files
                        }
                    })

        self._motions_cache = motions
        return motions

    def get_motion_by_id(self, motion_id: str) -> Optional[Dict[str, Any]]:
        motions = self.get_all_motions()
        for m in motions:
            if m["motion_id"].upper() == motion_id.upper():
                return m
        return None

    def get_bvh_file_path(self, motion_id: str, variant: str = "clean", subvariant: Optional[str] = None) -> Optional[str]:
        """
        Locates the file path for a given motion ID and variant:
        - variant="clean" -> MOTIONFORGE_DATASET/clean/bvh/{id}_clean.bvh
        - variant="denoising" -> MOTIONFORGE_DATASET/public/denoising/{id}_{subvariant.lower()}.bvh
        - variant="gap_filling" -> MOTIONFORGE_DATASET/public/gap_filling/{id}_{subvariant.lower()}.bvh
        - variant="retargeting" -> MOTIONFORGE_DATASET/public/retargeting/{id}_{subvariant.lower()}.bvh
        """
        m_id = motion_id.upper()
        if variant == "clean":
            path = os.path.join(DATASET_DIR, "clean", "bvh", f"{m_id}_clean.bvh")
        elif variant == "denoising":
            lvl = (subvariant or "medium").lower()
            path = os.path.join(DATASET_DIR, "public", "denoising", f"{m_id}_{lvl}.bvh")
        elif variant == "gap_filling":
            lvl = (subvariant or "medium").lower()
            path = os.path.join(DATASET_DIR, "public", "gap_filling", f"{m_id}_{lvl}.bvh")
        elif variant == "retargeting":
            tgt = (subvariant or "target_medium").lower()
            if not tgt.startswith("target_"):
                tgt = f"target_{tgt}"
            path = os.path.join(DATASET_DIR, "public", "retargeting", f"{m_id}_{tgt}.bvh")
        else:
            path = None

        if path and os.path.exists(path):
            return path
        return None

    def read_bvh_text(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _categorize_motion(self, desc: str) -> str:
        d = desc.lower()
        if "walk" in d:
            return "Walking"
        elif "run" in d or "jog" in d:
            return "Running"
        elif "jump" in d or "hop" in d or "leap" in d:
            return "Jumping"
        elif "dance" in d or "salsa" in d or "charleston" in d:
            return "Dance"
        elif "kick" in d or "punch" in d or "cartwheel" in d or "ground" in d:
            return "Martial Arts & Acrobatics"
        return "Locomotion"

motion_service = MotionService()
