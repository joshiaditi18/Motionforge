"""
test_security_validation.py — Unit tests for security_validator.py
"""

import os
import zipfile
import pytest

from validator.security_validator import (
    validate_archive_security,
    safe_extract_zip,
    is_path_traversal,
    is_symlink_zipinfo,
    MAX_FILE_COUNT,
)
from validator.error_codes import ErrorCode


def test_path_traversal_detection():
    assert is_path_traversal("../../evil.txt")[0] is True
    assert is_path_traversal("..\\..\\evil.txt")[0] is True
    assert is_path_traversal("/etc/passwd")[0] is True
    assert is_path_traversal("C:\\Windows\\System32\\calc.exe")[0] is True
    assert is_path_traversal("\\\\remote\\share\\file.txt")[0] is True
    assert is_path_traversal("sub/dir/normal.bvh")[0] is False


def test_archive_with_traversal_slash(tmp_path):
    zip_path = tmp_path / "traversal_slash.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../../evil.txt", "exploit")
    
    ok, errors = validate_archive_security(str(zip_path))
    assert ok is False
    assert any(e.code == ErrorCode.PATH_TRAVERSAL.value for e in errors)


def test_archive_with_traversal_backslash(tmp_path):
    zip_path = tmp_path / "traversal_backslash.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("..\\..\\evil.txt", "exploit")
    
    ok, errors = validate_archive_security(str(zip_path))
    assert ok is False
    assert any(e.code == ErrorCode.PATH_TRAVERSAL.value for e in errors)


def test_archive_with_drive_letter(tmp_path):
    zip_path = tmp_path / "drive_letter.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("C:\\evil.txt", "exploit")
    
    ok, errors = validate_archive_security(str(zip_path))
    assert ok is False
    assert any(e.code == ErrorCode.PATH_TRAVERSAL.value for e in errors)


def test_archive_with_absolute_path(tmp_path):
    zip_path = tmp_path / "absolute_path.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("/root/evil.txt", "exploit")
    
    ok, errors = validate_archive_security(str(zip_path))
    assert ok is False
    assert any(e.code == ErrorCode.PATH_TRAVERSAL.value for e in errors)


def test_archive_with_forbidden_executable(tmp_path):
    zip_path = tmp_path / "malicious_script.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("denoising/script.py", "import os; print('pwned')")
    
    ok, errors = validate_archive_security(str(zip_path))
    assert ok is False
    assert any(e.code == ErrorCode.FORBIDDEN_FILE_TYPE.value for e in errors)


def test_archive_with_symlink(tmp_path):
    zip_path = tmp_path / "symlink.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zinfo = zipfile.ZipInfo("symlink_entry")
        # 0o120000 = S_IFLNK (Symbolic link)
        zinfo.external_attr = 0o120777 << 16
        zf.writestr(zinfo, "/target/path")
    
    ok, errors = validate_archive_security(str(zip_path))
    assert ok is False
    assert any(e.code == ErrorCode.UNSAFE_SYMLINK.value for e in errors)


def test_archive_too_many_members(tmp_path, monkeypatch):
    zip_path = tmp_path / "many_files.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("test.txt", "hello")
    
    # Mock infolist length to exceed limit
    import zipfile as zf_module
    orig_infolist = zf_module.ZipFile.infolist
    monkeypatch.setattr(
        zf_module.ZipFile,
        "infolist",
        lambda self: [zipfile.ZipInfo(f"file_{i}.txt") for i in range(MAX_FILE_COUNT + 10)]
    )
    
    ok, errors = validate_archive_security(str(zip_path))
    assert ok is False
    assert any(e.code == ErrorCode.ARCHIVE_TOO_MANY_FILES.value for e in errors)


def test_safe_extract_protects_destination(tmp_path):
    zip_path = tmp_path / "safe.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("denoising/MF002_low.bvh", "HIERARCHY\n")
    
    dest_dir = tmp_path / "extracted"
    os.makedirs(dest_dir, exist_ok=True)
    ok, errors = safe_extract_zip(str(zip_path), str(dest_dir))
    assert ok is True
    assert (dest_dir / "denoising" / "MF002_low.bvh").exists()
