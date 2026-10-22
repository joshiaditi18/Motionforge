from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from backend.services.processing_service import processing_service

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

class DenoisingRequest(BaseModel):
    motion_id: str = Field(..., description="Motion ID e.g. MF001")
    noise_level: str = Field("MEDIUM", description="LOW, MEDIUM, or HIGH")

class GapFillingRequest(BaseModel):
    motion_id: str = Field(..., description="Motion ID e.g. MF001")
    gap_type: str = Field("MEDIUM", description="SHORT, MEDIUM, or LONG")
    custom_joint: Optional[str] = Field(None, description="Custom occluded joint name")
    custom_start: Optional[int] = Field(None, description="Custom start frame")
    custom_end: Optional[int] = Field(None, description="Custom end frame")
    method: str = Field("cubic", description="cubic or linear")

class RetargetingRequest(BaseModel):
    motion_id: str = Field(..., description="Motion ID e.g. MF001")
    target_type: str = Field("target_medium", description="target_small, target_medium, target_tall")

@router.get("/gap_metadata")
def get_gap_metadata():
    """
    Returns ground truth gap metadata specifying joint, frame range, and difficulty for each motion.
    """
    return processing_service.get_gap_metadata()

@router.post("/denoising")
def run_denoising(req: DenoisingRequest):
    """
    Executes real Savitzky-Golay denoising with phase unwrapping on noisy motion
    and computes Phase 4 official evaluation metrics against clean ground truth.
    """
    try:
        return processing_service.process_denoising(
            motion_id=req.motion_id,
            noise_level=req.noise_level
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/gap_filling")
def run_gap_filling(req: GapFillingRequest):
    """
    Executes real cubic spline / linear inpainting on gapped motion while strictly
    preserving unoccluded frames, and evaluates with Phase 4 boundary and continuity metrics.
    """
    try:
        return processing_service.process_gap_filling(
            motion_id=req.motion_id,
            gap_type=req.gap_type,
            custom_joint=req.custom_joint,
            custom_start=req.custom_start,
            custom_end=req.custom_end,
            method=req.method
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.post("/retargeting")
def run_retargeting(req: RetargetingRequest):
    """
    Executes real kinematic retargeting to non-uniform avatar morphologies and computes
    bone invariance, end-effector position error, and angular deviation.
    """
    try:
        return processing_service.process_retargeting(
            motion_id=req.motion_id,
            target_type=req.target_type
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
