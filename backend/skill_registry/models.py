from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SkillRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SkillReviewRequirement(str, Enum):
    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"


@dataclass(frozen=True)
class SkillInput:
    type: str
    description: str = ""
    required: bool = True


@dataclass(frozen=True)
class SkillOutput:
    type: str
    description: str = ""


@dataclass(frozen=True)
class SkillExecutor:
    type: str = "placeholder"
    path: str | None = None
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None) -> "SkillExecutor":
        data = data or {}
        known = {"type", "path"}
        return cls(
            type=str(data.get("type", "placeholder")),
            path=data.get("path"),
            config={key: value for key, value in data.items() if key not in known},
        )


@dataclass(frozen=True)
class SkillMetadata:
    id: str
    name: str
    domain: str
    version: str
    status: str
    description: str
    input_types: list[str]
    output_types: list[str]
    primary_tools: list[str]
    risk_level: SkillRiskLevel
    requires_review: bool
    next_skills: list[str]
    executor: SkillExecutor
    skill_path: Path

    @classmethod
    def from_registry_entry(
        cls,
        entry: dict[str, Any],
        registry_root: Path,
    ) -> "SkillMetadata":
        return cls(
            id=str(entry["id"]),
            name=str(entry["name"]),
            domain=str(entry["domain"]),
            version=str(entry["version"]),
            status=str(entry["status"]),
            description=str(entry["description"]),
            input_types=list(entry.get("input_types", [])),
            output_types=list(entry.get("output_types", [])),
            primary_tools=list(entry.get("primary_tools", [])),
            risk_level=SkillRiskLevel(str(entry["risk_level"])),
            requires_review=bool(entry.get("requires_review", False)),
            next_skills=list(entry.get("next_skills", [])),
            executor=SkillExecutor.from_mapping(entry.get("executor")),
            skill_path=(registry_root / str(entry["path"])).resolve(),
        )


@dataclass(frozen=True)
class LoadedSkill:
    metadata: SkillMetadata
    skill_markdown: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    parameters: dict[str, Any]
    executor_config: dict[str, Any]
    method_notes: str = ""
    risk_notes: str = ""

    @property
    def id(self) -> str:
        return self.metadata.id

    @property
    def domain(self) -> str:
        return self.metadata.domain


@dataclass(frozen=True)
class SkillRouteRecommendation:
    skill_id: str | None
    reason: str
    missing_inputs: list[str]
    risk_level: SkillRiskLevel | None
    requires_review: bool
    next_skills: list[str]
