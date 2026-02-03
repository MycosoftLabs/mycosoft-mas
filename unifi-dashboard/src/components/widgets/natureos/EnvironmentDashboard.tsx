"use client";
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface EnvironmentData {
  temperature: number;
  humidity: number;
  pressure: number;
  co2: number;
  voc: number;
  pm25: number;
}

export function EnvironmentDashboard() {
  const [data, setData] = useState<EnvironmentData>({
    temperature: 25,
    humidity: 60,
    pressure: 1013,
    co2: 450,
    voc: 50,
    pm25: 10,
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setData({
        temperature: 24 + Math.random() * 4,
        humidity: 55 + Math.random() * 20,
        pressure: 1010 + Math.random() * 10,
        co2: 400 + Math.random() * 200,
        voc: 30 + Math.random() * 50,
        pm25: 5 + Math.random() * 20,
      });
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const metrics = [
    { label: "Temperature", value: data.temperature.toFixed(1), unit: "Â°C", max: 40, color: "bg-orange-500" },
    { label: "Humidity", value: data.humidity.toFixed(0), unit: "%", max: 100, color: "bg-blue-500" },
    { label: "Pressure", value: data.pressure.toFixed(0), unit: "hPa", max: 1050, color: "bg-purple-500" },
    { label: "CO2", value: data.co2.toFixed(0), unit: "ppm", max: 1000, color: "bg-green-500" },
    { label: "VOC Index", value: data.voc.toFixed(0), unit: "", max: 100, color: "bg-yellow-500" },
    { label: "PM2.5", value: data.pm25.toFixed(1), unit: "Î¼g/mÂ³", max: 50, color: "bg-red-500" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Environment Overview</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {metrics.map((metric) => (
            <div key={metric.label} className="p-3 border rounded-lg">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-muted-foreground">{metric.label}</span>
                <span className="font-bold">{metric.value}{metric.unit}</span>
              </div>
              <Progress value={(parseFloat(metric.value) / metric.max) * 100} className={`h-2 ${metric.color}`} />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
