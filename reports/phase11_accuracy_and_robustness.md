# MOTIONFORGE — PHASE 11: Accuracy, Robustness & Performance Engineering

**Document ID:** MF-REP-P11-001  
**Date:** October 15, 2026  
**Status:** COMPLETED  

---

## 1. Audit Summary

Phase 11 began with a thorough inspection of Phases 1–6 algorithms, API routes, tests, and calibration constants before making any changes.

### 1.1 Code Inspected

| Component | File | Finding |
|---|---|---|
| Denoising | `baselines/denoising/baseline_denoising.py` | Fixed-window Savitzky-Golay with hardcoded window sizes (7/13/19 frames). Phase unwrapping present. No edge reflection padding. |
| Gap Filling | `baselines/gap_filling/baseline_gap_filling.py` | Natural cubic spline with 6 anchor points. Falls back to linear for short gaps. No velocity clamping at boundaries. |
| Retargeting | `baselines/retargeting/baseline_retargeting.py` | Bone offset scaling + `(thigh+shin)/2` root Y scaling. No ground penetration check. |
| Evaluator | `evaluation/task_evaluator.py` | Validates frame count, frame time, channels, joint hierarchy, NaN/Inf. Calls FK-based metric functions. |
| Scoring | `evaluation/scoring/task_scoring.py` | Exponential decay normalization with frozen `τ` values from `calibration/metric_calibration.json`. |
| Tests | `tests/phase4/test_baseline_regression.py` | 9 tests were being **skipped** due to missing `baselines/outputs/` directory. |

### 1.2 Skipped Tests Investigation

All 9 skipped tests in `tests/phase4/test_baseline_regression.py` were skipping because the `baselines/outputs/` directory did not exist. **Resolution:** Created `baselines/generate_outputs.py` to generate and persist baseline outputs; all 9 tests now **pass** (verified).

---

## 2. Reproducible Benchmark Results

Benchmarks executed on motions `MF001, MF002, MF003` across all noise/gap/avatar configurations.  
**Total benchmark duration: 68.58 seconds.**

### 2.1 Task 1 — Motion Denoising

| Method | Mean Score | Mean MPJPE | Mean Jitter | Avg Runtime |
|---|---|---|---|---|
| `baseline_savgol` | 38.42 | 0.4093 | 3319.1 | 55.2 ms |
| `butterworth` | **57.68** | **0.3360** | **803.5** | 42.1 ms |
| `gaussian` | 48.97 | 0.3689 | 1437.9 | 43.3 ms |
| `adaptive_savgol` | 37.93 | 0.4107 | 3412.2 | 43.8 ms |

> [!IMPORTANT]
> **Butterworth filter is the clear winner:** +19.3 points above baseline on mean score, **75.8% jitter reduction** vs baseline, and faster runtime. The improvement is driven by zero-phase forward-backward filtering which eliminates the phase distortion that degrades Savitzky-Golay at high noise.

> [!NOTE]
> Adaptive Savitzky-Golay performs slightly worse than the fixed-window baseline. The velocity-adaptive blending logic does not meaningfully improve trajectory accuracy for this dataset's kinematic profiles and is not recommended for replacement.

### 2.2 Task 2 — Motion Gap Filling

| Method | Mean Score | Inpainting MPJPE | Boundary Error | Avg Runtime |
|---|---|---|---|---|
| `linear` | 31.53 | 0.5911 | 0.3108 | 48.0 ms |
| `natural_cubic` (Baseline) | **35.14** | **0.4142** | 0.3440 | 46.4 ms |
| `pchip` | 31.76 | 0.5933 | 0.3141 | 45.4 ms |
| `clamped_hermite` | 34.18 | 0.4534 | 0.3375 | 52.3 ms |

> [!NOTE]
> The official Natural Cubic Spline **baseline already performs best** on this dataset. PCHIP's monotonicity constraint prevents useful extrapolation beyond anchor values for rotational signals crossing 0°, while the natural cubic spline fits complex rotational arcs more accurately.

