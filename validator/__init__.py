"""
MOTIONFORGE — Official Submission Validator
Package: validator
Version: 0.1.0
Contract: 1.0.0
"""

from validator.error_codes import ErrorCode
from validator.validation_result import (
    ValidationStatus,
    ValidationError,
    ValidationResult,
    EXIT_CODE_MAP,
)
def validate_submission(*args, **kwargs):
    from validator.validator import validate_submission as _validate_submission_impl
    return _validate_submission_impl(*args, **kwargs)

MOTIONFORGE_VALIDATOR_VERSION = "0.1.0"
CONTRACT_VERSION = "1.0.0"

__version__ = MOTIONFORGE_VALIDATOR_VERSION
__all__ = [
    "MOTIONFORGE_VALIDATOR_VERSION",
    "CONTRACT_VERSION",
    "ErrorCode",
    "ValidationStatus",
    "ValidationError",
    "ValidationResult",
    "EXIT_CODE_MAP",
    "validate_submission",
]
