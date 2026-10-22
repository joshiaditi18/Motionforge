"""
MOTIONFORGE — Local Competition Runner
Package: runner
Version: 0.1.0
Contract: 1.0.0
"""

from runner.runner_config import (
    RUNNER_VERSION,
    OFFICIAL_SCORING_WEIGHTS,
    RunnerConfig,
)
from runner.job_manager import (
    Job,
    JobStatus,
    InvalidStateTransitionError,
    ALLOWED_TRANSITIONS,
)
from runner.result_writer import (
    build_runner_result,
    write_runner_result,
    format_runner_summary,
)


def run_competition(*args, **kwargs):
    """Deferred import wrapper to avoid module-level runpy conflicts."""
    from runner.competition_runner import run_competition as _impl
    return _impl(*args, **kwargs)


__version__ = RUNNER_VERSION

__all__ = [
    "RUNNER_VERSION",
    "OFFICIAL_SCORING_WEIGHTS",
    "RunnerConfig",
    "Job",
    "JobStatus",
    "InvalidStateTransitionError",
    "ALLOWED_TRANSITIONS",
    "build_runner_result",
    "write_runner_result",
    "format_runner_summary",
    "run_competition",
]
