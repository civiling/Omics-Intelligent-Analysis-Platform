from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .loader import _load_yaml_file


REQUIRED_REGISTRY_FIELDS = {
    "id",
    "name",
    "domain",
    "version",
    "status",
    "description",
    "path",
    "input_types",
    "output_types",
    "primary_tools",
    "risk_level",
    "requires_review",
    "next_skills",
    "executor",
}

REQUIRED_SKILL_SECTIONS = [
    "# ",
    "## Purpose",
    "## Use when",
    "## Inputs",
    "## Outputs",
    "## Primary tools",
    "## Default strategy",
    "## Parameters",
    "## QC checks",
    "## Interpretation limits",
    "## Risk notes",
    "## Next skills",
    "## Review requirement",
]

VALID_RISK_LEVELS = {"low", "medium", "high"}


class SkillValidator:
    def __init__(self, registry_path: str | Path | None = None) -> None:
        package_root = Path(__file__).resolve().parent
        self.registry_path = Path(registry_path or package_root / "registry.yaml").resolve()
        self.registry_root = self.registry_path.parent

    def validate(self) -> list[str]:
        errors: list[str] = []
        registry = self._load_registry(errors)
        if registry is None:
            return errors

        skills = registry.get("skills")
        if not isinstance(skills, list):
            return [*errors, f"{self.registry_path}: top-level 'skills' must be a list."]

        skill_ids = {
            str(skill.get("id"))
            for skill in skills
            if isinstance(skill, dict) and skill.get("id")
        }
        seen_ids: set[str] = set()

        for index, entry in enumerate(skills):
            label = f"skills[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{label}: registry entry must be a mapping.")
                continue

            skill_id = str(entry.get("id", label))
            missing_fields = sorted(REQUIRED_REGISTRY_FIELDS - set(entry))
            for field_name in missing_fields:
                errors.append(f"{skill_id}: missing required field: {field_name}")

            if skill_id in seen_ids:
                errors.append(f"{skill_id}: duplicate skill id.")
            seen_ids.add(skill_id)

            risk_level = entry.get("risk_level")
            if risk_level is not None and str(risk_level) not in VALID_RISK_LEVELS:
                errors.append(
                    f"{skill_id}: risk_level must be one of low, medium, high; got {risk_level!r}."
                )

            for field_name in ("input_types", "output_types", "primary_tools", "next_skills"):
                if field_name in entry and not isinstance(entry[field_name], list):
                    errors.append(f"{skill_id}: {field_name} must be a list.")

            executor = entry.get("executor")
            if executor is not None and not isinstance(executor, dict):
                errors.append(f"{skill_id}: executor must be a mapping.")

            for next_skill in entry.get("next_skills", []) or []:
                if next_skill not in skill_ids:
                    errors.append(f"{skill_id}: next_skills references unknown skill {next_skill!r}.")

            path_value = entry.get("path")
            if path_value:
                self._validate_skill_directory(skill_id, self.registry_root / str(path_value), errors)

        return errors

    def _load_registry(self, errors: list[str]) -> dict[str, Any] | None:
        if not self.registry_path.exists():
            errors.append(f"Registry file not found: {self.registry_path}")
            return None
        try:
            return _load_yaml_file(self.registry_path)
        except Exception as exc:
            errors.append(str(exc))
            return None

    def _validate_skill_directory(self, skill_id: str, skill_dir: Path, errors: list[str]) -> None:
        if not skill_dir.exists():
            errors.append(f"{skill_id}: skill directory not found: {skill_dir}")
            return

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            errors.append(f"{skill_id}: missing SKILL.md: {skill_md}")
        else:
            try:
                content = skill_md.read_text(encoding="utf-8")
            except Exception as exc:
                errors.append(f"{skill_id}: cannot read SKILL.md: {exc}")
            else:
                for section in REQUIRED_SKILL_SECTIONS:
                    if section not in content:
                        errors.append(f"{skill_id}: SKILL.md missing required section {section!r}.")

        for filename in ("input_schema.json", "output_schema.json"):
            path = skill_dir / filename
            if not path.exists():
                errors.append(f"{skill_id}: missing {filename}: {path}")
                continue
            try:
                with path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except Exception as exc:
                errors.append(f"{skill_id}: invalid JSON in {filename}: {exc}")
                continue
            if not isinstance(data, dict):
                errors.append(f"{skill_id}: {filename} must contain a JSON object.")

        for filename in ("parameters.yaml", "executor.yaml"):
            path = skill_dir / filename
            if not path.exists():
                errors.append(f"{skill_id}: missing {filename}: {path}")
                continue
            try:
                _load_yaml_file(path)
            except Exception as exc:
                errors.append(f"{skill_id}: invalid YAML in {filename}: {exc}")
