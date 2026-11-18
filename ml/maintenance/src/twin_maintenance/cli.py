"""Command-line interface: ``python -m twin_maintenance <validate|summarize|plot>``."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from twin_maintenance import __version__, paths
from twin_maintenance.features import DEFAULT_COLLISION_THRESHOLD_MPS2, summarize_runs
from twin_maintenance.io import coerce_types, load_runs, read_raw_run
from twin_maintenance.plots import plot_run_timeseries, plot_run_trajectory
from twin_maintenance.validation import (
    DEFAULT_FALL_THRESHOLD_M,
    DEFAULT_MIN_DURATION_S,
    DEFAULT_STEP_TOLERANCE_S,
    ValidationReport,
    validate_run,
)


def _csv_files(targets: Sequence[Path]) -> list[Path]:
    """Expand files and directories into a sorted list of CSV files."""
    files: list[Path] = []
    for target in targets:
        if target.is_dir():
            files.extend(sorted(target.glob("*.csv")))
        else:
            files.append(target)
    return files


def _cmd_validate(args: argparse.Namespace) -> int:
    files = _csv_files(args.paths or [args.raw_dir])
    if not files:
        print("No CSV file found.")
        return 0
    reports: list[ValidationReport] = []
    for path in files:
        if not path.is_file():
            report = ValidationReport(run_id=path.stem)
            report.add("error", "file_not_found", f"no such file: {path}")
        else:
            report = validate_run(
                read_raw_run(path),
                step_tolerance_s=args.step_tolerance,
                min_duration_s=args.min_duration,
                fall_threshold_m=args.fall_threshold,
            )
        reports.append(report)
        print(report.format())

    n_bad = sum(not r.is_valid for r in reports)
    n_warn = sum(bool(r.warnings) for r in reports)
    print(
        f"\n{len(reports)} run(s): {len(reports) - n_bad} valid, {n_bad} invalid, "
        f"{n_warn} with warnings"
    )
    return 1 if n_bad else 0


def _cmd_summarize(args: argparse.Namespace) -> int:
    data, reports = load_runs(args.raw_dir)
    excluded = [r.run_id for r in reports if not r.is_valid]
    if excluded:
        print(f"Excluded {len(excluded)} invalid run(s): {', '.join(excluded)}")
    if data.empty:
        print("No valid run to summarize.")
        return 1

    summary = summarize_runs(data, args.collision_threshold, args.fall_threshold)
    out = args.processed_dir / "run_summary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out, index=False, float_format="%.4f")

    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(summary.set_index("run_id").T.to_string(float_format=lambda x: f"{x:.3f}"))
    print(f"\nWritten: {out}")
    return 0


def _resolve_run(run: str | None, raw_dir: Path) -> Path | None:
    """Return the CSV for a run id / path, or the most recent run in ``raw_dir``."""
    if run is None:
        files = sorted(raw_dir.glob("*.csv"))  # names embed a sortable timestamp
        return files[-1] if files else None
    candidate = Path(run)
    if candidate.is_file():
        return candidate
    candidate = raw_dir / f"{Path(run).stem}.csv"
    return candidate if candidate.is_file() else None


def _cmd_plot(args: argparse.Namespace) -> int:
    path = _resolve_run(args.run, args.raw_dir)
    if path is None:
        print(f"Run not found: {args.run or '(no CSV in ' + str(args.raw_dir) + ')'}")
        return 1
    raw = read_raw_run(path)
    report = validate_run(raw)
    if not report.is_valid:
        print(report.format())
        print("Cannot plot an invalid run.")
        return 1

    df = coerce_types(raw)
    out_dir = args.processed_dir / "figures"
    outputs = [
        (plot_run_timeseries, out_dir / f"{report.run_id}_timeseries.png"),
        (plot_run_trajectory, out_dir / f"{report.run_id}_trajectory.png"),
    ]
    for plot, out in outputs:
        plt.close(plot(df, out))
        print(f"Written: {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Argument parser for all subcommands."""
    parser = argparse.ArgumentParser(
        prog="python -m twin_maintenance",
        description="Validate, summarize and plot simulator telemetry runs.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--raw-dir", type=Path, default=paths.raw_data_dir(), help="input CSV directory"
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=paths.processed_data_dir(),
        help="output directory for summaries and figures",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="validate CSV runs (default: every CSV in --raw-dir)")
    p.add_argument("paths", nargs="*", type=Path, help="CSV files or directories")
    p.add_argument("--step-tolerance", type=float, default=DEFAULT_STEP_TOLERANCE_S)
    p.add_argument("--min-duration", type=float, default=DEFAULT_MIN_DURATION_S)
    p.add_argument("--fall-threshold", type=float, default=DEFAULT_FALL_THRESHOLD_M)
    p.set_defaults(func=_cmd_validate)

    p = sub.add_parser("summarize", help="write run_summary.csv for every valid run")
    p.add_argument("--collision-threshold", type=float, default=DEFAULT_COLLISION_THRESHOLD_MPS2)
    p.add_argument("--fall-threshold", type=float, default=DEFAULT_FALL_THRESHOLD_M)
    p.set_defaults(func=_cmd_summarize)

    p = sub.add_parser("plot", help="write PNG figures for one run (default: most recent)")
    p.add_argument("run", nargs="?", help="run id (file stem) or CSV path")
    p.set_defaults(func=_cmd_plot)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point; returns the process exit code."""
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
