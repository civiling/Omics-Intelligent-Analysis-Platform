from __future__ import annotations

from pathlib import Path

from skill_registry.loader import _load_yaml_file

from .exceptions import WorkflowConfigError, WorkflowNotFoundError
from .models import WorkflowConfig


class WorkflowRegistry:
    def __init__(self, configs_dir: str | Path | None = None) -> None:
        self.package_root = Path(__file__).resolve().parent
        self.project_root = self.package_root.parent
        self.configs_dir = Path(configs_dir or self.package_root / "configs").resolve()
        self._workflows: dict[str, WorkflowConfig] | None = None

    def load_all(self) -> dict[str, WorkflowConfig]:
        if self._workflows is not None:
            return self._workflows

        if not self.configs_dir.exists():
            raise WorkflowConfigError(f"Workflow configs directory not found: {self.configs_dir}")

        workflows: dict[str, WorkflowConfig] = {}
        for config_path in sorted(self.configs_dir.glob("*.yaml")):
            config = self.load_config_file(config_path)
            if config.id in workflows:
                raise WorkflowConfigError(f"Duplicate workflow id: {config.id}")
            workflows[config.id] = config

        self._workflows = workflows
        return workflows

    def load_config_file(self, config_path: Path) -> WorkflowConfig:
        try:
            data = _load_yaml_file(config_path)
            return WorkflowConfig.from_mapping(
                data,
                config_path=config_path,
                project_root=self.project_root,
            )
        except Exception as exc:
            raise WorkflowConfigError(f"Cannot load workflow config {config_path}: {exc}") from exc

    def get(self, workflow_id: str) -> WorkflowConfig:
        workflow = self.load_all().get(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow id is not registered: {workflow_id}")
        return workflow

    def list(self) -> list[WorkflowConfig]:
        return list(self.load_all().values())

    def get_by_skill(self, skill_id: str) -> WorkflowConfig | None:
        for workflow in self.load_all().values():
            if workflow.skill_id == skill_id:
                return workflow
        return None
