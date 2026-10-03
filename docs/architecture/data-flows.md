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
- ManualInputSource

Future source:
- Driving AI

## Telemetry

The Unity simulator currently exposes:

- vehicleId
- timestampMs
- position
- velocity
- speedMetersPerSecond
- accelerationMetersPerSecondSquared
- steering
- throttle
- brake

Future telemetry will add simulated vehicle-health variables such as:

- battery level;
- motor temperature;
- motor load;
- travelled distance;
- runtime.

Telemetry transport through MQTT is not implemented during P0.