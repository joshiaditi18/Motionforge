# MOTIONFORGE Evaluation Engine

## Overview

The `evaluation/` module is the **official, deterministic competition evaluation engine** for MOTIONFORGE — Clean. Complete. Retarget.

It evaluates participant submissions across three tasks:
- **Task 1** — Motion Denoising
- **Task 2** — Motion Gap Filling
- **Task 3** — Motion Retargeting

## Architecture

```
evaluation/
├── __init__.py                      # Version constants
├── evaluator.py                     # Full submission evaluator (batch)
├── task_evaluator.py                # Per-task evaluator (structural validation + metrics + scoring)
│
├── metrics/                         # Raw metric computation
│   ├── common_metrics.py            # NaN/Inf validation, SO(3) geodesic
│   ├── kinematic_metrics.py         # MPJPE, velocity, acceleration, jitter, preservation
│   ├── denoising_metrics.py         # Task 1 metrics via FK
│   ├── gap_filling_metrics.py       # Task 2 metrics (distal endpoint, boundary continuity)
│   └── retargeting_metrics.py       # Task 3 metrics (end-effector, angular, penetration)
│
├── scoring/                         # Score normalization and aggregation
│   ├── normalization.py             # Load τ from calibration JSON, exp(-Σ wE/τ) formula
│   ├── task_scoring.py              # Per-task scorers with anti-degeneracy guards
│   └── overall_scoring.py           # Weighted overall score (30/30/40)
│
├── io/                              # Result serialization
│   ├── evaluation_schema.py         # Result schema, SubmissionStatus enum, exit codes
│   └── result_writer.py             # Atomic JSON writer, human-readable summary
│
└── runners/
    └── evaluation_runner.py         # CLI entry point
```

## Scoring Formula

All tasks use the same normalized exponential decay:

$$S_{\text{task}} = 100 \cdot \exp\!\left(-\sum_k w_k \cdot \frac{E_k}{\tau_k}\right)$$

Where:
- $E_k$ = raw metric error
- $\tau_k$ = calibrated normalizer (from `calibration/metric_calibration.json`)
- $w_k$ = intra-task weight (sum to 1.0)

Overall: $S = 0.30 \cdot S_1 + 0.30 \cdot S_2 + 0.40 \cdot S_3$

## CLI Usage

### Single-task evaluation

```bash
# Task 1 — Denoising
python -m evaluation.runners.evaluation_runner \
    --task 1 \
    --prediction pred_denoised.bvh \
    --ground-truth gt_clean.bvh \
    --output result.json

# Task 2 — Gap Filling
python -m evaluation.runners.evaluation_runner \
    --task 2 \
    --prediction pred_filled.bvh \
    --ground-truth gt_clean.bvh \
    --joint RightArm --gap-start 50 --gap-end 70 \
    --output result.json

# Task 3 — Retargeting
python -m evaluation.runners.evaluation_runner \
    --task 3 \
    --prediction pred_retargeted.bvh \
    --ground-truth source_clean.bvh \
    --target-type medium \
    --output result.json
```

### Batch submission evaluation

```bash
python -m evaluation.runners.evaluation_runner \
    --submission ./my_submission/ \
    --output batch_result.json \
    --submission-id "my-submission-001"
```

Expected submission directory layout:
```
my_submission/
├── task1/          # MFxxx_denoised.bvh files
├── task2/          # MFxxx_short_filled.bvh, etc.
└── task3/          # MFxxx_small_retargeted.bvh, etc.
```

## Exit Codes

| Code | Status     | Meaning                               |
|------|-----------|---------------------------------------|
| 0    | `VALID`    | Submission evaluated successfully     |
| 1    | `REJECTED` | Structural or contract violation      |
| 2    | `ERROR`    | Internal evaluator error              |

## Anti-Degeneracy Guards

- **Task 1**: Motion preservation ratio must be in [0.35, 3.0] → otherwise score = 0
- **Task 2**: Unmodified frames must have max diff ≤ 1e-6 → otherwise REJECTED
- **Task 3**: Invalid target type → REJECTED

## Key Design Decisions

1. **τ values are never hardcoded** — always loaded from `calibration/metric_calibration.json`
2. **Deterministic** — same input always produces same output (verified by tests)
3. **Float64 throughout** — all FK and metric computations use `numpy.float64`
4. **Distal endpoint for gap filling MPJPE** — evaluates the child joint endpoint, not the pivot joint itself (Phase 3 finding)
5. **Atomic file writes** — results are written via temp file + rename

## Tests

```bash
python -m pytest tests/phase4/ -v
```

8 test files covering:
- `test_normalization.py` — τ loading, formula verification, anti-degeneracy
- `test_scoring.py` — per-task and overall scoring
- `test_denoising_metrics.py` — integration tests with real BVH
- `test_gap_filling_metrics.py` — distal endpoint resolution, boundary errors
- `test_retargeting_metrics.py` — all target types, key presence
- `test_determinism.py` — identical re-evaluation produces identical results
- `test_edge_cases.py` — NaN/Inf detection, boundary gaps, adversarial inputs
- `test_baseline_regression.py` — scores match Phase 3 calibrated baselines (±15 pts)
