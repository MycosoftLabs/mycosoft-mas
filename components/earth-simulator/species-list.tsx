"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

interface SpeciesListProps {
  observations?: any[];
}

export function SpeciesList({ observations }: SpeciesListProps) {
  if (!observations || observations.length === 0) {
    return null;
  }

  // Group by species
  const speciesMap = new Map<string, number>();
  observations.forEach((obs) => {
    const species = obs.species || "Unknown";
    speciesMap.set(species, (speciesMap.get(species) || 0) + 1);
  });

  const speciesList = Array.from(speciesMap.entries())
    .map(([species, count]) => ({ species, count }))
    .sort((a, b) => b.count - a.count);

  return (
    <Card className="bg-gray-800 border-gray-700">
      <CardHeader>
        <CardTitle className="text-sm text-white">Species Found</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-64">
          <div className="space-y-2">
            {speciesList.map((item, index) => (
              <div
                key={index}
                className="flex justify-between items-center text-sm p-2 bg-gray-700/50 rounded"
              >
                <span className="text-gray-300">{item.species}</span>
                <span className="text-white font-semibold">{item.count}</span>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
