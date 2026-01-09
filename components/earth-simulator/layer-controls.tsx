"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

interface LayerControlsProps {
  layers: {
    mycelium: boolean;
    heat: boolean;
    organisms: boolean;
    weather: boolean;
  };
  onLayersChange: (layers: LayerControlsProps["layers"]) => void;
}

export function LayerControls({ layers, onLayersChange }: LayerControlsProps) {
  const handleToggle = (layer: keyof typeof layers) => {
    onLayersChange({
      ...layers,
      [layer]: !layers[layer],
    });
  };

  return (
    <Card className="w-64 bg-gray-900/90 backdrop-blur-sm border-gray-700">
      <CardHeader>
        <CardTitle className="text-sm text-white">Layers</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <Label htmlFor="mycelium" className="text-sm text-gray-300">
            Mycelium
          </Label>
          <Switch
            id="mycelium"
            checked={layers.mycelium}
            onCheckedChange={() => handleToggle("mycelium")}
          />
        </div>
        <div className="flex items-center justify-between">
          <Label htmlFor="heat" className="text-sm text-gray-300">
            Heat Map
          </Label>
          <Switch
            id="heat"
            checked={layers.heat}
            onCheckedChange={() => handleToggle("heat")}
          />
        </div>
        <div className="flex items-center justify-between">
          <Label htmlFor="organisms" className="text-sm text-gray-300">
            Organisms
          </Label>
          <Switch
            id="organisms"
            checked={layers.organisms}
            onCheckedChange={() => handleToggle("organisms")}
          />
        </div>
        <div className="flex items-center justify-between">
          <Label htmlFor="weather" className="text-sm text-gray-300">
            Weather
          </Label>
          <Switch
            id="weather"
            checked={layers.weather}
            onCheckedChange={() => handleToggle("weather")}
          />
        </div>
      </CardContent>
    </Card>
  );
}
