class ReportError(RuntimeError):
    """Base exception for report generation failures."""


class ReportGenerationError(ReportError):
    """Raised when a report cannot be generated."""
