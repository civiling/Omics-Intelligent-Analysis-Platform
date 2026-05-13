from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agents.context import AgentContext
from agents.models import AgentResult, AgentTask, SpecialistAgentType
from agents.tools import SkillTool, WorkflowTool


class BaseSpecialistAgent(ABC):
    agent_type: SpecialistAgentType
    supported_skill_ids: tuple[str, ...]

    def __init__(self, context: AgentContext | None = None) -> None:
        self.context = context or AgentContext()
        self.skill_tool = SkillTool(self.context.skill_loader)
        self.workflow_tool = WorkflowTool(self.context.workflow_runner)

    def can_handle(self, task: AgentTask) -> bool:
        if task.domain and task.domain in {self.agent_type.value, "reporting"}:
            return True
        query = task.user_query.lower()
        return any(skill_id.split(".")[0] in query for skill_id in self.supported_skill_ids)

    @abstractmethod
    def select_skill(self, task: AgentTask) -> str:
        """Return a registered skill id this specialist can handle."""

    def prepare_parameters(self, task: AgentTask, skill_id: str) -> dict[str, Any]:
        workflow = self.workflow_tool.get_workflow_by_skill(skill_id)
        if workflow is None:
            return dict(task.constraints)
        parameters = dict(workflow.default_parameters)
        parameters.update(task.constraints)
        return parameters

    def run(self, task: AgentTask) -> AgentResult:
        from agents.supervisor import SupervisorAgent

        return SupervisorAgent(context=self.context).run(task)

    def _validate_supported_skill(self, skill_id: str) -> str:
        if skill_id not in self.supported_skill_ids:
            raise ValueError(f"{self.agent_type.value} specialist does not support skill {skill_id}.")
        self.skill_tool.validate_skill_exists(skill_id)
        return skill_id
