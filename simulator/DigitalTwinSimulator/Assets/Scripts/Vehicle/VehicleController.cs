using UnityEngine;

[DefaultExecutionOrder(-100)]
[RequireComponent(typeof(Rigidbody))]
public class VehicleController : MonoBehaviour
{
    [Header("Movement")]
    [SerializeField] private float acceleration = 12f;
    [SerializeField] private float maxSpeed = 15f;
    [Tooltip("Maximum speed when driving backwards (m/s).")]
    [SerializeField] private float maxReverseSpeed = 5f;
    [SerializeField] private float brakeStrength = 10f;
    [Tooltip("Forward speed (m/s) above which an opposite throttle is treated as braking instead of a direction change.")]
    [SerializeField] private float directionChangeSpeed = 0.5f;

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

        ForwardSpeed = Vector3.Dot(rb.linearVelocity, transform.forward);

        LastCommand = controlSource.GetControlCommand();
        EffectiveCommand = ResolveCommand(LastCommand);

        ApplyThrottle(EffectiveCommand.Throttle);
        ApplySteering(EffectiveCommand.Steering);
        ApplyBrake(EffectiveCommand.Brake);
        LimitSpeed();
    }

    // Converts a throttle opposite to the current direction of travel into braking,
    // so that "reverse while moving forward" (and vice versa) is not counted as motor effort.
    private VehicleControlCommand ResolveCommand(VehicleControlCommand cmd)
    {
        bool movingForward = ForwardSpeed > directionChangeSpeed;
        bool movingBackward = ForwardSpeed < -directionChangeSpeed;

        if ((movingForward && cmd.Throttle < 0f) ||
            (movingBackward && cmd.Throttle > 0f))
        {
            cmd.Brake = Mathf.Max(cmd.Brake, Mathf.Abs(cmd.Throttle));
            cmd.Throttle = 0f;
        }

        return cmd;
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
        if (Mathf.Abs(ForwardSpeed) < 0.2f)
            return;

        // Invert yaw when reversing, like a real car
        float rotation =
            steering *
            steeringSpeed *
            Mathf.Sign(ForwardSpeed) *
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
        float limit = ForwardSpeed >= 0f ? maxSpeed : maxReverseSpeed;

        if (rb.linearVelocity.magnitude <= limit)
            return;

        rb.linearVelocity =
            rb.linearVelocity.normalized * limit;
    }

    // Raw command from the IVehicleControlSource
    public VehicleControlCommand LastCommand { get; private set; }

    // Command actually applied to the vehicle (after ResolveCommand)
    public VehicleControlCommand EffectiveCommand { get; private set; }

    // Signed speed along transform.forward, sampled at the start of FixedUpdate (negative = reversing)
    public float ForwardSpeed { get; private set; }
}