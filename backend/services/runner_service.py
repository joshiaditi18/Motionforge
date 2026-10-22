import os
import sys
import glob
import json
from typing import Dict, Any, Optional, List

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from runner.competition_runner import run_competition
from runner.job_manager import JobStatus

RUNNER_RESULTS_DIR = os.path.join(WORKSPACE_ROOT, "runner_results")

class RunnerService:
    def __init__(self):
        os.makedirs(RUNNER_RESULTS_DIR, exist_ok=True)

    def run_submission(self, submission_path: str, submission_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes Phase 6 Local Competition Runner on a submission archive or folder.
        Runs Phase 5 Validator, Phase 4 Evaluator, and writes output artifact.
        """
        exit_code, result = run_competition(
            submission_path=submission_path,
            submission_id=submission_id,
            out_directory=RUNNER_RESULTS_DIR,
            quiet=True
        )
        return {
            "exit_code": exit_code,
            "result": result
        }

    def list_recent_results(self) -> List[Dict[str, Any]]:
        """
        Lists all past runner result artifacts.
        """
        results = []
        files = glob.glob(os.path.join(RUNNER_RESULTS_DIR, "result_*.json"))
        # Sort by modification time descending
        files.sort(key=os.path.getmtime, reverse=True)

        for fpath in files[:20]:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    results.append({
                        "file": os.path.basename(fpath),
                        "timestamp": data.get("timestamp"),
                        "job_id": data.get("job_id"),
                        "submission_id": data.get("submission_id"),
                        "status": data.get("status"),
                        "overall_score": data.get("scores", {}).get("overall_score") if "scores" in data else None,
                        "validation_status": data.get("validation", {}).get("status") if "validation" in data else None,
                    })
            except Exception:
                continue
        return results

    def get_result_detail(self, filename: str) -> Optional[Dict[str, Any]]:
        fpath = os.path.join(RUNNER_RESULTS_DIR, filename)
        if os.path.exists(fpath) and os.path.isfile(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

runner_service = RunnerService()
