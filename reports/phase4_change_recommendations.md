# MOTIONFORGE — Phase 4 Change Recommendations

**Status:** Phase 4 Complete — Frozen pending Phase 5 review

This document records discrepancies, clarifications, and recommended updates
discovered during Phase 4 (Evaluation & Scoring Engine) implementation.

No frozen specification documents were silently modified.

---

## 1. Foot Contact Velocity Threshold Discrepancy

**Location:** `calibration/metric_calibration.json` → `task_2_gap_filling.normalizers.foot_contact_velocity_threshold_inch_per_sec`

**Current JSON value:** `0.907` (mean 10th percentile of foot velocities from Phase 3 analysis)

**Implemented default:** `0.539` in/s (`evaluation/metrics/gap_filling_metrics.py`, line 19)

**Phase 3 analysis:** The empirical 15th-percentile foot velocity across all 30 motions was
`0.539 in/s`, which provides a tighter, more precise stance-phase classification.
The JSON value `0.907` was the mean of per-motion 10th-percentile velocities,
which is a looser threshold.

**Recommendation:** Update `metric_calibration.json` to use `0.539` (15th percentile)
after further validation in Phase 5. The default in `gap_filling_metrics.py` already uses
the more precise value. Participants do not see or use this threshold directly — it is
internal to the evaluator.

**Risk:** Low. Affects only foot skating penalty for leg/foot gap fills.

---

## 2. Distal Endpoint Clarification for Inpainting MPJPE

**Context:** Rotating an internal joint's Euler channels does NOT displace that joint's
own 3D position — it only displaces the joint's children. This is a fundamental property
of forward kinematics.

**Phase 3 Finding:** Inpainting MPJPE for Task 2 must evaluate the **distal child
endpoint** (the first child of the occluded joint), not the pivot joint itself.

**Implementation:** `evaluation/metrics/gap_filling_metrics.py` →
`resolve_distal_joint_endpoint()` returns the first child's name, and MPJPE is computed
on that child's 3D position trajectory.

**Recommendation:** Add this clarification to `docs/DATA_CONTRACT.md` when it is
next updated (Phase 5+). Specifically, in the Task 2 evaluation section, state:

> *"Inpainting accuracy is measured at the distal bone endpoint (the first child joint
> of the occluded pivot), not at the pivot joint itself, because rotating a joint's
> channels only displaces its descendants."*

**Risk:** None. Already correctly implemented. This is a documentation gap only.

---

## 3. Metric Key Name Mapping (Internal)

**Context:** The raw metric dictionaries returned by `denoising_metrics.py`,
`gap_filling_metrics.py`, and `retargeting_metrics.py` use slightly different key names
than what the `task_scoring.py` scorer functions expect.

**Task Evaluator Resolution:** `evaluation/task_evaluator.py` contains explicit
mapping dictionaries in `evaluate_task2()` and `evaluate_task3()`:

| Metric Module Output Key        | Scorer Expected Key          | Task |
|---------------------------------|------------------------------|------|
| `boundary_error`                | `boundary_position_error`    | 2    |
| `velocity_boundary_error`       | `boundary_velocity_error`    | 2    |
| `angular_geodesic_error`        | `angular_deviation_deg`      | 3    |
| `ground_penetration_penalty`    | `ground_penetration_in`      | 3    |

**Recommendation:** Consider unifying key names in Phase 5 to eliminate the mapping
layer. Either rename metric module outputs or scorer inputs. Not urgent — the mapping
is correct and tested.

---

## 4. Retargeting Baseline Score Range (~43–68%)

**Observation:** The proportional bone-rescaling baseline achieves:
- `target_small`: ~43%
- `target_medium`: ~67%
- `target_tall`: ~68%

This is **expected behavior**, not a bug. The baseline applies pure bone scaling
with no motion adaptation, which introduces:
1. Ground penetration when legs are shortened
2. Non-zero normalized end-effector error from proportional scaling artifacts

**Recommendation:** Document this in the participant starter kit as the expected
baseline performance level. Scores above ~70% on retargeting require motion
adaptation beyond simple scaling.

---

## 5. Boundary Continuity Error Semantics

**Observation:** The boundary error for Task 2 compares `pred[gap_start]` vs
`gt[gap_start - 1]` (adjacent frames), meaning even a perfect fill produces
non-zero boundary error. This measures the natural motion step at the gap boundary.

**Current Behavior:** This is intentional — the metric incentivizes participants to
produce smooth transitions into and out of the gap, not just accurate reconstruction.

**Recommendation:** Clarify in `DATA_CONTRACT.md` that boundary continuity is measured
as the position/velocity jump between the last observed frame and the first filled frame,
not as reconstruction error at the boundary.
