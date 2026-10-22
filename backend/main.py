import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from backend.routers import motions, tasks, runner_router, accuracy, demo

app = FastAPI(
    title="MOTIONFORGE Motion-Capture Platform API",
    description="Backend engine for MOTIONFORGE: Clean. Complete. Retarget.",
    version="1.0.0"
)

# Configure CORS for frontend Vite dev server (usually localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(motions.router)
app.include_router(tasks.router)
app.include_router(runner_router.router)
app.include_router(accuracy.router)
app.include_router(demo.router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "competition": "MOTIONFORGE",
        "tagline": "Clean. Complete. Retarget.",
        "version": "1.0.0",
        "tasks": ["denoising", "gap_filling", "retargeting"]
    }

# Mount static build files if frontend/dist exists
frontend_dist = os.path.join(WORKSPACE_ROOT, "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
