"""
validation_result.py — MOTIONFORGE Phase 5 Validation Result Schema & Data Structures

Defines the canonical validation result structure, error reporting objects,
and status definitions matching DATA_CONTRACT.md §4.2-4.3 and Phase 5 specification.

Status enum:
    VALID    — submission passes all structural and data contract requirements (exit code 0)
    REJECTED — structural or contract violation detected (exit code 1)
    ERROR    — unexpected internal validator exception (exit code 2)
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any, List

from validator.error_codes import ErrorCode


class ValidationStatus(str, Enum):
    VALID = "VALID"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


EXIT_CODE_MAP: Dict[ValidationStatus, int] = {
    ValidationStatus.VALID: 0,
    ValidationStatus.REJECTED: 1,
    ValidationStatus.ERROR: 2,
}


@dataclass
class ValidationError:
    code: str
    message: str
    file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.file:
            d["file"] = self.file
        return d


@dataclass
class ValidationResult:
    validator_version: str = "0.1.0"
    contract_version: str = "1.0.0"
    status: ValidationStatus = ValidationStatus.VALID
    submission_id: str = "unknown"
    task: Optional[str] = None
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checks: Dict[str, str] = field(default_factory=lambda: {
        "archive": "PASS",
        "security": "PASS",
        "schema": "PASS",
        "bvh": "PASS",
        "skeleton": "PASS",
        "motion": "PASS",
        "task": "PASS",
    })
    file_summary: Dict[str, Any] = field(default_factory=lambda: {
        "total_files_found": 0,
        "total_files_expected": 0,
        "denoising_files": 0,
        "gap_filling_files": 0,
        "retargeting_files": 0,
    })
    runtime_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def add_error(self, code: ErrorCode | str, message: str, file: Optional[str] = None) -> None:
        """Add a validation error. Automatically demotes status to REJECTED (or ERROR)."""
        code_str = code.value if isinstance(code, ErrorCode) else str(code)
        self.errors.append(ValidationError(code=code_str, message=message, file=file))
        if code_str == ErrorCode.INTERNAL_VALIDATION_ERROR.value:
            self.status = ValidationStatus.ERROR
        else:
            if self.status != ValidationStatus.ERROR:
                self.status = ValidationStatus.REJECTED

    def add_warning(self, message: str) -> None:
        """Record an advisory warning without failing validation."""
        self.warnings.append(message)

    def set_check(self, check_name: str, result: str) -> None:
        """Record status ('PASS', 'FAIL', 'SKIP') for an individual check."""
        self.checks[check_name] = result

    def get_exit_code(self) -> int:
        """Return deterministic process exit code (0=VALID, 1=REJECTED, 2=ERROR)."""
        return EXIT_CODE_MAP.get(self.status, 2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to clean dictionary suitable for JSON serialization."""
        return {
            "validator_version": self.validator_version,
            "contract_version": self.contract_version,
            "status": self.status.value,
            "submission_id": self.submission_id,
            "task": self.task,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": list(self.warnings),
            "checks": dict(self.checks),
            "file_summary": dict(self.file_summary),
            "runtime_seconds": round(float(self.runtime_seconds), 4),
            "timestamp": self.timestamp,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize result to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
