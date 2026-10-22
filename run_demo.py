"""
run_demo.py — MOTIONFORGE Interactive Motion-Capture Demo Launcher

Starts the FastAPI server serving the Three.js + React frontend and
motion capture processing backend at http://127.0.0.1:8000.
"""

import os
import sys
import webbrowser
import uvicorn

WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

def main():
    print("=" * 70)
    print(" MOTIONFORGE — 3D Motion Capture Engineering Demonstration")
    print(" Clean. Complete. Retarget.")
    print("=" * 70)
    print("  * Web Interface & API: http://127.0.0.1:8000")
    print("  * API Docs:            http://127.0.0.1:8000/docs")
    print("  * 3D Viewport:         Dual Skeleton (Side-by-Side & Superimposed Overlay)")
    print("  * Real Execution:      Task 1 Denoising, Task 2 Gap Filling, Task 3 Retargeting")
    print("  * Official Scoring:    Phase 4 Evaluator & Phase 5 Validator Integrated")
    print("=" * 70)

    url = "http://127.0.0.1:8000"
    try:
        webbrowser.open(url)
    except Exception:
        pass

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    main()
