from __future__ import annotations

from agents.models import AgentTask, SpecialistAgentType

from .base import BaseSpecialistAgent


class MultiomicsAgent(BaseSpecialistAgent):
    agent_type = SpecialistAgentType.MULTIOMICS
    supported_skill_ids = ("multiomics.correlation_network",)

    def select_skill(self, task: AgentTask) -> str:
        return self._validate_supported_skill("multiomics.correlation_network")
