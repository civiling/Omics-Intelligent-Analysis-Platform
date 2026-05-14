class WorkflowRuntimeError(RuntimeError):
    """Base exception for workflow runtime failures."""


class WorkflowConfigError(WorkflowRuntimeError):
    """Raised when a workflow configuration cannot be loaded."""


class WorkflowNotFoundError(WorkflowRuntimeError):
    """Raised when a requested workflow id is not registered."""


class WorkflowValidationError(WorkflowRuntimeError):
    """Raised when workflow inputs or parameters are invalid."""


class WorkflowExecutionError(WorkflowRuntimeError):
    """Raised when a workflow executor fails unexpectedly."""
