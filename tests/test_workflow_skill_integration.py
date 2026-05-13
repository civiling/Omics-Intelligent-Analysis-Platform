from skill_registry import SkillLoader
from workflows import WorkflowRegistry, WorkflowRunner, WorkflowValidator


def test_workflow_validator_passes_with_skill_registry_alignment():
    assert WorkflowValidator().validate() == []


def test_workflow_skill_ids_exist_in_skill_registry():
    skills = SkillLoader().load_all()
    workflows = WorkflowRegistry().load_all()

    for workflow in workflows.values():
        assert workflow.skill_id in skills


def test_workflow_input_output_types_align_with_skill_registry():
    skills = SkillLoader().load_all()
    workflows = WorkflowRegistry().load_all()

    for workflow in workflows.values():
        skill = skills[workflow.skill_id]
        assert set(workflow.input_types).issubset(set(skill.metadata.input_types))
        assert set(workflow.output_types).issubset(set(skill.metadata.output_types))
        assert workflow.risk_level == skill.metadata.risk_level.value
        assert workflow.requires_review == skill.metadata.requires_review


def test_runner_can_find_workflow_by_skill_id():
    workflow = WorkflowRunner().get_workflow_by_skill("multiomics.correlation_network")

    assert workflow is not None
    assert workflow.id == "multiomics.correlation_network"
