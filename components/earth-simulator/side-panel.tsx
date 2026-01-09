"use client";

import { useState, useEffect } from "react";
import { X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DataPanel } from "./data-panel";
import { Statistics } from "./statistics";
import { SpeciesList } from "./species-list";

interface SidePanelProps {
  cellId: string;
  lat: number;
  lon: number;
  onClose: () => void;
}

export function SidePanel({ cellId, lat, lon, onClose }: SidePanelProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [probResponse, obsResponse] = await Promise.all([
          fetch(`/api/earth-simulator/mycelium-probability?lat=${lat}&lon=${lon}&zoom=15`),
          fetch(`/api/earth-simulator/inaturalist?action=fungi&lat=${lat}&lng=${lon}&radius=100`),
        ]);

        const probData = await probResponse.json();
        const obsData = await obsResponse.json();

        setData({
          probability: probData,
          observations: obsData.observations || [],
        });
      } catch (error) {
        console.error("Error fetching cell data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [cellId, lat, lon]);

  return (
    <div className="h-full bg-gray-900/95 backdrop-blur-sm border-l border-gray-700 overflow-y-auto">
      <div className="sticky top-0 bg-gray-900 border-b border-gray-700 p-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Cell Data</h2>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      <div className="p-4 space-y-4">
        {loading ? (
          <div className="text-gray-400">Loading...</div>
        ) : data ? (
          <>
            <DataPanel
              cellId={cellId}
              lat={lat}
              lon={lon}
              probability={data.probability}
            />
            <Statistics probability={data.probability} observations={data.observations} />
            <SpeciesList observations={data.observations} />
          </>
        ) : (
          <div className="text-gray-400">No data available</div>
        )}
      </div>
    </div>
  );
}
