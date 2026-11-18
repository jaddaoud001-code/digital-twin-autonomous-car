"""Tests for run summaries."""

import math

import pandas as pd
import pytest
from conftest import (
    EXPECTED_COLLISIONS,
    EXPECTED_DISTANCE_M,
    EXPECTED_DURATION_S,
)

from twin_maintenance.features import collision_events, summarize_run, summarize_runs


@pytest.fixture
def run(valid_df: pd.DataFrame) -> pd.DataFrame:
    return valid_df.assign(run_id="synthetic")


def test_summary_known_values(run: pd.DataFrame) -> None:
    s = summarize_run(run)
    assert s["run_id"] == "synthetic"
    assert s["duration_s"] == pytest.approx(EXPECTED_DURATION_S)
    assert s["distance_m"] == pytest.approx(EXPECTED_DISTANCE_M, abs=0.2)
    assert s["max_speed_mps"] == pytest.approx(10.0)
    assert s["collisions"] == EXPECTED_COLLISIONS
    # Reverse: t >= 27.0 s -> 31 of 301 samples
    assert s["reverse_share"] == pytest.approx(31 / 301)
    # Braking: 20 < t <= 25 -> 50 samples
    assert s["braking_share"] == pytest.approx(50 / 301)
    assert s["max_motor_temp_c"] == pytest.approx(s["final_motor_temp_c"])
    assert s["battery_used_pct"] > 0
    assert s["consumption_pct_per_km"] == pytest.approx(
        s["battery_used_pct"] / (s["distance_m"] / 1000)
    )
    assert s["wear_added"] > 0
    assert s["fell"] is False


def test_summary_fell(run: pd.DataFrame) -> None:
    fallen = run.copy()
    fallen.loc[fallen["sim_time_s"] >= 28.0, "pos_y"] = -5.0
    assert summarize_run(fallen)["fell"] is True
    assert summarize_run(fallen, fall_threshold_m=10.0)["fell"] is False


def test_consecutive_samples_count_as_one_collision(run: pd.DataFrame) -> None:
    starts = collision_events(run)
    assert run.loc[starts, "sim_time_s"].round(1).tolist() == [12.0, 15.0]


def test_collision_threshold_is_configurable(run: pd.DataFrame) -> None:
    assert summarize_run(run, collision_threshold=40.0)["collisions"] == 3  # adds the 49 spike
    assert summarize_run(run, collision_threshold=200.0)["collisions"] == 1
    assert summarize_run(run, collision_threshold=1000.0)["collisions"] == 0


def test_consumption_nan_below_10m(run: pd.DataFrame) -> None:
    s = summarize_run(run.iloc[:40])  # first 3.9 s: ~7.6 m
    assert s["distance_m"] < 10
    assert math.isnan(s["consumption_pct_per_km"])


def test_cumulative_values_use_differences(run: pd.DataFrame) -> None:
    # A run recorded mid-session starts with non-zero counters
    s = summarize_run(run.iloc[100:])
    assert s["distance_m"] == pytest.approx(
        run["distance_m"].iloc[-1] - run["distance_m"].iloc[100]
    )


def test_summarize_runs_one_row_per_run(run: pd.DataFrame) -> None:
    data = pd.concat([run, run.assign(run_id="other")], ignore_index=True)
    table = summarize_runs(data)
    assert table["run_id"].tolist() == ["other", "synthetic"]


def test_empty_run_raises(run: pd.DataFrame) -> None:
    with pytest.raises(ValueError):
        summarize_run(run.iloc[0:0])
