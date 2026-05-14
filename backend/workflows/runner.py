from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .exceptions import WorkflowValidationError
from .executors import BaseExecutor, LocalExecutor, PlaceholderExecutor
from .models import ExecutorType, WorkflowConfig, WorkflowResult, WorkflowRun, WorkflowStatus
from .registry import WorkflowRegistry


class WorkflowRunner:
    def __init__(
        self,
        registry: WorkflowRegistry | None = None,
        runs_dir: str | Path | None = None,
    ) -> None:
        self.registry = registry or WorkflowRegistry()
        self.runs_dir = Path(runs_dir or Path(__file__).resolve().parents[2] / "runs").resolve()

    def load_workflow_config(self, workflow_id: str) -> WorkflowConfig:
        return self.registry.get(workflow_id)

    def list_workflows(self) -> list[WorkflowConfig]:
        return self.registry.list()

    def get_workflow_by_skill(self, skill_id: str) -> WorkflowConfig | None:
        return self.registry.get_by_skill(skill_id)

    def validate_inputs(self, workflow_id: str, input_files: dict[str, str]) -> None:
        config = self.load_workflow_config(workflow_id)
        missing = [input_type for input_type in config.input_types if input_type not in input_files]
        if missing:
            raise WorkflowValidationError(
                f"Workflow {workflow_id} is missing required input types: {', '.join(missing)}"
            )

    def validate_parameters(self, config: WorkflowConfig, parameters: dict[str, Any]) -> None:
        missing = [
            parameter
            for parameter in config.required_parameters
            if parameter not in parameters and parameter not in config.default_parameters
        ]
        if missing:
            raise WorkflowValidationError(
                f"Workflow {config.id} is missing required parameters: {', '.join(missing)}"
            )

    def create_run_directory(self, workflow_id: str) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = uuid.uuid4().hex[:6]
        run_dir = self.runs_dir / f"run_{timestamp}_{suffix}"
        for subdir in (
            run_dir,
            run_dir / "logs",
            run_dir / "outputs",
            run_dir / "outputs" / "tables",
            run_dir / "outputs" / "figures",
            run_dir / "outputs" / "notes",
        ):
            subdir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def run(
        self,
        workflow_id: str,
        input_files: dict[str, str],
        parameters: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        config = self.load_workflow_config(workflow_id)
        user_parameters = parameters or {}
        merged_parameters = {**config.default_parameters, **user_parameters}
        self.validate_inputs(workflow_id, input_files)
        self.validate_parameters(config, user_parameters)

        run_dir = self.create_run_directory(workflow_id)
        started_at = datetime.now()
        workflow_run = WorkflowRun(
            run_id=run_dir.name,
            workflow_id=config.id,
            skill_id=config.skill_id,
            status=WorkflowStatus.RUNNING,
            input_files={key: str(value) for key, value in input_files.items()},
            output_dir=run_dir / "outputs",
            parameters=merged_parameters,
            started_at=started_at,
        )

        self.write_inputs_json(run_dir, workflow_run.input_files)
        self.write_parameters_yaml(run_dir, merged_parameters)

        executor = self._get_executor(config.executor_type)
        try:
            result = executor.execute(config, run_dir, workflow_run.input_files, merged_parameters)
        except Exception as exc:
            result = WorkflowResult(
                run_id=run_dir.name,
                status=WorkflowStatus.FAILED,
                error_message=f"Workflow execution failed: {exc}",
                logs={"stdout": "", "stderr": str(exc)},
            )

        finished_at = datetime.now()
        workflow_run.finished_at = finished_at
        workflow_run.duration_seconds = (finished_at - started_at).total_seconds()
        workflow_run.status = result.status
        workflow_run.error_message = result.error_message

        log_paths = self.write_stdout_stderr_log(run_dir, result.logs)
        result.logs = log_paths
        manifest_path = self.write_run_manifest(run_dir, workflow_run, result, config)
        result.manifest_path = manifest_path
        return result

    def write_inputs_json(self, run_dir: Path, input_files: dict[str, str]) -> Path:
        path = run_dir / "inputs.json"
        path.write_text(json.dumps(input_files, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def write_parameters_yaml(self, run_dir: Path, parameters: dict[str, Any]) -> Path:
        path = run_dir / "parameters.yaml"
        _dump_yaml_file(path, parameters)
        return path

    def write_stdout_stderr_log(self, run_dir: Path, logs: dict[str, str]) -> dict[str, str]:
        logs_dir = run_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = logs_dir / "stdout.log"
        stderr_path = logs_dir / "stderr.log"
        stdout_path.write_text(logs.get("stdout", ""), encoding="utf-8")
        stderr_path.write_text(logs.get("stderr", ""), encoding="utf-8")
        return {"stdout": str(stdout_path), "stderr": str(stderr_path)}

    def write_run_manifest(
        self,
        run_dir: Path,
        workflow_run: WorkflowRun,
        result: WorkflowResult,
        workflow_config: WorkflowConfig,
    ) -> Path:
        manifest = {
            "run_id": workflow_run.run_id,
            "workflow_id": workflow_run.workflow_id,
            "skill_id": workflow_run.skill_id,
            "status": workflow_run.status.value,
            "input_files": workflow_run.input_files,
            "parameters": workflow_run.parameters,
            "output_files": result.output_files,
            "metrics": result.metrics,
            "logs": result.logs,
            "started_at": workflow_run.started_at.isoformat() if workflow_run.started_at else None,
            "finished_at": workflow_run.finished_at.isoformat() if workflow_run.finished_at else None,
            "duration_seconds": workflow_run.duration_seconds,
            "error_message": workflow_run.error_message,
            "workflow_config": workflow_config.to_manifest_dict(),
            "executor_type": workflow_config.executor_type.value,
        }
        path = run_dir / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def _get_executor(self, executor_type: ExecutorType) -> BaseExecutor:
        if executor_type == ExecutorType.PLACEHOLDER:
            return PlaceholderExecutor()
        if executor_type == ExecutorType.LOCAL:
            return LocalExecutor()
        raise WorkflowValidationError(f"Unsupported executor_type: {executor_type}")


def _dump_yaml_file(path: Path, data: dict[str, Any]) -> None:
    try:
        import yaml

        path.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    except ImportError:
        path.write_text(_dump_simple_yaml(data), encoding="utf-8")


def _dump_simple_yaml(data: dict[str, Any], indent: int = 0) -> str:
    lines: list[str] = []
    prefix = " " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_dump_simple_yaml(value, indent + 2).rstrip())
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                lines.append(f"{prefix}  - {item}")
        elif value is None:
            lines.append(f"{prefix}{key}: null")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {str(value).lower()}")
        else:
            lines.append(f"{prefix}{key}: {value}")
    return "\n".join(lines) + "\n"
