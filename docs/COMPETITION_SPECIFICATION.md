# MOTIONFORGE: Clean. Complete. Retarget.
# Official Technical Competition Specification

- **Document ID**: `MOTIONFORGE-SPEC-V1.0`
- **Specification Status**: `FROZEN FOR PHASE 2`
- **Benchmark Version**: 1.0.0
- **Random Seed Grounding**: `2026`
- **Primary Data Source**: Carnegie Mellon University (CMU) Motion Capture Database

---

## 1. Executive Summary & Competition Overview

**MOTIONFORGE** is an open scientific and engineering benchmark competition targeting three foundational challenges in 3D computer animation, biomechanics, and spatial computing:
1. **Task 1 — Motion Denoising**: Recovering clean, artifact-free skeletal trajectories from high-frequency marker jitter, sensor drift, and sporadic tracking spikes.
2. **Task 2 — Motion Gap Filling**: Inpainting missing joint kinematics caused by marker occlusions and tracking loss over varying temporal windows.
3. **Task 3 — Motion Retargeting**: Adapting semantic motion sequences across diverse body proportions and skeletal topologies without introducing foot sliding, limb disarticulation, or motion distortion.

Participants develop algorithms that ingest corrupted or parameter-specified **Biovision Hierarchy (`.bvh`)** input files and output reconstructed, standardized `.bvh` motion files.

Submissions are evaluated through dual criteria:
- **Numerical Kinematic Accuracy**: 3D joint Euclidean displacement, boundary displacement, and angular geodesic distance.
- **Temporal & Motion Quality**: Velocity smoothness, acceleration jitter mitigation, and anatomical bone-length conservation.

Every metric in this specification is mathematically defined, fully reproducible, and deterministic.

---

## 2. Grounding in the Standardized MOTIONFORGE Dataset

All rules and constraints are grounded directly in the frozen **`MOTIONFORGE_DATASET`**:
- **Total Master Motions**: 30 distinct motion trials (`MF001` through `MF030`).
- **Anatomical Skeleton**: Standardized 31-joint hierarchy with 7 End Sites (38 total structural nodes).
- **Degrees of Freedom (DOF)**: Exactly 96 motion channels per frame (6 root channels + 30 $\times$ 3 joint rotational channels).
- **Sampling Rate**: Unified 120.0 Frames Per Second (FPS) ($\Delta t = 0.0083333\text{ s}$).
- **Total Frames in Master Pool**: 54,560 frames (~454.7 seconds of high-fidelity capture).
- **Dataset Partitioning**: 70% Public Training (21 motions), 30% Hidden Evaluation (9 motions).

---

## 3. Task Specifications & Contract Constraints

### 3.1 Task 1 — Motion Denoising

```text
┌─────────────────────────────────┐
│ INPUT: Noisy BVH (MFxxx_level)   │
│ (Low, Medium, or High Noise)     │
└────────────────┬────────────────┘
                 │
                 ▼ [Participant Denoising Algorithm]
                 │
┌────────────────┴────────────────┐
│ OUTPUT: Denoised BVH            │
│ (MFxxx_denoised.bvh)            │
└─────────────────────────────────┘
```

- **Objective**: Reconstruct the uncorrupted motion trajectory from simulated optical mocap noise while preserving intentional human acceleration and subtle movement dynamics.
- **Noise Variants**:
  - `LOW`: Gaussian displacement jitter ($\sigma_{pos}=0.08$, $\sigma_{rot}=0.40^\circ$), sporadic spike probability $0.5\%$.
  - `MEDIUM`: Moderate sensor noise ($\sigma_{pos}=0.25$, $\sigma_{rot}=1.20^\circ$), sporadic spike probability $1.5\%$.
  - `HIGH`: Severe sensor degradation ($\sigma_{pos}=0.60$, $\sigma_{rot}=2.80^\circ$), sporadic spike probability $3.5\%$.
- **Hard Output Invariants**:
  - Exact frame count preservation ($N_{out} == N_{in}$).
  - Exact sampling rate preservation ($\Delta t = 0.0083333\text{ s}$).
  - Strict preservation of the standardized 31-joint hierarchy and 96-channel definitions.
  - Zero tolerance for global temporal lag or phase delay.
- **Evaluation Mechanism**: The reconstructed output is evaluated against the isolated **Hidden Clean Ground Truth** (`hidden/ground_truth/MFxxx_clean.bvh`).

---

### 3.2 Task 2 — Motion Gap Filling

