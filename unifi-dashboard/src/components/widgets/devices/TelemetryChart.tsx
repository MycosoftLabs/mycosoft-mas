"use client";
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface TelemetryPoint {
  timestamp: string;
  value: number;
}

interface TelemetryChartProps {
  deviceId: string;
  sensorType?: string;
  title?: string;
  height?: number;
}

export function TelemetryChart({ deviceId, sensorType = "temperature", title, height = 200 }: TelemetryChartProps) {
  const [data, setData] = useState<TelemetryPoint[]>([]);
  const [selectedSensor, setSelectedSensor] = useState(sensorType);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 5000);
    return () => clearInterval(interval);
  }, [deviceId, selectedSensor]);

  async function fetchTelemetry() {
    try {
      const response = await fetch(`/api/natureos/telemetry?deviceId=${deviceId}&sensorType=${selectedSensor}&limit=100`);
      if (response.ok) {
        const result = await response.json();
        setData(result.telemetry || []);
      }
    } catch (error) {
      console.error("Failed to fetch telemetry:", error);
    } finally {
      setLoading(false);
    }
  }

  const sensorTypes = ["temperature", "humidity", "pressure", "gas_resistance", "voc", "co2", "pm25"];

  const maxValue = Math.max(...data.map((d) => d.value), 1);
  const minValue = Math.min(...data.map((d) => d.value), 0);
  const range = maxValue - minValue || 1;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{title || `${selectedSensor} Telemetry`}</CardTitle>
          <Select value={selectedSensor} onValueChange={setSelectedSensor}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {sensorTypes.map((type) => (
                <SelectItem key={type} value={type}>{type}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center" style={{ height }}>Loading...</div>
        ) : data.length === 0 ? (
          <div className="flex items-center justify-center text-muted-foreground" style={{ height }}>No telemetry data</div>
        ) : (
          <svg width="100%" height={height} className="overflow-visible">
            <polyline
              fill="none"
              stroke="hsl(var(--primary))"
              strokeWidth="2"
              points={data.map((d, i) => `${(i / (data.length - 1 || 1)) * 100}%,${height - ((d.value - minValue) / range) * height}`).join(" ")}
            />
            {data.slice(-1).map((d, i) => (
              <circle
                key={i}
                cx="100%"
                cy={height - ((d.value - minValue) / range) * height}
                r="4"
                fill="hsl(var(--primary))"
              />
            ))}
          </svg>
        )}
        {data.length > 0 && (
          <div className="flex justify-between text-xs text-muted-foreground mt-2">
            <span>Min: {minValue.toFixed(2)}</span>
            <span>Current: {data[data.length - 1]?.value.toFixed(2)}</span>
            <span>Max: {maxValue.toFixed(2)}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
