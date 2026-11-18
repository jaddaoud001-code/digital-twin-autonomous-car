"""Validation of a single telemetry run against the contract and known simulator behavior."""

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import pandas as pd

from twin_maintenance import contract

Severity = Literal["error", "warning"]

EXPECTED_STEP_S = 0.1
DEFAULT_STEP_TOLERANCE_S = 0.005
DEFAULT_MIN_DURATION_S = 5.0
DEFAULT_FALL_THRESHOLD_M = 1.0

# Cumulative quantities that the simulator never decreases
NON_DECREASING = ("distance_m", "runtime_s", "motor_wear")


@dataclass(frozen=True)
class Issue:
    """One validation finding."""

    severity: Severity
    code: str
    message: str
    rows: int = 0  # number of rows (or row transitions) concerned


@dataclass
class ValidationReport:
    """Result of validating one run."""

    run_id: str
    n_rows: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def is_valid(self) -> bool:
        """True when there is no error (warnings are allowed)."""
        return not self.errors

    def codes(self, severity: Severity | None = None) -> set[str]:
        """Set of issue codes, optionally filtered by severity."""
        return {i.code for i in self.issues if severity is None or i.severity == severity}

    def add(self, severity: Severity, code: str, message: str, rows: int = 0) -> None:
        self.issues.append(Issue(severity, code, message, rows))

    def format(self) -> str:
        """Human-readable multi-line report."""
        status = "OK" if self.is_valid else "INVALID"
        head = (
            f"[{status}] {self.run_id}  ({self.n_rows} rows, "
            f"{len(self.errors)} error(s), {len(self.warnings)} warning(s))"
        )
        lines = [head]
        for i in self.issues:
            rows = f" [{i.rows} row(s)]" if i.rows else ""
            lines.append(f"    {i.severity.upper():7} {i.code}: {i.message}{rows}")
        return "\n".join(lines)


def fall_mask(pos_y: pd.Series, threshold_m: float = DEFAULT_FALL_THRESHOLD_M) -> pd.Series:
    """True where the vehicle is below the run's median height minus ``threshold_m``.

    The median is the road height for a run spent mostly on the road.
    """
    y = pd.to_numeric(pos_y, errors="coerce").astype("float64")
    return y < y.median() - threshold_m


def _missing_mask(s: pd.Series) -> pd.Series:
    """Missing = NA or empty/whitespace string."""
    if pd.api.types.is_numeric_dtype(s):
        return s.isna()
    return s.isna() | (s.astype("string").str.strip() == "")


def _to_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype("float64")


def _check_header(df: pd.DataFrame, expected: list[str], report: ValidationReport) -> None:
    actual = [c for c in df.columns if c != "run_id"]
    if actual == expected:
        return
    missing = [c for c in expected if c not in actual]
    unexpected = [c for c in actual if c not in expected]
    parts = []
    if missing:
        parts.append(f"missing {missing}")
    if unexpected:
        parts.append(f"unexpected {unexpected}")
    if not parts:
        parts.append("same names, wrong order")
    report.add(
        "error",
        "header_mismatch",
        f"header differs from contract ({len(actual)} vs {len(expected)} columns): "
        + "; ".join(parts),
    )


