from __future__ import annotations

from .models import AgentRoute, SpecialistAgentType


ROUTING_RULES = [
    (
        SpecialistAgentType.MULTIOMICS,
        "multiomics",
        ["multiomics", "multi-omics", "多组学", "correlation", "network", "关联网络", "相关网络"],
        ["multiomics.correlation_network"],
    ),
    (
        SpecialistAgentType.EVIDENCE,
        "reporting",
        ["evidence", "文献", "pubmed", "证据", "机制解释"],
        ["reporting.evidence_report_generation"],
    ),
    (
        SpecialistAgentType.REPORTING,
        "reporting",
        ["report", "报告", "总结", "专家报告"],
        ["reporting.evidence_report_generation"],
    ),
    (
        SpecialistAgentType.TRANSCRIPTOMICS,
        "transcriptomics",
        ["rna-seq", "rnaseq", "transcriptome", "count matrix", "差异基因", "表达矩阵", "转录组"],
        ["transcriptomics.differential_expression"],
    ),
    (
        SpecialistAgentType.METABOLOMICS,
        "metabolomics",
        ["metabolomics", "代谢组", "peak table", "代谢物", "差异代谢物"],
        ["metabolomics.differential_metabolites"],
    ),
    (
        SpecialistAgentType.MICROBIOME,
        "microbiome",
        ["microbiome", "菌群", "asv", "otu", "taxonomy", "16s", "metagenomics", "宏基因组", "差异菌群"],
        ["microbiome.read_qc", "microbiome.differential_abundance"],
    ),
]


DOMAIN_TO_SPECIALIST = {
    "microbiome": SpecialistAgentType.MICROBIOME,
    "transcriptomics": SpecialistAgentType.TRANSCRIPTOMICS,
    "metabolomics": SpecialistAgentType.METABOLOMICS,
    "multiomics": SpecialistAgentType.MULTIOMICS,
    "evidence": SpecialistAgentType.EVIDENCE,
    "reporting": SpecialistAgentType.REPORTING,
}


class AgentRouter:
    def route(
        self,
        user_query: str,
        available_inputs: dict[str, str] | None = None,
        domain: str | None = None,
    ) -> AgentRoute:
        normalized = user_query.lower()
        if domain:
            specialist = DOMAIN_TO_SPECIALIST.get(domain)
            if specialist:
                return AgentRoute(
                    domain="reporting" if domain == "evidence" else domain,
                    specialist_agent=specialist,
                    candidate_skill_ids=self._candidate_skills_for(specialist),
                    reasoning=f"Domain was provided explicitly as {domain}.",
                    confidence=0.9,
                )

        best: tuple[int, SpecialistAgentType, str, list[str], list[str]] | None = None
        for specialist, route_domain, keywords, skill_ids in ROUTING_RULES:
            matches = [keyword for keyword in keywords if keyword.lower() in normalized]
            score = len(matches)
            if score and (best is None or score > best[0]):
                best = (score, specialist, route_domain, skill_ids, matches)

        if best is None:
            input_route = self._route_by_inputs(available_inputs or {})
            if input_route:
                return input_route
            return AgentRoute(
                domain=None,
                specialist_agent=None,
                candidate_skill_ids=[],
                reasoning="No routing rule matched the query or available input types.",
                confidence=0.0,
            )

        score, specialist, route_domain, skill_ids, matches = best
        confidence = min(0.95, 0.55 + score * 0.15)
        return AgentRoute(
            domain=route_domain,
            specialist_agent=specialist,
            candidate_skill_ids=skill_ids,
            reasoning=f"Matched keywords for {specialist.value}: {', '.join(matches)}.",
            confidence=confidence,
        )

    def _candidate_skills_for(self, specialist: SpecialistAgentType) -> list[str]:
        for rule_specialist, _domain, _keywords, skill_ids in ROUTING_RULES:
            if rule_specialist == specialist:
                return skill_ids
        return []

    def _route_by_inputs(self, available_inputs: dict[str, str]) -> AgentRoute | None:
        input_types = set(available_inputs)
        if {"feature_table", "taxonomy_table"} & input_types:
            return AgentRoute("microbiome", SpecialistAgentType.MICROBIOME, ["microbiome.read_qc", "microbiome.differential_abundance"], "Routed from microbiome input types.", 0.55)
        if {"count_matrix", "expression_matrix"} & input_types:
            return AgentRoute("transcriptomics", SpecialistAgentType.TRANSCRIPTOMICS, ["transcriptomics.differential_expression"], "Routed from transcriptomics input types.", 0.55)
        if {"peak_table", "metabolite_annotation"} & input_types:
            return AgentRoute("metabolomics", SpecialistAgentType.METABOLOMICS, ["metabolomics.differential_metabolites"], "Routed from metabolomics input types.", 0.55)
        if {"analysis_result_table", "method_note", "risk_notes"} & input_types:
            return AgentRoute("reporting", SpecialistAgentType.REPORTING, ["reporting.evidence_report_generation"], "Routed from reporting input types.", 0.55)
        return None
