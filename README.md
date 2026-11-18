# Digital Twin Autonomous Car

A Digital Twin of an autonomous vehicle driving in a virtual environment. A
Unity simulator drives a physics-based vehicle, simulates its health (battery,
motor temperature, load, wear) and records telemetry; a Python pipeline
validates and analyses that telemetry. Later phases will add a driving AI, a
live twin backend, predictive maintenance and a dashboard.

## Status

| Phase | Content | Status |
|-------|---------|--------|
| P0 | Simulator foundation: Unity project, road scene, physics vehicle, manual control, follow camera, control and telemetry interfaces | Done |
| P1 | Telemetry and simulated health model, CSV recording, HUD, data contract, Python validation / analysis pipeline | Done |
| P2+ | See [roadmap](#roadmap) | Planned |

## Repository layout

```
.
├── simulator/DigitalTwinSimulator/   # Unity project (implemented)
├── contracts/                        # data contracts, JSON Schema (implemented)
├── ml/maintenance/                   # Python package twin-maintenance (implemented)
├── ml/driving/                       # driving AI (planned, empty)
├── data/raw/                         # CSV recorded by the simulator (git-ignored)
├── data/processed/                   # summaries and figures (git-ignored)
├── docs/architecture/                # scope, architecture, data flows
├── backend/, dashboard/, infra/      # planned, empty placeholders
└── models/, scripts/, tests/         # planned, empty placeholders
```

## Running the simulator

1. Install **Unity 6000.3.23f1**.
2. Open the project folder `simulator/DigitalTwinSimulator` in Unity Hub.
3. Open the scene `Assets/Scenes/Main.unity` and press Play.

Controls (physical keys, AZERTY layout):

| Key | Action |
|-----|--------|
| Z / ↑ | Throttle forward |
| S / ↓ | Reverse (brakes first when moving forward) |
| Q / ← and D / → | Steer left / right |
| Space | Brake |
| R | Start / stop CSV recording |
| H | Show / hide the telemetry HUD |

Recording starts automatically on Play. In the editor each recording is written
to `data/raw/telemetry_YYYYMMDD_HHMMSS.csv` (10 Hz).

## Analysing the data

```bash
cd ml/maintenance
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

.venv/bin/python -m twin_maintenance validate    # check every run against the contract
.venv/bin/python -m twin_maintenance summarize   # data/processed/run_summary.csv
.venv/bin/python -m twin_maintenance plot        # data/processed/figures/*.png
```

Details: [ml/maintenance/README.md](ml/maintenance/README.md). The CSV format is
defined in [contracts/telemetry/telemetry-sample.v1.schema.json](contracts/telemetry/telemetry-sample.v1.schema.json).

## Documentation

- [Project scope](docs/architecture/scope.md)
- [System architecture](docs/architecture/system-architecture.md)
- [Data flows](docs/architecture/data-flows.md)
- [Technology stack](docs/architecture/technology-stack.md)
- [Contracts](contracts/README.md)

## Roadmap

All items below are **planned**, not implemented:

- Live telemetry transport over MQTT.
- Digital twin backend service with a TimescaleDB time-series store.
- Real-time dashboard.
- Predictive maintenance models trained on recorded telemetry.
- Driving AI (camera-based control source replacing manual input).
- Procedural environment generation.
- Containerized services (Docker) and MLOps tooling.
