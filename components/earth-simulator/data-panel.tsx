"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface DataPanelProps {
  cellId: string;
  lat: number;
  lon: number;
  probability?: any;
}

export function DataPanel({ cellId, lat, lon, probability }: DataPanelProps) {
  const densityColor = {
    none: "bg-gray-500",
    low: "bg-green-500",
    medium: "bg-yellow-500",
    high: "bg-red-500",
  }[probability?.density || "none"];

  return (
    <Card className="bg-gray-800 border-gray-700">
      <CardHeader>
        <CardTitle className="text-sm text-white">Cell Information</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <div className="text-xs text-gray-400">Cell ID</div>
          <div className="text-sm text-white font-mono">{cellId}</div>
        </div>
        <div>
          <div className="text-xs text-gray-400">Coordinates</div>
          <div className="text-sm text-white">
            {lat.toFixed(6)}°, {lon.toFixed(6)}°
          </div>
        </div>
        {probability && (
          <>
            <div>
              <div className="text-xs text-gray-400">Mycelium Probability</div>
              <div className="flex items-center gap-2 mt-1">
                <div className="flex-1 bg-gray-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${densityColor}`}
                    style={{ width: `${probability.probability * 100}%` }}
                  />
                </div>
                <span className="text-sm text-white">
                  {(probability.probability * 100).toFixed(1)}%
                </span>
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-400">Density</div>
              <Badge className={densityColor}>
                {probability.density || "none"}
              </Badge>
            </div>
            <div>
              <div className="text-xs text-gray-400">Confidence</div>
              <div className="text-sm text-white">
                {(probability.confidence * 100).toFixed(0)}%
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
