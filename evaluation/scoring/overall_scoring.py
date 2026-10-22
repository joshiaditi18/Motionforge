"""
overall_scoring.py — MOTIONFORGE Phase 4 Overall Score Aggregation

Official inter-task weights (from Phase 2, frozen):
    Denoising    = 0.30
    Gap Filling  = 0.30
    Retargeting  = 0.40

Formula: S_overall = w1 * S1 + w2 * S2 + w3 * S3
"""

from __future__ import annotations

from typing import Optional, Dict, Any

# Official inter-task competition weights (Phase 2, frozen)
TASK_WEIGHT_DENOISING = 0.30
TASK_WEIGHT_GAP_FILLING = 0.30
TASK_WEIGHT_RETARGETING = 0.40


def compute_overall_score(
    denoising_score: Optional[float],
    gap_filling_score: Optional[float],
    retargeting_score: Optional[float],
) -> Dict[str, Any]:
    """
    Compute the weighted overall competition score.

    If a task score is None (task not evaluated / not submitted),
    it is excluded from the weighted sum and its weight is redistributed
    proportionally among the evaluated tasks.

    Parameters
    ----------
    denoising_score   : float [0,100] or None
    gap_filling_score : float [0,100] or None
    retargeting_score : float [0,100] or None

    Returns
    -------
    dict with keys:
        overall_score   : float [0,100] or None if no tasks evaluated
        task_weights    : dict of applied weights
        tasks_evaluated : list of task names evaluated
    """
    task_map = {
        "denoising":    (denoising_score,   TASK_WEIGHT_DENOISING),
        "gap_filling":  (gap_filling_score, TASK_WEIGHT_GAP_FILLING),
        "retargeting":  (retargeting_score, TASK_WEIGHT_RETARGETING),
    }

    evaluated = {
        name: (score, weight)
        for name, (score, weight) in task_map.items()
        if score is not None
    }

    if not evaluated:
        return {
            "overall_score": None,
            "task_weights": {},
            "tasks_evaluated": [],
        }

    total_weight = sum(w for _, w in evaluated.values())
    # Redistribute weights proportionally if any task missing
    applied_weights = {
        name: w / total_weight
        for name, (_, w) in evaluated.items()
    }

    overall = sum(
        applied_weights[name] * score
        for name, (score, _) in evaluated.items()
    )
    overall = float(max(0.0, min(100.0, overall)))

    return {
        "overall_score": overall,
        "task_weights": applied_weights,
        "tasks_evaluated": list(evaluated.keys()),
        "raw_task_scores": {
            name: score for name, (score, _) in evaluated.items()
        },
    }
