using UnityEngine;
using UnityEngine.InputSystem;

[RequireComponent(typeof(Rigidbody))]
public class ManualVehicleController : MonoBehaviour
{
    [Header("Movement")]
    [SerializeField] private float acceleration = 6f;
    [SerializeField] private float maxSpeed = 15f;

    [Header("Steering")]
    [SerializeField] private float steeringSpeed = 70f;

    private Rigidbody rb;

    private void Awake()
    {
        rb = GetComponent<Rigidbody>();
    }

    private void FixedUpdate()
    {
        Keyboard keyboard = Keyboard.current;

        if (keyboard == null)
            return;

        float throttle = 0f;
        float steering = 0f;

        if (keyboard.wKey.isPressed || keyboard.upArrowKey.isPressed)
            throttle += 1f;

        if (keyboard.sKey.isPressed || keyboard.downArrowKey.isPressed)
            throttle -= 1f;

        if (keyboard.aKey.isPressed || keyboard.leftArrowKey.isPressed)
            steering -= 1f;

        if (keyboard.dKey.isPressed || keyboard.rightArrowKey.isPressed)
            steering += 1f;

        // Acceleration / reverse
        rb.AddForce(
            transform.forward * throttle * acceleration,
            ForceMode.Acceleration
        );

        // Limit speed
        if (rb.linearVelocity.magnitude > maxSpeed)
        {
            rb.linearVelocity =
                rb.linearVelocity.normalized * maxSpeed;
        }

        // Steering only while the vehicle is moving
        if (rb.linearVelocity.magnitude > 0.2f)
        {
            float rotation =
                steering * steeringSpeed * Time.fixedDeltaTime;

            Quaternion deltaRotation =
                Quaternion.Euler(0f, rotation, 0f);

            rb.MoveRotation(rb.rotation * deltaRotation);
        }
    }
}