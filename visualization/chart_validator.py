from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .models import ChartSpec, ChartType, ChartValidationResult


FIELD_REFERENCES = ("x", "y", "label", "color_by", "size_by")
CODE_KEYS = {"code", "script", "javascript", "python", "r_code", "shell", "command", "exec"}


class ChartValidator:
    def validate(self, spec: ChartSpec | dict[str, Any], run_dir: str | Path) -> ChartValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        run_path = Path(run_dir).resolve()

        if isinstance(spec, dict):
            try:
                spec = ChartSpec.from_mapping(spec)
            except Exception as exc:
                return ChartValidationResult(False, [f"Invalid chart spec: {exc}"], [])

        if spec.chart_type not in set(ChartType):
            errors.append(f"chart_type is not allowed: {spec.chart_type}")

        if self._contains_code_keys(spec.to_dict()):
            errors.append("chart_spec contains executable-code-like keys, which are not allowed.")

        data_path = (run_path / spec.data_source).resolve()
        if not self._is_within(data_path, run_path):
            errors.append(f"data_source must stay inside run_dir: {spec.data_source}")
        if not data_path.exists():
            errors.append(f"data_source does not exist: {spec.data_source}")
            headers: list[str] = []
        else:
            try:
                headers = self._read_headers(data_path)
            except Exception as exc:
                errors.append(f"Cannot read data_source headers: {exc}")
                headers = []

        if headers:
            for field_name in FIELD_REFERENCES:
                value = getattr(spec, field_name)
                if value and value not in headers:
                    errors.append(f"{field_name} field {value!r} is not present in data_source headers.")
            for filter_name in spec.filters:
                referenced = self._filter_field_name(filter_name)
                if referenced not in headers:
                    errors.append(f"filter {filter_name!r} references missing field {referenced!r}.")

        for key, value in spec.thresholds.items():
            if not isinstance(value, (int, float)):
                errors.append(f"threshold {key!r} must be numeric; got {value!r}.")

        if spec.output_path:
            output_path = (run_path / spec.output_path).resolve()
            figures_dir = (run_path / "outputs" / "figures").resolve()
            if not self._is_within(output_path, figures_dir):
                errors.append("output_path must stay inside outputs/figures for this run.")
        else:
            warnings.append("output_path is not set; renderer will choose a default path.")

        if spec.chart_type in {ChartType.VOLCANO, ChartType.BARPLOT, ChartType.BOXPLOT, ChartType.PCA}:
            if not spec.x:
                errors.append(f"{spec.chart_type.value} chart requires x.")
            if not spec.y:
                errors.append(f"{spec.chart_type.value} chart requires y.")

        return ChartValidationResult(valid=not errors, errors=errors, warnings=warnings)

    def _read_headers(self, path: Path) -> list[str]:
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            return next(reader, [])

    def _filter_field_name(self, filter_name: str) -> str:
        for suffix in ("_lt", "_lte", "_gt", "_gte", "_eq", "_neq"):
            if filter_name.endswith(suffix):
                return filter_name[: -len(suffix)]
        return filter_name

    def _is_within(self, path: Path, parent: Path) -> bool:
        return path == parent or parent in path.parents

    def _contains_code_keys(self, value: Any) -> bool:
        if isinstance(value, dict):
            for key, nested in value.items():
                if str(key).lower() in CODE_KEYS:
                    return True
                if self._contains_code_keys(nested):
                    return True
        if isinstance(value, list):
            return any(self._contains_code_keys(item) for item in value)
        return False
