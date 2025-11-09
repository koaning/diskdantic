class DiskdanticError(Exception):
    """Base exception for diskdantic errors."""


class UnknownFormatError(DiskdanticError):
    """Raised when a requested file format is not supported."""


class MissingPathError(DiskdanticError):
    """Raised when an operation requires a path but none is known."""


class InconsistentFormatError(DiskdanticError):
    """Raised when multiple file formats are encountered in a collection."""