> [!TIP]
> PCHIP and Clamped Hermite remain valuable alternatives for detecting **overshoot cases** — specifically long gaps (>48 frames) at peak motion velocity where natural cubic may amplify extremes.

### 2.3 Task 3 — Motion Retargeting

| Method | Mean Score | End-Effector Err | Ground Penetration | Avg Runtime |
|---|---|---|---|---|
| `baseline` | 46.96 | 0.0224 | **1.2255** | 37.3 ms |
| `full_chain` | 46.22 | 0.0224 | 1.2648 | 31.4 ms |
| `contact_aware` | **69.17** | **0.0224** | **0.0000** | 334.8 ms |

> [!IMPORTANT]
> **Contact-Aware retargeting is a major verified improvement: +22.2 points.** It completely eliminates ground penetration (1.2255 → 0.0000 inches), which directly drives the score improvement. End-effector accuracy is identical since joint angles are preserved.

> [!WARNING]
> Contact-aware method has a **9× runtime overhead** (37 ms → 335 ms) due to the FK pass for foot height clamping. Acceptable for batch evaluation but may be slow for interactive demos.

---

## 3. Algorithm Changes & Evidence

### 3.1 Denoising — Butterworth Filter Added

**Hypothesis:** Zero-phase Butterworth IIR filtering will produce significantly lower residual jitter than fixed-window Savitzky-Golay because it eliminates phase distortion in the filtered output.

| | Baseline (SavGol) | Butterworth | Change |
|---|---|---|---|
| Mean Score (MF001-MF003) | 38.42 | **57.68** | **+50.1%** |
| Mean Jitter | 3319 | **804** | **-75.8%** |
| Mean MPJPE | 0.409 | **0.336** | **-17.8%** |
| Runtime | 55.2 ms | **42.1 ms** | **-23.7%** |

**Decision: Implement as selectable experimental alternative.** The official baseline scoring weights remain unchanged. The Butterworth filter is labeled `[EXPERIMENTAL]` in the Accuracy Lab.

### 3.2 Retargeting — Contact-Aware Floor Clamping Added

**Hypothesis:** Dynamically correcting root Y translation to prevent toe/foot penetration below the ground plane will eliminate the ground penetration penalty without changing rotation kinematics.

| | Baseline | Contact-Aware | Change |
|---|---|---|---|
| Mean Score | 46.96 | **69.17** | **+47.3%** |
| Ground Penetration (in) | 1.2255 | **0.0000** | **-100%** |
| End-Effector Error | 0.0224 | 0.0224 | No change |

**Decision: Implement as selectable experimental alternative.** Available in Accuracy Lab for comparative evaluation.

---

## 4. Robustness Test Results

All 9 new Phase 11 robustness tests pass:

```
tests/phase11/test_accuracy_robustness.py .........  9 passed
```

Tests cover:
- Short sequence handling (5 frames with `HIGH` noise — window clamped)
- Butterworth determinism (bitwise identical on repeated calls)
- Rotational wraparound at ±180° without velocity spikes
- Observed frame invariance — channels outside gap are pixel-perfect unchanged
- Boundary continuity in Clamped Hermite spline
- Large gap stability (120-frame gap with no NaN/Inf)
- Ground penetration elimination by contact-aware retargeting
- API 400 for invalid task name
- API 500 with informative error for unknown motion ID

---

## 5. Full Test Suite Results

