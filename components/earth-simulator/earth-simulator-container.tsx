"use client";

import { useState, useCallback } from "react";
import { WebGLGlobe } from "./webgl-globe";
import { SidePanel } from "./side-panel";
import { LayerControls } from "./layer-controls";
import { Controls } from "./controls";
import { HUD } from "./hud";

interface EarthSimulatorContainerProps {
  className?: string;
}

export function EarthSimulatorContainer({ className = "" }: EarthSimulatorContainerProps) {
  const [selectedCell, setSelectedCell] = useState<{
    cellId: string;
    lat: number;
    lon: number;
  } | null>(null);
  const [viewport, setViewport] = useState<{
    north: number;
    south: number;
    east: number;
    west: number;
  } | null>(null);
  const [layers, setLayers] = useState({
    mycelium: true,
    heat: false,
    organisms: false,
    weather: false,
  });

  const handleCellClick = useCallback((cellId: string, lat: number, lon: number) => {
    setSelectedCell({ cellId, lat, lon });
  }, []);

  const handleViewportChange = useCallback(
    (newViewport: { north: number; south: number; east: number; west: number }) => {
      setViewport(newViewport);
    },
    []
  );

  return (
    <div className={`earth-simulator-container w-full h-screen relative ${className}`}>
      {/* WebGL Globe */}
      <div className="absolute inset-0">
        <WebGLGlobe onCellClick={handleCellClick} onViewportChange={handleViewportChange} layers={layers} />
      </div>

      {/* HUD Overlay */}
      <div className="absolute top-4 left-4 z-10">
        <HUD viewport={viewport} />
      </div>

      {/* Layer Controls */}
      <div className="absolute top-4 right-4 z-10">
        <LayerControls layers={layers} onLayersChange={setLayers} />
      </div>

      {/* Controls */}
      <div className="absolute bottom-4 left-4 z-10">
        <Controls />
      </div>

      {/* Side Panel */}
      {selectedCell && (
        <div className="absolute right-0 top-0 bottom-0 w-96 z-10">
          <SidePanel
            cellId={selectedCell.cellId}
            lat={selectedCell.lat}
            lon={selectedCell.lon}
            onClose={() => setSelectedCell(null)}
          />
        </div>
      )}
    </div>
  );
}
