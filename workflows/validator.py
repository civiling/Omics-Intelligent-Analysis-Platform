from __future__ import annotations

from pathlib import Path
from typing import Any

from skill_registry import SkillLoader
from skill_registry.loader import _load_yaml_file

from .models import ExecutorType


REQUIRED_WORKFLOW_FIELDS = {
    "id",
    "name",
    "domain",
    "version",
    "description",
    "skill_id",
    "executor_type",
    "script_path",
    "input_types",
    "output_types",
    "default_parameters",
    "required_parameters",
    "timeout_seconds",
    "risk_level",
    "requires_review",
}

VALID_RISK_LEVELS = {"low", "medium", "high"}


class WorkflowValidator:
    def __init__(
        self,
        configs_dir: str | Path | None = None,
        skill_loader: SkillLoader | None = None,
    ) -> None:
        self.package_root = Path(__file__).resolve().parent
        self.project_root = self.package_root.parent
        self.configs_dir = Path(configs_dir or self.package_root / "configs").resolve()
        self.skill_loader = skill_loader or SkillLoader()

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.configs_dir.exists():
            return [f"Workflow configs directory not found: {self.configs_dir}"]

        configs = self._load_configs(errors)
        seen_ids: set[str] = set()
        skill_map = self._load_skills(errors)

        for path, config in configs:
            workflow_id = str(config.get("id", path.name))
            missing = sorted(REQUIRED_WORKFLOW_FIELDS - set(config))
            for field_name in missing:
                errors.append(f"{workflow_id}: missing required field: {field_name}")

            if workflow_id in seen_ids:
                errors.append(f"{workflow_id}: duplicate workflow id.")
            seen_ids.add(workflow_id)

            executor_type = config.get("executor_type")
            if executor_type is not None and executor_type not in {item.value for item in ExecutorType}:
                errors.append(
                    f"{workflow_id}: executor_type must be one of placeholder, local; got {executor_type!r}."
                )

            for field_name in ("input_types", "output_types", "required_parameters"):
                if field_name in config and not isinstance(config[field_name], list):
                    errors.append(f"{workflow_id}: {field_name} must be a list.")
                elif field_name in ("input_types", "output_types") and config.get(field_name) == []:
                    errors.append(f"{workflow_id}: {field_name} must not be empty.")

            if "default_parameters" in config and not isinstance(config["default_parameters"], dict):
                errors.append(f"{workflow_id}: default_parameters must be a mapping.")

            risk_level = config.get("risk_level")
            if risk_level is not None and str(risk_level) not in VALID_RISK_LEVELS:
                errors.append(
                    f"{workflow_id}: risk_level must be one of low, medium, high; got {risk_level!r}."
                )

            timeout = config.get("timeout_seconds")
            if timeout is not None:
                if not isinstance(timeout, int) or timeout <= 0:
                    errors.append(f"{workflow_id}: timeout_seconds must be a positive integer.")

            script_path = config.get("script_path")
            if script_path and executor_type == ExecutorType.LOCAL.value:
                resolved_script_path = (self.project_root / str(script_path)).resolve()
                if not resolved_script_path.exists():
                    errors.append(f"{workflow_id}: script_path does not exist: {resolved_script_path}")

            self._validate_skill_alignment(workflow_id, config, skill_map, errors)

        return errors

    def _load_configs(self, errors: list[str]) -> list[tuple[Path, dict[str, Any]]]:
        configs: list[tuple[Path, dict[str, Any]]] = []
        for path in sorted(self.configs_dir.glob("*.yaml")):
            try:
                data = _load_yaml_file(path)
            except Exception as exc:
                errors.append(f"{path}: cannot read workflow config: {exc}")
                continue
            if not isinstance(data, dict):
                errors.append(f"{path}: workflow config must be a mapping.")
                continue
            configs.append((path, data))
        return configs

    def _load_skills(self, errors: list[str]) -> dict[str, Any]:
        try:
            return self.skill_loader.load_all()
        except Exception as exc:
            errors.append(f"Cannot load skill registry for workflow validation: {exc}")
            return {}

    def _validate_skill_alignment(
        self,
        workflow_id: str,
        config: dict[str, Any],
        skill_map: dict[str, Any],
        errors: list[str],
    ) -> None:
        skill_id = config.get("skill_id")
        if not skill_id or not skill_map:
            return

        skill = skill_map.get(skill_id)
        if skill is None:
            errors.append(f"{workflow_id}: skill_id is not registered in skill_registry: {skill_id}")
            return

        input_types = set(config.get("input_types", []) or [])
        skill_input_types = set(skill.metadata.input_types)
        if not input_types.issubset(skill_input_types):
            extra = sorted(input_types - skill_input_types)
            errors.append(f"{workflow_id}: input_types not declared by skill {skill_id}: {extra}")

        output_types = set(config.get("output_types", []) or [])
        skill_output_types = set(skill.metadata.output_types)
        if not output_types.issubset(skill_output_types):
            extra = sorted(output_types - skill_output_types)
            errors.append(f"{workflow_id}: output_types not declared by skill {skill_id}: {extra}")

        risk_level = config.get("risk_level")
        if risk_level is not None and str(risk_level) != skill.metadata.risk_level.value:
            errors.append(
                f"{workflow_id}: risk_level {risk_level!r} does not match skill {skill_id} risk_level {skill.metadata.risk_level.value!r}."
            )

        requires_review = config.get("requires_review")
        if requires_review is not None and bool(requires_review) != skill.metadata.requires_review:
            errors.append(
                f"{workflow_id}: requires_review {requires_review!r} does not match skill {skill_id}."
            )
