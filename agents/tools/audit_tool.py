from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.logger import AgentLogger
from agents.models import AgentPlan, AgentResult, AgentStatus, AgentTask


class AuditTool:
    def __init__(self, logger: AgentLogger | None = None) -> None:
        self.logger = logger or AgentLogger()

    def write_agent_action_log(
        self,
        task: AgentTask,
        plan: AgentPlan | None,
        result: AgentResult,
        run_dir: Path | None = None,
        actions: list[dict[str, Any]] | None = None,
    ) -> Path:
        return self.logger.write_trace(task, plan, result, run_dir, actions)

    def write_agent_plan(
        self,
        task: AgentTask,
        plan: AgentPlan,
        actions: list[dict[str, Any]] | None = None,
    ) -> Path:
        pending_result = AgentResult(
            task_id=task.task_id,
            status=AgentStatus.PLANNED,
            selected_skill_id=plan.selected_skill_id,
            selected_workflow_id=plan.selected_workflow_id,
            run_id=None,
            summary="Agent plan generated.",
            output_files={},
            risk_notes="",
            requires_review=plan.requires_review,
            next_steps=plan.next_steps,
        )
        return self.logger.write_trace(task, plan, pending_result, None, actions)

    def write_agent_result(
        self,
        task: AgentTask,
        plan: AgentPlan | None,
        result: AgentResult,
        run_dir: Path | None = None,
        actions: list[dict[str, Any]] | None = None,
    ) -> Path:
        return self.logger.write_trace(task, plan, result, run_dir, actions)
