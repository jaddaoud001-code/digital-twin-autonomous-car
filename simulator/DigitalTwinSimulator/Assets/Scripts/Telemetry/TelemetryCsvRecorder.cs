using System;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

[RequireComponent(typeof(VehicleTelemetryCollector))]
public class TelemetryCsvRecorder : MonoBehaviour
{
    [SerializeField] private bool recordOnStart = true;
    [SerializeField, Range(1f, 50f)] private float sampleRateHz = 10f;

    private IVehicleTelemetrySource source;
    private StreamWriter writer;
    private float nextSampleTime;
    private int samplesWritten;

    public bool IsRecording => writer != null;
    public string CurrentFilePath { get; private set; }

    private void Awake()
    {
        source = GetComponent<VehicleTelemetryCollector>();
    }

    private void Start()
    {
        if (recordOnStart)
            StartRecording();
    }

    private void FixedUpdate()
    {
        if (!IsRecording || Time.time + 0.0001f< nextSampleTime)
            return;

        nextSampleTime += 1f / sampleRateHz;
        WriteSample(source.GetTelemetrySample());
    }

    public void StartRecording()
    {
        if (IsRecording)
            return;

        string directory = GetOutputDirectory();
        Directory.CreateDirectory(directory);

        string fileName =
            $"telemetry_{DateTime.Now:yyyyMMdd_HHmmss}.csv";
        CurrentFilePath = Path.Combine(directory, fileName);

        writer = new StreamWriter(CurrentFilePath, false, Encoding.UTF8);
        writer.WriteLine(
            "vehicle_id,timestamp_ms,sim_time_s," +
            "pos_x,pos_y,pos_z,vel_x,vel_y,vel_z," +
            "speed_mps,accel_mps2,steering,throttle,brake");

        samplesWritten = 0;
        nextSampleTime = Time.time;
        Debug.Log($"[Telemetry] Recording to {CurrentFilePath}");
    }

    public void StopRecording()
    {
        if (!IsRecording)
            return;

        writer.Flush();
        writer.Dispose();
        writer = null;
        Debug.Log($"[Telemetry] Stopped. {samplesWritten} samples written.");
    }

    private void WriteSample(VehicleTelemetrySample s)
    {
        CultureInfo inv = CultureInfo.InvariantCulture;

        writer.WriteLine(string.Join(",",
            s.vehicleId,
            s.timestampMs.ToString(inv),
            Time.time.ToString("F3", inv),
            s.position.x.ToString("F3", inv),
            s.position.y.ToString("F3", inv),
            s.position.z.ToString("F3", inv),
            s.velocity.x.ToString("F3", inv),
            s.velocity.y.ToString("F3", inv),
            s.velocity.z.ToString("F3", inv),
            s.speedMetersPerSecond.ToString("F3", inv),
            s.accelerationMetersPerSecondSquared.ToString("F3", inv),
            s.steering.ToString("F2", inv),
            s.throttle.ToString("F2", inv),
            s.brake.ToString("F2", inv)));

        samplesWritten++;

        // Flush every second so data survives a crash
        if (samplesWritten % Mathf.CeilToInt(sampleRateHz) == 0)
            writer.Flush();
    }

    private static string GetOutputDirectory()
    {
#if UNITY_EDITOR
        // Assets -> DigitalTwinSimulator -> simulator -> repo root
        return Path.GetFullPath(
            Path.Combine(Application.dataPath, "../../../data/raw"));
#else
        return Path.Combine(Application.persistentDataPath, "telemetry");
#endif
    }

    private void OnDisable() => StopRecording();
    private void OnApplicationQuit() => StopRecording();
}