"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface StatisticsProps {
  probability?: any;
  observations?: any[];
}

export function Statistics({ probability, observations }: StatisticsProps) {
  return (
    <Card className="bg-gray-800 border-gray-700">
      <CardHeader>
        <CardTitle className="text-sm text-white">Statistics</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {probability?.factors && (
          <>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Observations</span>
              <span className="text-white">{probability.factors.observationCount}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Species Diversity</span>
              <span className="text-white">{probability.factors.speciesDiversity}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Habitat Suitability</span>
              <span className="text-white">
                {(probability.factors.habitatSuitability * 100).toFixed(0)}%
              </span>
            </div>
          </>
        )}
        {observations && (
          <div className="flex justify-between text-sm">
            <span className="text-gray-400">Total Observations</span>
            <span className="text-white">{observations.length}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
