from __future__ import annotations

from agents.models import AgentTask, SpecialistAgentType

from .base import BaseSpecialistAgent


class MicrobiomeAgent(BaseSpecialistAgent):
    agent_type = SpecialistAgentType.MICROBIOME
    supported_skill_ids = ("microbiome.read_qc", "microbiome.differential_abundance")

    def select_skill(self, task: AgentTask) -> str:
        query = task.user_query.lower()
        if any(keyword in query for keyword in ("differential abundance", "差异菌群", "差异丰度", "ancom", "aldex", "maaslin")):
            return self._validate_supported_skill("microbiome.differential_abundance")
        if "differential_taxa_table" in task.requested_outputs:
            return self._validate_supported_skill("microbiome.differential_abundance")
        return self._validate_supported_skill("microbiome.read_qc")
