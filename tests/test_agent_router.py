from agents.models import SpecialistAgentType
from agents.router import AgentRouter


def test_microbiome_query_routes_to_microbiome_agent():
    route = AgentRouter().route("请对菌群 ASV table 做差异菌群分析", {})

    assert route.specialist_agent == SpecialistAgentType.MICROBIOME
    assert "microbiome.differential_abundance" in route.candidate_skill_ids


def test_transcriptomics_query_routes_to_transcriptomics_agent():
    route = AgentRouter().route("RNA-seq count matrix 差异基因分析", {})

    assert route.specialist_agent == SpecialistAgentType.TRANSCRIPTOMICS


def test_metabolomics_query_routes_to_metabolomics_agent():
    route = AgentRouter().route("代谢组 peak table 差异代谢物分析", {})

    assert route.specialist_agent == SpecialistAgentType.METABOLOMICS


def test_multiomics_query_routes_to_multiomics_agent():
    route = AgentRouter().route("构建多组学 correlation network 关联网络", {})

    assert route.specialist_agent == SpecialistAgentType.MULTIOMICS


def test_evidence_query_routes_to_evidence_agent():
    route = AgentRouter().route("生成 PubMed 文献证据和机制解释问题", {})

    assert route.specialist_agent == SpecialistAgentType.EVIDENCE


def test_report_query_routes_to_report_agent():
    route = AgentRouter().route("生成专家报告和总结", {})

    assert route.specialist_agent == SpecialistAgentType.REPORTING


def test_unknown_query_returns_no_specialist():
    route = AgentRouter().route("I have a vague task without omics context", {})

    assert route.specialist_agent is None
    assert route.confidence == 0.0
