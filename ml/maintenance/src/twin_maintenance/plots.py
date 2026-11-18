"""Run visualizations (headless, matplotlib Agg backend)."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from twin_maintenance.features import (  # noqa: E402
    DEFAULT_COLLISION_THRESHOLD_MPS2,
    collision_events,
)

# Categorical slots 1-3 of the reference palette (validated colorblind-safe as a set)
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SURFACE = "#fcfcfb"
# Single-hue sequential ramp; the palest steps are dropped so slow points stay visible
SPEED_CMAP = ListedColormap(plt.get_cmap("Blues")(np.linspace(0.3, 1.0, 256)))


def _style(ax: plt.Axes) -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.tick_params(colors=MUTED, labelsize=8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)


def _title(df: pd.DataFrame, suffix: str) -> str:
    run_id = str(df["run_id"].iloc[0]) if "run_id" in df.columns and len(df) else "run"
    return f"{run_id} - {suffix}"


def _save(fig: Figure, out_path: Path | str | None) -> None:
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=120, facecolor=SURFACE)


def plot_run_timeseries(
    df: pd.DataFrame,
    out_path: Path | str | None = None,
    collision_threshold: float = DEFAULT_COLLISION_THRESHOLD_MPS2,
) -> Figure:
    """Multi-panel time series sharing ``sim_time_s``; collisions as vertical lines."""
    t = df["sim_time_s"]
    panels = 6
    fig, axes = plt.subplots(panels, 1, sharex=True, figsize=(11, 13), facecolor=SURFACE)

    axes[0].plot(t, df["speed_mps"] * 3.6, color=BLUE, linewidth=2)
    axes[0].set_ylabel("speed (km/h)")

    for col, color in (("throttle", BLUE), ("brake", ORANGE), ("steering", AQUA)):
        axes[1].plot(t, df[col], color=color, linewidth=1.5, label=col)
    axes[1].set_ylabel("command")
    axes[1].set_ylim(-1.1, 1.1)
    axes[1].legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), fontsize=8, frameon=False, ncols=3)

    single = (
        ("motor_load", "motor load (0-1)"),
        ("motor_temp_c", "motor temp (°C)"),
        ("battery_pct", "battery (%)"),
        ("motor_wear", "motor wear (0-1)"),
    )
    for ax, (col, label) in zip(axes[2:], single, strict=True):
        ax.plot(t, df[col], color=BLUE, linewidth=2)
        ax.set_ylabel(label)

    hits = t[collision_events(df, collision_threshold)]
    for ax in axes:
        _style(ax)
        ax.yaxis.label.set_color(INK)
        ax.yaxis.label.set_fontsize(9)
        for x in hits:
            ax.axvline(x, color=MUTED, linestyle="--", linewidth=1)
    for x in hits:
        axes[0].annotate(
            "collision",
            (x, 1.0),
            xycoords=("data", "axes fraction"),
            xytext=(3, -10),
            textcoords="offset points",
            fontsize=8,
            color=MUTED,
        )

    axes[-1].set_xlabel("sim time (s)", color=INK)
    fig.suptitle(_title(df, "telemetry"), color=INK, fontsize=12)
    fig.tight_layout()
    _save(fig, out_path)
    return fig


def plot_run_trajectory(
    df: pd.DataFrame,
    out_path: Path | str | None = None,
) -> Figure:
    """Top-down trajectory (pos_x, pos_z), equal axes, colored by speed."""
    fig, ax = plt.subplots(figsize=(8, 8), facecolor=SURFACE)
    _style(ax)
    ax.plot(df["pos_x"], df["pos_z"], color=GRID, linewidth=1, zorder=1)
    points = ax.scatter(
        df["pos_x"],
        df["pos_z"],
        c=df["speed_mps"] * 3.6,
        cmap=SPEED_CMAP,
        vmin=0,
        s=12,
        zorder=2,
    )
    cbar = fig.colorbar(points, ax=ax, shrink=0.8)
    cbar.set_label("speed (km/h)", color=INK)
    cbar.ax.tick_params(colors=MUTED, labelsize=8)

    start, end = df.iloc[0], df.iloc[-1]
    ax.scatter(start["pos_x"], start["pos_z"], marker="o", s=90, facecolor=SURFACE,
               edgecolor=INK, linewidth=2, zorder=3, label="start")  # fmt: skip
    ax.scatter(end["pos_x"], end["pos_z"], marker="s", s=90, facecolor=INK,
               edgecolor=SURFACE, linewidth=2, zorder=3, label="end")  # fmt: skip
    ax.legend(loc="best", fontsize=9, frameon=False)

    ax.set_aspect("equal", adjustable="datalim")
    ax.set_xlabel("x (m)", color=INK)
    ax.set_ylabel("z (m)", color=INK)
    ax.set_title(_title(df, "trajectory (top view)"), color=INK)
    fig.tight_layout()
    _save(fig, out_path)
    return fig
