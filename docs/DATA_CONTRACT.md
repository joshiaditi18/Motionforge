# MOTIONFORGE — Technical Data Contract & Interface Specification

- **Document ID**: `MOTIONFORGE-CONTRACT-V1.0`
- **Status**: `FROZEN FOR PHASE 2`
- **Standard**: Biovision Hierarchy (BVH) / JSON Data Exchange
- **Version**: 1.0.0

---

## 1. System Pipeline Overview

This contract governs data structures and interfaces between all components in the MOTIONFORGE evaluation lifecycle:

```text
       ┌────────────────────────┐
       │   Public Input Data    │
       └───────────┬────────────┘
                   │
                   ▼ [Contract Interface 1]
       ┌────────────────────────┐
       │  Participant Algorithm │
       └───────────┬────────────┘
                   │
                   ▼ [Contract Interface 2]
       ┌────────────────────────┐
       │  Candidate Submission  │
       └───────────┬────────────┘
                   │
                   ▼ [Contract Interface 3]
       ┌────────────────────────┐
       │  Submission Validator  │ ── (Fail) ──► Status: REJECTED (Score: 0.0)
       └───────────┬────────────┘
                   │ (Pass)
                   ▼ [Contract Interface 4]
       ┌────────────────────────┐      ┌────────────────────────┐
       │   Evaluation Engine    │ ◄─── │   Hidden Ground Truth  │
       └───────────┬────────────┘      └────────────────────────┘
                   │
                   ▼ [Contract Interface 5]
       ┌────────────────────────┐
       │  Leaderboard Score JSON│
       └────────────────────────┘
```

---

## 2. Interface 1: Input Data Contract (Evaluator $\rightarrow$ Participant)

The participant code ingests motion sequences formatted strictly according to this schema.

### 2.1 File Location & Access
- **Input Directory**: Provided via command-line argument `--input_dir <path>` or environment variable `MF_INPUT_DIR`.
- **File System Permissions**: Read-only (`ro`).

### 2.2 Task Input Schemas

#### Task 1 (Denoising Input)
- **Path Pattern**: `{input_dir}/denoising/{motion_id}_{noise_level}.bvh`
- **Variables**:
  - `motion_id`: Formatted as `MF[0-9]{3}` (e.g., `MF004`).
  - `noise_level`: Enum string `['low', 'medium', 'high']`.

#### Task 2 (Gap-Filling Input)
- **Path Pattern**: `{input_dir}/gap_filling/{motion_id}_{gap_type}.bvh`
- **Variables**:
  - `motion_id`: Formatted as `MF[0-9]{3}`.
  - `gap_type`: Enum string `['short', 'medium', 'long']`.

#### Task 3 (Retargeting Input)
- **Source Motion**: `{input_dir}/retargeting/sources/{motion_id}_clean.bvh`
- **Target Skeleton Template**: `{input_dir}/retargeting/targets/{motion_id}_{target_type}.bvh`
- **Variables**:
  - `target_type`: Enum string `['target_small', 'target_medium', 'target_tall']`.

---

## 3. Interface 2: Participant Output Contract (Participant $\rightarrow$ Submission Archive)

The participant algorithm must generate a compressed `.zip` archive containing exact output hierarchies.

### 3.1 Directory Topology
```text
submission.zip/
├── denoising/
│   ├── MF004_low.bvh
│   ├── MF004_medium.bvh
│   ├── MF004_high.bvh
│   └── ...
├── gap_filling/
│   ├── MF004_short.bvh
│   ├── MF004_medium.bvh
│   ├── MF004_long.bvh
│   └── ...
└── retargeting/
    ├── MF004_target_small.bvh
    ├── MF004_target_medium.bvh
    ├── MF004_target_tall.bvh
    └── ...
```

### 3.2 BVH Structural Invariants
Every `.bvh` file in the archive must satisfy these technical invariants:

```text
BVH Invariant Checklist:
├── Line 1: 'HIERARCHY'
├── Root Node: Exactly 'ROOT Hips'
├── Skeleton Node Count: Exactly 31 JOINT nodes + 7 End Site nodes
├── Channel Count: Exactly 96 scalar channels
├── Channel Order (Root): Xposition Yposition Zposition Zrotation Yrotation Xrotation
├── Channel Order (Joints): Zrotation Yrotation Xrotation
├── Section Divider: Exactly 'MOTION'
├── Frame Header 1: 'Frames: <N>' (N strictly equals ground-truth frame count)
├── Frame Header 2: 'Frame Time: 0.0083333'
└── Data Rows: Exactly N space-delimited rows of 96 IEEE-754 floating point numbers
```

