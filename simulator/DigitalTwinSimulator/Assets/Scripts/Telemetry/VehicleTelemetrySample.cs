using UnityEngine;

[System.Serializable]
public struct VehicleTelemetrySample
{
    public string vehicleId;
    public long timestampMs;

    public Vector3 position;
    public Vector3 velocity;

    public float speedMetersPerSecond;
    public float accelerationMetersPerSecondSquared;

    public float steering;
    public float throttle;
    public float brake;

    // Vehicle health
    public float motorLoad;
    public float batteryPercent;
    public float motorTemperatureC;
    public float motorWear;
    public float distanceMeters;
    public float runtimeSeconds;
}