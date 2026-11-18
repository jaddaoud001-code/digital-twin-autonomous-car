# Data Flows

## Vehicle control

A control source produces a VehicleControlCommand.

VehicleControlCommand:
- throttle: [-1, 1]
  - -1 = full reverse
  - 0 = no throttle
  - +1 = full forward
- steering: [-1, 1]
- brake: [0, 1]

Current source:
- ManualInputSource (keyboard)

Planned source:
- Driving AI

### Raw command vs. effective command

`VehicleController` keeps two commands per physics step:

- `LastCommand`: the raw command returned by the `IVehicleControlSource`, exactly
  as requested by the driver.
- `EffectiveCommand`: the command actually applied to the vehicle, after
  `ResolveCommand()`. When the throttle opposes the current direction of travel
  (forward speed above 0.5 m/s with a negative throttle, or the reverse), the
  throttle is converted into braking (`brake = max(brake, |throttle|)`,
  `throttle = 0`). Pressing "reverse" while moving forward therefore brakes
  first and only starts reversing once the vehicle has nearly stopped.

Telemetry and the health model use `EffectiveCommand`, so motor load, energy
and wear are not counted for a reverse request that is really braking. A
negative `throttle` in the telemetry means the vehicle is actually driving (or
starting to drive) backwards.

Speed limits: 15 m/s forward, 5 m/s in reverse.

## Simulated vehicle health

`VehicleHealthModel` updates at every physics step from the effective command
and the horizontal speed:

| Variable | Model |
|----------|-------|
| motor_load | `|throttle| * (0.4 + 0.6 * speed / 15)`, clamped to [0, 1] |
| battery_pct | decreases with power = idle 0.3 kW + load * 20 kW, on a 5 kWh battery; never increases (no charging yet) |
| motor_temp_c | first-order response (time constant 30 s) towards ambient 20 °C + load * 60 °C * (1 + wear) |
| motor_wear | accumulates with load (0.001 per second at full load), never decreases |
| distance_m | cumulative horizontal distance |
| runtime_s | cumulative running time |

## Telemetry

```
VehicleController + VehicleHealthModel + Rigidbody
        |
        v
VehicleTelemetryCollector  (IVehicleTelemetrySource -> VehicleTelemetrySample)
        |
        +----> TelemetryHud           (on-screen, H to toggle)
        |
        +----> TelemetryCsvRecorder   (10 Hz, R to start/stop)
                    |
                    v
          data/raw/telemetry_YYYYMMDD_HHMMSS.csv
                    |
                    v
          twin_maintenance (Python): validate -> summarize / plot
                    |
                    v
          data/processed/run_summary.csv, data/processed/figures/*.png
```

Each CSV row is one `VehicleTelemetrySample`, with 20 columns:

```
vehicle_id, timestamp_ms, sim_time_s, pos_x, pos_y, pos_z, vel_x, vel_y, vel_z,
speed_mps, accel_mps2, steering, throttle, brake, motor_load, battery_pct,
motor_temp_c, motor_wear, distance_m, runtime_s
```

- `sim_time_s` (Unity `Time.time`) is the reference clock, +0.1 s per row.
  `timestamp_ms` is the wall clock and may jump at startup.
- `speed_mps` is the norm of the 3D velocity; `accel_mps2` is the norm of the
  velocity change per physics step (it includes the centripetal component and
  spikes on collisions).
- `steering`, `throttle`, `brake` are the effective command.
- Files are written in UTF-8 with a BOM.

The authoritative definition (column order, types, units, outlier bounds) is the
data contract: [contracts/telemetry/telemetry-sample.v1.schema.json](../../contracts/telemetry/telemetry-sample.v1.schema.json).
Python tests check that the C# recorder and the contract stay in sync.

## Planned

Not implemented yet: live telemetry transport over MQTT, the digital twin
backend, storage in TimescaleDB and the dashboard. Today telemetry only flows
through CSV files.
