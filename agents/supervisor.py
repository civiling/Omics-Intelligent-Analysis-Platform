from __future__ import annotations

from pathlib import Path

from workflows import WorkflowStatus
from workflows.exceptions import WorkflowRuntimeError

from .context import AgentContext
from .logger import AgentLogger
from .models import AgentAction, AgentPlan, AgentResult, AgentStatus, AgentTask
from .planner import AgentPlanner
from .router import AgentRouter
from .tools import AuditTool, ResultTool, SkillTool, WorkflowTool


class SupervisorAgent:
    def __init__(
        self,
        context: AgentContext | None = None,
        router: AgentRouter | None = None,
    ) -> None:
        self.context = context or AgentContext()
        self.router = router or AgentRouter()
        self.planner = AgentPlanner(self.context)
        self.skill_tool = SkillTool(self.context.skill_loader)
        self.workflow_tool = WorkflowTool(self.context.workflow_runner)
        self.result_tool = ResultTool(self.context.workflow_runner.runs_dir)
        self.logger = AgentLogger(self.context.agent_logs_dir)
        self.audit_tool = AuditTool(self.logger)

    def plan(self, task: AgentTask) -> AgentPlan:
        route = self.router.route(task.user_query, task.available_inputs, task.domain)
        return self.planner.build_plan(task, route)

    def run(self, task: AgentTask) -> AgentResult:
        actions: list[dict] = []
        plan = self.plan(task)
        actions.append(
            AgentAction.create(
                task.task_id,
                "plan",
                "AgentPlanner.build_plan",
                {"user_query": task.user_query, "domain": task.domain},
                plan.to_dict(),
                AgentStatus.PLANNED,
            ).to_dict()
        )

        if plan.selected_skill_id is None or plan.selected_workflow_id is None:
            result = AgentResult(
                task_id=task.task_id,
                status=AgentStatus.NEEDS_INPUT,
                selected_skill_id=plan.selected_skill_id,
                selected_workflow_id=plan.selected_workflow_id,
                run_id=None,
                summary="The supervisor could not select a registered workflow.",
                output_files={},
                risk_notes="",
                requires_review=plan.requires_review,
                next_steps=plan.next_steps,
                error_message=plan.reasoning,
            )
            self.audit_tool.write_agent_result(task, plan, result, None, actions)
            return result

        if plan.missing_inputs:
            result = AgentResult(
                task_id=task.task_id,
                status=AgentStatus.NEEDS_INPUT,
                selected_skill_id=plan.selected_skill_id,
                selected_workflow_id=plan.selected_workflow_id,
                run_id=None,
                summary=f"Missing required inputs: {', '.join(plan.missing_inputs)}.",
                output_files={},
                risk_notes=self._skill_risk_notes(plan.selected_skill_id),
                requires_review=plan.requires_review,
                next_steps=plan.next_steps,
                error_message=f"Missing required inputs: {', '.join(plan.missing_inputs)}",
            )
            self.audit_tool.write_agent_result(task, plan, result, None, actions)
            return result

        try:
            workflow_result = self.workflow_tool.run_workflow(
                plan.selected_workflow_id,
                task.available_inputs,
                plan.parameters,
            )
            actions.append(
                AgentAction.create(
                    task.task_id,
                    "workflow_run",
                    "WorkflowTool.run_workflow",
                    {
                        "workflow_id": plan.selected_workflow_id,
                        "skill_id": plan.selected_skill_id,
                        "parameters": plan.parameters,
                    },
                    workflow_result.to_dict(),
                    AgentStatus.SUCCESS if workflow_result.status == WorkflowStatus.SUCCESS else AgentStatus.FAILED,
                    workflow_result.error_message,
                ).to_dict()
            )
        except WorkflowRuntimeError as exc:
            result = AgentResult(
                task_id=task.task_id,
                status=AgentStatus.NEEDS_INPUT,
                selected_skill_id=plan.selected_skill_id,
                selected_workflow_id=plan.selected_workflow_id,
                run_id=None,
                summary="Workflow could not be started because required inputs or parameters are incomplete.",
                output_files={},
                risk_notes=self._skill_risk_notes(plan.selected_skill_id),
                requires_review=plan.requires_review,
                next_steps=plan.next_steps,
                error_message=str(exc),
            )
            self.audit_tool.write_agent_result(task, plan, result, None, actions)
            return result

        run_dir = workflow_result.manifest_path.parent if workflow_result.manifest_path else None
        if workflow_result.status == WorkflowStatus.SUCCESS:
            summary = self.summarize_result(workflow_result)
            risk_notes = self._runtime_risk_notes(run_dir) if run_dir else self._skill_risk_notes(plan.selected_skill_id)
            status = AgentStatus.SUCCESS
        else:
            summary = "Workflow execution failed."
            risk_notes = self._skill_risk_notes(plan.selected_skill_id)
            status = AgentStatus.FAILED

        result = AgentResult(
            task_id=task.task_id,
            status=status,
            selected_skill_id=plan.selected_skill_id,
            selected_workflow_id=plan.selected_workflow_id,
            run_id=workflow_result.run_id,
            summary=summary,
            output_files=workflow_result.output_files,
            risk_notes=risk_notes,
            requires_review=plan.requires_review,
            next_steps=plan.next_steps,
            error_message=workflow_result.error_message,
        )
        self.audit_tool.write_agent_result(task, plan, result, run_dir, actions)
        return result

    def summarize_result(self, workflow_result) -> str:
        if workflow_result.status != WorkflowStatus.SUCCESS:
            return workflow_result.error_message or "Workflow failed."
        if workflow_result.manifest_path:
            run_dir = workflow_result.manifest_path.parent
            return self.result_tool.summarize_outputs(run_dir)
        output_count = len(workflow_result.output_files)
        return f"Workflow completed and generated {output_count} output files."

    def _runtime_risk_notes(self, run_dir: Path | None) -> str:
        if run_dir is None:
            return ""
        return self.result_tool.read_risk_notes(run_dir)

    def _skill_risk_notes(self, skill_id: str | None) -> str:
        if skill_id is None:
            return ""
        skill = self.skill_tool.get_skill(skill_id)
        return skill.risk_notes
