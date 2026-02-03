"use client";
import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { AlertTriangle, CheckCircle, Shield, AlertCircle } from "lucide-react";

interface SafetyMetric {
  name: string;
  status: "ok" | "warning" | "critical";
  value: number;
  max: number;
  unit: string;
}

export function SafetyMonitor() {
  const [overallStatus, setOverallStatus] = useState<"safe" | "warning" | "critical">("safe");
  const [metrics, setMetrics] = useState<SafetyMetric[]>([
    { name: "Biosafety Level", status: "ok", value: 1, max: 4, unit: "BSL" },
    { name: "Air Quality Index", status: "ok", value: 42, max: 100, unit: "AQI" },
    { name: "Containment Integrity", status: "ok", value: 100, max: 100, unit: "%" },
    { name: "Active Experiments", status: "warning", value: 12, max: 15, unit: "" },
    { name: "Unreviewed Actions", status: "ok", value: 3, max: 50, unit: "" },
    { name: "System Alignment Score", status: "ok", value: 98, max: 100, unit: "%" },
  ]);

  const statusIcons = {
    ok: <CheckCircle className="h-5 w-5 text-green-500" />,
    warning: <AlertTriangle className="h-5 w-5 text-yellow-500" />,
    critical: <AlertCircle className="h-5 w-5 text-red-500" />,
  };

  const statusColors = {
    ok: "bg-green-500",
    warning: "bg-yellow-500",
    critical: "bg-red-500",
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" /> Safety Monitor
          </CardTitle>
          <Badge className={statusColors[overallStatus]}>
            {overallStatus === "safe" ? "All Systems Safe" : overallStatus === "warning" ? "Warnings Active" : "Critical Alert"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-2">
          {metrics.map((metric) => (
            <div key={metric.name} className="p-3 border rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  {statusIcons[metric.status]}
                  <span className="font-medium">{metric.name}</span>
                </div>
                <span className="font-bold">{metric.value}{metric.unit && ` ${metric.unit}`}</span>
              </div>
              <Progress value={(metric.value / metric.max) * 100} className={`h-2 ${statusColors[metric.status]}`} />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
