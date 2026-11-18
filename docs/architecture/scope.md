# Project Scope

The project aims to build a Digital Twin of an autonomous vehicle evolving
inside a virtual environment.

The system will progressively include:

- a Unity-based vehicle simulator;
- procedural environment generation;
- a Driving AI module;
- vehicle telemetry;
- a synchronized Digital Twin;
- predictive maintenance;
- a backend and time-series database;
- a real-time dashboard;
- containerized services and MLOps tooling.

## Current P0 scope

P0 establishes the technical foundation:

- Unity simulator;
- minimal road environment;
- physics-based vehicle;
- manual vehicle control;
- follow camera;
- interchangeable vehicle control interface;
- telemetry collection interface.

Advanced AI, MQTT communication, backend integration and predictive
maintenance are intentionally deferred to later phases.

## P1 scope

P1 makes the simulator produce usable, checked data:

- telemetry: a `VehicleTelemetrySample` per sample (position, velocity, speed,
  acceleration, effective command, health variables);
- simulated health model: motor load, battery level, motor temperature, motor
  wear, travelled distance, runtime;
- realistic braking and reverse (raw vs. effective command);
- CSV recording at 10 Hz into `data/raw/`, toggled with R;
- on-screen telemetry HUD, toggled with H;
- data contract: `contracts/telemetry/telemetry-sample.v1.schema.json`, kept in
  sync with the C# recorder by cross-language tests;
- Python analysis pipeline (`ml/maintenance`, package `twin_maintenance`):
  loading, validation, per-run summary and plots, with a CLI.

Still out of scope after P1 (planned): MQTT transport, backend and TimescaleDB,
dashboard, Docker, driving AI, procedural generation and predictive maintenance
models.