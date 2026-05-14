from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AiChatRequest(BaseModel):
    question: str
    context: dict[str, Any] = Field(default_factory=dict)


class AiChatResponse(BaseModel):
    answer: str
    model: str

