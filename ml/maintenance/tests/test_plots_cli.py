"""Tests for plots and the command-line interface (all outputs go to tmp_path)."""

from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest

from twin_maintenance.cli import main
from twin_maintenance.plots import plot_run_timeseries, plot_run_trajectory


@pytest.mark.parametrize("plot", [plot_run_timeseries, plot_run_trajectory])
def test_plot_writes_non_empty_png(
    plot: Callable[..., object], valid_df: pd.DataFrame, tmp_path: Path
) -> None:
    out = tmp_path / "fig" / "out.png"
    plot(valid_df.assign(run_id="synthetic"), out)
    assert out.is_file() and out.stat().st_size > 1000
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    raw, processed = tmp_path / "raw", tmp_path / "processed"
    raw.mkdir()
    return raw, processed


def _cli(dirs: tuple[Path, Path], *args: str) -> int:
    raw, processed = dirs
    return main(["--raw-dir", str(raw), "--processed-dir", str(processed), *args])


def test_validate_returns_0_on_valid_data(
    dirs: tuple[Path, Path], valid_df: pd.DataFrame, write_run: Callable[..., Path]
) -> None:
    write_run(valid_df, name="raw/telemetry_20260101_000000")
    assert _cli(dirs, "validate") == 0


def test_validate_returns_1_on_invalid_data(
    dirs: tuple[Path, Path],
    valid_df: pd.DataFrame,
    write_run: Callable[..., Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_run(valid_df, name="raw/telemetry_20260101_000000")
    bad = write_run(valid_df.drop(columns=["brake"]), name="raw/telemetry_20260101_000100")
    assert _cli(dirs, "validate") == 1
    assert "header_mismatch" in capsys.readouterr().out
    # Explicit path arguments
    assert _cli(dirs, "validate", str(bad)) == 1
    assert _cli(dirs, "validate", str(dirs[0] / "missing.csv")) == 1


def test_summarize_and_plot(
    dirs: tuple[Path, Path], valid_df: pd.DataFrame, write_run: Callable[..., Path]
) -> None:
    write_run(valid_df, name="raw/telemetry_20260101_000000")
    write_run(valid_df.drop(columns=["brake"]), name="raw/telemetry_20260101_000100")
    raw, processed = dirs

    assert _cli(dirs, "summarize") == 0
    summary = pd.read_csv(processed / "run_summary.csv")
    assert summary["run_id"].tolist() == ["telemetry_20260101_000000"]

    # Default run is the most recent file, which is invalid here
    assert _cli(dirs, "plot") == 1
    assert _cli(dirs, "plot", "telemetry_20260101_000000") == 0
    figures = sorted(p.name for p in (processed / "figures").iterdir())
    assert figures == [
        "telemetry_20260101_000000_timeseries.png",
        "telemetry_20260101_000000_trajectory.png",
    ]
