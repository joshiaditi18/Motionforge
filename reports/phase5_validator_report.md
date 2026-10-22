# MOTIONFORGE — Phase 5 Validator Report
**Phase:** 5 — Official Submission Validator  
**Status:** COMPLETE  
**Timestamp:** 2026-10-12  
**Validator Version:** 0.1.0  
**Data Contract Version:** 1.0.0  

---

## 1. Executive Summary

Phase 5 delivers the **official, deterministic submission validation layer** for the MOTIONFORGE competition benchmark. The validator enforces all technical, structural, and security invariants from `docs/DATA_CONTRACT.md` and `docs/COMPETITION_SPECIFICATION.md` prior to evaluation.

### Key Deliverables:
- **Modular Validator Architecture**: 9 functional modules in `validator/` covering archive integrity, path sanitization, schema layout, BVH syntax, skeleton topology, motion numerical safety, and task contract invariants.
- **Strict Separation of Concerns**: Validates *structural and contractual compliance* only; never evaluates motion quality or computes scores.
- **Robust Security & Resource Protection**: Rejects directory traversal (`../`, `..\`), absolute/drive/UNC paths, symlinks, zip bombs (size/ratio/file count limits), and executable payloads.
- **Deterministic 3-State Status & Exit Codes**: Returns strictly `VALID` (exit 0), `REJECTED` (exit 1), or `ERROR` (exit 2).
- **Comprehensive Test Suite**: 10 test files with 64 test cases in `tests/phase5/`, achieving 100% pass rate.
- **Zero Regressions**: 100% pass rate maintained across Phase 3 and Phase 4 test suites.

---

## 2. Validator Architecture & Pipeline

```text
Submission Archive (.zip) / Directory
              │
              ▼
    1. Archive Validation       ── [Integrity testzip(), Size <= 100MB, Format .zip]
              │
              ▼
    2. Security Validation      ── [Path Traversal, Drive/UNC, Symlinks, Zip Bombs, Forbidden Types]
              │
              ▼
    3. Schema Validation        ── [Task Directories, Metadata JSON, File Completeness]
              │
              ▼ (For each BVH output)
    4. BVH Syntax Validation    ── [HIERARCHY, ROOT Hips, MOTION, 120.0 FPS / 0.0083333s]
              │
              ▼
    5. Skeleton Validation      ── [31 Functional Joints, 7 End Sites, 96 Channels, Z-Y-X Euler]
              │
              ▼
    6. Motion Validation        ── [Shape (N, 96), Non-Empty, Strict NaN / Inf Rejection]
              │
              ▼
    7. Task Invariants          ── [Task 1: Frame Match; Task 2: Untouched Observed Frames; Task 3: Target Proportions]
              │
              ▼
    Final Validation Result     ──> VALID (0) | REJECTED (1) | ERROR (2)
```

---

## 3. Files Created

### Core Validator Package (`validator/`)
| File | Lines | Purpose |
|---|:---:|---|
| `validator/__init__.py` | 27 | Package exports and version constants |
| `validator/error_codes.py` | 55 | Stable, non-sensitive ErrorCode enum |
| `validator/validation_result.py` | 108 | Schema, ValidationStatus, and JSON serializer |
| `validator/security_validator.py` | 178 | Zip path sanitization, symlink/bomb detection, safe extraction |
| `validator/archive_validator.py` | 114 | Zip existence, size, format, and CRC integrity check |
| `validator/schema_validator.py` | 192 | Directory layout, metadata validation, file counting |
| `validator/bvh_validator.py` | 165 | Strict line-level BVH syntax, 120 FPS frame time check |
| `validator/skeleton_validator.py` | 158 | 31 canonical joints, 7 end sites, 96 channels, hierarchy |
| `validator/motion_validator.py` | 102 | Motion matrix shape, non-empty, strict NaN/Inf rejection |
| `validator/task_validator.py` | 148 | Task 1 frame match, Task 2 untouched frames, Task 3 target rest bone proportions |
| `validator/validator.py` | 315 | Main validation orchestrator and CLI entry point |
| `validator/README.md` | 190 | Technical documentation and user guide |

### Test Suite (`tests/phase5/`)
| Test File | Test Count | Status |
|---|:---:|:---:|
| `tests/phase5/__init__.py` | - | - |
| `tests/phase5/test_archive_validation.py` | 7 | ✅ Passed |
| `tests/phase5/test_security_validation.py` | 9 | ✅ Passed |
| `tests/phase5/test_schema_validation.py` | 6 | ✅ Passed |
| `tests/phase5/test_bvh_validation.py` | 7 | ✅ Passed |
| `tests/phase5/test_skeleton_validation.py` | 8 | ✅ Passed |
| `tests/phase5/test_motion_validation.py` | 7 | ✅ Passed |
| `tests/phase5/test_task_validation.py` | 7 | ✅ Passed |
| `tests/phase5/test_valid_submissions.py` | 2 | ✅ Passed |
| `tests/phase5/test_invalid_submissions.py` | 9 | ✅ Passed |
| `tests/phase5/test_determinism.py` | 2 | ✅ Passed |
| **Total Phase 5 Tests** | **64** | **100% Passed** |

---

## 4. Test Results & Matrix

### A. Valid Submissions
| Test Case | Output Status | Exit Code | Checks Summary |
|---|:---:|:---:|---|
| Full Multi-Task Archive (9 BVH files) | `VALID` | `0` | All 7 checks PASS |
| Single-Task Denoising Submission | `VALID` | `0` | All checks PASS |

### B. Invalid Submissions Matrix
| Test Case | Triggered Error Code | Expected Status | Actual Status | Exit Code |
|---|---|:---:|:---:|:---:|
| Missing archive file | `ARCHIVE_NOT_FOUND` | `REJECTED` | `REJECTED` | `1` |
| Corrupted zip archive (invalid magic / payload) | `ARCHIVE_CORRUPTED` | `REJECTED` | `REJECTED` | `1` |
| Archive exceeding 100 MB | `ARCHIVE_TOO_LARGE` | `REJECTED` | `REJECTED` | `1` |
| Path climbing traversal (`../../evil.txt`) | `PATH_TRAVERSAL` | `REJECTED` | `REJECTED` | `1` |
| Windows drive path (`C:\evil.txt`) | `PATH_TRAVERSAL` | `REJECTED` | `REJECTED` | `1` |
| Prohibited executable file (`.py` script) | `FORBIDDEN_FILE_TYPE` | `REJECTED` | `REJECTED` | `1` |
| Symbolic link entry in archive | `UNSAFE_SYMLINK` | `REJECTED` | `REJECTED` | `1` |
| Member count exceeding 1,000 files | `ARCHIVE_TOO_MANY_FILES` | `REJECTED` | `REJECTED` | `1` |
| Missing required task directory | `MISSING_REQUIRED_DIRECTORY` | `REJECTED` | `REJECTED` | `1` |
| Missing challenge output for evaluated motion | `MISSING_REQUIRED_FILE` | `REJECTED` | `REJECTED` | `1` |
| Unexpected non-BVH file in task folder | `UNEXPECTED_FILE` | `REJECTED` | `REJECTED` | `1` |
| Malformed JSON in metadata | `INVALID_METADATA` | `REJECTED` | `REJECTED` | `1` |
| Header missing `HIERARCHY` | `INVALID_BVH_HEADER` | `REJECTED` | `REJECTED` | `1` |
| Missing `MOTION` section | `INVALID_BVH` | `REJECTED` | `REJECTED` | `1` |
| Altered Frame Time (60 FPS instead of 120 FPS) | `INVALID_FRAME_TIME` | `REJECTED` | `REJECTED` | `1` |
| Frame count $\le 0$ | `INVALID_FRAME_COUNT` | `REJECTED` | `REJECTED` | `1` |
| Root joint name not `Hips` | `INVALID_ROOT_JOINT` | `REJECTED` | `REJECTED` | `1` |
| Functional joint count $\ne 31$ | `INVALID_JOINT_COUNT` | `REJECTED` | `REJECTED` | `1` |
| Canonical joint order violated | `INVALID_JOINT_ORDER` | `REJECTED` | `REJECTED` | `1` |
| Channel count $\ne 96$ | `INVALID_CHANNEL_COUNT` | `REJECTED` | `REJECTED` | `1` |
| Root channel order violated | `INVALID_CHANNEL_ORDER` | `REJECTED` | `REJECTED` | `1` |
| Parent-child hierarchy mismatch | `INVALID_HIERARCHY` | `REJECTED` | `REJECTED` | `1` |
| Motion array contains IEEE-754 `NaN` | `NAN_DETECTED` | `REJECTED` | `REJECTED` | `1` |
| Motion array contains IEEE-754 `Inf` | `INF_DETECTED` | `REJECTED` | `REJECTED` | `1` |
| Empty motion data (0 frames) | `EMPTY_MOTION_DATA` | `REJECTED` | `REJECTED` | `1` |
| Task 2 modified observed frames | `OBSERVED_FRAME_MODIFIED` | `REJECTED` | `REJECTED` | `1` |
| Task 3 unknown target avatar morphology | `INVALID_TARGET` | `REJECTED` | `REJECTED` | `1` |
| Task 3 target rest bone proportions violated | `BONE_LENGTH_VIOLATION` | `REJECTED` | `REJECTED` | `1` |

### C. Security Hardening Tests
| Attack Vector | Defense Mechanism | Test Result |
|---|---|:---:|
| `../` Directory Traversal | Pre-extraction path normalization & check | Blocked (`PATH_TRAVERSAL`) |
| `..\` Windows Traversal | Normalized slash check | Blocked (`PATH_TRAVERSAL`) |
| Absolute Paths (`/root/evil.txt`) | Root slash check | Blocked (`PATH_TRAVERSAL`) |
| Drive Letter (`C:\evil.txt`) | Drive pattern regex check | Blocked (`PATH_TRAVERSAL`) |
| UNC Network Shares (`\\server\share`) | UNC pattern regex check | Blocked (`PATH_TRAVERSAL`) |
| Symlink Poisoning | `ZipInfo.external_attr` mode inspection | Blocked (`UNSAFE_SYMLINK`) |
| Malicious Executables (`.exe`, `.py`, `.sh`) | Extension blacklist inspection | Blocked (`FORBIDDEN_FILE_TYPE`) |
| Zip Bomb / Resource Depletion | Size, member count, ratio caps | Blocked |

### D. Determinism
Repeated validation runs on both valid and invalid submission archives confirmed:
- Identical `status` (`VALID` / `REJECTED`)
- Identical error codes and error messages
- Identical validation checks map
- Identical `file_summary` counts
- Identical process exit codes (0 / 1)

---

## 5. Performance Profile

Measured on the 9-motion full challenge submission archive:
- **Archive Extraction Time**: ~0.025 seconds
- **Schema & Layout Validation**: ~0.008 seconds
- **BVH Syntax Parsing (9 files)**: ~0.082 seconds
- **Skeleton & Topology Validation**: ~0.005 seconds
- **Motion & Numerical Check**: ~0.012 seconds
- **Task Invariant Validation**: ~0.009 seconds
- **Total End-to-End Validation Time**: **~0.141 seconds**
- **Peak RAM Overhead**: $< 25\text{ MB}$

The validation pass is approximately **100x faster** than full kinematic metric evaluation in Phase 4, providing instant rejection of malformed or invalid submissions without wasting evaluation server compute.

---

## 6. Regression Status Across Prior Phases

- **Phase 3 Baseline Tests**: 6 / 6 passed (100%)
- **Phase 4 Evaluation Tests**: 81 / 81 passed (100%, 9 skipped baseline regression files)
- **Phase 5 Validator Tests**: 64 / 64 passed (100%)

---

## 7. Known Issues & Classifications

1. **Foot Contact Velocity Threshold**: `RESOLVED` in Phase 4 (implemented default 0.539 in/s). Does not affect validator.
2. **Distal Endpoint Inpainting Evaluation**: `RESOLVED` in Phase 4. Does not affect validator.
3. **Archive Directory Aliases**: `RESOLVED` in Phase 5 schema validator (accepts both `denoising`/`task1`, `gap_filling`/`task2`, `retargeting`/`task3`).

---

## 8. Phase 6 Readiness

The official submission validation layer is complete, verified, and sealed.
The system is fully prepared for:
**PHASE 6 — LOCAL COMPETITION RUNNER**.