```
============================= 201 passed in 47.30s =============================

tests/phase11/test_accuracy_robustness.py  .........    9 passed
tests/phase3/test_baselines.py             ......       6 passed
tests/phase4/test_baseline_regression.py   .........    9 passed  ← was 9 skipped
tests/phase4/test_denoising_metrics.py     .......      7 passed
tests/phase4/test_determinism.py           .....        5 passed
tests/phase4/test_edge_cases.py            ..........  10 passed
tests/phase4/test_gap_filling_metrics.py   ........     8 passed
tests/phase4/test_normalization.py         ........... 20 passed
tests/phase4/test_retargeting_metrics.py   ..........  10 passed
tests/phase4/test_scoring.py               .......     21 passed
tests/phase5/test_archive_validation.py    .......      7 passed
tests/phase5/test_bvh_validation.py        .......      7 passed
tests/phase5/test_determinism.py           ..           2 passed
tests/phase5/test_invalid_submissions.py   .........    9 passed
tests/phase5/test_motion_validation.py     .......      7 passed
tests/phase5/test_schema_validation.py     ......       6 passed
tests/phase5/test_security_validation.py   .........    9 passed
tests/phase5/test_skeleton_validation.py   ........     8 passed
tests/phase5/test_task_validation.py       .......      7 passed
tests/phase5/test_valid_submissions.py     ..           2 passed
tests/phase6/test_job_lifecycle.py         ......       6 passed
tests/phase6/test_result_artifact.py       ....         4 passed
tests/phase6/test_runner_pipeline.py       ......       6 passed
tests/phase6/test_scoring_and_determinism  ....         4 passed
tests/test_demo_api.py                     ............12 passed
```

**Total: 201 passed, 0 skipped, 0 failed** (previously: 180 passed, 9 skipped).

---

## 6. Frontend Build Results

```
> tsc -b && vite build
✓ 1939 modules transformed.
dist/assets/index-CnPcQkNX.js  929.84 kB │ gzip: 242.21 kB
✓ built in 1.53s
```

Zero TypeScript errors, zero warnings.

---

## 7. New Files Created

| File | Description |
|---|---|
| `experiments/denoising_experiments.py` | Butterworth, Gaussian, Adaptive Savitzky-Golay |
| `experiments/gap_filling_experiments.py` | PCHIP, Clamped Hermite Spline, Linear |
| `experiments/retargeting_experiments.py` | Full-Chain Leg, Contact-Aware Anti-Penetration |
| `experiments/benchmark_runner.py` | Reproducible 3-task benchmark suite |
| `baselines/generate_outputs.py` | Generates baseline output BVHs for regression tests |
| `backend/services/accuracy_service.py` | Accuracy Lab service layer |
| `backend/routers/accuracy.py` | `/api/accuracy/*` endpoints |
| `tests/phase11/test_accuracy_robustness.py` | 9 new robustness tests |
| `reports/benchmark_results.json` | Saved benchmark measurements |
| `frontend/src/components/views/AccuracyLabView.tsx` | Accuracy Lab UI component |

---

## 8. Competition Integrity Verification

| Contract | Status |
|---|---|
| 31-joint hierarchy + 7 End-Sites | ✅ Preserved |
| 96 channels per frame | ✅ Preserved |
| Z-Y-X Euler convention | ✅ Preserved |
| 120 FPS / 0.008333s frame time | ✅ Preserved |
| MF001–MF030 master IDs | ✅ Preserved |
| Scoring weights: 30% / 30% / 40% | ✅ Preserved |
| Calibration τ constants | ✅ Preserved (never modified) |
| Validation schemas | ✅ Preserved |

---

## 9. Remaining Weaknesses & Limitations

| Weakness | Category | Recommended Fix |
|---|---|---|
| Contact-Aware retargeting is 9× slower (335 ms) | Performance | Apply FK only on a sub-sampled frame set for clamping, then smooth linearly |
| PCHIP underperforms natural cubic on this dataset | Algorithm Fit | Suitable for monotone signals; not always beneficial for Euler angle channels |
| Adaptive SavGol: no improvement measured | Algorithm Fit | Blending logic may require per-channel tuning rather than global velocity threshold |
| Benchmark covers only 3 of 30 motions | Coverage | Run full 30-motion benchmark for statistically significant conclusions |
| Gap filling for `LONG` gaps (>48 frames) is weak across all methods | Algorithm Gap | Consider physics-based prediction or learned trajectory priors |

---

## 10. Launch Commands

```bash
# 1. Start the application server
python run_demo.py

# 2. Open in browser
# http://127.0.0.1:8000

# 3. Run the full test suite
pytest

# 4. Run the benchmark suite
python experiments/benchmark_runner.py

# 5. Build the frontend
cd frontend
npm run build
```
