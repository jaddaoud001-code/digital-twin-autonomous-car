using UnityEngine;
using UnityEngine.InputSystem;

[RequireComponent(typeof(VehicleTelemetryCollector))]
public class TelemetryHud : MonoBehaviour
{
    [SerializeField] private bool visible = true;

    private IVehicleTelemetrySource source;
    private TelemetryCsvRecorder recorder;
    private GUIStyle style;

    private void Awake()
    {
        source = GetComponent<VehicleTelemetryCollector>();
        recorder = GetComponent<TelemetryCsvRecorder>(); // optional
    }

    private void Update()
    {
        Keyboard keyboard = Keyboard.current;
        if (keyboard == null)
            return;

        if (keyboard.hKey.wasPressedThisFrame)
            visible = !visible;

        if (recorder != null && keyboard.rKey.wasPressedThisFrame)
        {
            if (recorder.IsRecording)
                recorder.StopRecording();
            else
                recorder.StartRecording();
        }
    }

    private void OnGUI()
    {
        if (!visible)
            return;

        if (style == null)
        {
            style = new GUIStyle(GUI.skin.label)
            {
                fontSize = 16,
                richText = true
            };
        }

        VehicleTelemetrySample s = source.GetTelemetrySample();

        string recLine = recorder == null
            ? "REC : n/a"
            : recorder.IsRecording
                ? "<color=red>● REC</color>  (R to stop)"
                : "○ not recording  (R to start)";

        string text =
            $"<b>{s.vehicleId}</b>\n" +
            $"Speed     : {s.speedMetersPerSecond * 3.6f,6:F1} km/h  ({s.speedMetersPerSecond:F2} m/s)\n" +
            $"Accel     : {s.accelerationMetersPerSecondSquared,6:F2} m/s²\n" +
            $"Throttle  : {s.throttle,5:F2}\n" +
            $"Steering  : {s.steering,5:F2}\n" +
            $"Brake     : {s.brake,5:F2}\n" +
            $"Position  : ({s.position.x:F1}, {s.position.y:F1}, {s.position.z:F1})\n" +
            $"Sim time  : {Time.time:F1} s\n" +
            $"──────────────\n" +
            $"Motor load: {s.motorLoad * 100f,5:F0} %\n" +
            $"Battery   : {s.batteryPercent,6:F2} %\n" +
            $"Motor temp: {s.motorTemperatureC,6:F1} °C\n" +
            $"Motor wear: {s.motorWear * 100f,6:F3} %\n" +
            $"Distance  : {s.distanceMeters,6:F0} m\n" +
            $"Runtime   : {s.runtimeSeconds,6:F0} s\n" +
            recLine + "\n" +
            "<size=12>H : hide HUD</size>";

        GUI.Box(new Rect(10, 10, 360, 380), GUIContent.none);
        GUI.Label(new Rect(20, 15, 350, 370), text, style);
    }
}