from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import Generic, TypeVar

from backend.storage.models import SerializableModel


ModelT = TypeVar("ModelT", bound=SerializableModel)


class RepositoryError(Exception):
    """Base error for local persistence failures."""


class JsonRepository(Generic[ModelT]):
    def __init__(
        self,
        model_cls: type[ModelT],
        id_field: str,
        storage_dir: str | Path,
        collection_name: str | None = None,
    ) -> None:
        self.model_cls = model_cls
        self.id_field = id_field
        self.storage_dir = Path(storage_dir).resolve()
        self.collection_name = collection_name or model_cls.__name__.lower()
        self.path = self.storage_dir / f"{self.collection_name}.json"
        self._field_names = {model_field.name for model_field in fields(model_cls)}
        if id_field not in self._field_names:
            raise RepositoryError(f"{model_cls.__name__} has no id field named {id_field}.")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, model: ModelT) -> ModelT:
        data = self._read_collection()
        model_id = self.get_model_id(model)
        data[model_id] = model.to_dict()
        self._write_collection(data)
        return model

    def get(self, model_id: str) -> ModelT | None:
        data = self._read_collection()
        raw = data.get(model_id)
        if raw is None:
            return None
        return self.model_cls.from_dict(raw)

    def require(self, model_id: str) -> ModelT:
        model = self.get(model_id)
        if model is None:
            raise RepositoryError(f"{self.model_cls.__name__} {model_id} was not found.")
        return model

    def list(self) -> list[ModelT]:
        data = self._read_collection()
        return [self.model_cls.from_dict(item) for item in data.values()]

    def delete(self, model_id: str) -> bool:
        data = self._read_collection()
        if model_id not in data:
            return False
        del data[model_id]
        self._write_collection(data)
        return True

    def filter_by(self, **criteria: object) -> list[ModelT]:
        unknown_fields = set(criteria) - self._field_names
        if unknown_fields:
            raise RepositoryError(f"Unknown filter field(s): {', '.join(sorted(unknown_fields))}.")
        return [
            model
            for model in self.list()
            if all(getattr(model, key) == value for key, value in criteria.items())
        ]

    def get_model_id(self, model: ModelT) -> str:
        model_id = getattr(model, self.id_field)
        if not model_id:
            raise RepositoryError(f"{self.model_cls.__name__}.{self.id_field} cannot be empty.")
        return str(model_id)

    def _read_collection(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RepositoryError(f"Could not read repository file {self.path}: {exc}") from exc

    def _write_collection(self, data: dict[str, dict]) -> None:
        temporary_path = self.path.with_suffix(".json.tmp")
        temporary_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary_path.replace(self.path)
