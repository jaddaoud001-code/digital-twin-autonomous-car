"""Synthetic telemetry fixtures (no real recorded data is used in tests)."""

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from twin_maintenance import contract
from twin_maintenance.io import read_raw_run

DT = 0.1
N_SAMPLES = 301  # 0.0 .. 30.0 s

# Known values of the synthetic run (used by feature tests)
EXPECTED_DURATION_S = 30.0
EXPECTED_DISTANCE_M = 181.0  # 50 (accel) + 100 (cruise) + 25 (braking) + 6 (reverse)
COLLISION_TIMES_S = (12.0, 15.0, 15.1, 15.2)  # two events: 12.0 and 15.0-15.2
EXPECTED_COLLISIONS = 2

# C# number formats of TelemetryCsvRecorder.WriteSample, per column
_DECIMALS = {
    "sim_time_s": 3, "pos_x": 3, "pos_y": 3, "pos_z": 3, "vel_x": 3, "vel_y": 3, "vel_z": 3,
    "speed_mps": 3, "accel_mps2": 3, "steering": 2, "throttle": 2, "brake": 2,
    "motor_load": 3, "battery_pct": 3, "motor_temp_c": 2, "motor_wear": 5,
    "distance_m": 2, "runtime_s": 2,
}  # fmt: skip


def _signed_speed(t: np.ndarray) -> np.ndarray:
    """Forward speed profile: accelerate, cruise, brake, stop, reverse."""
    return np.select(
        [t <= 10, t <= 20, t <= 25, t < 27],
        [t, np.full_like(t, 10.0), 10.0 - 2.0 * (t - 20), np.zeros_like(t)],
        default=-2.0,
    )


def make_valid_run() -> pd.DataFrame:
    """Build a realistic, fully valid 30 s run as a typed DataFrame (contract columns only)."""
    i = np.arange(N_SAMPLES)
    t = np.round(i * DT, 3)
    v = _signed_speed(t)
    speed = np.abs(v)

    # Commands consistent with the speed profile
    throttle = np.select([t <= 10, t <= 20, t <= 25, t < 27], [1.0, 0.5, 0.0, 0.0], default=-1.0)
    brake = np.where((t > 20) & (t <= 25), 1.0, 0.0)
    steering = np.round(0.3 * np.sin(t / 3.0), 2)

    # Straight line along X; startup drop from 0.60 to 0.35 m
    pos_x = np.concatenate([[0.0], np.cumsum(v[1:] * DT)])
    pos_y = np.where(i == 0, 0.60, np.where(i == 1, 0.542, 0.35))
    vel_y = np.where(i == 1, -0.952, 0.0)

    accel = np.abs(np.gradient(v, DT))
    accel[np.isin(t, [5.0])] = 49.0  # just below the default collision threshold
    accel[np.isin(t, [12.0])] = 120.0
    accel[np.isin(t, [15.0, 15.1, 15.2])] = 258.0

    load = np.clip(np.abs(throttle) * (0.4 + 0.6 * np.clip(speed / 15.0, 0, 1)), 0, 1)
    battery = 100.0 - np.cumsum((0.3 + load * 20.0) * DT / 3600.0 / 5.0 * 100.0)
    temp = 20.0 + 30.0 * (1.0 - np.exp(-t / 30.0))
    wear = np.cumsum(load * 0.001 * DT)
    # Trapezoidal integral of |v| gives the exact piecewise-linear distance
    distance = np.concatenate([[0.0], np.cumsum((speed[1:] + speed[:-1]) / 2 * DT)])
    runtime = t + 0.02

    timestamp = 1_794_935_641_683 + i * 100 + np.where(i >= 1, 1000, 0)  # startup jump

    df = pd.DataFrame(
        {
            "vehicle_id": "vehicle-001",
            "timestamp_ms": timestamp.astype("int64"),
            "sim_time_s": t,
            "pos_x": pos_x,
            "pos_y": pos_y,
            "pos_z": 0.0,
            "vel_x": v,
            "vel_y": vel_y,
            "vel_z": 0.0,
            "speed_mps": np.sqrt(speed**2 + vel_y**2),
            "accel_mps2": accel,
            "steering": steering,
            "throttle": throttle,
            "brake": brake,
            "motor_load": load,
            "battery_pct": battery,
            "motor_temp_c": temp,
            "motor_wear": wear,
            "distance_m": distance,
            "runtime_s": runtime,
        }
    )
    return df[contract.columns()]


def write_run_csv(df: pd.DataFrame, path: Path, header: list[str] | None = None) -> Path:
    """Write a run the way the C# recorder does (UTF-8 BOM, fixed decimals)."""
    out = df.copy()
    for col, dec in _DECIMALS.items():
        if col in out.columns and pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].map(lambda x, d=dec: "" if pd.isna(x) else f"{x:.{d}f}")
    lines = [",".join(header if header is not None else map(str, out.columns))]
    lines += [",".join(map(str, row)) for row in out.itertuples(index=False)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return path


@pytest.fixture
def valid_df() -> pd.DataFrame:
    return make_valid_run()


@pytest.fixture
def write_run(tmp_path: Path) -> Callable[..., Path]:
    """Factory: write a DataFrame to ``tmp_path/<name>.csv`` and return the path."""

    def _write(df: pd.DataFrame, name: str = "run", header: list[str] | None = None) -> Path:
        return write_run_csv(df, tmp_path / f"{name}.csv", header)

    return _write


@pytest.fixture
def raw_roundtrip(write_run: Callable[..., Path]) -> Callable[..., pd.DataFrame]:
    """Factory: write a DataFrame to CSV and read it back as raw strings."""

    def _rt(df: pd.DataFrame, name: str = "run", header: list[str] | None = None) -> pd.DataFrame:
        return read_raw_run(write_run(df, name, header))

    return _rt
