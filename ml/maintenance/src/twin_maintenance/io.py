"""Loading telemetry CSV runs."""

import csv
from pathlib import Path

import pandas as pd

from twin_maintenance import contract
from twin_maintenance.validation import ValidationReport, validate_run

RUN_ID_COLUMN = "run_id"


def run_id_from_path(path: Path) -> str:
    """Run identifier: the file name without extension."""
    return Path(path).stem


def read_raw_run(path: Path | str) -> pd.DataFrame:
    """Read a run as untyped strings, keeping the file's own header.

    Uses the ``csv`` module rather than ``pd.read_csv`` so that a malformed header
    (e.g. a missing comma) cannot silently shift columns. Rows whose width differs
    from the header are dropped and counted in ``df.attrs["ragged_rows"]``.
    The UTF-8 BOM written by the C# recorder is stripped.
    """
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader, [])
        rows = [row for row in reader if row]  # ignore blank lines (e.g. trailing newline)

    width = len(header)
    good = [row for row in rows if len(row) == width]
    df = pd.DataFrame(good, columns=header, dtype="string")
    df[RUN_ID_COLUMN] = run_id_from_path(path)
    df.attrs["run_id"] = run_id_from_path(path)
    df.attrs["source"] = str(path)
    df.attrs["ragged_rows"] = len(rows) - len(good)
    return df


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Convert contract columns to their dtypes (string / Int64 / float64)."""
    out = df.copy()
    for name, kind in contract.column_types().items():
        if name not in out.columns:
            continue
        if kind == "string":
            out[name] = out[name].astype("string")
        elif kind == "integer":
            out[name] = pd.to_numeric(out[name], errors="coerce").astype("Int64")
        else:
            out[name] = pd.to_numeric(out[name], errors="coerce").astype("float64")
    if RUN_ID_COLUMN in out.columns:
        out[RUN_ID_COLUMN] = out[RUN_ID_COLUMN].astype("string")
    return out


def load_run(path: Path | str) -> pd.DataFrame:
    """Load one run with typed columns and a ``run_id`` column (no validation)."""
    return coerce_types(read_raw_run(path))


def load_runs(
    directory: Path | str, pattern: str = "*.csv"
) -> tuple[pd.DataFrame, list[ValidationReport]]:
    """Load and validate every CSV in ``directory``.

    Returns the concatenation of valid runs (typed) and one report per file.
    Invalid runs are excluded from the DataFrame but present in the reports.
    """
    frames: list[pd.DataFrame] = []
    reports: list[ValidationReport] = []
    for path in sorted(Path(directory).glob(pattern)):
        raw = read_raw_run(path)
        report = validate_run(raw)
        reports.append(report)
        if report.is_valid:
            frames.append(coerce_types(raw))

    if frames:
        data = pd.concat(frames, ignore_index=True)
    else:
        data = coerce_types(pd.DataFrame(columns=[*contract.columns(), RUN_ID_COLUMN]))
    return data, reports
