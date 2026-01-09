import { NextRequest, NextResponse } from "next/server";
import { inaturalistClient } from "@/lib/inaturalist-client";
import { calculateMyceliumProbability } from "@/lib/earth-simulator/mycelium-model";
import { calculateGridCells, getViewportFromCenter } from "@/lib/earth-simulator/grid-calculator";

/**
 * Data Aggregation API
 * 
 * Aggregates data from all sources for a viewport and calculates probabilities.
 */

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { viewport, zoomLevel, centerLat, centerLon, width, height } = body;

    let actualViewport = viewport;
    if (!actualViewport && centerLat && centerLon && zoomLevel) {
      actualViewport = getViewportFromCenter(centerLat, centerLon, zoomLevel, width || 1920, height || 1080);
    }

    if (!actualViewport) {
      return NextResponse.json(
        { success: false, error: "viewport or center coordinates required" },
        { status: 400 }
      );
    }

    // Calculate grid cells
    const gridCells = calculateGridCells(actualViewport, zoomLevel || 15);

    // Fetch observations for the viewport
    const observations = await inaturalistClient.getObservationsInBounds({
      nelat: actualViewport.north,
      nelng: actualViewport.east,
      swlat: actualViewport.south,
      swlng: actualViewport.west,
      taxon_id: 47170, // Kingdom Fungi
      per_page: 500,
    });

    // Calculate probabilities for each grid cell
    const cellProbabilities = await Promise.all(
      gridCells.slice(0, 100).map(async (cell) => {
        // Find observations in this cell
        const cellObservations = observations.filter((obs) => {
          return (
            obs.latitude >= cell.south &&
            obs.latitude <= cell.north &&
            obs.longitude >= cell.west &&
            obs.longitude <= cell.east
          );
        });

        const cellData = {
          observations: cellObservations.map((obs) => ({
            id: obs.id,
            species: obs.species_guess || obs.taxon?.name,
            observed_on: obs.observed_on,
            latitude: obs.latitude,
            longitude: obs.longitude,
          })),
        };

        const result = calculateMyceliumProbability(cell, cellData);

        return {
          cellId: cell.id,
          cell: {
            centerLat: cell.centerLat,
            centerLon: cell.centerLon,
            bounds: {
              north: cell.north,
              south: cell.south,
              east: cell.east,
              west: cell.west,
            },
          },
          probability: result.probability,
          density: result.density,
          confidence: result.confidence,
          factors: result.factors,
          observationCount: cellObservations.length,
        };
      })
    );

    return NextResponse.json({
      success: true,
      viewport: actualViewport,
      zoomLevel: zoomLevel || 15,
      gridCells: gridCells.length,
      observations: observations.length,
      cellProbabilities,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Aggregation error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
