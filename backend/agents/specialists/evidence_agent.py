from __future__ import annotations

from agents.models import AgentTask, SpecialistAgentType

from .base import BaseSpecialistAgent


class EvidenceAgent(BaseSpecialistAgent):
    agent_type = SpecialistAgentType.EVIDENCE
    supported_skill_ids = ("reporting.evidence_report_generation",)

    def select_skill(self, task: AgentTask) -> str:
        return self._validate_supported_skill("reporting.evidence_report_generation")
