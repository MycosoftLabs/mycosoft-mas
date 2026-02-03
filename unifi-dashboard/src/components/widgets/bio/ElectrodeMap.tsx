"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface ElectrodeData {
  index: number;
  active: boolean;
  impedance: number;
  signal: number;
}

interface ElectrodeMapProps {
  rows?: number;
  cols?: number;
  electrodes?: ElectrodeData[];
  onElectrodeClick?: (index: number) => void;
}

export function ElectrodeMap({ rows = 8, cols = 8, electrodes, onElectrodeClick }: ElectrodeMapProps) {
  const [selectedElectrodes, setSelectedElectrodes] = useState<Set<number>>(new Set());
  
  const defaultElectrodes: ElectrodeData[] = electrodes || Array.from({ length: rows * cols }, (_, i) => ({
    index: i,
    active: Math.random() > 0.1,
    impedance: Math.random() * 100 + 50,
    signal: Math.random() * 100,
  }));

  const getElectrodeColor = (electrode: ElectrodeData) => {
    if (!electrode.active) return "bg-gray-300 dark:bg-gray-700";
    if (selectedElectrodes.has(electrode.index)) return "bg-blue-500";
    const intensity = Math.min(electrode.signal / 100, 1);
    if (intensity > 0.7) return "bg-red-500";
    if (intensity > 0.4) return "bg-yellow-500";
    return "bg-green-500";
  };

  const toggleElectrode = (index: number) => {
    const newSelected = new Set(selectedElectrodes);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedElectrodes(newSelected);
    onElectrodeClick?.(index);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Electrode Array ({rows}x{cols})</CardTitle>
      </CardHeader>
      <CardContent>
        <TooltipProvider>
          <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
            {defaultElectrodes.map((electrode) => (
              <Tooltip key={electrode.index}>
                <TooltipTrigger asChild>
                  <button
                    className={`aspect-square rounded-full transition-all hover:scale-110 ${getElectrodeColor(electrode)}`}
                    onClick={() => toggleElectrode(electrode.index)}
                  />
                </TooltipTrigger>
                <TooltipContent>
                  <div className="text-xs">
                    <p>Electrode {electrode.index + 1}</p>
                    <p>Status: {electrode.active ? "Active" : "Inactive"}</p>
                    <p>Impedance: {electrode.impedance.toFixed(0)} kÎ©</p>
                    <p>Signal: {electrode.signal.toFixed(1)}%</p>
                  </div>
                </TooltipContent>
              </Tooltip>
            ))}
          </div>
        </TooltipProvider>
        <div className="flex justify-between text-xs text-muted-foreground mt-4">
          <span>ðŸŸ¢ Low Signal</span>
          <span>ðŸŸ¡ Medium</span>
          <span>ðŸ”´ High Signal</span>
          <span>âš« Inactive</span>
        </div>
        {selectedElectrodes.size > 0 && (
          <p className="text-sm mt-2">Selected: {Array.from(selectedElectrodes).map(i => i + 1).join(", ")}</p>
        )}
      </CardContent>
    </Card>
  );
}