```text
┌──────────────────────────────────────┐
│ INPUT: Gapped BVH (MFxxx_gaptype)     │
│ (Tracking Loss in Target Joint)      │
└──────────────────┬───────────────────┘
                   │
                   ▼ [Participant Gap-Filling Algorithm]
                   │
┌──────────────────┴───────────────────┐
│ OUTPUT: Inpainted BVH                │
│ (MFxxx_filled.bvh)                   │
└──────────────────────────────────────┘
```

- **Objective**: Synthesize physically plausible, kinematically coherent joint motion across occlusion intervals where tracking failed.
- **Occlusion Regimes**:
  - `SHORT`: 3 to 10 frames ($25\text{ ms} - 83\text{ ms}$). Typical of quick line-of-sight dropouts.
  - `MEDIUM`: 11 to 30 frames ($91\text{ ms} - 250\text{ ms}$). Turnarounds and self-occlusions.
  - `LONG`: 31 to 60 frames ($258\text{ ms} - 500\text{ ms}$). Sustained occlusions.
- **Target Joints**: Randomly distributed across 9 primary non-root anatomical nodes:
  `LeftArm`, `RightArm`, `LeftForeArm`, `RightForeArm`, `LeftLeg`, `RightLeg`, `LeftFoot`, `RightFoot`, `Head`.
- **Temporal Zones**:
  - *Pre-Gap Boundary*: Interval $[t_{start}-5, t_{start}-1]$.
  - *Gap Region*: Interval $[t_{start}, t_{end}]$ (where signal was frozen/lost).
  - *Post-Gap Boundary*: Interval $[t_{end}+1, t_{end}+5]$.
- **Hard Output Invariants**:
  - Frames outside the gap interval must remain strictly untouched (unmodified data fidelity).
  - Reconstructed joint trajectory must be $C^1$ (velocity) continuous at boundary junctions $t_{start}$ and $t_{end}$.
  - Frame count, joint hierarchy, and channel layout must be preserved.

---

### 3.3 Task 3 — Motion Retargeting

```text
┌──────────────────────────────────────┐
│ INPUT 1: Source BVH (Clean Motion)   │
│ INPUT 2: Target Skeleton Config      │
│ (target_small, medium, or tall)      │
└──────────────────┬───────────────────┘
                   │
                   ▼ [Participant Retargeting Algorithm]
                   │
┌──────────────────┴───────────────────┐
│ OUTPUT: Retargeted BVH               │
│ (MFxxx_retargeted.bvh)               │
└──────────────────────────────────────┘
```

- **Objective**: Transfer the semantic movement of a source actor to an avatar with non-uniform skeletal body proportions without artifacts.
- **Explicit Non-Goal**: Global uniform scaling ($S_x=S_y=S_z$) is explicitly prohibited and fails evaluation.
- **Target Body Proportion Profiles**:
  | Target Skeleton | Torso Scale | Upper Arm Scale | Forearm Scale | Thigh Scale | Shin Scale | Foot Scale |
  |---|---|---|---|---|---|---|
  | `target_small` | 0.82 | 0.80 | 0.82 | 0.78 | 0.76 | 0.85 |
  | `target_medium` | 0.95 | 1.12 | 1.15 | 1.08 | 1.10 | 1.02 |
  | `target_tall` | 1.25 | 1.22 | 1.28 | 1.32 | 1.35 | 1.15 |
- **Hard Output Invariants**:
  - The output BVH header must incorporate the exact bone offsets of the requested target skeleton profile.
  - Total frame count and frame time must match the source motion sequence.
  - Joint rotation channels must remain within anatomical biological limits.
  - Root vertical displacement ($Y_{position}$) must dynamically account for the changed leg length.

---

## 4. Standard Input Data Contract

All input motion sequences provided to participants comply with the following data contract:

