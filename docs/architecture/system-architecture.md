# System Architecture

## Current P0 architecture

ManualInputSource
        |
        | IVehicleControlSource
        v
VehicleController
        |
        v
Rigidbody / Unity Physics
        |
        v
Vehicle
        |
        +----> FollowCamera
        |
        +----> VehicleTelemetryCollector
                    |
                    | IVehicleTelemetrySource
                    v
              Future telemetry pipeline

## Target architecture

Procedural Generation
        |
        v
Unity Simulator
        |
        +---- Camera ----> Driving AI ----> Vehicle Control
        |
        +---- Telemetry ----> MQTT ----> Digital Twin Backend
                                      |
                                      +----> TimescaleDB
                                      |
                                      +----> Predictive Maintenance
                                      |
                                      +----> Dashboard