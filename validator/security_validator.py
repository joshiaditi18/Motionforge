"""
security_validator.py — MOTIONFORGE Phase 5 Archive Security & Path Sanitization

Protects the evaluation runner against malicious or abusive participant submissions:
- Zip path traversal (directory climbing '../' and '..\\')
- Absolute paths, drive-letter paths ('C:\\'), UNC paths ('\\\\')
- Symbolic links and hardlink abuse
- Zip bomb / resource exhaustion (excessive uncompressed size, file count, ratio)
- Forbidden executable files (.exe, .py, .sh, .bat, etc.)
"""

from __future__ import annotations

import os
import re
import sys
import zipfile
from typing import List, Tuple, Optional

from validator.error_codes import ErrorCode
from validator.validation_result import ValidationError

# --- Security Limits ---
MAX_ARCHIVE_SIZE_BYTES = 100 * 1024 * 1024       # 100 MB compressed
MAX_UNCOMPRESSED_SIZE_BYTES = 500 * 1024 * 1024   # 500 MB uncompressed
MAX_FILE_COUNT = 1000                             # Max members in archive
MAX_COMPRESSION_RATIO = 100.0                     # Max uncompressed/compressed ratio

# Disallowed file extensions (no executable scripts or binary payloads)
FORBIDDEN_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".sh", ".bash", ".bat", ".cmd", ".ps1", ".vbs",
    ".py", ".pyc", ".pyd", ".pyo",
    ".js", ".jar", ".msi", ".com", ".scr"
}

DRIVE_LETTER_PATTERN = re.compile(r"^[a-zA-Z]:")
UNC_PATH_PATTERN = re.compile(r"^\\\\[^\\]+\\[^\\]+")


def is_path_traversal(path_str: str) -> Tuple[bool, str]:
    """
    Check if a path string attempts directory traversal, drive specification,
    UNC network sharing, or absolute addressing.
    
    Returns:
        (is_dangerous, reason_description)
    """
    if not path_str:
        return False, ""

    # Check for null bytes
    if "\0" in path_str:
        return True, "Path contains null byte character"

    # Normalize slashes for inspection
    normalized = path_str.replace("\\", "/")

    # Check for drive letter (e.g. C:/ or C:)
    if DRIVE_LETTER_PATTERN.match(path_str) or DRIVE_LETTER_PATTERN.match(normalized):
        return True, f"Path specifies drive letter: '{path_str}'"

    # Check for UNC network path
    if path_str.startswith("\\\\") or normalized.startswith("//"):
        return True, f"Path specifies UNC network resource: '{path_str}'"

    # Check for absolute path
    if normalized.startswith("/"):
        return True, f"Path is absolute: '{path_str}'"

    # Check for parent directory climbing
    segments = normalized.split("/")
    if ".." in segments:
        return True, f"Path contains directory climbing parent references ('..'): '{path_str}'"

    # Raw string substring check for ..\ or ../
    if ".." in path_str:
        return True, f"Path contains directory climbing parent references ('..'): '{path_str}'"

    return False, ""


def is_symlink_zipinfo(zinfo: zipfile.ZipInfo) -> bool:
    """Detect if a ZipInfo member represents a UNIX symbolic link."""
    # Upper 16 bits of external_attr hold POSIX permissions and file type
    mode = zinfo.external_attr >> 16
    # 0o120000 = S_IFLNK (Symbolic link)
    return (mode & 0o170000) == 0o120000


