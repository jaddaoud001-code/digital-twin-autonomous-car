# twin-maintenance

Python tooling to **load, validate, summarize and plot** the telemetry runs
recorded by the Unity simulator (`data/raw/telemetry_YYYYMMDD_HHMMSS.csv`, 10 Hz,
one file per run).

The CSV format is defined by the data contract
[`contracts/telemetry/telemetry-sample.v1.schema.json`](../../contracts/telemetry/telemetry-sample.v1.schema.json):
column order, types and outlier bounds are read from it, never hard-coded.

## Installation

Requires Python >= 3.12.

```bash
cd ml/maintenance
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Command-line interface

All commands resolve `data/raw` and `data/processed` from the repository root,
so they work from any directory.

```bash
python -m twin_maintenance validate                 # every CSV in data/raw
python -m twin_maintenance validate path/to/run.csv other_dir/
python -m twin_maintenance validate --step-tolerance 0.01 --min-duration 10 --fall-threshold 2

python -m twin_maintenance summarize                # -> data/processed/run_summary.csv
python -m twin_maintenance summarize --collision-threshold 80 --fall-threshold 2

python -m twin_maintenance plot                     # most recent run
python -m twin_maintenance plot telemetry_20261117_181401
# -> data/processed/figures/<run_id>_timeseries.png
#    data/processed/figures/<run_id>_trajectory.png
```

Global options (before the command): `--raw-dir DIR`, `--processed-dir DIR`.

| Command | Behavior | Exit code |
|---------|----------|-----------|
| `validate [paths...]` | Prints one report per run (errors and warnings) and a total. | `1` if any run has an error, else `0` |
| `summarize` | Validates every run in `--raw-dir`, excludes invalid ones (listed), writes one row per valid run. | `1` if no valid run |
| `plot [run]` | Run id (file stem) or CSV path; default is the most recent file. Refuses invalid runs. | `1` if not found or invalid |

### Validation checks

| Severity | Code | Check |
|----------|------|-------|
| error | `header_mismatch` | header names or order differ from the contract |
| error | `row_width_mismatch` | rows with a different number of values than the header |
| error | `missing_values` | empty / missing values |
| error | `non_numeric` | values that are not numbers (or not integers for `timestamp_ms`) |
| error | `out_of_bounds` | values outside the schema's `minimum` / `maximum` |
| error | `sim_time_not_increasing` | `sim_time_s` not strictly increasing |
| error | `multiple_vehicle_ids` | more than one `vehicle_id` in a run |
| error | `empty_run` | the file has no data row at all (not raised when rows exist but were all dropped: the other errors explain why) |
| warning | `irregular_sampling` | step differs from 0.1 s by more than the tolerance (5 ms) |
| warning | `decreasing_cumulative` | `distance_m`, `runtime_s` or `motor_wear` decreases |
| warning | `battery_increase` | `battery_pct` increases (no charging yet) |
| warning | `timestamp_decrease` | wall-clock `timestamp_ms` decreases |
| warning | `short_run` | run shorter than 5 s |
| warning | `vehicle_fell` | `pos_y` drops below the run's median `pos_y` minus 1.0 m (vehicle left the road); reports the first `sim_time_s` and the minimum `pos_y` |

A run is valid when it has no error; warnings are informative. Thresholds are
configurable: `--step-tolerance`, `--min-duration`, `--fall-threshold`.
`vehicle_fell` is a consistency rule, not a format bound, so it is not part of
the JSON contract.

### Run summary columns

`run_id`, `duration_s`, `distance_m`, `max_speed_mps`, `mean_speed_mps`,
`reverse_share` (effective throttle < 0), `stopped_share` (speed < 0.2 m/s),
`braking_share` (brake > 0), `mean_motor_load`, `max_motor_temp_c`,
`final_motor_temp_c`, `battery_used_pct`, `consumption_pct_per_km` (NaN under
10 m), `wear_added`, `collisions` (distinct events with `accel_mps2` above the
threshold, default 50 m/s²; consecutive samples count once), `fell` (bool, same
rule as the `vehicle_fell` warning).

Shares are fractions of samples. Cumulative values are last-minus-first, so a
run started mid-session is summarized correctly.

## Python API

```python
from twin_maintenance.io import load_run, load_runs
from twin_maintenance.validation import validate_run
from twin_maintenance.features import summarize_run
from twin_maintenance.paths import raw_data_dir

data, reports = load_runs(raw_data_dir())  # valid runs concatenated + all reports
for r in reports:
    print(r.format())
```

## Package layout

```
ml/maintenance/
├── pyproject.toml
├── src/twin_maintenance/
│   ├── __init__.py      # __version__
│   ├── __main__.py      # python -m twin_maintenance
│   ├── cli.py           # argparse commands: validate, summarize, plot
│   ├── paths.py         # repo root (found from __file__), data and contract paths
│   ├── contract.py      # columns, types and bounds read from the JSON Schema
│   ├── io.py            # read_raw_run, load_run, load_runs
│   ├── validation.py    # validate_run -> ValidationReport
│   ├── features.py      # summarize_run, collision_events
│   └── plots.py         # timeseries and trajectory figures (Agg backend)
└── tests/
    ├── conftest.py              # synthetic 30 s run + CSV writer (no real data)
    ├── test_package.py          # version, schema well-formed
    ├── test_validation.py       # one test per check, valid + corrupted
    ├── test_contract_csharp.py  # C# recorder header / value count vs schema
    ├── test_features.py         # summary values, collision counting
    └── test_plots_cli.py        # PNG output, CLI exit codes
```

## Tests and lint

```bash
cd ml/maintenance
.venv/bin/ruff check .
.venv/bin/pytest -q
```

`test_contract_csharp.py` reads
`simulator/DigitalTwinSimulator/Assets/Scripts/Telemetry/TelemetryCsvRecorder.cs`
and fails if the CSV header written in `StartRecording()` or the number of values
written in `WriteSample()` no longer matches the schema. Change the C# recorder and
the contract together (see [`contracts/README.md`](../../contracts/README.md)).
