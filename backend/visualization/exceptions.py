class VisualizationError(RuntimeError):
    """Base exception for visualization layer failures."""


class ChartSpecError(VisualizationError):
    """Raised when a chart specification is malformed."""


class ChartRenderError(VisualizationError):
    """Raised when chart rendering fails."""
