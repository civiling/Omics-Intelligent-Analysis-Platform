from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from visualization.models import ChartSpec, RenderedChart


class BaseChartRenderer(ABC):
    @abstractmethod
    def render(self, spec: ChartSpec, run_dir: str | Path) -> RenderedChart:
        """Render a validated chart spec to a deterministic artifact."""
