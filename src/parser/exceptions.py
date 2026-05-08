"""
Custom exceptions for the AWR Parser module.
"""


class ParserError(Exception):
    """Base exception for all AWR parsing errors."""

    pass


class AWRFileNotFoundError(ParserError):
    """Raised when the specified AWR file does not exist."""

    pass
