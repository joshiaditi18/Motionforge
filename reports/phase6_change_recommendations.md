# MOTIONFORGE — Phase 6 Change Recommendations

**Phase:** 6 — Local Competition Runner  
**Status:** Audit & Recommendations Documented  
**Timestamp:** 2026-10-14  

---

## 1. Resolution of `validate_motion_array` Signature Discrepancy

### Location
`evaluation/task_evaluator.py`, lines 102 and 291.

### Root Cause
The helper function `validate_motion_array(arr, expected_frames=None, expected_channels=96)` in `evaluation/metrics/common_metrics.py` defines `expected_frames` (type `int` or `None`) as its second positional parameter.

In `evaluation/task_evaluator.py`:
- Line 102 previously called: `validate_motion_array(bvh_pred.motion_data, "predicted motion")`
- Line 291 previously called: `validate_motion_array(bvh_pred.motion_data, "predicted retargeted motion")`

Passing a string description into `expected_frames` resulted in the comparison:
`arr.shape[0] != "predicted motion"` (e.g. `317 != "predicted motion"` $\rightarrow$ `True`), causing structural validation to reject valid submissions with the error:
`"Motion data has 317 frames, expected predicted motion"`.

### Smallest Compatible Fix Applied
Invoked `validate_motion_array(bvh_pred.motion_data)` without the second positional string argument. Exact frame counts are already explicitly verified against ground truth in lines 82–89 and 277–288 of `evaluation/task_evaluator.py`.

### Impact & Safety
- Metric formulas, τ values, and scoring weights remain 100% unchanged.
- Allows valid participant predictions to be evaluated correctly.
- Prevents false-positive structural rejections.

---

## 2. Harmonization of Submission Directory Topologies

### Issue
`docs/DATA_CONTRACT.md` §3.1 defines participant submission directory layouts using semantic folder names:
```text
submission.zip/
├── denoising/
│   └── MFxxx_low.bvh
├── gap_filling/
│   └── MFxxx_short.bvh
└── retargeting/
    └── MFxxx_target_small.bvh
```
While the Phase 4 batch evaluation module (`evaluation/evaluator.py`) expects task index names:
```text
submission/
├── task1/          # MFxxx_denoised.bvh
├── task2/          # MFxxx_short_filled.bvh
└── task3/          # MFxxx_small_retargeted.bvh
```

### Resolution
`runner/competition_runner.py` implements transparent staging normalization in `_normalize_workspace_layout()` within the isolated temporary execution workspace:
- Creates aliases/mirrors between `denoising` $\leftrightarrow$ `task1`, `gap_filling` $\leftrightarrow$ `task2`, and `retargeting` $\leftrightarrow$ `task3`.
- Bridges file naming conventions (`MFxxx_low.bvh` $\leftrightarrow$ `MFxxx_denoised.bvh`, `MFxxx_short.bvh` $\leftrightarrow$ `MFxxx_short_filled.bvh`, `MFxxx_target_small.bvh` $\leftrightarrow$ `MFxxx_small_retargeted.bvh`).
- Leaves participant submission archives completely untouched.

### Recommendation
For the upcoming Phase 7 / online platform submission portal, explicitly accept both topological conventions as first-class aliases.

---

## 3. Strict Gatekeeping & Decoupled Architecture

### Principle
The Phase 5 Validator acts as a deterministic, non-bypassable pre-flight gate. Under no circumstances should an invalid or rejected submission reach the Phase 4 Evaluation Engine.

### Validation
- Tested and confirmed in Phase 6: submissions returning `REJECTED` or `VALIDATION_ERROR` immediately halt execution, receive an overall score of `null` (not evaluated), and yield exit code 1 or 2 respectively.
- Confirmed zero participant code execution: only pre-rendered BVH motion data files are parsed and evaluated.
