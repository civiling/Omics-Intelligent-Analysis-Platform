from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutorType(str, Enum):
    PLACEHOLDER = "placeholder"
    LOCAL = "local"


@dataclass(frozen=True)
class WorkflowConfig:
    id: str
    name: str
    domain: str
    version: str
    description: str
    skill_id: str
    executor_type: ExecutorType
    script_path: Path | None
    input_types: list[str]
    output_types: list[str]
    default_parameters: dict[str, Any]
    required_parameters: list[str]
    timeout_seconds: int
    risk_level: str
    requires_review: bool
    config_path: Path | None = None

    @classmethod
    def from_mapping(
        cls,
        data: dict[str, Any],
        config_path: Path | None = None,
        project_root: Path | None = None,
    ) -> "WorkflowConfig":
        script_path = data.get("script_path")
        resolved_script_path = None
        if script_path is not None:
            base = project_root or Path.cwd()
            resolved_script_path = (base / str(script_path)).resolve()

        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            domain=str(data["domain"]),
            version=str(data["version"]),
            description=str(data["description"]),
            skill_id=str(data["skill_id"]),
            executor_type=ExecutorType(str(data["executor_type"])),
            script_path=resolved_script_path,
            input_types=list(data.get("input_types", [])),
            output_types=list(data.get("output_types", [])),
            default_parameters=dict(data.get("default_parameters", {})),
            required_parameters=list(data.get("required_parameters", [])),
            timeout_seconds=int(data["timeout_seconds"]),
            risk_level=str(data["risk_level"]),
            requires_review=bool(data.get("requires_review", False)),
            config_path=config_path.resolve() if config_path else None,
        )

    def to_manifest_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["executor_type"] = self.executor_type.value
        data["script_path"] = str(self.script_path) if self.script_path else None
        data["config_path"] = str(self.config_path) if self.config_path else None
        return data


@dataclass
class WorkflowRun:
    run_id: str
    workflow_id: str
    skill_id: str
    status: WorkflowStatus
    input_files: dict[str, str]
    output_dir: Path
    parameters: dict[str, Any]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_seconds: float | None = None
    error_message: str | None = None


@dataclass
class WorkflowResult:
    run_id: str
    status: WorkflowStatus
    output_files: dict[str, str] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    logs: dict[str, str] = field(default_factory=dict)
    manifest_path: Path | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "output_files": self.output_files,
            "metrics": self.metrics,
            "logs": self.logs,
            "manifest_path": str(self.manifest_path) if self.manifest_path else None,
            "error_message": self.error_message,
        }
