from __future__ import annotations

from typing import Any

from workflows import WorkflowRunner


class WorkflowTool:
    def __init__(self, runner: WorkflowRunner | None = None) -> None:
        self.runner = runner or WorkflowRunner()

    def list_workflows(self):
        return self.runner.list_workflows()

    def get_workflow_by_skill(self, skill_id: str):
        return self.runner.get_workflow_by_skill(skill_id)

    def validate_workflow_inputs(self, workflow_id: str, input_files: dict[str, str]) -> None:
        self.runner.validate_inputs(workflow_id, input_files)

    def run_workflow(
        self,
        workflow_id: str,
        input_files: dict[str, str],
        parameters: dict[str, Any],
    ):
        return self.runner.run(workflow_id, input_files, parameters)
