import os
import sys
import pytest

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["competition"] == "MOTIONFORGE"
    assert "denoising" in data["tasks"]

def test_api_list_motions(client):
    res = client.get("/api/motions")
    assert res.status_code == 200
    motions = res.json()
    assert len(motions) == 30
    assert motions[0]["motion_id"] == "MF001"
    assert motions[0]["joint_count"] == 31

def test_api_filter_motions_by_category(client):
    res = client.get("/api/motions?category=Walking")
    assert res.status_code == 200
    motions = res.json()
    assert len(motions) > 0
    assert all("walk" in m["category"].lower() for m in motions)

def test_api_get_bvh(client):
    res = client.get("/api/motions/MF001/bvh?variant=clean")
    assert res.status_code == 200
    assert "HIERARCHY" in res.text
    assert "MOTION" in res.text
    assert "Frames:" in res.text

def test_api_gap_metadata(client):
    res = client.get("/api/tasks/gap_metadata")
    assert res.status_code == 200
    gaps = res.json()
    assert "MF001_medium" in gaps
    assert gaps["MF001_medium"]["joint_name"] == "Head"

def test_api_task1_denoising(client):
    res = client.post("/api/tasks/denoising", json={"motion_id": "MF001", "noise_level": "LOW"})
    assert res.status_code == 200
    data = res.json()
    assert data["task"] == "denoising"
    assert data["status"] == "VALID"
    assert "mpjpe" in data["metrics"]
    assert "jitter_reduction_pct" in data["metrics"]
    assert data["score"] > 0.0

def test_api_task2_gap_filling(client):
    res = client.post("/api/tasks/gap_filling", json={"motion_id": "MF001", "gap_type": "SHORT", "method": "cubic"})
    assert res.status_code == 200
    data = res.json()
    assert data["task"] == "gap_filling"
    assert data["status"] == "VALID"
    assert "inpainting_mpjpe" in data["metrics"]
    assert data["score"] > 0.0

def test_api_task3_retargeting(client):
    res = client.post("/api/tasks/retargeting", json={"motion_id": "MF001", "target_type": "target_medium"})
    assert res.status_code == 200
    data = res.json()
    assert data["task"] == "retargeting"
    assert data["status"] == "VALID"
    assert "end_effector_error" in data["metrics"]
    assert data["score"] > 0.0

def test_api_runner_config(client):
    res = client.get("/api/runner/config")
    assert res.status_code == 200
    data = res.json()
    assert data["competition_name"] == "MOTIONFORGE"
    assert data["scoring_weights"]["denoising"] == 0.3
    assert data["scoring_weights"]["gap_filling"] == 0.3
    assert data["scoring_weights"]["retargeting"] == 0.4

def test_api_accuracy_methods(client):
    res = client.get("/api/accuracy/methods")
    assert res.status_code == 200
    data = res.json()
    assert "denoising" in data
    assert "gap_filling" in data
    assert "retargeting" in data
    assert any(m["id"] == "adaptive_savgol" for m in data["denoising"])
    assert any(m["id"] == "pchip" for m in data["gap_filling"])
    assert any(m["id"] == "contact_aware" for m in data["retargeting"])

def test_api_accuracy_compare_denoising(client):
    res = client.post("/api/accuracy/compare", json={
        "task": "denoising",
        "motion_id": "MF001",
        "method_baseline": "baseline_savgol",
        "method_experimental": "butterworth",
        "noise_level": "LOW"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["task"] == "denoising"
    assert "score_baseline" in data
    assert "score_experimental" in data
    assert "error_curve" in data
    assert len(data["error_curve"]) > 0
    assert "diagnostics" in data
    assert "worst_joint" in data["diagnostics"]

def test_api_accuracy_benchmarks(client):
    res = client.get("/api/accuracy/benchmarks")
    assert res.status_code == 200
    data = res.json()
    assert "task1_denoising" in data
    assert "task2_gap_filling" in data
    assert "task3_retargeting" in data
