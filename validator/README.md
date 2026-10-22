# MOTIONFORGE Submission Validator

**Version:** 0.1.0  
**Contract Version:** 1.0.0  
**Standard:** Biovision Hierarchy (BVH) / JSON Data Exchange  

---

## 1. Overview

The `validator/` module implements the **official, deterministic submission validation layer** for MOTIONFORGE — Clean. Complete. Retarget.

Its sole responsibility is to answer:
> *"Is this submission structurally and contractually valid for evaluation?"*

It acts as a strict, secure gate between untrusted participant submission archives and the official evaluation engine. It enforces all hard invariants defined in `docs/DATA_CONTRACT.md` and `docs/COMPETITION_SPECIFICATION.md` without computing algorithm quality scores.

---

## 2. Validation Pipeline Architecture

```text
Submission Archive (.zip)
          │
          ▼
1. Archive Validation       ── [Integrity, Size <= 100MB, Format]
          │
          ▼
2. Security Validation      ── [Path Traversal, Symlinks, Zip Bombs, Forbidden Files]
          │
          ▼
3. Schema Validation        ── [Task Directories, Metadata, File Completeness]
          │
          ▼ (For each BVH output)
4. BVH Syntax Validation    ── [HIERARCHY, ROOT Hips, MOTION, 120 FPS / 0.0083333s]
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

## 3. Exit Codes

In accordance with `docs/DATA_CONTRACT.md` §4.2:

| Exit Code | Status | Meaning |
|:---:|:---:|---|
| **0** | `VALID` | Submission satisfies all structural and contractual criteria. Ready for evaluation. |
| **1** | `REJECTED` | Submission contains structural, security, or contractual defects. Disqualified from scoring. |
| **2** | `ERROR` | Unexpected internal validator error or environment exception. |

---

## 4. Security & Resource Protection

Untrusted archives are rigorously isolated and checked prior to unpacking:

- **Path Traversal Protection**: Rejects `../`, `..\`, absolute paths (`/`), Windows drive paths (`C:\`), and UNC network paths (`\\`).
- **Archive Size Cap**: Compressed archive size strictly limited to **100 MB**.
- **Uncompressed Size Cap**: Maximum total uncompressed payload limited to **500 MB**.
- **Member Count Cap**: Maximum archive member count limited to **1,000 files**.
- **Compression Ratio Cap**: Guards against zip bombs by flagging ratios $> 100:1$.
- **Symbolic Link Rejection**: Detects and rejects UNIX symbolic link entries.
- **Prohibited File Types**: Immediately rejects binary executables or scripts (`.exe`, `.dll`, `.so`, `.sh`, `.bat`, `.py`, etc.).
- **Safe Extraction**: Extracts only to an ephemeral temporary directory, guaranteed to be destroyed in a `finally` block.

---

## 5. Technical Validation Invariants

### 5.1 BVH Invariants
- First non-empty line must start with `HIERARCHY`.
- Root joint must be strictly `ROOT Hips`.
- Contains `MOTION` divider.
- Frame count $N > 0$.
- `Frame Time: 0.0083333` strictly enforced (120.0 FPS, tolerance $\pm 10^{-5}$).

### 5.2 Skeleton Invariants
- Functional anatomical joints: exactly **31 joints** in canonical order (`CANONICAL_31_JOINTS`).
- End Sites: exactly **7 terminal End Sites** with canonical parent attachments.
- Motion channels: exactly **96 scalar channels**.
- Root channels: `Xposition Yposition Zposition Zrotation Yrotation Xrotation`.
- Joint channels: `Zrotation Yrotation Xrotation` (Z-Y-X Euler rotation order).
- Offsets: valid 3D vectors with no `NaN` or `Inf`.

### 5.3 Motion Matrix Invariants
- Shape: 2D array of dimension `(N, 96)`.
- Finiteness: zero tolerance for `NaN`, `Inf`, `-Inf`, or invalid float tokens.
- Frame count must match reference motion length.

### 5.4 Task-Specific Invariants
- **Task 1 (Denoising)**: Frame count preservation. Does not reject poor denoising (quality is scored by Phase 4 evaluator).
- **Task 2 (Gap Filling)**: Contract invariant: observed frames outside gap $[t_{start}, t_{end}]$ must remain strictly unmodified ($L_\infty \le 10^{-6}$).
- **Task 3 (Retargeting)**: Valid target morphology (`target_small`, `target_medium`, `target_tall`). Rest bone lengths must adhere to assigned target scaling proportions within tolerance.

---

## 6. Stable Error Codes

| Code Category | Error Code | Description |
|---|---|---|
| **Archive** | `ARCHIVE_NOT_FOUND` | Archive file not found or inaccessible |
| | `ARCHIVE_CORRUPTED` | Malformed zip or CRC checksum failure |
| | `ARCHIVE_TOO_LARGE` | Compressed archive $> 100\text{ MB}$ or uncompressed $> 500\text{ MB}$ |
| | `ARCHIVE_TOO_MANY_FILES` | Member count $> 1,000$ files |
| | `SUSPICIOUS_COMPRESSION_RATIO` | Excessive compression ratio (zip bomb signature) |
| **Security** | `PATH_TRAVERSAL` | Path climbing (`..`), absolute, or UNC path |
| | `UNSAFE_SYMLINK` | Symbolic link entry in archive |
| | `FORBIDDEN_FILE_TYPE` | Executable or script payload detected |
| **Schema** | `MISSING_REQUIRED_DIRECTORY` | Missing task directory (`denoising/`, `gap_filling/`, etc.) |
| | `MISSING_REQUIRED_FILE` | Missing challenge output for an evaluation motion |
| | `UNEXPECTED_FILE` | Non-BVH file inside task directory |
| | `INVALID_METADATA` | Malformed or invalid JSON/YAML metadata |
| | `INVALID_TASK` | Unknown task identifier |
| **BVH / Format** | `INVALID_BVH` | Unparseable BVH or missing section |
| | `INVALID_BVH_HEADER` | Header does not start with `HIERARCHY` |
| | `INVALID_FRAME_TIME` | Frame time altered from $0.0083333\text{ s}$ |
| | `INVALID_FPS` | Sampling rate deviates from $120.0\text{ FPS}$ |
| | `INVALID_FRAME_COUNT` | Frame count $\le 0$ or mismatched from reference |
| **Skeleton** | `INVALID_ROOT_JOINT` | Root is not `Hips` |
| | `INVALID_JOINT_COUNT` | Functional joint count $\ne 31$ |
| | `INVALID_JOINT_ORDER` | Canonical joint order violated |
| | `INVALID_END_SITE` | End site count $\ne 7$ or incorrect parent |
| | `INVALID_CHANNEL_COUNT` | Channel count $\ne 96$ |
| | `INVALID_CHANNEL_ORDER` | Root or rotation channel order violated |
| | `INVALID_HIERARCHY` | Parent-child relationship mismatch |
| **Numerical** | `INVALID_MOTION_SHAPE` | Motion array dimension $\ne (N, 96)$ |
| | `EMPTY_MOTION_DATA` | Motion array has 0 frames |
| | `NAN_DETECTED` | IEEE-754 NaN detected in data or offsets |
| | `INF_DETECTED` | IEEE-754 Inf detected in data or offsets |
| **Task Contracts** | `OBSERVED_FRAME_MODIFIED` | Task 2 observed frames outside gap modified |
| | `INVALID_TARGET` | Task 3 unknown target avatar morphology |
| | `BONE_LENGTH_VIOLATION` | Task 3 rest bone offsets do not match target proportions |
| **Internal** | `INTERNAL_VALIDATION_ERROR` | Unexpected validator runtime exception |

---

## 7. CLI Usage

### Basic Invocation
```bash
python -m validator.validator --submission submission.zip
```

### Validate Specific Task
```bash
python -m validator.validator --submission submission.zip --task denoising
```

### Save Machine-Readable JSON Report
```bash
python -m validator.validator \
    --submission submission.zip \
    --output validation_result.json