---

## 4. Interface 3: Submission Validator Contract (Validator Component)

The Validator inspects the submission before passing it to the evaluation sandbox.

### 4.1 Invocation Signature
```bash
python scripts/validate_submission.py \
    --submission_path <path_to_submission.zip> \
    --manifest_path <path_to_dataset_manifest.json> \
    --output_report <path_to_validation_result.json>
```

### 4.2 Exit Codes
- `0`: **SUCCESS / VALID** — Archive passes all structural requirements.
- `1`: **STRUCTURAL ERROR / REJECTED** — Archive corrupt, missing files, or BVH hierarchy violated.
- `2`: **INTERNAL VALIDATOR ERROR** — Unexpected runtime exception in validator script.

### 4.3 Validation Output Schema (`validation_result.json`)
```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "file_summary": {
    "total_files_found": 27,
    "total_files_expected": 27,
    "denoising_files": 9,
    "gap_filling_files": 9,
    "retargeting_files": 9
  },
  "timestamp": "2026-10-08T09:16:00Z"
}
```

---

## 5. Interface 4: Evaluation Engine Contract (Evaluator Component)

The evaluator consumes verified candidate BVH files and compares them against isolated hidden ground-truth files.

### 5.1 Invocation Signature
```bash
python evaluation/evaluate_submission.py \
    --submission_dir <path_to_unzipped_submission> \
    --ground_truth_dir <path_to_hidden_ground_truth> \
    --metadata_dir <path_to_metadata> \
    --output_json <path_to_final_score.json>
```

### 5.2 Input Invariants
- `submission_dir`: Guaranteed to contain valid, pre-screened `.bvh` files.
- `ground_truth_dir`: Read-only access to sequestered ground-truth files (`hidden/ground_truth/`).
- Sandboxing: No subprocesses may write outside the designated score output directory.

---

## 6. Interface 5: Leaderboard Score JSON Contract (Evaluator $\rightarrow$ Backend/Leaderboard)

This is the definitive machine-readable artifact produced at the conclusion of every evaluation run.

### 6.1 JSON Schema Specification

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "MotionforgeEvaluationResult",
  "type": "object",
  "required": [
    "submission_id",
    "status",
    "overall_score",
    "task_scores",
    "metrics",
    "runtime_seconds",
    "timestamp"
  ],
  "properties": {
    "submission_id": { "type": "string" },
    "status": { "type": "string", "enum": ["VALID", "REJECTED", "ERROR"] },
    "overall_score": { "type": "number", "minimum": 0.0, "maximum": 100.0 },
    "task_scores": {
      "type": "object",
      "required": ["denoising", "gap_filling", "retargeting"],
      "properties": {
        "denoising": { "type": "number", "minimum": 0.0, "maximum": 100.0 },
        "gap_filling": { "type": "number", "minimum": 0.0, "maximum": 100.0 },
        "retargeting": { "type": "number", "minimum": 0.0, "maximum": 100.0 }
      }
    },
    "metrics": {
      "type": "object",
      "required": ["denoising", "gap_filling", "retargeting"],
      "properties": {
        "denoising": {
          "type": "object",
          "properties": {
            "mean_mpjpe": { "type": "number" },
            "mean_velocity_error": { "type": "number" },
            "mean_jitter": { "type": "number" },
            "preservation_ratio": { "type": "number" }
          }
        },
        "gap_filling": {
          "type": "object",
          "properties": {
            "mean_inpainting_mpjpe": { "type": "number" },
            "mean_boundary_error": { "type": "number" },
            "mean_velocity_boundary_error": { "type": "number" },
            "foot_skating_score": { "type": ["number", "null"] }
          }
        },
        "retargeting": {
          "type": "object",
          "properties": {
            "end_effector_error": { "type": "number" },
            "angular_geodesic_error": { "type": "number" },
            "bone_length_violation_max": { "type": "number" },
            "ground_penetration_penalty": { "type": "number" }
          }
        }
      }
    },
    "runtime_seconds": { "type": "number" },
    "error_message": { "type": ["string", "null"] },
    "timestamp": { "type": "string", "format": "date-time" }
  }
}
```