def validate_archive_security(zip_path: str) -> Tuple[bool, List[ValidationError]]:
    """
    Inspects archive structure without extracting it to identify security risks,
    resource exhaustion attempts, and malicious archive members.
    
    Returns:
        (is_safe, list_of_validation_errors)
    """
    errors: List[ValidationError] = []

    # 1. Archive file size check
    try:
        compressed_size = os.path.getsize(zip_path)
    except OSError as e:
        errors.append(ValidationError(
            code=ErrorCode.ARCHIVE_NOT_FOUND.value,
            message=f"Cannot access archive file: {e}"
        ))
        return False, errors

    if compressed_size > MAX_ARCHIVE_SIZE_BYTES:
        errors.append(ValidationError(
            code=ErrorCode.ARCHIVE_TOO_LARGE.value,
            message=(
                f"Archive compressed size ({compressed_size / (1024*1024):.2f} MB) "
                f"exceeds maximum allowed limit of {MAX_ARCHIVE_SIZE_BYTES / (1024*1024):.0f} MB"
            )
        ))
        return False, errors

    # 2. Inspect ZIP members
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            infolist = zf.infolist()
            total_files = len(infolist)

            if total_files > MAX_FILE_COUNT:
                errors.append(ValidationError(
                    code=ErrorCode.ARCHIVE_TOO_MANY_FILES.value,
                    message=f"Archive contains {total_files} members, exceeding limit of {MAX_FILE_COUNT}"
                ))
                return False, errors

            total_uncompressed = 0
            for info in infolist:
                # Check for symlink
                if is_symlink_zipinfo(info):
                    errors.append(ValidationError(
                        code=ErrorCode.UNSAFE_SYMLINK.value,
                        message=f"Archive contains symbolic link '{info.filename}' which is forbidden",
                        file=info.filename
                    ))

                # Check path traversal
                is_danger, reason = is_path_traversal(info.filename)
                if is_danger:
                    errors.append(ValidationError(
                        code=ErrorCode.PATH_TRAVERSAL.value,
                        message=f"Path traversal detected in archive entry: {reason}",
                        file=info.filename
                    ))

                # Check forbidden extensions
                _, ext = os.path.splitext(info.filename)
                if ext.lower() in FORBIDDEN_EXTENSIONS:
                    errors.append(ValidationError(
                        code=ErrorCode.FORBIDDEN_FILE_TYPE.value,
                        message=f"Archive contains prohibited file type '{ext}': '{info.filename}'",
                        file=info.filename
                    ))

                total_uncompressed += info.file_size

            # Check uncompressed size
            if total_uncompressed > MAX_UNCOMPRESSED_SIZE_BYTES:
                errors.append(ValidationError(
                    code=ErrorCode.ARCHIVE_TOO_LARGE.value,
                    message=(
                        f"Archive uncompressed size ({total_uncompressed / (1024*1024):.2f} MB) "
                        f"exceeds maximum allowed limit of {MAX_UNCOMPRESSED_SIZE_BYTES / (1024*1024):.0f} MB"
                    )
                ))

            # Check compression ratio
            if compressed_size > 0:
                ratio = total_uncompressed / compressed_size
                if ratio > MAX_COMPRESSION_RATIO and total_uncompressed > 10 * 1024 * 1024:
                    errors.append(ValidationError(
                        code=ErrorCode.SUSPICIOUS_COMPRESSION_RATIO.value,
                        message=(
                            f"Suspicious compression ratio ({ratio:.1f}:1). "
                            f"Compressed: {compressed_size} bytes, Uncompressed: {total_uncompressed} bytes"
                        )
                    ))

    except zipfile.BadZipFile as e:
        errors.append(ValidationError(
            code=ErrorCode.ARCHIVE_CORRUPTED.value,
            message=f"Corrupted or invalid zip archive: {e}"
        ))
    except Exception as e:
        errors.append(ValidationError(
            code=ErrorCode.INTERNAL_VALIDATION_ERROR.value,
            message=f"Error inspecting archive security: {e}"
        ))

    return (len(errors) == 0), errors


def safe_extract_zip(zip_path: str, destination_dir: str) -> Tuple[bool, List[ValidationError]]:
    """
    Safely extract members of a zip archive into destination_dir, ensuring
    every extracted file lands strictly within destination_dir.
    """
    is_safe, sec_errors = validate_archive_security(zip_path)
    if not is_safe:
        return False, sec_errors

    dest_real = os.path.realpath(destination_dir)
    errors: List[ValidationError] = []

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                # Prevent directory traversal on final extraction path
                target_path = os.path.realpath(os.path.join(destination_dir, member.filename))
                if not (target_path == dest_real or target_path.startswith(dest_real + os.sep)):
                    errors.append(ValidationError(
                        code=ErrorCode.PATH_TRAVERSAL.value,
                        message=f"Attempted path breakout outside extraction directory: '{member.filename}'",
                        file=member.filename
                    ))
                    return False, errors

                zf.extract(member, destination_dir)
    except Exception as e:
        errors.append(ValidationError(
            code=ErrorCode.ARCHIVE_CORRUPTED.value,
            message=f"Failed extracting archive: {e}"
        ))
        return False, errors

    return True, []
