"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Info } from "lucide-react";

export function Controls() {
  return (
    <Card className="bg-gray-900/90 backdrop-blur-sm border-gray-700">
      <CardContent className="p-4">
        <div className="flex items-center gap-2 text-sm text-gray-300">
          <Info className="w-4 h-4" />
          <div className="space-y-1">
            <div>Mouse: Drag to rotate, Scroll to zoom</div>
            <div>Keyboard: Arrow keys to navigate, +/- to zoom</div>
            <div>Touch: Pinch to zoom, drag to rotate</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
