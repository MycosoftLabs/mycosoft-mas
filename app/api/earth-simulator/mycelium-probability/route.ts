import { NextRequest, NextResponse } from "next/server";
import { calculateMyceliumProbability } from "@/lib/earth-simulator/mycelium-model";
import { getCellId, type GridCell } from "@/lib/earth-simulator/grid-calculator";
import { inaturalistClient } from "@/lib/inaturalist-client";

/**
 * Mycelium Probability API
 * 
 * Calculates mycelium probability for grid cells based on:
 * - iNaturalist observations
 * - Environmental data
 * - Habitat suitability
 */

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  
  const lat = parseFloat(searchParams.get("lat") || "0");
  const lon = parseFloat(searchParams.get("lon") || "0");
  const zoomLevel = parseInt(searchParams.get("zoom") || "15");
  const radius = parseFloat(searchParams.get("radius") || "100"); // meters

  try {
    // Get cell ID
    const cellId = getCellId(lat, lon, zoomLevel);
    
    // Create grid cell object
    const gridSizeMeters = 0.3048; // 1ft
    const latStep = gridSizeMeters / 111320;
    const lonStep = gridSizeMeters / (111320 * Math.cos((lat * Math.PI) / 180));
    const cellLat = Math.floor(lat / latStep) * latStep + latStep / 2;
    const cellLon = Math.floor(lon / lonStep) * lonStep + lonStep / 2;

    const cell: GridCell = {
      id: cellId,
      centerLat: cellLat,
      centerLon: cellLon,
      north: cellLat + latStep / 2,
      south: cellLat - latStep / 2,
      east: cellLon + lonStep / 2,
      west: cellLon - lonStep / 2,
      zoomLevel,
      sizeMeters: gridSizeMeters,
    };

    // Fetch iNaturalist observations for this area
    const observations = await inaturalistClient.getFungalObservations({
      lat: cell.centerLat,
      lng: cell.centerLon,
      radius: radius,
      per_page: 200,
    });

    // Prepare cell data
    const cellData = {
      observations: observations.map((obs) => ({
        id: obs.id,
        species: obs.species_guess || obs.taxon?.name,
        observed_on: obs.observed_on,
        latitude: obs.latitude,
        longitude: obs.longitude,
      })),
      // TODO: Fetch from other APIs
      vegetationIndex: undefined,
      temperature: undefined,
      humidity: undefined,
      soilPH: undefined,
      elevation: undefined,
    };

    // Calculate probability
    const result = calculateMyceliumProbability(cell, cellData);

    return NextResponse.json({
      success: true,
      cellId,
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
      observationCount: observations.length,
    });
  } catch (error) {
    console.error("Mycelium probability calculation error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { cells, environmentalData } = body;

    if (!Array.isArray(cells)) {
      return NextResponse.json(
        { success: false, error: "cells must be an array" },
        { status: 400 }
      );
    }

    // Calculate probabilities for multiple cells
    const results = await Promise.all(
      cells.map(async (cell: GridCell) => {
        try {
          // Fetch observations
          const observations = await inaturalistClient.getFungalObservations({
            lat: cell.centerLat,
            lng: cell.centerLon,
            radius: 100, // 100m radius
            per_page: 200,
          });

          const cellData = {
            observations: observations.map((obs) => ({
              id: obs.id,
              species: obs.species_guess || obs.taxon?.name,
              observed_on: obs.observed_on,
              latitude: obs.latitude,
              longitude: obs.longitude,
            })),
            ...(environmentalData?.[cell.id] || {}),
          };

          const result = calculateMyceliumProbability(cell, cellData);
          return {
            cellId: cell.id,
            ...result,
            observationCount: observations.length,
          };
        } catch (error) {
          console.error(`Error calculating probability for cell ${cell.id}:`, error);
          return {
            cellId: cell.id,
            probability: 0,
            density: "none" as const,
            confidence: 0,
            error: error instanceof Error ? error.message : "Unknown error",
          };
        }
      })
    );

    return NextResponse.json({
      success: true,
      results,
      count: results.length,
    });
  } catch (error) {
    console.error("Batch probability calculation error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
