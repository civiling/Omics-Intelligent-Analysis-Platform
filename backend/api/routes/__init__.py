from .ai import router as ai_router
from .health import router as health_router
from .platform import router as platform_router
from .scrna import router as scrna_router
from .workflow_runs import router as workflow_runs_router

__all__ = ["ai_router", "health_router", "platform_router", "scrna_router", "workflow_runs_router"]
