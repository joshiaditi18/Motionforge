from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from backend.services.accuracy_service import accuracy_service

router = APIRouter(prefix="/api/accuracy", tags=["Accuracy Lab"])

class CompareRequest(BaseModel):
    task: str = Field(..., description="denoising, gap_filling, or retargeting")
    motion_id: str = Field("MF001", description="Motion identifier (e.g. MF001)")
    method_baseline: Optional[str] = Field(None, description="Baseline algorithm ID")
    method_experimental: Optional[str] = Field(None, description="Experimental algorithm ID")
    noise_level: Optional[str] = Field("MEDIUM", description="LOW, MEDIUM, HIGH (Task 1)")
    gap_type: Optional[str] = Field("MEDIUM", description="SHORT, MEDIUM, LONG (Task 2)")
    target_type: Optional[str] = Field("target_tall", description="target_small, target_medium, target_tall (Task 3)")

@router.get("/methods")
def get_methods():
    """
    Returns the catalog of available baseline and experimental algorithms across all 3 tasks.
    """
    return accuracy_service.get_available_methods()

@router.post("/compare")
def compare_algorithms(req: CompareRequest):
    """
    Executes on-demand comparative evaluation between Baseline and Experimental algorithms
    on identical authorized inputs. Computes official Phase 4 metrics, score deltas,
    per-frame error dynamics curves, and problematic frame/joint diagnostics.
    """
    try:
        t = req.task.lower()
        if t == "denoising":
            m_base = req.method_baseline or "baseline_savgol"
            m_exp = req.method_experimental or "butterworth"
            return accuracy_service.compare_denoising(
                motion_id=req.motion_id,
                noise_level=req.noise_level or "MEDIUM",
                method_baseline=m_base,
                method_experimental=m_exp
            )
        elif t == "gap_filling":
            m_base = req.method_baseline or "natural_cubic"
            m_exp = req.method_experimental or "clamped_hermite"
            return accuracy_service.compare_gap_filling(
                motion_id=req.motion_id,
                gap_type=req.gap_type or "MEDIUM",
                method_baseline=m_base,
                method_experimental=m_exp
            )
        elif t == "retargeting":
            m_base = req.method_baseline or "baseline"
            m_exp = req.method_experimental or "contact_aware"
            return accuracy_service.compare_retargeting(
                motion_id=req.motion_id,
                target_type=req.target_type or "target_tall",
                method_baseline=m_base,
                method_experimental=m_exp
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported task: '{req.task}'. Must be denoising, gap_filling, or retargeting.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/benchmarks")
def get_benchmarks():
    """
    Retrieves full reproducible benchmark suite results across all tasks and noise/gap/avatar configurations.
    """
    res = accuracy_service.get_benchmark_results()
    if res.get("status") == "not_run":
        raise HTTPException(status_code=404, detail="Benchmark results not found. Run benchmark_runner.py first.")
    return res
