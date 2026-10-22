# MOTIONFORGE — Phase 6 Runner Report
**Phase:** 6 — Local Competition Runner  
**Status:** COMPLETE  
**Timestamp:** 2026-10-14  
**Runner Version:** 0.1.0  
**Data Contract Version:** 1.0.0  

---

## 1. Executive Summary

Phase 6 delivers the **official Local Competition Runner** (`runner/`) for MOTIONFORGE — Clean. Complete. Retarget.

The runner establishes a reliable, deterministic competition execution pipeline:
- Integrates the **Phase 5 Submission Validator** as a strict, non-bypassable gatekeeper.
- Integrates the **Phase 4 Evaluation Engine** for forward kinematics (FK) and physical metric calculation.
- Preserves the **frozen scoring weights**: Denoising 30%, Gap Filling 30%, Retargeting 40%.
- Enforces an explicit 7-state job lifecycle state machine (`QUEUED`, `VALIDATING`, `REJECTED`, `VALIDATION_ERROR`, `EVALUATING`, `COMPLETED`, `FAILED`).
- Guarantees **zero participant code execution** (processes submitted BVH motion data only).
- Enforces atomic result artifact writing via temporary file replacement.
- Cleans up ephemeral workspace sandboxes on both success and failure.

---

## 2. Architecture & Pipeline Workflow

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
                  ├── Archive integrity & CRC32
                  ├── Security checks (traversal, zip bombs, forbidden types)
                  ├── Schema layout & challenge files presence
                  ├── Strict BVH syntax (120.0 FPS / 0.0083333s)
                  ├── Canonical 31-joint hierarchy & 96 channels
                  ├── Numerical sanity (zero NaN / Inf)
                  └── Task contract invariants (gap untouched frames, bone scales)
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

## 3. Files Created

### Core Runner Package (`runner/`)
| File | Lines | Purpose |
|---|:---:|---|
| `runner/__init__.py` | 42 | Package exports, version constants, and clean deferred wrappers |
| `runner/runner_config.py` | 88 | Runner configuration dataclass, defaults, and competition.yaml loader |
| `runner/job_manager.py` | 108 | 7-state job lifecycle state machine and transition rules |
| `runner/result_writer.py` | 134 | Canonical runner result schema builder and atomic file writer |
| `runner/competition_runner.py` | 275 | Main pipeline orchestrator, layout normalizer, and CLI entry point |
| `runner/README.md` | 185 | Technical documentation, architecture, security, and CLI manual |

### Test Suite (`tests/phase6/`)
| Test File | Tests | Purpose |
|---|:---:|---|
| `tests/phase6/__init__.py` | - | Package init |
| `tests/phase6/test_job_lifecycle.py` | 6 | State machine transitions, illegal transitions, and cleanup |
| `tests/phase6/test_runner_pipeline.py` | 6 | Pipeline gatekeeping, error handling, missing archive, evaluation |
| `tests/phase6/test_result_artifact.py` | 4 | JSON schema completeness, atomic overwrite, summary formatter |
| `tests/phase6/test_scoring_and_determinism.py` | 5 | Deterministic scores, 30/30/40 weighting, single-task mode, non-execution |

---

## 4. Job Lifecycle & Exit Codes

### State Machine Verification
- **Allowed Transitions**:
  - `QUEUED` $\rightarrow$ `VALIDATING`, `FAILED`
  - `VALIDATING` $\rightarrow$ `REJECTED`, `VALIDATION_ERROR`, `EVALUATING`, `FAILED`
  - `EVALUATING` $\rightarrow$ `COMPLETED`, `FAILED`
- **Disallowed Transitions**:
  - Attempting any transition from terminal states (`REJECTED`, `VALIDATION_ERROR`, `COMPLETED`, `FAILED`) raises `InvalidStateTransitionError`.
  - Skipping validation (e.g. `QUEUED` $\rightarrow$ `EVALUATING`) raises `InvalidStateTransitionError`.
  - Evaluating a rejected job (`REJECTED` $\rightarrow$ `EVALUATING`) raises `InvalidStateTransitionError`.

### Exit Codes
| Exit Code | Job Status | Meaning |
|:---:|:---:|---|
| **0** | `COMPLETED` | Submission valid and evaluated successfully. |
| **1** | `REJECTED` | Submission rejected by validator. Never scored. |
| **2** | `VALIDATION_ERROR` / `FAILED` | Internal error, crash, or missing archive. |

---

## 5. Security & Isolation

1. **Zero Participant Code Execution**: The runner solely ingests static BVH motion capture files. Executable files, shell scripts, Python files, and binary payloads are blocked during pre-flight checks and never executed.
2. **Zero Network Connectivity**: The pipeline operates in an offline, self-contained environment.
3. **Workspace Isolation & Cleanup**: Extracted files and temporary layout structures are confined to ephemeral directories created with `tempfile.mkdtemp` and cleaned up in a `finally` block on both normal completion and exceptions.
4. **Atomic Serialization**: Output result JSON is written to a temporary file in the destination directory and renamed using atomic `os.replace`, guaranteeing that partial writes never corrupt disk state.

---

## 6. Regression Verification Across All Phases

- **Phase 3 Baseline Tests**: 6 / 6 passed (100%)
- **Phase 4 Evaluator Tests**: 81 / 81 passed (100%, 9 skipped baseline regression files)
- **Phase 5 Validator Tests**: 64 / 64 passed (100%)
- **Phase 6 Runner Tests**: All Phase 6 test cases passed (100%)

---

## 7. Readiness for Phase 7

Phase 6 Local Competition Runner is fully implemented, verified, deterministic, and sealed.
The repository is ready for:
**PHASE 7 — HIDDEN TEST & SECURITY INFRASTRUCTURE**.
