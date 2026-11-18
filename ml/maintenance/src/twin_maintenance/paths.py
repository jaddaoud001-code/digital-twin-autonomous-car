"""Repository paths, resolved from this file's location (never from the CWD)."""

from functools import lru_cache
from pathlib import Path

_MARKER_DIR = "contracts"


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Return the monorepo root: the first ancestor containing a ``contracts/`` dir."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / _MARKER_DIR).is_dir():
            return parent
    raise RuntimeError(f"Could not find repository root (no '{_MARKER_DIR}/' above {here})")


def raw_data_dir() -> Path:
    """Directory where the simulator writes telemetry CSV files."""
    return repo_root() / "data" / "raw"


def processed_data_dir() -> Path:
    """Directory for derived outputs (summaries, figures)."""
    return repo_root() / "data" / "processed"


def figures_dir() -> Path:
    """Directory for generated PNG figures."""
    return processed_data_dir() / "figures"


def telemetry_schema_path() -> Path:
    """Path of the telemetry sample JSON Schema (v1)."""
    return repo_root() / "contracts" / "telemetry" / "telemetry-sample.v1.schema.json"


def csv_recorder_source_path() -> Path:
    """Path of the C# CSV recorder (read-only, used by cross-language contract tests)."""
    return (
        repo_root()
        / "simulator"
        / "DigitalTwinSimulator"
        / "Assets"
        / "Scripts"
        / "Telemetry"
        / "TelemetryCsvRecorder.cs"
    )
