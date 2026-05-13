class AgentOrchestrationError(RuntimeError):
    """Base exception for controlled agent orchestration failures."""


class AgentRoutingError(AgentOrchestrationError):
    """Raised when an agent route cannot be determined."""


class AgentToolError(AgentOrchestrationError):
    """Raised when a controlled agent tool call fails."""


class AgentExecutionError(AgentOrchestrationError):
    """Raised when a supervisor or specialist cannot complete a task."""
