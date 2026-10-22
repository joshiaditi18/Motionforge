"""
archive_validator.py — MOTIONFORGE Phase 5 Submission Archive Validator

Validates submission zip archive files:
- Archive existence and file access permissions
- Supported archive format (.zip)
- Maximum archive size check (100 MB)
- Archive integrity via zip CRC checksum test
- Top-level archive hierarchy inspection
"""

from __future__ import annotations

import os
import zipfile
from typing import List, Tuple, Dict, Any, Optional

from validator.error_codes import ErrorCode
from validator.validation_result import ValidationError
from validator.security_validator import (
    validate_archive_security,
    safe_extract_zip,
    MAX_ARCHIVE_SIZE_BYTES,
)


def validate_archive(archive_path: str) -> Tuple[bool, List[ValidationError], List[str]]:
    """
    Validate that a submission archive exists, is well-formed, passes integrity tests,
    and meets security standards.

    Returns:
        (is_valid, errors_list, warnings_list)
    """
    errors: List[ValidationError] = []
    warnings: List[str] = []

    # 1. Check file existence
    if not os.path.exists(archive_path):
        errors.append(ValidationError(
            code=ErrorCode.ARCHIVE_NOT_FOUND.value,
            message=f"Submission archive not found: '{os.path.basename(archive_path)}'"
        ))
        return False, errors, warnings

    if not os.path.isfile(archive_path):
        errors.append(ValidationError(
            code=ErrorCode.ARCHIVE_NOT_FOUND.value,
            message=f"Submission path is not a regular file: '{os.path.basename(archive_path)}'"
        ))
        return False, errors, warnings

    # 2. Check format extension
    _, ext = os.path.splitext(archive_path)
    if ext.lower() != ".zip":
        errors.append(ValidationError(
            code=ErrorCode.ARCHIVE_CORRUPTED.value,
            message=f"Unsupported archive format '{ext}'. Submissions must be compressed '.zip' archives."
        ))
        return False, errors, warnings

    # 3. Check file readability and size
    try:
        size = os.path.getsize(archive_path)
        if size == 0:
            errors.append(ValidationError(
                code=ErrorCode.ARCHIVE_CORRUPTED.value,
                message="Submission archive is empty (0 bytes)."
            ))
            return False, errors, warnings

        if size > MAX_ARCHIVE_SIZE_BYTES:
            errors.append(ValidationError(
                code=ErrorCode.ARCHIVE_TOO_LARGE.value,
                message=(
                    f"Submission archive size ({size / (1024*1024):.2f} MB) "
                    f"exceeds the 100 MB competition limit."
                )
            ))
            return False, errors, warnings
    except OSError as e:
        errors.append(ValidationError(
            code=ErrorCode.ARCHIVE_NOT_FOUND.value,
            message=f"Cannot read submission archive: {e}"
        ))
        return False, errors, warnings

    # 4. Check zip validity and CRC integrity
    try:
        if not zipfile.is_zipfile(archive_path):
            errors.append(ValidationError(
                code=ErrorCode.ARCHIVE_CORRUPTED.value,
                message="File is not a valid zip archive."
            ))
            return False, errors, warnings

        with zipfile.ZipFile(archive_path, "r") as zf:
            corrupt_file = zf.testzip()
            if corrupt_file is not None:
                errors.append(ValidationError(
                    code=ErrorCode.ARCHIVE_CORRUPTED.value,
                    message=f"Corrupted entry detected in zip archive (CRC check failed): '{corrupt_file}'",
                    file=corrupt_file
                ))
                return False, errors, warnings

    except zipfile.BadZipFile as e:
        errors.append(ValidationError(
            code=ErrorCode.ARCHIVE_CORRUPTED.value,
            message=f"Corrupt or malformed zip archive: {e}"
        ))
        return False, errors, warnings
    except Exception as e:
        errors.append(ValidationError(
            code=ErrorCode.INTERNAL_VALIDATION_ERROR.value,
            message=f"Unexpected error testing zip archive: {e}"
        ))
        return False, errors, warnings

    # 5. Run security validation (traversal, symlinks, bombs, forbidden files)
    is_safe, sec_errors = validate_archive_security(archive_path)
    if not is_safe:
        errors.extend(sec_errors)
        return False, errors, warnings

    return True, errors, warnings
