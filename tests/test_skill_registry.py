import json
from pathlib import Path

import pytest

from skill_registry import SkillLoader, SkillRouter, SkillValidator
from skill_registry.validator import REQUIRED_SKILL_SECTIONS


EXPECTED_SKILLS = {
    "scrna.data_ingestion",
    "scrna.metadata_design",
    "scrna.qc_clustering",
    "microbiome.read_qc",
    "microbiome.differential_abundance",
    "transcriptomics.differential_expression",
    "metabolomics.differential_metabolites",
    "multiomics.correlation_network",
    "reporting.evidence_report_generation",
}


def test_registry_can_be_loaded():
    loader = SkillLoader()
    skills = loader.load_all()

    assert set(skills) == EXPECTED_SKILLS


@pytest.mark.parametrize("skill_id", sorted(EXPECTED_SKILLS))
def test_initial_skills_can_be_found(skill_id):
    skill = SkillLoader().get_by_id(skill_id)

    assert skill is not None
    assert skill.metadata.id == skill_id


def test_each_skill_markdown_contains_required_sections():
    skills = SkillLoader().load_all()

    for skill in skills.values():
        for section in REQUIRED_SKILL_SECTIONS:
            assert section in skill.skill_markdown, f"{skill.id} missing {section}"


def test_validator_reports_missing_registry_field(tmp_path):
    registry_path = tmp_path / "registry.yaml"
    registry_path.write_text(
        """
skills:
  - id: broken.skill
    domain: testing
    version: 0.1.0
    status: active
    description: Missing name and other required fields.
""".strip(),
        encoding="utf-8",
    )

    errors = SkillValidator(registry_path).validate()

    assert any("broken.skill: missing required field: name" in error for error in errors)


@pytest.mark.parametrize(
    ("description", "available_inputs", "expected_skill"),
    [
        (
            "请做差异菌群分析，输入有 ASV feature table、taxonomy 和 metadata",
            ["feature_table", "taxonomy_table", "metadata"],
            "microbiome.differential_abundance",
        ),
        (
            "RNA-seq count matrix 差异基因分析",
            ["count_matrix", "metadata"],
            "transcriptomics.differential_expression",
        ),
        (
            "代谢组 peak table 中寻找差异代谢物",
            ["peak_table", "metadata"],
            "metabolomics.differential_metabolites",
        ),
        (
            "构建菌群、基因、代谢物之间的多组学关联网络",
            ["feature_table", "expression_matrix", "metabolite_matrix", "metadata"],
            "multiomics.correlation_network",
        ),
        (
            "根据分析结果生成文献证据和报告段落",
            ["analysis_result_table", "method_note", "risk_notes"],
            "reporting.evidence_report_generation",
        ),
    ],
)
def test_router_recommends_expected_skill(description, available_inputs, expected_skill):
    recommendation = SkillRouter().recommend(description, available_inputs)

    assert recommendation.skill_id == expected_skill


def test_next_skill_references_are_valid():
    assert SkillValidator().validate() == []


def test_input_and_output_schemas_are_valid_json():
    skills_root = Path(__file__).resolve().parents[1] / "skill_registry" / "skills"

    for schema_path in list(skills_root.rglob("input_schema.json")) + list(
        skills_root.rglob("output_schema.json")
    ):
        with schema_path.open("r", encoding="utf-8") as handle:
            assert isinstance(json.load(handle), dict)
