using System;
using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
[RequireComponent(typeof(VehicleController))]
public class VehicleTelemetryCollector :
    MonoBehaviour,
    IVehicleTelemetrySource
{
    [SerializeField] private string vehicleId = "vehicle-001";

    private Rigidbody rb;
    private VehicleController vehicleController;

    private Vector3 previousVelocity;
    private float currentAcceleration;

    private void Awake()
    {
        rb = GetComponent<Rigidbody>();
        vehicleController = GetComponent<VehicleController>();

        previousVelocity = rb.linearVelocity;
    }

    private void FixedUpdate()
    {
        Vector3 currentVelocity = rb.linearVelocity;

        currentAcceleration =
            (currentVelocity - previousVelocity).magnitude
            / Time.fixedDeltaTime;

        previousVelocity = currentVelocity;
    }

    public VehicleTelemetrySample GetTelemetrySample()
    {
        VehicleControlCommand command =
            vehicleController.LastCommand;

        return new VehicleTelemetrySample
        {
            vehicleId = vehicleId,

            timestampMs =
                DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),

            position = transform.position,

            velocity = rb.linearVelocity,

            speedMetersPerSecond =
                rb.linearVelocity.magnitude,

            accelerationMetersPerSecondSquared =
                currentAcceleration,

            steering = command.Steering,
            throttle = command.Throttle,
            brake = command.Brake
        };
    }
}