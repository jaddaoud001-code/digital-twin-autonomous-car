"""Telemetry data contract, read from the JSON Schema (single source of truth)."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from twin_maintenance.paths import telemetry_schema_path

Bound = tuple[float | None, float | None]


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_schema(path: Path | None = None) -> dict[str, Any]:
    """Load the telemetry JSON Schema (cached)."""
    return _load(str(path or telemetry_schema_path()))


def columns(schema: dict[str, Any] | None = None) -> list[str]:
    """Ordered CSV column names (the schema's ``required`` array)."""
    schema = schema or load_schema()
    return list(schema["required"])


def column_types(schema: dict[str, Any] | None = None) -> dict[str, str]:
    """JSON Schema type per column: ``string``, ``integer`` or ``number``."""
    schema = schema or load_schema()
    return {name: schema["properties"][name]["type"] for name in columns(schema)}


def numeric_columns(schema: dict[str, Any] | None = None) -> list[str]:
    """Columns whose type is ``integer`` or ``number``, in CSV order."""
    return [c for c, t in column_types(schema).items() if t in ("integer", "number")]


def bounds(schema: dict[str, Any] | None = None) -> dict[str, Bound]:
    """Inclusive (min, max) per bounded column; ``None`` means unbounded on that side."""
    schema = schema or load_schema()
    result: dict[str, Bound] = {}
    for name in columns(schema):
        prop = schema["properties"][name]
        lo, hi = prop.get("minimum"), prop.get("maximum")
        if lo is not None or hi is not None:
            result[name] = (lo, hi)
    return result


def descriptions(schema: dict[str, Any] | None = None) -> dict[str, str]:
    """Human-readable description (with unit) per column."""
    schema = schema or load_schema()
    return {name: schema["properties"][name].get("description", "") for name in columns(schema)}
