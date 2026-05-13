from __future__ import annotations

from agents.models import AgentTask, SpecialistAgentType

from .base import BaseSpecialistAgent


class MetabolomicsAgent(BaseSpecialistAgent):
    agent_type = SpecialistAgentType.METABOLOMICS
    supported_skill_ids = ("metabolomics.differential_metabolites",)

    def select_skill(self, task: AgentTask) -> str:
        return self._validate_supported_skill("metabolomics.differential_metabolites")
