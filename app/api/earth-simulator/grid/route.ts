import { NextRequest, NextResponse } from "next/server";
import { calculateGridCells, getViewportFromCenter, type Viewport } from "@/lib/earth-simulator/grid-calculator";

/**
 * Grid Data API
 * 
 * Returns grid cell data for a given viewport and zoom level.
 */

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  
  const centerLat = parseFloat(searchParams.get("lat") || "0");
  const centerLon = parseFloat(searchParams.get("lon") || "0");
  const zoomLevel = parseInt(searchParams.get("zoom") || "10");
  const width = parseInt(searchParams.get("width") || "1920");
  const height = parseInt(searchParams.get("height") || "1080");

  try {
    // Calculate viewport from center point
    const viewport = getViewportFromCenter(centerLat, centerLon, zoomLevel, width, height);
    
    // Calculate grid cells
    const gridCells = calculateGridCells(viewport, zoomLevel);

    return NextResponse.json({
      success: true,
      viewport,
      zoomLevel,
      gridCells: gridCells.map((cell) => ({
        id: cell.id,
        centerLat: cell.centerLat,
        centerLon: cell.centerLon,
        bounds: {
          north: cell.north,
          south: cell.south,
          east: cell.east,
          west: cell.west,
        },
        zoomLevel: cell.zoomLevel,
        sizeMeters: cell.sizeMeters,
      })),
      count: gridCells.length,
    });
  } catch (error) {
    console.error("Grid calculation error:", error);
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
    const { viewport, zoomLevel } = body as { viewport: Viewport; zoomLevel: number };

    if (!viewport || !zoomLevel) {
      return NextResponse.json(
        { success: false, error: "viewport and zoomLevel required" },
        { status: 400 }
      );
    }

    const gridCells = calculateGridCells(viewport, zoomLevel);

    return NextResponse.json({
      success: true,
      viewport,
      zoomLevel,
      gridCells: gridCells.map((cell) => ({
        id: cell.id,
        centerLat: cell.centerLat,
        centerLon: cell.centerLon,
        bounds: {
          north: cell.north,
          south: cell.south,
          east: cell.east,
          west: cell.west,
        },
        zoomLevel: cell.zoomLevel,
        sizeMeters: cell.sizeMeters,
      })),
      count: gridCells.length,
    });
  } catch (error) {
    console.error("Grid calculation error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
