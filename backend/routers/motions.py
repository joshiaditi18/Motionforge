from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from typing import List, Optional
from backend.services.motion_service import motion_service

router = APIRouter(prefix="/api/motions", tags=["Motions"])

@router.get("", response_model=List[dict])
def list_motions(category: Optional[str] = None):
    """
    List all available motions with metadata, categories, duration, and supported tasks.
    """
    motions = motion_service.get_all_motions()
    if category and category.lower() != "all":
        motions = [m for m in motions if m["category"].lower() == category.lower()]
    return motions

@router.get("/{motion_id}")
def get_motion(motion_id: str):
    """
    Get detailed metadata for a single motion.
    """
    m = motion_service.get_motion_by_id(motion_id)
    if not m:
        raise HTTPException(status_code=404, detail=f"Motion {motion_id} not found")
    return m

@router.get("/{motion_id}/bvh", response_class=PlainTextResponse)
def get_motion_bvh(
    motion_id: str,
    variant: str = Query("clean", pattern="^(clean|denoising|gap_filling|retargeting)$"),
    subvariant: Optional[str] = Query(None)
):
    """
    Fetches raw BVH file text for 3D visualization.
    """
    path = motion_service.get_bvh_file_path(motion_id, variant=variant, subvariant=subvariant)
    if not path:
        raise HTTPException(status_code=404, detail=f"BVH not found for {motion_id} variant={variant} subvariant={subvariant}")
    return motion_service.read_bvh_text(path)
