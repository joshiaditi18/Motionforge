# MOTIONFORGE — System Architecture & Component Blueprint

- **Document ID**: `MOTIONFORGE-ARCH-V1.0`
- **Phase**: Phase 2 (Architecture Design)
- **Status**: `FROZEN FOR PHASE 2`

---

## 1. End-to-End System Topology

The diagram below outlines the complete dataflow and component pipeline of the MOTIONFORGE competition system, tracing the path from raw motion capture datasets to public leaderboard scoring:

```text
                             MOTIONFORGE
                                  │
                  ┌───────────────┴───────────────┐
                  │                               │
        MOTIONFORGE_DATASET             Participant Ecosystem
        ├── source/ (CMU)               ├── Starter Kit
        ├── clean/ (BVH)                ├── Baseline Algorithms
        ├── public/                     └── Local Validation Tool
        └── hidden/ (Ground Truth)                │
                  │                               │
                  └───────────────┬───────────────┘
                                  ▼
                         Submission Package
                         (submission.zip)
                                  │
                                  ▼
                        Submission Validator
                        (scripts/validate_submission.py)
                        ├── Format & Archive Integrity
                        ├── Canonical Hierarchy Inspection
                        └── Numerical Validity (NaN / Inf)
                                  │
                                  ▼ (Passed)
                          Execution Sandbox
                          (Isolated Docker / Container)
                          ├── Zero Network Access
                          ├── Memory & CPU Quotas
                          └── Read-Only Volume Mounting
                                  │
                                  ▼
                             Task Runner
                             ├── Ingests Submission BVH
                             ├── Ingests Hidden Ground Truth
                             └── Dispatches Task Sub-Processors
                                  │
                                  ▼
                          Evaluation Engine
                          (evaluation/evaluate_submission.py)
                          ├── Task 1: Denoising Evaluation
                          ├── Task 2: Gap Inpainting Evaluation
                          └── Task 3: Retargeting Evaluation
                                  │
                                  ▼
                           Kinematic Metrics
                           ├── MPJPE (3D Euclidean Distance)
                           ├── Velocity & Acceleration Jitter
                           ├── Boundary Continuity
                           └── End-Effector Trajectories
                                  │
                                  ▼
                            Scoring Engine
                            ├── Exponential Normalization (0-100)
                            ├── Task Weight Aggregation (30/30/40)
                            └── Result JSON Serializer
                                  │
                                  ▼
                          Backend & Database
                          ├── Submission History & Metadata
                          ├── Score Breakdown Persistence
                          └── Verification Ledger
                                  │
                                  ▼
                             Leaderboard
                             ├── Public Ranking Dashboard
                             └── 3D Visual Comparator (Viewer)
```

---

## 2. Component Breakdown & Responsibilities

### 2.1 MOTIONFORGE_DATASET (The Data Foundation)
- **Purpose**: Authoritative motion capture database derived from CMU mocap and standardized into canonical 31-joint BVH.
- **Sub-Modules**:
  - `source/cmu_original/`: Pristine, untouched CMU `.asf` skeletons and `.amc` motion files.
  - `clean/bvh/`: Master ground-truth motions with standardized naming and topology (`MF001` - `MF030`).
  - `public/`: Public challenges for denoising (Low/Med/High), gap filling (Short/Med/Long), and retargeting (Small/Med/Tall).
  - `hidden/ground_truth/`: Sequestered ground-truth reference vault for test set scoring.
  - `metadata/`: Ground-truth manifests, partition splits, and perturbation parameters.

### 2.2 Participant Starter Kit (Developer Onboarding)
- **Purpose**: Lowers friction for competitors by providing reproducible starter code.
- **Planned Sub-Modules**:
  - `baselines/`: Reference implementations (Butterworth filter for Task 1, SLERP/Spline for Task 2, FK Retargeter for Task 3).
  - `tools/`: Local BVH parser, inspection scripts, and local format validator.
  - `documentation/`: Tutorials and API contracts.

### 2.3 Submission Validator (Gatekeeper)
- **Purpose**: Deterministic pre-flight inspector. Rejects non-conforming submissions before consuming expensive compute resources.
- **Key Responsibilities**:
  - Validates `.zip` file structure against the expected directory layout.
  - Checks BVH hierarchy: exactly 31 joints, root `Hips`, 96 channels, channel types and ordering.
  - Verifies exact frame preservation: $N_{\text{submitted}} == N_{\text{expected}}$.
  - Detects corrupted floats, non-finite values (`NaN`, `Inf`).

### 2.4 Execution Sandbox (Security & Fairness Boundary)
- **Purpose**: Executes evaluation in an isolated runtime environment.
- **Key Constraints**:
  - **Network Isolation**: Complete network disconnection (`--network none`) ensures no test data leakage or external server querying.
  - **Filesystem Confinement**: Submission files mounted read-only (`ro`); ground truth accessible only by the evaluator process; write access confined to ephemeral output directories.
  - **Resource Enforcement**: Strict RAM limits (cgroups) and wall-clock execution limits.

### 2.5 Task Runner & Evaluation Engine
- **Purpose**: Performs high-performance forward kinematics and numerical evaluation.
- **Key Responsibilities**:
  - Evaluates all test split sequences across the three benchmark tasks.
  - Computes global 3D joint coordinate trajectories from local BVH Euler angle trees using forward kinematics.
  - Produces raw mathematical error values and applies normalization formulas.

### 2.6 Scoring Engine & Database Persistence
- **Purpose**: Translates physical error vectors into standard leaderboard rankings.
- **Key Responsibilities**:
  - Maps raw errors to standardized $[0, 100]$ task scores via calibrated decay functions.
  - Computes aggregated overall score using frozen competition weights.
  - Writes structured `score.json` and records entry in persistent database storage.

### 2.7 Public Leaderboard & Visual Comparison Player
- **Purpose**: Transparent, interactive participant interface.
- **Key Responsibilities**:
  - Displays real-time ranks, task score breakdowns, and submission timestamps.
  - Powers side-by-side 3D WebGL motion playback (`viewer.html` engine) comparing Corrupted Input vs. Participant Reconstruction vs. Ground Truth (for public training/validation sets).

---

## 3. Security Boundaries & Isolation Model

```text
Participant Space (Untrusted) ──► Submission Validator (Trusted Boundary)
                                       │
                                       ▼
                              Container Sandbox (Isolated)
                              ├── No network
                              ├── Strict RAM / CPU quotas
                              └── Evaluator (Trusted Code)
                                       │
                                       ▼
                              Leaderboard Database (Secure)
```

1. **Ground Truth Confidentiality**: The hidden ground-truth directory (`hidden/ground_truth/`) is never mounted to participant code or exposed via APIs. Only the trusted evaluation engine reads these files.
2. **Determinism Guarantee**: Every calculation uses fixed floating-point representations and deterministic forward kinematics, guaranteeing that evaluating the same submission twice yields bit-for-bit identical scores.
