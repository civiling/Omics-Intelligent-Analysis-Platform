from __future__ import annotations

from agents.models import AgentTask, SpecialistAgentType

from .base import BaseSpecialistAgent


class TranscriptomicsAgent(BaseSpecialistAgent):
    agent_type = SpecialistAgentType.TRANSCRIPTOMICS
    supported_skill_ids = ("transcriptomics.differential_expression",)

    def select_skill(self, task: AgentTask) -> str:
        return self._validate_supported_skill("transcriptomics.differential_expression")
