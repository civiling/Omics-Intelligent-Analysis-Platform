from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SampleMetadataUpdateRequest(BaseModel):
    updates_by_sample_id: dict[str, dict[str, Any]] = Field(default_factory=dict)
    confirm: bool = True
    evaluate: bool = True
    min_replicates_per_condition: int = 2


class SampleMetadataUpdateResponse(BaseModel):
    updated_rows: list[dict[str, Any]]
    design: dict[str, Any] | None = None

