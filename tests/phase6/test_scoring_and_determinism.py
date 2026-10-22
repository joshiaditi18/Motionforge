"""
test_scoring_and_determinism.py — Tests verifying determinism, scoring weights, and code non-execution
"""

import os
import shutil
import zipfile
import pytest

from runner.competition_runner import run_competition
from runner.job_manager import JobStatus
from baselines.retargeting.baseline_retargeting import TARGET_CONFIGS, retarget_hierarchy_offsets
from baselines.common.bvh_io import parse_bvh, write_bvh

_CLEAN_BVH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh"
)


def _prepare_valid_zip(zip_path: str, motion_id: str = "MF001"):
    bvh = parse_bvh(_CLEAN_BVH)
    staging = os.path.join(os.path.dirname(zip_path), "stage_det")
    os.makedirs(os.path.join(staging, "denoising"), exist_ok=True)
    os.makedirs(os.path.join(staging, "gap_filling"), exist_ok=True)
    os.makedirs(os.path.join(staging, "retargeting"), exist_ok=True)

    for lvl in ["low", "medium", "high"]:
        shutil.copyfile(_CLEAN_BVH, os.path.join(staging, "denoising", f"{motion_id}_{lvl}.bvh"))
    for gt in ["short", "medium", "long"]:
        shutil.copyfile(_CLEAN_BVH, os.path.join(staging, "gap_filling", f"{motion_id}_{gt}.bvh"))
    for tgt in ["target_small", "target_medium", "target_tall"]:
        nh = retarget_hierarchy_offsets(bvh, TARGET_CONFIGS[tgt])
        out_f = os.path.join(staging, "retargeting", f"{motion_id}_{tgt}.bvh")
        write_bvh(out_f, nh, bvh.frame_time, bvh.motion_data)

    with zipfile.ZipFile(zip_path, "w") as zf:
        for root, _, files in os.walk(staging):
            for file in files:
                full_p = os.path.join(root, file)
                zf.write(full_p, os.path.relpath(full_p, staging))

    shutil.rmtree(staging, ignore_errors=True)


def test_determinism_identical_runs(tmp_path):
    zip_path = str(tmp_path / "det_sub.zip")
    _prepare_valid_zip(zip_path, motion_id="MF001")

    code1, res1 = run_competition(
        submission_path=zip_path,
        run_id="det_job_1",
        output_dir=str(tmp_path / "r1"),
        motion_ids=["MF001"],
        quiet=True,
    )
    code2, res2 = run_competition(
        submission_path=zip_path,
        run_id="det_job_2",
        output_dir=str(tmp_path / "r2"),
        motion_ids=["MF001"],
        quiet=True,
    )

    assert code1 == code2 == 0
    assert res1["job_status"] == res2["job_status"] == JobStatus.COMPLETED.value
    assert res1["overall_score"] == pytest.approx(res2["overall_score"], abs=1e-6)
    assert res1["task_scores"] == pytest.approx(res2["task_scores"], abs=1e-6)


def test_three_task_scoring_weights_30_30_40(tmp_path):
    zip_path = str(tmp_path / "weights_sub.zip")
    _prepare_valid_zip(zip_path, motion_id="MF001")

    code, res = run_competition(
        submission_path=zip_path,
        output_dir=str(tmp_path / "results"),
        motion_ids=["MF001"],
        quiet=True,
    )

    assert code == 0
    t1 = res["task_scores"]["denoising"]
    t2 = res["task_scores"]["gap_filling"]
    t3 = res["task_scores"]["retargeting"]

    expected_overall = 0.30 * t1 + 0.30 * t2 + 0.40 * t3
    assert res["overall_score"] == pytest.approx(expected_overall, abs=1e-4)


def test_single_task_evaluation_supported(tmp_path):
    zip_path = str(tmp_path / "single_task_sub.zip")
    _prepare_valid_zip(zip_path, motion_id="MF001")

    code, res = run_competition(
        submission_path=zip_path,
        tasks=[1],
        output_dir=str(tmp_path / "results"),
        motion_ids=["MF001"],
        quiet=True,
    )

    assert code == 0
    assert res["task_scores"]["denoising"] is not None
    assert res["task_scores"]["gap_filling"] is None
    assert res["task_scores"]["retargeting"] is None
    # For single task, normalized weight = 1.0
    assert res["overall_score"] == pytest.approx(res["task_scores"]["denoising"], abs=1e-4)


def test_no_participant_code_executed(tmp_path):
    # Construct archive with a prohibited python script that attempts to create a marker file
    marker_file = tmp_path / "marker_pwned.txt"
    zip_path = tmp_path / "exploit.zip"

    script_content = f"import os\nwith open(r'{str(marker_file)}', 'w') as f: f.write('PWNED')\n"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("denoising/MF001_low.bvh", "HIERARCHY\n")
        zf.writestr("denoising/exploit.py", script_content)

    exit_code, res = run_competition(
        submission_path=str(zip_path),
        output_dir=str(tmp_path / "results"),
        quiet=True,
    )

    # Must be rejected by validator due to forbidden file type (.py)
    assert exit_code == 1
    assert res["job_status"] == JobStatus.REJECTED.value
    # Marker file must NEVER exist
    assert not marker_file.exists()
