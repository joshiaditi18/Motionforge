"""
runner_config.py — MOTIONFORGE Phase 6 Local Competition Runner Configuration

Holds configuration defaults and loader for competition runner settings,
grounded in config/competition.yaml and frozen Phase 2 specifications.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import yaml

from evaluation.evaluator import HIDDEN_MOTION_IDS, PUBLIC_MOTION_IDS
from evaluation import (
    MOTIONFORGE_EVALUATOR_VERSION,
    MOTIONFORGE_METRIC_VERSION,
    MOTIONFORGE_CALIBRATION_VERSION,
)
from validator import MOTIONFORGE_VALIDATOR_VERSION, CONTRACT_VERSION

RUNNER_VERSION = "0.1.0"

OFFICIAL_SCORING_WEIGHTS: Dict[str, float] = {
    "denoising": 0.30,
    "gap_filling": 0.30,
    "retargeting": 0.40,
}


@dataclass
class RunnerConfig:
    competition_name: str = "MOTIONFORGE"
    runner_version: str = RUNNER_VERSION
    contract_version: str = CONTRACT_VERSION
    evaluator_version: str = MOTIONFORGE_EVALUATOR_VERSION
    validator_version: str = MOTIONFORGE_VALIDATOR_VERSION
    calibration_version: str = MOTIONFORGE_CALIBRATION_VERSION
    metric_version: str = MOTIONFORGE_METRIC_VERSION

    # Scoring weights (frozen Phase 2: 30% / 30% / 40%)
    scoring_weights: Dict[str, float] = field(
        default_factory=lambda: dict(OFFICIAL_SCORING_WEIGHTS)
    )

    # Motion sets
    hidden_motion_ids: List[str] = field(
        default_factory=lambda: list(HIDDEN_MOTION_IDS)
    )
    public_motion_ids: List[str] = field(
        default_factory=lambda: list(PUBLIC_MOTION_IDS)
    )

    # Runtime constraints
    timeout_seconds: float = 300.0
    memory_limit_mb: int = 8192
    max_archive_size_mb: int = 100
    network_access: bool = False
    allow_code_execution: bool = False  # Strictly False: runner processes output BVH only

    # Output defaults
    output_dir: str = "runner_results"
    cleanup_temp: bool = True

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> RunnerConfig:
        """Load configuration, optionally overlaying settings from competition.yaml."""
        instance = cls()
        if config_path and os.path.isfile(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}

                comp = data.get("competition", {})
                if "name" in comp:
                    instance.competition_name = str(comp["name"])

                runtime = data.get("runtime", {})
                if "timeout_seconds" in runtime and runtime["timeout_seconds"]:
                    instance.timeout_seconds = float(runtime["timeout_seconds"])
                if "memory_limit_mb" in runtime and runtime["memory_limit_mb"]:
                    instance.memory_limit_mb = int(runtime["memory_limit_mb"])
                if "max_archive_size_mb" in runtime and runtime["max_archive_size_mb"]:
                    instance.max_archive_size_mb = int(runtime["max_archive_size_mb"])

                scoring = data.get("scoring", {}).get("provisional_weights", {})
                if scoring:
                    w1 = float(scoring.get("denoising", 0.30))
                    w2 = float(scoring.get("gap_filling", 0.30))
                    w3 = float(scoring.get("retargeting", 0.40))
                    instance.scoring_weights = {
                        "denoising": w1,
                        "gap_filling": w2,
                        "retargeting": w3,
                    }
            except Exception:
                pass  # Fall back gracefully to defaults
        return instance
