"""One test per validation check: a valid case and a corrupted variant."""

from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest

from twin_maintenance import contract
from twin_maintenance.io import load_run, load_runs, read_raw_run
from twin_maintenance.validation import validate_run

RawRoundtrip = Callable[..., pd.DataFrame]


def test_valid_run_has_no_issues(valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip) -> None:
    report = validate_run(raw_roundtrip(valid_df))
    assert report.issues == [], report.format()
    assert report.is_valid
    assert report.n_rows == 301


def test_typed_dataframe_is_also_accepted(valid_df: pd.DataFrame) -> None:
    assert validate_run(valid_df, run_id="typed").issues == []


# --- Errors -------------------------------------------------------------------------------


def test_header_wrong_order(valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip) -> None:
    cols = contract.columns()
    swapped = cols.copy()
    swapped[0], swapped[1] = swapped[1], swapped[0]
    report = validate_run(raw_roundtrip(valid_df[swapped]))
    assert "header_mismatch" in report.codes("error")
    assert "wrong order" in report.errors[0].message


def test_header_missing_and_renamed_columns(
    valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip
) -> None:
    report = validate_run(raw_roundtrip(valid_df.drop(columns=["runtime_s"])))
    assert "header_mismatch" in report.codes("error")

    renamed = valid_df.rename(columns={"brake": "brake_cmd"})
    report = validate_run(raw_roundtrip(renamed))
    assert "header_mismatch" in report.codes("error")
    assert "brake_cmd" in report.errors[0].message


def test_header_missing_comma_shifts_nothing(
    valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip
) -> None:
    # Reproduces a 19-name header over 20-value rows ("brakemotor_load")
    header = contract.columns()
    i = header.index("brake")
    header = header[:i] + ["brakemotor_load"] + header[i + 2 :]
    report = validate_run(raw_roundtrip(valid_df, header=header))
    assert {"header_mismatch", "row_width_mismatch"} <= report.codes("error")
    assert not report.is_valid


def test_missing_values(valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip) -> None:
    df = valid_df.copy()
    df.loc[[10, 11, 12], "motor_temp_c"] = float("nan")
    report = validate_run(raw_roundtrip(df))
    issue = next(i for i in report.errors if i.code == "missing_values")
    assert issue.rows == 3


def test_non_numeric_values(valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip) -> None:
    df = valid_df.astype({"speed_mps": "object", "timestamp_ms": "object"})
    df.loc[5, "speed_mps"] = "fast"
    df.loc[6, "timestamp_ms"] = "1794935641683.5"  # not an integer
    report = validate_run(raw_roundtrip(df))
    bad = [i for i in report.errors if i.code == "non_numeric"]
    assert {i.message.split("'")[1] for i in bad} == {"speed_mps", "timestamp_ms"}


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("speed_mps", 25.0),
        ("accel_mps2", -1.0),
        ("throttle", 1.5),
        ("brake", -0.1),
        ("battery_pct", 100.5),
        ("motor_temp_c", 250.0),
        ("motor_wear", 1.2),
        ("distance_m", -3.0),
    ],
)
def test_out_of_bounds(
    valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip, column: str, value: float
) -> None:
    df = valid_df.copy()
    df.loc[0, column] = value
    report = validate_run(raw_roundtrip(df))
    issue = next(i for i in report.errors if i.code == "out_of_bounds")
    assert column in issue.message and issue.rows == 1


def test_bounds_come_from_schema() -> None:
    b = contract.bounds()
    assert b["speed_mps"] == (0, 20)
    assert b["motor_temp_c"] == (-40, 200)
    assert b["accel_mps2"] == (0, None)
    assert "pos_x" not in b


def test_sim_time_not_strictly_increasing(
    valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip
) -> None:
    df = valid_df.copy()
    df.loc[100, "sim_time_s"] = df.loc[99, "sim_time_s"]  # duplicate
    report = validate_run(raw_roundtrip(df))
    assert "sim_time_not_increasing" in report.codes("error")


def test_multiple_vehicle_ids(valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip) -> None:
    df = valid_df.copy()
    df.loc[200:, "vehicle_id"] = "vehicle-002"
    report = validate_run(raw_roundtrip(df))
    assert "multiple_vehicle_ids" in report.codes("error")


def test_empty_run(valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip) -> None:
    report = validate_run(raw_roundtrip(valid_df.iloc[0:0]))
    assert report.codes("error") == {"empty_run"}
    assert report.n_rows == 0


def test_all_rows_dropped_is_not_empty_run(
    valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip
) -> None:
    # Header with one column too few: every data row is dropped, but the file is not empty
    report = validate_run(raw_roundtrip(valid_df, header=contract.columns()[:-1]))
    assert report.n_rows == 0
    assert report.codes("error") == {"header_mismatch", "row_width_mismatch"}
    assert next(i for i in report.errors if i.code == "row_width_mismatch").rows == 301


# --- Warnings -----------------------------------------------------------------------------


def test_irregular_sampling(valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip) -> None:
    df = valid_df.copy()
    df.loc[1:, "sim_time_s"] += 0.02  # first step is 0.120 s, as seen at startup
    report = validate_run(raw_roundtrip(df))
    assert report.is_valid
    issue = next(i for i in report.warnings if i.code == "irregular_sampling")
    assert issue.rows == 1


