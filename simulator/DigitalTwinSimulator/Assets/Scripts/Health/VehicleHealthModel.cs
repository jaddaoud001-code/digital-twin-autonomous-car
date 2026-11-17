using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
[RequireComponent(typeof(VehicleController))]
public class VehicleHealthModel : MonoBehaviour
{
    [Header("Motor load")]
    [SerializeField] private float referenceSpeed = 15f;

    [Header("Battery")]
    [SerializeField] private float batteryCapacityKwh = 5f;
    [SerializeField] private float maxMotorPowerKw = 20f;
    [SerializeField] private float idlePowerKw = 0.3f;
    [SerializeField, Range(0f, 100f)] private float initialBatteryPercent = 100f;

    [Header("Thermal (1st-order model)")]
    [SerializeField] private float ambientTemperatureC = 20f;
    [SerializeField] private float maxTemperatureRiseC = 60f;
    [SerializeField] private float thermalTimeConstantS = 30f;

    [Header("Wear")]
    [SerializeField] private float initialMotorWear = 0f;
    [SerializeField] private float wearRatePerSecondAtFullLoad = 0.001f;

    public float MotorLoad { get; private set; }
    public float BatteryPercent { get; private set; }
    public float MotorTemperatureC { get; private set; }
    public float MotorWear { get; private set; }
    public float DistanceMeters { get; private set; }
    public float RuntimeSeconds { get; private set; }

    private Rigidbody rb;
    private VehicleController controller;

    private void Awake()
    {
        rb = GetComponent<Rigidbody>();
        controller = GetComponent<VehicleController>();

        BatteryPercent = initialBatteryPercent;
        MotorTemperatureC = ambientTemperatureC;
        MotorWear = Mathf.Clamp01(initialMotorWear);
    }

    private void FixedUpdate()
    {
        float dt = Time.fixedDeltaTime;
        VehicleControlCommand cmd = controller.EffectiveCommand;

        Vector3 horizontalVelocity = rb.linearVelocity;
        horizontalVelocity.y = 0f;
        float speed = horizontalVelocity.magnitude;

        // Load: throttle demand, heavier at high speed
        float speedRatio = Mathf.Clamp01(speed / referenceSpeed);
        MotorLoad = Mathf.Clamp01(
            Mathf.Abs(cmd.Throttle) * (0.4f + 0.6f * speedRatio));

        // Battery: energy = power * time
        float powerKw = idlePowerKw + MotorLoad * maxMotorPowerKw;
        float energyKwh = powerKw * dt / 3600f;
        BatteryPercent = Mathf.Max(
            0f, BatteryPercent - energyKwh / batteryCapacityKwh * 100f);

        // Temperature: 1st-order response, worn motor heats more
        float targetTemperature =
            ambientTemperatureC +
            MotorLoad * maxTemperatureRiseC * (1f + MotorWear);
        MotorTemperatureC +=
            (targetTemperature - MotorTemperatureC) * (dt / thermalTimeConstantS);

        // Wear accumulates with load
        MotorWear = Mathf.Min(
            1f, MotorWear + MotorLoad * wearRatePerSecondAtFullLoad * dt);

        DistanceMeters += speed * dt;
        RuntimeSeconds += dt;
    }
}