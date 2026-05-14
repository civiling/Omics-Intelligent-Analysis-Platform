from __future__ import annotations

from agents.context import AgentContext
from agents.models import AgentPlan, AgentRoute, AgentTask
from agents.specialists import (
    EvidenceAgent,
    MetabolomicsAgent,
    MicrobiomeAgent,
    MultiomicsAgent,
    ReportAgent,
    TranscriptomicsAgent,
)
from agents.models import SpecialistAgentType
from agents.tools import SkillTool, WorkflowTool


SPECIALIST_CLASSES = {
    SpecialistAgentType.MICROBIOME: MicrobiomeAgent,
    SpecialistAgentType.TRANSCRIPTOMICS: TranscriptomicsAgent,
    SpecialistAgentType.METABOLOMICS: MetabolomicsAgent,
    SpecialistAgentType.MULTIOMICS: MultiomicsAgent,
    SpecialistAgentType.EVIDENCE: EvidenceAgent,
    SpecialistAgentType.REPORTING: ReportAgent,
}


class AgentPlanner:
    def __init__(self, context: AgentContext | None = None) -> None:
        self.context = context or AgentContext()
        self.skill_tool = SkillTool(self.context.skill_loader)
        self.workflow_tool = WorkflowTool(self.context.workflow_runner)

    def build_plan(self, task: AgentTask, route: AgentRoute) -> AgentPlan:
        if route.specialist_agent is None:
            return AgentPlan(
                task_id=task.task_id,
                selected_skill_id=None,
                selected_workflow_id=None,
                specialist_agent=None,
                reasoning=route.reasoning,
                missing_inputs=[],
                parameters={},
                risk_level=None,
                requires_review=False,
                next_steps=["Provide a clearer task description or domain."],
            )

        specialist = SPECIALIST_CLASSES[route.specialist_agent](self.context)
        skill_id = specialist.select_skill(task)
        skill = self.skill_tool.get_skill(skill_id)
        workflow = self.workflow_tool.get_workflow_by_skill(skill_id)
        workflow_id = workflow.id if workflow else None
        required_inputs = workflow.input_types if workflow else skill.metadata.input_types
        missing_inputs = [
            input_type for input_type in required_inputs if input_type not in task.available_inputs
        ]
        parameters = specialist.prepare_parameters(task, skill_id)
        next_steps = list(skill.metadata.next_skills)
        return AgentPlan(
            task_id=task.task_id,
            selected_skill_id=skill_id,
            selected_workflow_id=workflow_id,
            specialist_agent=route.specialist_agent,
            reasoning=f"{route.reasoning} Selected skill {skill_id} through {route.specialist_agent.value} specialist.",
            missing_inputs=missing_inputs,
            parameters=parameters,
            risk_level=skill.metadata.risk_level.value,
            requires_review=skill.metadata.requires_review,
            next_steps=next_steps,
        )
