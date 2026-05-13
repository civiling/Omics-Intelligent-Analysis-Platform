from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from workflows.models import WorkflowConfig, WorkflowResult


class BaseExecutor(ABC):
    @abstractmethod
    def execute(
        self,
        workflow_config: WorkflowConfig,
        run_dir: Path,
        input_files: dict[str, str],
        parameters: dict[str, Any],
    ) -> WorkflowResult:
        """Execute a registered workflow configuration."""
