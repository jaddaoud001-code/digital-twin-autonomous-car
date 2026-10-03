public struct VehicleControlCommand
{
    public float Throttle;
    public float Steering;
    public float Brake;

    public VehicleControlCommand(
        float throttle,
        float steering,
        float brake)
    {
        Throttle = throttle;
        Steering = steering;
        Brake = brake;
    }
}