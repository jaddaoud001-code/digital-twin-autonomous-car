using UnityEngine;
using UnityEngine.InputSystem;

public class ManualInputSource : MonoBehaviour, IVehicleControlSource
{
    public VehicleControlCommand GetControlCommand()
    {
        Keyboard keyboard = Keyboard.current;

        if (keyboard == null)
        {
            return new VehicleControlCommand(0f, 0f, 0f);
        }

        float throttle = 0f;
        float steering = 0f;
        float brake = 0f;

        // AZERTY : wKey correspond physiquement à Z
        if (keyboard.wKey.isPressed || keyboard.upArrowKey.isPressed)
            throttle = 1f;

        if (keyboard.sKey.isPressed || keyboard.downArrowKey.isPressed)
            throttle = -1f;

        // AZERTY : aKey correspond physiquement à Q
        if (keyboard.aKey.isPressed || keyboard.leftArrowKey.isPressed)
            steering = -1f;

        if (keyboard.dKey.isPressed || keyboard.rightArrowKey.isPressed)
            steering = 1f;

        if (keyboard.spaceKey.isPressed)
            brake = 1f;

        return new VehicleControlCommand(
            throttle,
            steering,
            brake
        );
    }
}