| Property | Contract Specification | Grounding / Source |
|---|---|---|
| **File Format** | Biovision Hierarchy (`.bvh`) | CMU Standard Conversion |
| **Character Encoding** | ASCII / UTF-8 without BOM | Standard BVH RFC |
| **Coordinate System** | Right-Handed Cartesian ($+Y$ Up, $+X$ Lateral Right, $+Z$ Anterior Forward) | CMU Motion Standard |
| **Position Units** | Inches (CMU units $\approx 0.45\text{ in}$ base scale) | ASF `:units length 0.45` |
| **Rotation Units** | Degrees ($^\circ$) | ASF `:units angle deg` |
| **Rotation Euler Order** | `Zrotation` $\rightarrow$ `Yrotation` $\rightarrow$ `Xrotation` ($Z-Y-X$ intrinsic) | Standard BVH Channel definition |
| **Frame Rate** | 120.0 FPS | Derived from dataset metadata |
| **Frame Time ($\Delta t$)** | `0.0083333` seconds | BVH `Frame Time` header |
| **Root Joint Name** | `Hips` | Hierarchy Root Node |
| **Root Channels** | 6 DOF: `Xposition Yposition Zposition Zrotation Yrotation Xrotation` | BVH Root Channel Line |
| **Child Joint Channels**| 3 DOF: `Zrotation Yrotation Xrotation` (all non-root joints) | Standard Joint Nodes |
| **Total Joint Count** | 31 Functional Joints | Derived from dataset |
| **Total End Sites** | 7 Terminal Nodes (`End Site`) | Head, Hands, Toes, Thumbs |
| **Total Channels** | Exactly 96 scalar channels per frame line | Verified across all 30 master files |

### 4.1 Canonical Joint Ordering (31 Joints)

```text
 1. Hips (Root)       11. RightToeBase     21. LeftHand
 2. LHipJoint         12. LowerBack        22. LeftFingerBase
 3. LeftUpLeg         13. Spine            23. LeftHandIndex1
 4. LeftLeg           14. Spine1           24. LThumb
 5. LeftFoot          15. Neck             25. RightShoulder
 6. LeftToeBase       16. Neck1            26. RightArm
 7. RHipJoint         17. Head             27. RightForeArm
 8. RightUpLeg        18. LeftShoulder     28. RightHand
 9. RightLeg          19. LeftArm          29. RightFingerBase
10. RightFoot         20. LeftForeArm      30. RightHandIndex1
                                           31. RThumb
```

---

## 5. Standard Output Data Contract

### 5.1 Submission File Packaging
Participants submit a single compressed `.zip` archive per submission.
The archive contains a structured directory corresponding to the evaluated split:

```text
submission.zip
├── denoising/
│   ├── MF001_low.bvh
│   ├── MF001_medium.bvh
│   ├── MF001_high.bvh
│   └── ...
├── gap_filling/
│   ├── MF001_short.bvh
│   ├── MF001_medium.bvh
│   ├── MF001_long.bvh
│   └── ...
└── retargeting/
    ├── MF001_target_small.bvh
    ├── MF001_target_medium.bvh
    ├── MF001_target_tall.bvh
    └── ...
```

### 5.2 File Naming Convention & ID Mapping
Every submission file maps deterministically to its input test file and ground-truth benchmark:

| Task | Input Challenge File | Participant Submission File | Evaluation Ground Truth |
|---|---|---|---|
| **Task 1** | `public/denoising/{ID}_{level}.bvh` | `denoising/{ID}_{level}.bvh` | `hidden/ground_truth/{ID}_clean.bvh` |
| **Task 2** | `public/gap_filling/{ID}_{type}.bvh` | `gap_filling/{ID}_{type}.bvh` | `hidden/ground_truth/{ID}_clean.bvh` |
| **Task 3** | `public/retargeting/{ID}_{target}.bvh`| `retargeting/{ID}_{target}.bvh`| Forward Kinematics Target Reference |

---

## 6. Public vs. Hidden Data Separation

To ensure absolute competitive integrity, data visibility is partitioned into two mutually exclusive domains:

```text
┌────────────────────────────────────────────────────────┐
│                   PUBLIC DOMAIN                        │
│ - 21 Training Motions (MF001 - MF021)                 │
│ - clean/bvh/ (for training set only)                  │
│ - public/denoising/ (training set)                    │
│ - public/gap_filling/ (training set)                  │
│ - public/retargeting/ (training set)                  │
│ - metadata/ for training motions                      │
│ - Input challenge files for 9 Test Motions            │
└───────────────────────────┬────────────────────────────┘
                            │
               FIREWALL / ISOLATION BARRIER
                            │
┌───────────────────────────▼────────────────────────────┐
│                   HIDDEN DOMAIN                        │
│ - hidden/ground_truth/ (Master Clean for all files)    │
│ - Ground-truth clean BVH for 9 Test Motions           │
│ - Ground-truth 3D joint coordinate trajectories       │
│ - Test Gap exact frame intervals (start_frame, end)   │
│ - Test Noise exact random seeds & perturbation vectors │
│ - Official Leaderboard Evaluator Backend              │
└────────────────────────────────────────────────────────┘
```