```

### Sample Output: Valid Submission
```text
==================================================
MOTIONFORGE SUBMISSION VALIDATION
==================================================
Submission ID : candidate_001
Task          : all
Runtime       : 0.1240s

Validation Checks:
  Archive ............ PASS
  Security ........... PASS
  Schema ............. PASS
  Bvh ................ PASS
  Skeleton ........... PASS
  Motion ............. PASS
  Task ............... PASS

Files Found   : 27
STATUS        : VALID
EXIT CODE     : 0
==================================================
```

### Sample Output: Rejected Submission
```text
==================================================
MOTIONFORGE SUBMISSION VALIDATION
==================================================
Submission ID : malformed_sub
Task          : denoising
Runtime       : 0.0450s

Validation Checks:
  Archive ............ PASS
  Security ........... PASS
  Schema ............. PASS
  Bvh ................ FAIL
  Skeleton ........... FAIL
  Motion ............. PASS
  Task ............... PASS

Files Found   : 9
STATUS        : REJECTED
EXIT CODE     : 1

ERRORS:
  - INVALID_FRAME_TIME: Frame Time is 0.0166667 (60.0 FPS), expected 0.0083333 (120.0 FPS) [MF002_low.bvh]
  - INVALID_JOINT_ORDER: Joint mismatch at index 1: found 'LeftUpLeg', expected 'LHipJoint' [MF002_low.bvh]
==================================================
```
