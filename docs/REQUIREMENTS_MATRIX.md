# MOTIONFORGE — Requirements Traceability Matrix (RTM)

- **Document ID**: `MOTIONFORGE-RTM-V1.0`
- **Phase**: Phase 2 (Data Contract & Specification)
- **Status**: `FROZEN FOR PHASE 2`

---

## 1. Overview & Purpose

The Requirements Traceability Matrix (RTM) ensures end-to-end alignment from high-level competition objectives down to dataset fields, validator checks, mathematical metrics, and final scoring. Every competition rule is mapped to a tangible verification mechanism.

---

## 2. Global System & Structural Requirements

| Requirement ID | Competition Requirement | Dataset Field / Grounding | Validator Check | Evaluator Metric | Scoring Impact |
|---|---|---|---|---|---|
| **REQ-SYS-01** | Standard BVH Format | File extension `.bvh` | BVH parser verification (`parse_bvh`) | Header compliance check | Binary: `PASS` or `REJECT` |
| **REQ-SYS-02** | Root Joint Naming | `ROOT Hips` in BVH header | Check token is `Hips` | None | Binary: `PASS` or `REJECT` |
| **REQ-SYS-03** | 31-Joint Canonical Topology | 31 JOINT nodes in `clean/bvh/` | Check 31 joint names and hierarchy order | None | Binary: `PASS` or `REJECT` |
| **REQ-SYS-04** | 96 Channel Alignment | 6 root channels + 30 $\times$ 3 rotation channels | Check channel count equals 96 per frame | Array shape check | Binary: `PASS` or `REJECT` |
| **REQ-SYS-05** | Rotation Channel Order | `Zrotation Yrotation Xrotation` | Inspect `CHANNELS` header line | Kinematic FK mapping | Binary: `PASS` or `REJECT` |
| **REQ-SYS-06** | Frame Rate Consistency | `Frame Time: 0.0083333` (120 FPS) | `abs(frame_time - 0.0083333) < 1e-6` | Temporal scaling check | Binary: `PASS` or `REJECT` |
| **REQ-SYS-07** | Numerical Validity | IEEE-754 finite floats | Detect `NaN`, `Inf`, unparsable strings | None | Binary: `PASS` or `REJECT` |
| **REQ-SYS-08** | Packaging Topology | Structured `.zip` archive | Inspect archive tree for task folders | Missing file count check | Missing files trigger `REJECT` |

---

## 3. Task 1: Motion Denoising Requirements

| Requirement ID | Competition Requirement | Dataset Field / Grounding | Validator Check | Evaluator Metric | Scoring Impact |
|---|---|---|---|---|---|
| **REQ-DEN-01** | Exact Frame Count Preservation | `Frames: <N>` in metadata/motions.csv | `len(submitted) == N_expected` | None | Binary: `PASS` or `REJECT` |
| **REQ-DEN-02** | 3D Position Accuracy | `clean/bvh/` 3D joint positions | None (evaluated in sandbox) | 3D MPJPE ($E_{\text{MPJPE}}$) | Primary accuracy score component |
| **REQ-DEN-03** | Temporal Smoothness | Consecutive frame velocities | None | Joint Velocity Error ($E_{\text{vel}}$) | Smoothness score component |
| **REQ-DEN-04** | Jitter & Spike Mitigation | Local joint accelerations | None | Acceleration Penalty ($E_{\text{jit}}$) | Jitter penalty in task score |
| **REQ-DEN-05** | Anti-Over-Smoothing | Dynamic motion velocity variance | None | Motion Preservation Ratio ($R_{\text{pres}}$) | Penalizes flatlining or freezing |

---

## 4. Task 2: Motion Gap Filling Requirements

| Requirement ID | Competition Requirement | Dataset Field / Grounding | Validator Check | Evaluator Metric | Scoring Impact |
|---|---|---|---|---|---|
| **REQ-GAP-01** | Exact Frame Count Preservation | Total trial frames in `gap_metadata.csv` | `len(submitted) == N_expected` | None | Binary: `PASS` or `REJECT` |
| **REQ-GAP-02** | Uncorrupted Frame Conservation | Frames outside $[t_{\text{start}}, t_{\text{end}}]$ | None | Deviation on untouched frames ($E_{\text{unmodified}}$) | Severe penalty if uncorrupted frames modified |
| **REQ-GAP-03** | Inpainting Accuracy | Hidden clean values for affected joint | None | Interval Inpainting MPJPE ($E_{\text{inp}}$) | Primary gap-filling score component |
| **REQ-GAP-04** | Boundary Position Continuity | Frames $t_{\text{start}}-1$ and $t_{\text{end}}+1$ | None | Boundary Step Error ($E_{\text{bound}}$) | Continuity score component |
| **REQ-GAP-05** | Boundary Velocity Continuity | Velocities across boundary frames | None | Velocity Boundary Error ($E_{\text{v-bound}}$) | Jerk penalty at transition points |
| **REQ-GAP-06** | Foot Skating Conservation | Ground contact indicator frames | None | Foot Skating Displacement ($E_{\text{skate}}$) | Physical plausibility score component |

---

## 5. Task 3: Motion Retargeting Requirements

| Requirement ID | Competition Requirement | Dataset Field / Grounding | Validator Check | Evaluator Metric | Scoring Impact |
|---|---|---|---|---|---|
| **REQ-RET-01** | Target Skeleton Offset Adoption | Target `OFFSET` vectors in template BVH | Offset vector deviation $< 1e-4$ | None | Binary: `PASS` or `REJECT` |
| **REQ-RET-02** | Frame Count Preservation | Source trial frame count | `len(submitted) == N_expected` | None | Binary: `PASS` or `REJECT` |
| **REQ-RET-03** | Non-Uniform Bone Proportions | Scales in `retarget_metadata.csv` | Verify non-uniform offsets | Bone-Length Invariance ($E_{\text{bone}}$) | Binary: `PASS` or `REJECT` |
| **REQ-RET-04** | End-Effector Semantic Transfer | Hands, Feet, Head root-relative tracks | None | End-Effector Error ($E_{\text{EE}}$) | Primary retargeting accuracy component |
| **REQ-RET-05** | Joint Angular Consistency | Source rotation Euler angles / Quats | None | Angular Geodesic Deviation ($E_{\text{ang}}$) | Pose semantic preservation component |
| **REQ-RET-06** | Ground Plane Plausibility | Root $Y$ coordinate vs leg scale | None | Foot Penetration / Hovering ($E_{\text{ground}}$) | Grounding plausibility component |

---

## 6. Security, Runtime & Operational Requirements

| Requirement ID | Competition Requirement | Implementation Grounding | Validator Check | Evaluator Metric | Scoring Impact |
|---|---|---|---|---|---|
| **REQ-SEC-01** | Hidden GT Confidentiality | Isolated `hidden/ground_truth/` | Filesystem sandbox policy | Unauthorized access trap | `DISQUALIFIED` |
| **REQ-SEC-02** | Zero Network Access | Docker `--network none` | Sandbox network inspect | None | Execution aborted if breached |
| **REQ-SEC-03** | Wall-Clock Timeout | `competition.yaml: timeout_seconds` | Process supervisor timer | Execution time monitor | `TIMEOUT` if exceeded |
| **REQ-SEC-04** | Memory Envelope | `competition.yaml: memory_limit_mb` | Container cgroups memory cap | Memory usage monitor | `OOM_KILLED` if exceeded |
| **REQ-SEC-05** | Deterministic Tie-Breaking | Evaluator ranking hierarchy | None | Automated tie-break ranker | Resolves identical final scores |