def test_sampling_tolerance_is_configurable(
    valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip
) -> None:
    df = valid_df.copy()
    df.loc[1:, "sim_time_s"] += 0.004  # within default 5 ms tolerance
    raw = raw_roundtrip(df)
    assert "irregular_sampling" not in validate_run(raw).codes()
    assert "irregular_sampling" in validate_run(raw, step_tolerance_s=0.001).codes()


@pytest.mark.parametrize("column", ["distance_m", "runtime_s", "motor_wear"])
def test_cumulative_decreasing(
    valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip, column: str
) -> None:
    df = valid_df.copy()
    df.loc[150, column] = df.loc[149, column] - 0.01 if column != "motor_wear" else 0.0
    report = validate_run(raw_roundtrip(df))
    assert report.is_valid
    issue = next(i for i in report.warnings if i.code == "decreasing_cumulative")
    assert column in issue.message


def test_battery_increase(valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip) -> None:
    df = valid_df.copy()
    df.loc[150, "battery_pct"] = 100.0
    report = validate_run(raw_roundtrip(df))
    assert report.is_valid
    assert "battery_increase" in report.codes("warning")


def test_timestamp_decrease(valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip) -> None:
    df = valid_df.copy()
    df.loc[50, "timestamp_ms"] = df.loc[49, "timestamp_ms"] - 500
    report = validate_run(raw_roundtrip(df))
    assert report.is_valid
    assert "timestamp_decrease" in report.codes("warning")


def make_fall(df: pd.DataFrame, start_s: float = 25.0) -> pd.DataFrame:
    """Free fall from the road height after ``start_s`` (vehicle drove off the edge)."""
    out = df.copy()
    t = out["sim_time_s"]
    after = t >= start_s
    out.loc[after, "pos_y"] = 0.35 - 0.5 * 9.81 * (t[after] - start_s) ** 2
    return out


def test_startup_drop_is_not_a_fall(valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip) -> None:
    # The valid run already drops 0.60 -> 0.35 m at startup
    assert "vehicle_fell" not in validate_run(raw_roundtrip(valid_df)).codes()


def test_vehicle_fell(valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip) -> None:
    report = validate_run(raw_roundtrip(make_fall(valid_df)))
    assert report.is_valid
    issue = next(i for i in report.warnings if i.code == "vehicle_fell")
    # Below median (0.35) - 1.0 m once 4.905 * dt^2 > 1.0, i.e. dt > 0.45 s -> t = 25.5 s
    assert "sim_time_s=25.500" in issue.message
    assert "min pos_y=-122.275" in issue.message
    assert issue.rows == 46  # 25.5 .. 30.0 s


def test_fall_threshold_is_configurable(
    valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip
) -> None:
    raw = raw_roundtrip(make_fall(valid_df))
    report = validate_run(raw, fall_threshold_m=200.0)
    assert "vehicle_fell" not in report.codes()
    report = validate_run(raw, fall_threshold_m=0.1)
    assert (
        "sim_time_s=25.200" in next(i for i in report.warnings if i.code == "vehicle_fell").message
    )


def test_short_run(valid_df: pd.DataFrame, raw_roundtrip: RawRoundtrip) -> None:
    raw = raw_roundtrip(valid_df.iloc[:40])  # 3.9 s
    report = validate_run(raw)
    assert report.is_valid
    assert report.codes("warning") == {"short_run"}
    assert "short_run" not in validate_run(raw, min_duration_s=3).codes()


# --- Loading ------------------------------------------------------------------------------


def test_load_run_dtypes_and_run_id(valid_df: pd.DataFrame, write_run: Callable[..., Path]) -> None:
    df = load_run(write_run(valid_df, name="telemetry_20260101_120000"))
    assert list(df.columns) == [*contract.columns(), "run_id"]
    assert (df["run_id"] == "telemetry_20260101_120000").all()
    assert df["vehicle_id"].dtype == "string"
    assert df["timestamp_ms"].dtype == "Int64"
    assert df["speed_mps"].dtype == "float64"
    assert df["sim_time_s"].iloc[-1] == pytest.approx(30.0)


def test_read_raw_run_strips_bom(valid_df: pd.DataFrame, write_run: Callable[..., Path]) -> None:
    raw = read_raw_run(write_run(valid_df))
    assert raw.columns[0] == "vehicle_id"


def test_load_runs_excludes_invalid(valid_df: pd.DataFrame, write_run: Callable[..., Path]) -> None:
    write_run(valid_df, name="a_good")
    write_run(valid_df.drop(columns=["runtime_s"]), name="b_bad")
    path = write_run(valid_df, name="c_good")
    data, reports = load_runs(path.parent)
    assert [r.run_id for r in reports] == ["a_good", "b_bad", "c_good"]
    assert [r.is_valid for r in reports] == [True, False, True]
    assert sorted(data["run_id"].unique()) == ["a_good", "c_good"]
    assert len(data) == 2 * len(valid_df)


def test_load_runs_empty_directory(tmp_path: Path) -> None:
    data, reports = load_runs(tmp_path)
    assert reports == [] and data.empty
    assert list(data.columns) == [*contract.columns(), "run_id"]
