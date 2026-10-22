import os
import sys
import glob
import json
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Optional, Dict, Any

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from backend.services.runner_service import runner_service
from runner.runner_config import RunnerConfig

router = APIRouter(prefix="/api/runner", tags=["Competition Runner"])

@router.get("/config")
def get_runner_config():
    """
    Returns Phase 6 Runner and Competition Configuration.
    """
    cfg = RunnerConfig.load()
    return {
        "competition_name": cfg.competition_name,
        "contract_version": cfg.contract_version,
        "scoring_weights": cfg.scoring_weights,
        "timeout_seconds": cfg.timeout_seconds,
        "max_archive_size_mb": cfg.max_archive_size_mb,
    }

@router.get("/results")
def list_results():
    """
    Lists past runner result artifacts.
    """
    return runner_service.list_recent_results()

@router.get("/results/{filename}")
def get_result(filename: str):
    """
    Get full JSON details of a specific runner evaluation.
    """
    res = runner_service.get_result_detail(filename)
    if not res:
        raise HTTPException(status_code=404, detail=f"Result file {filename} not found")
    return res
