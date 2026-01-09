"use client";

import { Card, CardContent } from "@/components/ui/card";

interface HUDProps {
  viewport: { north: number; south: number; east: number; west: number } | null;
}

export function HUD({ viewport }: HUDProps) {
  return (
    <Card className="bg-gray-900/90 backdrop-blur-sm border-gray-700">
      <CardContent className="p-3">
        <div className="text-xs text-gray-300 space-y-1">
          {viewport && (
            <>
              <div>North: {viewport.north.toFixed(4)}°</div>
              <div>South: {viewport.south.toFixed(4)}°</div>
              <div>East: {viewport.east.toFixed(4)}°</div>
              <div>West: {viewport.west.toFixed(4)}°</div>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
