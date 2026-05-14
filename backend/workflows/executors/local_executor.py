from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from workflows.models import WorkflowConfig, WorkflowResult, WorkflowStatus

from .base import BaseExecutor


class LocalExecutor(BaseExecutor):
    def __init__(self, allowed_scripts_root: str | Path | None = None) -> None:
        default_root = Path(__file__).resolve().parents[1] / "scripts"
        self.allowed_scripts_root = Path(allowed_scripts_root or default_root).resolve()

    def execute(
        self,
        workflow_config: WorkflowConfig,
        run_dir: Path,
        input_files: dict[str, str],
        parameters: dict[str, Any],
    ) -> WorkflowResult:
        if workflow_config.script_path is None:
            return self._failed(run_dir, "Local executor requires a registered script_path.")

        script_path = workflow_config.script_path.resolve()
        if not script_path.exists():
            return self._failed(run_dir, f"Registered script_path does not exist: {script_path}")

        if not self._is_allowed_script(script_path):
            return self._failed(
                run_dir,
                f"Refusing to execute unregistered script outside {self.allowed_scripts_root}: {script_path}",
            )

        inputs_path = run_dir / "inputs.json"
        parameters_path = run_dir / "parameters.yaml"
        outputs_path = run_dir / "outputs"
        command = [
            sys.executable,
            str(script_path),
            "--run-dir",
            str(run_dir),
            "--inputs-json",
            str(inputs_path),
            "--parameters-yaml",
            str(parameters_path),
            "--outputs-dir",
            str(outputs_path),
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=workflow_config.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return self._failed(
                run_dir,
                f"Local workflow timed out after {workflow_config.timeout_seconds} seconds.",
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
            )

        if completed.returncode != 0:
            return self._failed(
                run_dir,
                f"Local workflow failed with return code {completed.returncode}.",
                stdout=completed.stdout,
                stderr=completed.stderr,
            )

        output_files = self._collect_output_files(outputs_path)
        metrics_path = outputs_path / "metrics.json"
        metrics: dict[str, Any] = {}
        if metrics_path.exists():
            try:
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                metrics = {"metrics_parse_error": str(metrics_path)}

        return WorkflowResult(
            run_id=run_dir.name,
            status=WorkflowStatus.SUCCESS,
            output_files=output_files,
            metrics=metrics,
            logs={"stdout": completed.stdout, "stderr": completed.stderr},
        )

    def _is_allowed_script(self, script_path: Path) -> bool:
        return script_path == self.allowed_scripts_root or self.allowed_scripts_root in script_path.parents

    def _collect_output_files(self, outputs_path: Path) -> dict[str, str]:
        if not outputs_path.exists():
            return {}
        return {
            str(path.relative_to(outputs_path)).replace("\\", "/"): str(path)
            for path in outputs_path.rglob("*")
            if path.is_file()
        }

    def _failed(
        self,
        run_dir: Path,
        message: str,
        stdout: str = "",
        stderr: str = "",
    ) -> WorkflowResult:
        return WorkflowResult(
            run_id=run_dir.name,
            status=WorkflowStatus.FAILED,
            error_message=message,
            logs={"stdout": stdout, "stderr": stderr or message},
        )
