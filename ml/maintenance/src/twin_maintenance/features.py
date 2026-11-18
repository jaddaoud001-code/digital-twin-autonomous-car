"""Per-run summary features."""

from typing import Any

import numpy as np
import pandas as pd

from twin_maintenance.validation import DEFAULT_FALL_THRESHOLD_M, fall_mask

DEFAULT_COLLISION_THRESHOLD_MPS2 = 50.0
STOP_SPEED_MPS = 0.2
MIN_DISTANCE_FOR_CONSUMPTION_M = 10.0


def collision_events(
    df: pd.DataFrame, threshold: float = DEFAULT_COLLISION_THRESHOLD_MPS2
) -> pd.Series:
    """Boolean mask marking the first sample of each collision event.

    A collision is a run of consecutive samples with ``accel_mps2 > threshold``;
    each run counts once.
    """
    above = (df["accel_mps2"] > threshold).to_numpy()
    starts = above & ~np.concatenate([[False], above[:-1]])
    return pd.Series(starts, index=df.index)


def summarize_run(
    df: pd.DataFrame,
    collision_threshold: float = DEFAULT_COLLISION_THRESHOLD_MPS2,
    fall_threshold_m: float = DEFAULT_FALL_THRESHOLD_M,
) -> dict[str, Any]:
    """Summarize one valid run (typed DataFrame, sorted by ``sim_time_s``).

    Time shares are fractions of samples (samples are evenly spaced at 10 Hz).
    "Reverse" means the effective throttle is negative: the controller only lets a
    negative throttle through when the vehicle is not moving forward.
    Cumulative quantities (distance, battery, wear) are differences between the last
    and first sample, so runs started mid-session are handled correctly.
    """
    if df.empty:
        raise ValueError("cannot summarize an empty run")
    df = df.sort_values("sim_time_s")
    first, last = df.iloc[0], df.iloc[-1]

    distance = float(last["distance_m"] - first["distance_m"])
    battery_used = float(first["battery_pct"] - last["battery_pct"])
    consumption = (
        battery_used / (distance / 1000.0)
        if distance >= MIN_DISTANCE_FOR_CONSUMPTION_M
        else float("nan")
    )

    return {
        "run_id": str(first["run_id"]) if "run_id" in df.columns else None,
        "duration_s": float(last["sim_time_s"] - first["sim_time_s"]),
        "distance_m": distance,
        "max_speed_mps": float(df["speed_mps"].max()),
        "mean_speed_mps": float(df["speed_mps"].mean()),
        "reverse_share": float((df["throttle"] < 0).mean()),
        "stopped_share": float((df["speed_mps"] < STOP_SPEED_MPS).mean()),
        "braking_share": float((df["brake"] > 0).mean()),
        "mean_motor_load": float(df["motor_load"].mean()),
        "max_motor_temp_c": float(df["motor_temp_c"].max()),
        "final_motor_temp_c": float(last["motor_temp_c"]),
        "battery_used_pct": battery_used,
        "consumption_pct_per_km": consumption,
        "wear_added": float(last["motor_wear"] - first["motor_wear"]),
        "collisions": int(collision_events(df, collision_threshold).sum()),
        "fell": bool(fall_mask(df["pos_y"], fall_threshold_m).any()),
    }


def summarize_runs(
    data: pd.DataFrame,
    collision_threshold: float = DEFAULT_COLLISION_THRESHOLD_MPS2,
    fall_threshold_m: float = DEFAULT_FALL_THRESHOLD_M,
) -> pd.DataFrame:
    """One summary row per ``run_id`` in a concatenated DataFrame."""
    rows = [
        summarize_run(group, collision_threshold, fall_threshold_m)
        for _, group in data.groupby("run_id", sort=True)
    ]
    return pd.DataFrame(rows)
