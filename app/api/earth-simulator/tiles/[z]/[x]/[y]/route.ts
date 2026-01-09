import { NextRequest, NextResponse } from "next/server";

/**
 * Tile-based Data API
 * 
 * Returns data for a specific tile coordinate (z/x/y).
 * Used for efficient tile-based loading.
 */

export async function GET(
  request: NextRequest,
  { params }: { params: { z: string; x: string; y: string } }
) {
  const { z, x, y } = params;
  const zoom = parseInt(z);
  const tileX = parseInt(x);
  const tileY = parseInt(y);

  try {
    // Convert tile coordinates to lat/lon bounds
    const n = Math.pow(2, zoom);
    const west = (tileX / n) * 360 - 180;
    const east = ((tileX + 1) / n) * 360 - 180;
    const north = Math.atan(Math.sinh(Math.PI * (1 - (2 * tileY) / n))) * (180 / Math.PI);
    const south = Math.atan(Math.sinh(Math.PI * (1 - (2 * (tileY + 1)) / n))) * (180 / Math.PI);

    // Fetch data for this tile
    // In production, this would:
    // 1. Check cache (Redis)
    // 2. Query database for grid cells in this tile
    // 3. Aggregate probability data
    // 4. Return tile data

    return NextResponse.json({
      success: true,
      tile: { z: zoom, x: tileX, y: tileY },
      bounds: { north, south, east, west },
      gridCells: [], // Would contain grid cell data
      probabilities: [], // Would contain mycelium probabilities
      observations: [], // Would contain iNaturalist observations
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Tile data error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
