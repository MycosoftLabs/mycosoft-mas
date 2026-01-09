"use client";

import { useState, useEffect } from "react";
import { MyceliumLayer } from "./mycelium-layer";
import { HeatLayer } from "./heat-layer";
import { OrganismLayer } from "./organism-layer";
import { WeatherLayer } from "./weather-layer";
import { DeviceMarkers } from "./device-markers";

interface LayerManagerProps {
  zoom: number;
  viewport?: { north: number; south: number; east: number; west: number };
  layers?: {
    mycelium: boolean;
    heat: boolean;
    organisms: boolean;
    weather: boolean;
  };
}

export interface LayerState {
  mycelium: boolean;
  heat: boolean;
  organisms: boolean;
  weather: boolean;
}

export function LayerManager({ zoom, viewport, layers }: LayerManagerProps) {
  const defaultLayers: LayerState = {
    mycelium: true,
    heat: false,
    organisms: false,
    weather: false,
  };
  
  const activeLayers = layers || defaultLayers;

  return (
    <>
      {activeLayers.mycelium && <MyceliumLayer zoom={zoom} viewport={viewport} />}
      {activeLayers.heat && <HeatLayer zoom={zoom} viewport={viewport} />}
      {activeLayers.organisms && <OrganismLayer zoom={zoom} viewport={viewport} />}
      {activeLayers.weather && <WeatherLayer zoom={zoom} viewport={viewport} />}
      <DeviceMarkers zoom={zoom} />
    </>
  );
}
