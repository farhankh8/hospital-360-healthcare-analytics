"""Typed API contract errors.

These exceptions carry an HTTP status, a stable machine-readable code and a
human-readable message. The global handlers in ``api.main`` render them with
the single structured error envelope.
"""
from __future__ import annotations

from typing import Any


class ApiContractError(Exception):
    """Base class for every deliberate API contract error."""

    status_code = 400
    code = "BAD_REQUEST"
    default_message = "Request could not be processed"

    def __init__(self, message: str | None = None, details: Any = None) -> None:
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class FilterValidationError(ApiContractError):
    """Raised for unsupported, malformed or contradictory filter values."""

    status_code = 422
    code = "VALIDATION_ERROR"
    default_message = "One or more request filters are invalid"


class ExportLimitExceeded(ApiContractError):
    """Raised when a server-side export would exceed ``MAX_EXPORT_ROWS``."""

    status_code = 413
    code = "EXPORT_LIMIT_EXCEEDED"
    default_message = "Export exceeds the permitted row limit"
