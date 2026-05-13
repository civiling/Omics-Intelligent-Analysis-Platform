import pytest

from agents.context import AgentContext
from agents.models import AgentTask
from agents.specialists import (
    EvidenceAgent,
    MetabolomicsAgent,
    MicrobiomeAgent,
    MultiomicsAgent,
    ReportAgent,
    TranscriptomicsAgent,
)
from workflows import WorkflowRunner


def context(tmp_path):
    return AgentContext(workflow_runner=WorkflowRunner(runs_dir=tmp_path / "runs"), agent_logs_dir=tmp_path / "logs")


def test_microbiome_agent_selects_differential_abundance(tmp_path):
    agent = MicrobiomeAgent(context(tmp_path))
    task = AgentTask(
        task_id="micro_diff",
        user_query="差异菌群分析",
        available_inputs={},
        requested_outputs=["differential_taxa_table"],
    )

    assert agent.select_skill(task) == "microbiome.differential_abundance"


def test_microbiome_agent_selects_read_qc_by_default(tmp_path):
    agent = MicrobiomeAgent(context(tmp_path))
    task = AgentTask(task_id="micro_qc", user_query="microbiome read QC", available_inputs={})

    assert agent.select_skill(task) == "microbiome.read_qc"


@pytest.mark.parametrize(
    ("agent_cls", "expected_skill"),
    [
        (TranscriptomicsAgent, "transcriptomics.differential_expression"),
        (MetabolomicsAgent, "metabolomics.differential_metabolites"),
        (MultiomicsAgent, "multiomics.correlation_network"),
        (EvidenceAgent, "reporting.evidence_report_generation"),
        (ReportAgent, "reporting.evidence_report_generation"),
    ],
)
def test_single_skill_specialists_select_registered_skill(tmp_path, agent_cls, expected_skill):
    agent = agent_cls(context(tmp_path))
    task = AgentTask(task_id="specialist_task", user_query="run analysis", available_inputs={})

    assert agent.select_skill(task) == expected_skill


def test_unregistered_skill_cannot_be_validated_by_specialist(tmp_path):
    agent = MicrobiomeAgent(context(tmp_path))

    with pytest.raises(ValueError, match="does not support skill"):
        agent._validate_supported_skill("unregistered.skill")
