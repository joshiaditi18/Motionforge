"""
test_archive_validation.py — Unit tests for archive_validator.py
"""

import os
import zipfile
import pytest

from validator.archive_validator import validate_archive
from validator.error_codes import ErrorCode
from validator.security_validator import MAX_ARCHIVE_SIZE_BYTES


def test_valid_archive(tmp_path):
    zip_path = tmp_path / "valid_submission.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("denoising/MF002_low.bvh", "HIERARCHY\n")
    
    ok, errors, warnings = validate_archive(str(zip_path))
    assert ok is True
    assert len(errors) == 0


def test_archive_not_found(tmp_path):
    missing_path = tmp_path / "non_existent.zip"
    ok, errors, _ = validate_archive(str(missing_path))
    assert ok is False
    assert any(e.code == ErrorCode.ARCHIVE_NOT_FOUND.value for e in errors)


def test_archive_wrong_extension(tmp_path):
    tar_path = tmp_path / "submission.tar.gz"
    tar_path.write_text("dummy")
    ok, errors, _ = validate_archive(str(tar_path))
    assert ok is False
    assert any(e.code == ErrorCode.ARCHIVE_CORRUPTED.value for e in errors)


def test_empty_archive(tmp_path):
    empty_path = tmp_path / "empty.zip"
    empty_path.write_bytes(b"")
    ok, errors, _ = validate_archive(str(empty_path))
    assert ok is False
    assert any(e.code == ErrorCode.ARCHIVE_CORRUPTED.value for e in errors)


def test_corrupted_archive(tmp_path):
    corrupt_path = tmp_path / "corrupt.zip"
    corrupt_path.write_bytes(b"PK\x03\x04this is not a real zip file data payload")
    ok, errors, _ = validate_archive(str(corrupt_path))
    assert ok is False
    assert any(e.code == ErrorCode.ARCHIVE_CORRUPTED.value for e in errors)


def test_archive_crc_corrupted_member(tmp_path):
    zip_path = tmp_path / "crc_bad.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("test.txt", "Original uncorrupted content")
    
    # Tamper with file content bytes to break CRC32
    raw = zip_path.read_bytes()
    # Replace some bytes in the data
    tampered = raw.replace(b"Original", b"Tampered")
    zip_path.write_bytes(tampered)

    ok, errors, _ = validate_archive(str(zip_path))
    assert ok is False
    assert any(e.code == ErrorCode.ARCHIVE_CORRUPTED.value for e in errors)


def test_archive_too_large(tmp_path, monkeypatch):
    zip_path = tmp_path / "large.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("dummy.txt", "hello")
    
    # Monkeypatch os.path.getsize to exceed 100 MB
    monkeypatch.setattr(os.path, "getsize", lambda p: MAX_ARCHIVE_SIZE_BYTES + 1024)
    ok, errors, _ = validate_archive(str(zip_path))
    assert ok is False
    assert any(e.code == ErrorCode.ARCHIVE_TOO_LARGE.value for e in errors)
