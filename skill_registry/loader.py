from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import LoadedSkill, SkillMetadata


class SkillRegistryError(RuntimeError):
    """Raised when the registry or a skill package cannot be loaded."""


def _load_yaml_file(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        try:
            return _load_simple_yaml_file(path)
        except Exception as fallback_exc:
            raise SkillRegistryError(
                f"Cannot read YAML file {path}: PyYAML is not installed and "
                f"the built-in simple parser failed: {fallback_exc}"
            ) from exc

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except Exception as exc:
        raise SkillRegistryError(f"Cannot parse YAML file {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SkillRegistryError(f"YAML file {path} must contain a mapping at top level.")
    return data


def _load_simple_yaml_file(path: Path) -> dict[str, Any]:
    lines: list[tuple[int, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        lines.append((indent, raw_line.strip()))

    if not lines:
        return {}

    data, next_index = _parse_yaml_block(lines, 0, lines[0][0])
    if next_index != len(lines):
        raise ValueError(f"Unexpected content at line {next_index + 1}.")
    if not isinstance(data, dict):
        raise ValueError("Top-level YAML value must be a mapping.")
    return data


def _parse_yaml_block(
    lines: list[tuple[int, str]],
    index: int,
    indent: int,
) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index

    current_indent, content = lines[index]
    if current_indent < indent:
        return {}, index
    if current_indent != indent:
        raise ValueError(f"Unexpected indentation near {content!r}.")

    if content.startswith("- "):
        values: list[Any] = []
        while index < len(lines) and lines[index][0] == indent and lines[index][1].startswith("- "):
            item_text = lines[index][1][2:].strip()
            index += 1
            if not item_text:
                value, index = _parse_yaml_block(lines, index, indent + 2)
                values.append(value)
            elif ":" in item_text and not item_text.startswith(("'", '"')):
                key, raw_value = _split_yaml_key_value(item_text)
                item: dict[str, Any] = {key: _parse_yaml_scalar(raw_value)}
                if index < len(lines) and lines[index][0] > indent:
                    nested, index = _parse_yaml_block(lines, index, indent + 2)
                    if isinstance(nested, dict):
                        item.update(nested)
                    else:
                        raise ValueError(f"List item mapping cannot merge nested {type(nested).__name__}.")
                values.append(item)
            else:
                values.append(_parse_yaml_scalar(item_text))
        return values, index

    mapping: dict[str, Any] = {}
    while index < len(lines) and lines[index][0] == indent and not lines[index][1].startswith("- "):
        key, raw_value = _split_yaml_key_value(lines[index][1])
        index += 1
        if raw_value == "":
            value, index = _parse_yaml_block(lines, index, indent + 2)
            mapping[key] = value
        else:
            mapping[key] = _parse_yaml_scalar(raw_value)
    return mapping, index


def _split_yaml_key_value(content: str) -> tuple[str, str]:
    if ":" not in content:
        raise ValueError(f"Expected key/value YAML line, got {content!r}.")
    key, value = content.split(":", 1)
    return key.strip(), value.strip()


def _parse_yaml_scalar(value: str) -> Any:
    if value in {"", "null", "Null", "NULL", "~"}:
        return None
    if value in {"true", "True", "TRUE"}:
        return True
    if value in {"false", "False", "FALSE"}:
        return False
    if value == "[]":
        return []
    if value == "{}":
        return {}
    if value.startswith("[") or value.startswith("{"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value.strip("'\"")


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        raise SkillRegistryError(f"Cannot parse JSON file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SkillRegistryError(f"JSON file {path} must contain an object at top level.")
    return data


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise SkillRegistryError(f"Cannot read text file {path}: {exc}") from exc


class SkillLoader:
    def __init__(self, registry_path: str | Path | None = None) -> None:
        package_root = Path(__file__).resolve().parent
        self.registry_path = Path(registry_path or package_root / "registry.yaml").resolve()
        self.registry_root = self.registry_path.parent
        self._skills: dict[str, LoadedSkill] | None = None

    def load_registry(self) -> list[SkillMetadata]:
        if not self.registry_path.exists():
            raise SkillRegistryError(f"Registry file not found: {self.registry_path}")

        registry = _load_yaml_file(self.registry_path)
        entries = registry.get("skills")
        if not isinstance(entries, list):
            raise SkillRegistryError(
                f"Registry file {self.registry_path} must define a 'skills' list."
            )

        metadata: list[SkillMetadata] = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise SkillRegistryError(
                    f"Registry entry at index {index} must be a mapping."
                )
            try:
                metadata.append(SkillMetadata.from_registry_entry(entry, self.registry_root))
            except KeyError as exc:
                raise SkillRegistryError(
                    f"Registry entry at index {index} is missing required field: {exc.args[0]}"
                ) from exc
            except ValueError as exc:
                skill_id = entry.get("id", f"index {index}")
                raise SkillRegistryError(f"Invalid registry entry {skill_id}: {exc}") from exc
        return metadata

    def load_skill(self, metadata: SkillMetadata) -> LoadedSkill:
        skill_dir = metadata.skill_path
        if not skill_dir.exists():
            raise SkillRegistryError(f"Skill directory not found for {metadata.id}: {skill_dir}")

        required_files = {
            "SKILL.md": skill_dir / "SKILL.md",
            "input_schema.json": skill_dir / "input_schema.json",
            "output_schema.json": skill_dir / "output_schema.json",
            "parameters.yaml": skill_dir / "parameters.yaml",
            "executor.yaml": skill_dir / "executor.yaml",
        }
        for label, path in required_files.items():
            if not path.exists():
                raise SkillRegistryError(f"Missing {label} for {metadata.id}: {path}")

        method_notes_path = skill_dir / "method_notes.md"
        risk_notes_path = skill_dir / "risk_notes.md"

        return LoadedSkill(
            metadata=metadata,
            skill_markdown=_read_text(required_files["SKILL.md"]),
            input_schema=_load_json_file(required_files["input_schema.json"]),
            output_schema=_load_json_file(required_files["output_schema.json"]),
            parameters=_load_yaml_file(required_files["parameters.yaml"]),
            executor_config=_load_yaml_file(required_files["executor.yaml"]),
            method_notes=_read_text(method_notes_path) if method_notes_path.exists() else "",
            risk_notes=_read_text(risk_notes_path) if risk_notes_path.exists() else "",
        )

    def load_all(self) -> dict[str, LoadedSkill]:
        if self._skills is None:
            skills: dict[str, LoadedSkill] = {}
            for metadata in self.load_registry():
                if metadata.id in skills:
                    raise SkillRegistryError(f"Duplicate skill id in registry: {metadata.id}")
                skills[metadata.id] = self.load_skill(metadata)
            self._skills = skills
        return self._skills

    def get_by_id(self, skill_id: str) -> LoadedSkill | None:
        return self.load_all().get(skill_id)

    def get_by_domain(self, domain: str) -> list[LoadedSkill]:
        return [
            skill
            for skill in self.load_all().values()
            if skill.metadata.domain == domain
        ]

    def get_by_input_type(self, input_type: str) -> list[LoadedSkill]:
        return [
            skill
            for skill in self.load_all().values()
            if input_type in skill.metadata.input_types
        ]