> [!CAUTION]
> Hardcoding test outputs, scraping hidden ground-truth hashes, or attempting to read files outside the designated submission container results in immediate disqualification (`DISQUALIFIED`).

---

## 7. Dataset Protocol: Training, Validation, and Test Splits

The dataset partitioning is derived deterministically from [`metadata/dataset_split.csv`](file:///c:/Users/aditi/OneDrive/Desktop/cgg_fa%202/MOTIONFORGE_DATASET/metadata/dataset_split.csv) with random seed `2026`:

- **Public Training Set (70% — 21 Sequences)**:
  `MF001`, `MF002`, `MF003`, `MF005`, `MF006`, `MF007`, `MF008`, `MF009`, `MF010`, `MF011`, `MF012`, `MF013`, `MF015`, `MF017`, `MF018`, `MF019`, `MF020`, `MF021`, `MF022`, `MF023`, `MF026`.
  *Access*: Both corrupted inputs and master clean ground-truth files are provided for model development and training.

- **Hidden Test Set (30% — 9 Sequences)**:
  `MF004`, `MF014`, `MF016`, `MF024`, `MF025`, `MF027`, `MF028`, `MF029`, `MF030`.
  *Access*: Only corrupted challenge files are published. Clean ground truth is permanently sequestered in `hidden/ground_truth/`.

- **Local Validation Recommendation**:
  Participants are instructed to carve out an internal validation split (e.g., 5 motions from the 21 training sequences) during development to avoid overfitting before submitting to the test leaderboard.

---

## 8. Mathematical Scoring Framework

The evaluation engine calculates task-specific kinematic error metrics and maps them to a normalized scale $[0, 100]$.

### 8.1 Task 1: Denoising Metrics

1. **Mean Per-Joint Position Error (MPJPE)**:
   Measures average 3D Euclidean displacement of all $J=31$ joints across all $N$ frames calculated via Forward Kinematics (FK):
   $$E_{\text{MPJPE}} = \frac{1}{N \cdot J} \sum_{t=1}^{N} \sum_{j=1}^{J} \|\mathbf{p}_{t,j}^{\text{pred}} - \mathbf{p}_{t,j}^{\text{gt}}\|_2$$

2. **Joint Velocity Error (JVE)**:
   Measures temporal fidelity and velocity consistency:
   $$E_{\text{vel}} = \frac{1}{(N-1) \cdot J} \sum_{t=1}^{N-1} \sum_{j=1}^{J} \|(\mathbf{p}_{t+1,j}^{\text{pred}} - \mathbf{p}_{t,j}^{\text{pred}}) - (\mathbf{p}_{t+1,j}^{\text{gt}} - \mathbf{p}_{t,j}^{\text{gt}})\|_2$$

3. **Jitter / Acceleration Penalty ($E_{\text{jit}}$)**:
   Penalizes high-frequency noise spikes and non-smooth trajectories:
   $$E_{\text{jit}} = \frac{1}{(N-2) \cdot J} \sum_{t=2}^{N-1} \sum_{j=1}^{J} \|\mathbf{a}_{t,j}^{\text{pred}} - \mathbf{a}_{t,j}^{\text{gt}}\|_2$$
   where $\mathbf{a}_{t,j} = \mathbf{p}_{t+1,j} - 2\mathbf{p}_{t,j} + \mathbf{p}_{t-1,j}$.

4. **Motion Preservation Ratio (Anti-Over-Smoothing)**:
   Ensures the algorithm does not achieve low jitter by trivial flatlining or excessive blurring:
   $$R_{\text{pres}} = \frac{\sum_{t,j} \|\mathbf{v}_{t,j}^{\text{pred}}\|_2^2}{\sum_{t,j} \|\mathbf{v}_{t,j}^{\text{gt}}\|_2^2}$$

---

### 8.2 Task 2: Gap Filling Metrics

1. **Inpainting MPJPE ($E_{\text{inp}}$)**:
   Calculated strictly over the occluded frames $t \in [t_{\text{start}}, t_{\text{end}}]$ for the affected joint $j^*$:
   $$E_{\text{inp}} = \frac{1}{t_{\text{end}} - t_{\text{start}} + 1} \sum_{t=t_{\text{start}}}^{t_{\text{end}}} \|\mathbf{p}_{t,j^*}^{\text{pred}} - \mathbf{p}_{t,j^*}^{\text{gt}}\|_2$$

2. **Boundary Continuity Error ($E_{\text{bound}}$)**:
   Measures position discontinuity at the entry and exit boundary frames:
   $$E_{\text{bound}} = \|\mathbf{p}_{t_{\text{start}}, j^*}^{\text{pred}} - \mathbf{p}_{t_{\text{start}}-1, j^*}^{\text{clean}}\|_2 + \|\mathbf{p}_{t_{\text{end}}, j^*}^{\text{pred}} - \mathbf{p}_{t_{\text{end}}+1, j^*}^{\text{clean}}\|_2$$

3. **Velocity Boundary Continuity ($E_{\text{v-bound}}$)**:
   $$E_{\text{v-bound}} = \|\mathbf{v}_{t_{\text{start}}, j^*}^{\text{pred}} - \mathbf{v}_{t_{\text{start}}-1, j^*}^{\text{clean}}\|_2 + \|\mathbf{v}_{t_{\text{end}}, j^*}^{\text{pred}} - \mathbf{v}_{t_{\text{end}}+1, j^*}^{\text{clean}}\|_2$$

4. **Foot Skating Penalty ($E_{\text{skate}}$)**:
   When leg or foot joints are occluded during stance phases, detects unnatural slipping across the ground plane:
   $$E_{\text{skate}} = \frac{1}{N_{\text{contact}}} \sum_{t \in \text{contact}} \|\mathbf{v}_{t, \text{foot}}^{\text{horizontal}}\|_2$$

---

### 8.3 Task 3: Retargeting Metrics

1. **End-Effector Semantic Error ($E_{\text{EE}}$)**:
   Compares normalized end-effector trajectories (Hands, Feet, Head) relative to the root frame of reference:
   $$E_{\text{EE}} = \frac{1}{N \cdot |EE|} \sum_{t=1}^{N} \sum_{e \in EE} \|\hat{\mathbf{r}}_{t,e}^{\text{pred}} - \hat{\mathbf{r}}_{t,e}^{\text{src}}\|_2$$
   where $\hat{\mathbf{r}}_{t,e} = \frac{\mathbf{p}_{t,e} - \mathbf{p}_{t,\text{root}}}{L_{\text{limb}}}$.

2. **Geodesic Joint Angular Deviation ($E_{\text{ang}}$)**:
   Measures orientation fidelity on the Lie group $SO(3)$ using quaternion inner products:
   $$E_{\text{ang}} = \frac{1}{N \cdot J} \sum_{t=1}^{N} \sum_{j=1}^{J} 2 \arccos(|\langle \mathbf{q}_{t,j}^{\text{pred}}, \mathbf{q}_{t,j}^{\text{src}} \rangle|)$$

3. **Bone-Length Invariance ($E_{\text{bone}}$)**:
   Ensures the submitted motion strictly adheres to the assigned target proportions without dynamic bone stretching:
   $$E_{\text{bone}} = \max_{j} \left| \|\mathbf{p}_{t,j}^{\text{pred}} - \mathbf{p}_{t,\text{parent}(j)}^{\text{pred}}\|_2 - L_{j}^{\text{target}} \right|$$

4. **Ground Penetration & Floating Penalty ($E_{\text{ground}}$)**:
   Penalizes feet sinking below the floor plane ($Y < 0$) or hovering during stance phases.

---

## 9. Score Normalization & Aggregation

### 9.1 Normalized Task Score Formula
To convert heterogeneous physical units (millimeters, degrees, velocity) into a standardized score $S \in [0, 100]$:
$$S_{\text{task}} = 100 \times \exp\left( - \sum_{k} w_k \cdot \frac{E_k}{\tau_k} \right)$$
where:
- $E_k$ is the raw error metric value.
- $\tau_k$ is the metric normalizer calibration constant.
- $w_k$ is the intra-task metric weight ($\sum w_k = 1.0$).

> [!NOTE]
> Specific calibration coefficients $\tau_k$ and weights $w_k$ are currently marked as **`NEEDS CALIBRATION IN PHASE 3/4`** following baseline empirical runs on the public training split.

### 9.2 Overall Competition Score
The overall leaderboard score is an aggregated weighted sum:
$$S_{\text{overall}} = W_1 \cdot S_{\text{Denoising}} + W_2 \cdot S_{\text{GapFilling}} + W_3 \cdot S_{\text{Retargeting}}$$

**Provisional Competition Weights**:
- $W_1$ (Denoising): **0.30** (30%)
- $W_2$ (Gap Filling): **0.30** (30%)
- $W_3$ (Retargeting): **0.40** (40%)

*Rationale for Retargeting Weight (40%)*: Retargeting requires both kinematic preservation and structural topological re-mapping across non-uniform skeletal morphologies, representing a higher-order generative and geometric challenge than temporal inpainting or filtering alone.

---

## 10. Submission Validation & Rejection Criteria

Submissions undergo automated two-stage validation:

### 10.1 Stage 1: Ingestion & Structural Checks (`REJECTED`)
A submission is immediately marked **`REJECTED`** (score = $0.0$, disqualified from evaluation) if:
1. **Archive Failure**: File is corrupt, cannot be uncompressed, or exceeds maximum archive size.
2. **Missing Challenge Output**: Any required test BVH sequence is missing from the archive.
3. **Hierarchy Incompatibility**: The BVH header does not match the canonical 31-joint hierarchy or specifies incorrect channel counts.
4. **Frame Count Mismatch**: The number of frames does not equal the required frame count for that trial sequence.
5. **Sampling Time Alteration**: `Frame Time` is modified from `0.0083333`.
6. **Numerical Invalidity**: Any channel contains `NaN`, `Inf`, or unparsable non-numeric tokens.
7. **Security / Policy Breach**: Execution attempts file manipulation, socket networking, or attempts to read `hidden/ground_truth/`.

### 10.2 Stage 2: Valid but Low Score
If a file passes all structural checks but exhibits poor kinematic reconstruction (e.g., severe joint teleportation, extreme jitter, bone distortion), it is scored normally and receives a low score ($0.0 \le S \le 100.0$).

---

## 11. Execution Environment & Runtime Rules

*(Provisional parameters to be calibrated during Phase 3 / 4 Sandbox testing)*

| Parameter | Provisional Rule | Status |
|---|---|---|
| **Max Evaluator Execution Time** | 300 seconds per submission archive | `PROVISIONAL` |
| **Max Memory Usage** | 8 GB RAM per evaluation job | `PROVISIONAL` |
| **Execution Sandbox** | Isolated Linux / Docker container | `PROVISIONAL` |
| **Network Access** | Completely Disabled during evaluation | `FINALIZED` |
| **Filesystem Access** | Read-only input, isolated scratch output | `FINALIZED` |

---

## 12. Allowed vs. Disallowed Methods

### Allowed Methods
- Classical signal processing (Butterworth, Kalman, Wiener, Savitzky-Golay filters).
- Classical kinematics & numerical optimization (Inverse Kinematics, gradient descent, FABRIK).
- Deep learning architectures (Transformers, Diffusion models, RNNs, Graph Neural Networks).
- Public motion capture datasets (AMASS, Human3.6M, CMU, LAFAN1) for pre-training.

### Disallowed Methods
- Hardcoding expected test sequence answers based on file sizes or motion metadata.
- Any attempt to access, probe, or leak `hidden/ground_truth/`.
- Dynamic network calls or external API queries during test inference.
- Adversarial exploitation of evaluator code vulnerabilities.

---

## 13. Deterministic Tie-Breaking Hierarchy

In the event of identical overall scores, rankings are resolved deterministically in the following sequential order:
1. **Higher Retargeting Score** ($S_{\text{Retargeting}}$).
2. **Higher Gap Filling Score** ($S_{\text{GapFilling}}$).
3. **Higher Denoising Score** ($S_{\text{Denoising}}$).
4. **Lower Total Evaluator Runtime** (seconds).
5. **Earlier Valid Submission Timestamp** (UTC ISO 8601).

---

## 14. Evaluation Result JSON Schema

The official evaluator produces a standardized, machine-readable JSON result object:

```json
{
  "submission_id": "SUB_2026_TEST_001",
  "status": "VALID",
  "overall_score": 84.72,
  "task_scores": {
    "denoising": 88.15,
    "gap_filling": 82.40,
    "retargeting": 83.89
  },
  "metrics": {
    "denoising": {
      "mean_mpjpe": 1.24,
      "mean_velocity_error": 0.42,
      "mean_jitter": 0.18
    },
    "gap_filling": {
      "mean_inpainting_mpjpe": 2.85,
      "mean_boundary_error": 0.31,
      "foot_skating_score": 0.09
    },
    "retargeting": {
      "end_effector_error": 1.95,
      "angular_geodesic_error": 3.42,
      "bone_length_violation_max": 0.00
    }
  },
  "validation_details": {
    "files_evaluated": 27,
    "checks_passed": 27,
    "checks_failed": 0
  },
  "runtime_seconds": 14.28,
  "timestamp": "2026-10-08T09:15:00Z"
}
```
