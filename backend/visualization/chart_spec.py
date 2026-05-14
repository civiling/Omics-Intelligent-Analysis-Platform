from __future__ import annotations

import json
from pathlib import Path

from .models import ChartSpec


def load_chart_spec(path: str | Path) -> ChartSpec:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return ChartSpec.from_mapping(data)


def write_chart_spec(spec: ChartSpec, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(spec.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path
