# MOTIONFORGE Local Competition Runner

**Version:** 0.1.0  
**Contract Version:** 1.0.0  
**Status:** Official Local Competition Execution Layer (Phase 6)  

---

## 1. Overview

The `runner/` package coordinates the official, deterministic end-to-end evaluation pipeline for MOTIONFORGE participant submissions.

It integrates:
1. **The Phase 5 Official Validator** (`validator/`) as an uncompromised gatekeeper.
2. **The Phase 4 Evaluation Engine** (`evaluation/`) for forward kinematics and physical metric computations.
3. **The Phase 3 / 4 Scoring Engine** (`evaluation/scoring/`) for calibrated exponential decay score mapping and 30/30/40 task aggregation.
4. **Job Lifecycle & Staging Management** (`runner/job_manager.py`) for deterministic status tracking and ephemeral isolation.
5. **Atomic Result Artifact Generation** (`runner/result_writer.py`) preventing partially written or corrupted JSON files.

---

## 2. End-to-End Pipeline Architecture

```text
                  Participant Submission (.zip)
                                │
                                ▼
                        [Job Created: QUEUED]
                                │
                                ▼
                       [State: VALIDATING]
                                │
                                ▼
                  Phase 5 Submission Validator
                  ├── Archive & Security Tests (traversal, bombs, symlinks, scripts)
                  ├── Schema Layout & Challenge Completeness
                  ├── Strict BVH Syntax (120 FPS / 0.0083333s)
                  ├── Canonical 31-Joint Hierarchy
                  ├── Numerical Safety (Zero NaN/Inf)
                  └── Task Invariants (Gap unchanged frames, Retarget proportions)
                                │
                 ┌──────────────┴──────────────┐
           (REJECTED)                    (ERROR)               (VALID)
                 │                             │                  │
                 ▼                             ▼                  ▼
        [State: REJECTED]          [State: VALIDATION_ERROR] [State: EVALUATING]
                 │                             │                  │
                 │ (STOP: Never Scored)        │ (STOP)           ▼
                 │                             │         Extract to Staging Sandbox
                 │                             │                  │
                 │                             │                  ▼
                 │                             │         Phase 4 Evaluation Engine
                 │                             │         ├── Task 1: Denoising FK
                 │                             │         ├── Task 2: Gap Inpainting FK
                 │                             │         └── Task 3: Retargeting FK
                 │                             │                  │
                 │                             │                  ▼
                 │                             │         Scoring & Aggregation
                 │                             │         └── 30% / 30% / 40% Weights
                 │                             │                  │
                 │                             │                  ▼
                 │                             │         [State: COMPLETED]
                 │                             │                  │
                 └──────────────┬──────────────┴──────────────────┘
                                │
                                ▼
                     Atomic JSON Result Write
                                │
                                ▼
                   Safe Ephemeral Sandbox Cleanup
```

---

## 3. Strict Gatekeeping Rule

> **A submission rejected by the validator is NEVER passed to the evaluation engine.**

- **Structural Failure**: Missing directories, non-BVH files, altered frame times, corrupt headers, or modified unoccluded frames immediately yield `REJECTED` status and process exit code `1`.
- **Score Integrity**: Rejected submissions receive an overall score of `null` (not evaluated), never confusing structural rejection with a valid submission achieving a low score.
- **Validator Fault**: If the validator experiences an internal error, the job transitions to `VALIDATION_ERROR` and halts with exit code `2`.

---

## 4. Job Lifecycle & State Machine

Every competition job follows an explicit, audited finite-state transition graph:

| Status | Type | Permitted Next States | Description |
|---|:---:|---|---|
| `QUEUED` | Initial | `VALIDATING`, `FAILED` | Job initialized with unique run identifier. |
| `VALIDATING` | Active | `REJECTED`, `VALIDATION_ERROR`, `EVALUATING`, `FAILED` | Actively undergoing Phase 5 pre-flight checks. |
| `REJECTED` | Terminal | *None* | Disqualified due to structural or data contract breach. |
| `VALIDATION_ERROR` | Terminal | *None* | Internal validator failure or system crash. |
| `EVALUATING` | Active | `COMPLETED`, `FAILED` | Passed validation; forward kinematics and scoring active. |
| `COMPLETED` | Terminal | *None* | Evaluated and scored successfully. |
| `FAILED` | Terminal | *None* | Unhandled runtime exception or missing input files. |

Any illegal transition (e.g. `REJECTED -> EVALUATING` or modifying a terminal state) raises `InvalidStateTransitionError`.

---

## 5. Security & Isolation Boundaries

1. **Zero Participant Code Execution**: The runner inspects and processes pre-rendered BVH motion data files only. Execution of participant Python scripts, shell scripts, notebooks, or compiled binaries is strictly disabled.
2. **Zero Network Access**: Evaluation and scoring operate completely offline.
3. **Safe Ephemeral Cleanup**: Extracted files and temporary symlinks are placed inside dedicated sandbox directories and deleted in a `finally` block on success or failure.
4. **Atomic Output Serialization**: All result JSON files are written via temporary files and atomic `os.replace` operations, ensuring no incomplete JSON files can exist.

---

## 6. Runner Exit Codes

In accordance with competition infrastructure standards:

| Exit Code | Final Job Status | Description |
|:---:|:---:|---|
| **0** | `COMPLETED` | Submission validated, evaluated, and scored successfully. |
| **1** | `REJECTED` | Submission rejected by Phase 5 pre-flight checks. |
| **2** | `VALIDATION_ERROR` / `FAILED` | Internal runner or validator exception, or missing input archive. |

---

## 7. CLI Usage

### Basic Invocation
```bash
python -m runner.competition_runner --submission path/to/submission.zip
```

### Specify Run ID and Output Directory
```bash
python -m runner.competition_runner \
    --submission submission.zip \
    --submission-id candidate_001 \
    --run-id job_2026_001 \
    --output-dir results/
```

### Evaluate Specific Tasks
```bash
python -m runner.competition_runner \
    --submission submission.zip \
    --tasks 1 2
```

### Quiet Mode (Machine-Readable JSON Only)
```bash
python -m runner.competition_runner \
    --submission submission.zip \
    --output results/result.json \
    --quiet
```

---

## 8. Result Artifact Schema

```json
{
  "schema_version": "1.0",
  "competition": "MOTIONFORGE",
  "runner_version": "0.1.0",
  "evaluator_version": "0.1.0",
  "validator_version": "0.1.0",
  "contract_version": "1.0.0",
  "calibration_version": "phase3_calibrated_2026",
  "job_id": "job_001",
  "submission_id": "candidate_001",
  "job_status": "COMPLETED",
  "validation_status": "VALID",
  "overall_score": 84.72,
  "task_scores": {
    "denoising": 88.15,
    "gap_filling": 82.40,
    "retargeting": 83.89
  },
  "scoring_weights": {
    "denoising": 0.30,
    "gap_filling": 0.30,
    "retargeting": 0.40
  },
  "metrics": { ... },
  "validation_errors": [],
  "validation_checks": {
    "archive": "PASS",
    "security": "PASS",
    "schema": "PASS",
    "bvh": "PASS",
    "skeleton": "PASS",
    "motion": "PASS",
    "task": "PASS"
  },
  "error_message": null,
  "runtime_seconds": 1.4520,
  "timestamps": {
    "created_at": "2026-10-14T12:00:00Z",
    "started_at": "2026-10-14T12:00:00.010Z",
    "completed_at": "2026-10-14T12:00:01.462Z"
  },
  "status_history": [ ... ]
}
```
