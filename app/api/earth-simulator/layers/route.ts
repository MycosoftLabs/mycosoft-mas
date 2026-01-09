import { NextRequest, NextResponse } from "next/server";

/**
 * Layer Data Aggregation API
 * 
 * Aggregates data from all sources for layer visualization.
 */

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  
  const bounds = {
    north: parseFloat(searchParams.get("north") || "0"),
    south: parseFloat(searchParams.get("south") || "0"),
    east: parseFloat(searchParams.get("east") || "0"),
    west: parseFloat(searchParams.get("west") || "0"),
  };
  const layers = searchParams.get("layers")?.split(",") || ["mycelium"];

  try {
    const layerData: Record<string, any> = {};

    // Fetch data for each requested layer
    for (const layer of layers) {
      switch (layer) {
        case "mycelium":
          // Fetch mycelium probability data
          // This would aggregate from multiple grid cells
          layerData.mycelium = {
            type: "probability",
            data: [], // Would contain grid cell probabilities
          };
          break;

        case "heat":
          // Fetch temperature/heat data from NASA/NOAA
          layerData.heat = {
            type: "temperature",
            data: [], // Would contain temperature data
          };
          break;

        case "organisms":
          // Fetch organism observations from iNaturalist
          try {
            const obsResponse = await fetch(
              `${request.nextUrl.origin}/api/earth-simulator/inaturalist?action=bounds&nelat=${bounds.north}&nelng=${bounds.east}&swlat=${bounds.south}&swlng=${bounds.west}&per_page=100`
            );
            const obsData = await obsResponse.json();
            layerData.organisms = {
              type: "observations",
              data: obsData.observations || [],
            };
          } catch (error) {
            console.error("Error fetching organisms:", error);
            layerData.organisms = { type: "observations", data: [] };
          }
          break;

        case "weather":
          // Fetch weather data from NOAA
          layerData.weather = {
            type: "weather",
            data: [], // Would contain weather data
          };
          break;

        default:
          break;
      }
    }

    return NextResponse.json({
      success: true,
      bounds,
      layers: layerData,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Layer aggregation error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