def validate_run(
    df: pd.DataFrame,
    run_id: str | None = None,
    step_tolerance_s: float = DEFAULT_STEP_TOLERANCE_S,
    min_duration_s: float = DEFAULT_MIN_DURATION_S,
    fall_threshold_m: float = DEFAULT_FALL_THRESHOLD_M,
) -> ValidationReport:
    """Validate one run (raw string or typed DataFrame) and return a report.

    Value checks run on every contract column present, even when the header is wrong,
    so that a single report lists as many problems as possible.
    """
    if run_id is None:
        run_id = df.attrs.get("run_id")
    if run_id is None and "run_id" in df.columns and len(df):
        run_id = str(df["run_id"].iloc[0])
    report = ValidationReport(run_id=run_id or "<unknown>", n_rows=len(df))

    expected = contract.columns()
    types = contract.column_types()
    _check_header(df, expected, report)

    ragged = int(df.attrs.get("ragged_rows", 0))
    if ragged:
        report.add(
            "error",
            "row_width_mismatch",
            "rows whose number of values differs from the header were dropped",
            ragged,
        )

    if len(df) == 0:
        # Only a truly empty file is "empty"; dropped rows are already reported above
        if ragged == 0:
            report.add("error", "empty_run", "file contains no data rows")
        return report

    # Duplicate column names make per-column checks ambiguous
    if df.columns.duplicated().any():
        return report

    present = [c for c in expected if c in df.columns]

    # --- Missing and non-numeric values -----------------------------------------------
    numeric: dict[str, pd.Series] = {}
    for col in present:
        missing = _missing_mask(df[col])
        n_missing = int(missing.sum())
        if n_missing:
            report.add("error", "missing_values", f"'{col}' has missing values", n_missing)
        if types[col] == "string":
            continue
        values = _to_numeric(df[col])
        bad = values.isna() & ~missing
        if types[col] == "integer":
            bad |= values.notna() & (values != np.floor(values))
        n_bad = int(bad.sum())
        if n_bad:
            report.add(
                "error",
                "non_numeric",
                f"'{col}' has values that are not valid {types[col]}s",
                n_bad,
            )
        numeric[col] = values

    # --- Schema bounds ------------------------------------------------------------------
    for col, (lo, hi) in contract.bounds().items():
        if col not in numeric:
            continue
        v = numeric[col]
        out = pd.Series(False, index=v.index)
        if lo is not None:
            out |= v < lo
        if hi is not None:
            out |= v > hi
        n_out = int(out.sum())
        if n_out:
            rng = f"[{'-inf' if lo is None else lo}, {'+inf' if hi is None else hi}]"
            report.add(
                "error",
                "out_of_bounds",
                f"'{col}' outside {rng} (observed {v.min():g} .. {v.max():g})",
                n_out,
            )

    # --- Single vehicle per run -----------------------------------------------------------
    if "vehicle_id" in df.columns:
        ids = df["vehicle_id"][~_missing_mask(df["vehicle_id"])].unique()
        if len(ids) > 1:
            report.add(
                "error",
                "multiple_vehicle_ids",
                f"{len(ids)} vehicle ids in one run: {sorted(map(str, ids))}",
            )

    # --- Time axis ----------------------------------------------------------------------
    if "sim_time_s" in numeric:
        t = numeric["sim_time_s"]
        dt = t.diff().iloc[1:]
        n_back = int((dt <= 0).sum())
        if n_back:
            report.add(
                "error",
                "sim_time_not_increasing",
                "sim_time_s is not strictly increasing",
                n_back,
            )
        off = (dt - EXPECTED_STEP_S).abs() > step_tolerance_s + 1e-9
        n_off = int(off.sum())
        if n_off:
            report.add(
                "warning",
                "irregular_sampling",
                f"step differs from {EXPECTED_STEP_S} s by more than {step_tolerance_s} s "
                f"(observed {dt.min():.3f} .. {dt.max():.3f} s)",
                n_off,
            )
        duration = float(t.max() - t.min()) if t.notna().any() else 0.0
        if duration < min_duration_s:
            report.add(
                "warning",
                "short_run",
                f"run lasts {duration:.1f} s (< {min_duration_s} s)",
            )

    # --- Vehicle left the road (consistency rule, not a contract bound) -------------------
    if "pos_y" in numeric:
        fell = fall_mask(numeric["pos_y"], fall_threshold_m)
        n_fell = int(fell.sum())
        if n_fell:
            where = ""
            if "sim_time_s" in numeric:
                where = f"first at sim_time_s={numeric['sim_time_s'][fell].iloc[0]:.3f}, "
            report.add(
                "warning",
                "vehicle_fell",
                f"pos_y below run median - {fall_threshold_m} m ({where}"
                f"min pos_y={numeric['pos_y'].min():.3f} m)",
                n_fell,
            )

    # --- Monotonic quantities -------------------------------------------------------------
    for col in NON_DECREASING:
        if col in numeric:
            n = int((numeric[col].diff() < 0).sum())
            if n:
                report.add("warning", "decreasing_cumulative", f"'{col}' decreases", n)
    if "battery_pct" in numeric:
        n = int((numeric["battery_pct"].diff() > 0).sum())
        if n:
            report.add("warning", "battery_increase", "'battery_pct' increases", n)
    if "timestamp_ms" in numeric:
        n = int((numeric["timestamp_ms"].diff() < 0).sum())
        if n:
            report.add("warning", "timestamp_decrease", "'timestamp_ms' decreases", n)

    return report
