using UnityEngine;

[RequireComponent(typeof(Rigidbody))]
public class VehicleController : MonoBehaviour
{
    [Header("Movement")]
    [SerializeField] private float acceleration = 12f;
    [SerializeField] private float maxSpeed = 15f;
    [SerializeField] private float brakeStrength = 10f;

    [Header("Steering")]
    [SerializeField] private float steeringSpeed = 70f;

    private Rigidbody rb;
    private IVehicleControlSource controlSource;

    private void Awake()
    {
        rb = GetComponent<Rigidbody>();

        MonoBehaviour[] behaviours = GetComponents<MonoBehaviour>();

        foreach (MonoBehaviour behaviour in behaviours)
        {
            if (behaviour is IVehicleControlSource source)
            {
                controlSource = source;
                break;
            }
        }

        if (controlSource == null)
        {
            Debug.LogError(
                "No component implementing IVehicleControlSource was found on Vehicle."
            );
        }
    }

    private void FixedUpdate()
    {
        if (controlSource == null)
            return;

        LastCommand = controlSource.GetControlCommand();

        ApplyThrottle(LastCommand.Throttle);
        ApplySteering(LastCommand.Steering);
        ApplyBrake(LastCommand.Brake);
        LimitSpeed();
    }

    private void ApplyThrottle(float throttle)
    {
        rb.AddForce(
            transform.forward * throttle * acceleration,
            ForceMode.Acceleration
        );
    }

    private void ApplySteering(float steering)
    {
        if (rb.linearVelocity.magnitude < 0.2f)
            return;

        float rotation =
            steering *
            steeringSpeed *
            Time.fixedDeltaTime;

        Quaternion deltaRotation =
            Quaternion.Euler(0f, rotation, 0f);

        rb.MoveRotation(
            rb.rotation * deltaRotation
        );
    }

    private void ApplyBrake(float brake)
    {
        if (brake <= 0f)
            return;

        rb.linearVelocity = Vector3.MoveTowards(
            rb.linearVelocity,
            Vector3.zero,
            brakeStrength * brake * Time.fixedDeltaTime
        );
    }

    private void LimitSpeed()
    {
        if (rb.linearVelocity.magnitude <= maxSpeed)
            return;

        rb.linearVelocity =
            rb.linearVelocity.normalized * maxSpeed;
    }

    public VehicleControlCommand LastCommand { get; private set; }
}