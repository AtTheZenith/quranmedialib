"""Custom exceptions for QuranMediaLib.

This module defines a hierarchy of exceptions used throughout the library
to provide granular error reporting and better control for library users.
"""

from __future__ import annotations


class QuranMediaLibError(Exception):
    """Base exception for all QuranMediaLib errors."""

    pass


class ResourceError(QuranMediaLibError):
    """Raised when a resource (font, database, etc.) is missing or inaccessible."""

    pass


class DatabaseError(QuranMediaLibError):
    """Raised when a database operation fails."""

    pass


class WorkflowError(QuranMediaLibError):
    """Raised when a workflow encounter an error during processing."""

    pass


class ValidationError(QuranMediaLibError, ValueError):
    """Raised when configuration or input validation fails.

    Inherits from ValueError for backward compatibility.
    """

    pass


class LayoutError(QuranMediaLibError):
    """Raised when a layout operation (framing, wrapping) fails."""

    pass
