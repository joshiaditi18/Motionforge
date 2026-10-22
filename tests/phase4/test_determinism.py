"""
tests/phase4/test_determinism.py — Determinism tests for the evaluation engine.

Verifies that evaluating the same input twice produces identical results.
Determinism is a requirement for a competition evaluator.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest

from baselines.common.bvh_io import parse_bvh
from evaluation.metrics.denoising_metrics import evaluate_denoising
from evaluation.metrics.gap_filling_metrics import evaluate_gap_filling
from evaluation.metrics.retargeting_metrics import evaluate_retargeting
from evaluation.scoring.task_scoring import score_denoising, score_gap_filling, score_retargeting
from evaluation.scoring.normalization import normalize_weighted_exponential

_BVH_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "MOTIONFORGE_DATASET", "clean", "bvh", "MF001_clean.bvh"
)


def _load_bvh():
    return parse_bvh(_BVH_PATH)


class TestDeterminism:
    def test_denoising_metrics_deterministic(self):
        bvh = _load_bvh()
        r1 = evaluate_denoising(bvh, bvh)
        r2 = evaluate_denoising(bvh, bvh)
        for k in r1:
            assert r1[k] == r2[k], f"Denoising metric '{k}' non-deterministic: {r1[k]} vs {r2[k]}"

    def test_gap_filling_metrics_deterministic(self):
        bvh = _load_bvh()
        r1 = evaluate_gap_filling(bvh, bvh, "RightArm", 50, 70)
        r2 = evaluate_gap_filling(bvh, bvh, "RightArm", 50, 70)
        for k in r1:
            assert r1[k] == r2[k], f"Gap filling metric '{k}' non-deterministic"

    def test_retargeting_metrics_deterministic(self):
        bvh = _load_bvh()
        r1 = evaluate_retargeting(bvh, bvh, "target_medium")
        r2 = evaluate_retargeting(bvh, bvh, "target_medium")
        for k in r1:
            assert r1[k] == r2[k], f"Retargeting metric '{k}' non-deterministic"

    def test_scoring_deterministic(self):
        metrics = {"mpjpe": 0.1, "velocity_error": 5.0, "jitter": 100.0, "motion_preservation": 1.0}
        s1, _ = score_denoising(metrics)
        s2, _ = score_denoising(metrics)
        assert s1 == s2, f"Scoring non-deterministic: {s1} vs {s2}"

    def test_normalization_deterministic(self):
        for _ in range(5):
            s = normalize_weighted_exponential(
                {"a": 0.5, "b": 0.5},
                {"a": 1.23, "b": 4.56},
                {"a": 2.0, "b": 8.0},
            )
        s2 = normalize_weighted_exponential(
            {"a": 0.5, "b": 0.5},
            {"a": 1.23, "b": 4.56},
            {"a": 2.0, "b": 8.0},
        )
        assert s == s2
