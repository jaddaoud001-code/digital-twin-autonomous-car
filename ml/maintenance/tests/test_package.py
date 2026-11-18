"""Smoke tests for the package and the telemetry contract file."""

import json
from pathlib import Path

import jsonschema

import twin_maintenance

SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "contracts"
    / "telemetry"
    / "telemetry-sample.v1.schema.json"
)


def test_version() -> None:
    assert twin_maintenance.__version__ == "0.1.0"


def test_schema_is_valid_draft_2020_12() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert len(schema["required"]) == 20
    assert set(schema["required"]) == set(schema["properties"])
    for name, prop in schema["properties"].items():
        assert prop.get("description"), f"missing description for {name}"
