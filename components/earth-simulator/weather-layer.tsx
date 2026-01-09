"use client";

import { useRef } from "react";
import * as THREE from "three";

interface WeatherLayerProps {
  zoom: number;
  viewport?: { north: number; south: number; east: number; west: number };
}

export function WeatherLayer({ zoom, viewport }: WeatherLayerProps) {
  const groupRef = useRef<THREE.Group>(null);

  // In production, this would fetch weather data from NOAA APIs
  // and render precipitation, wind patterns, etc.
  // For now, return null as placeholder

  return null;
}
