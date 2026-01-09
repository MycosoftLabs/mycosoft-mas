import { NextRequest, NextResponse } from "next/server";

/**
 * Individual Cell Data API
 * 
 * Returns detailed data for a specific grid cell.
 */

export async function GET(
  request: NextRequest,
  { params }: { params: { cellId: string } }
) {
  const { cellId } = params;

  try {
    // Parse cell ID (format: lat_lon_zoom)
    const [lat, lon, zoom] = cellId.split("_").map(parseFloat);

    if (isNaN(lat) || isNaN(lon) || isNaN(zoom)) {
      return NextResponse.json(
        { success: false, error: "Invalid cell ID format" },
        { status: 400 }
      );
    }

    // Fetch comprehensive data for this cell
    const [probResponse, obsResponse] = await Promise.all([
      fetch(
        `${request.nextUrl.origin}/api/earth-simulator/mycelium-probability?lat=${lat}&lon=${lon}&zoom=${zoom}`
      ),
      fetch(
        `${request.nextUrl.origin}/api/earth-simulator/inaturalist?action=fungi&lat=${lat}&lng=${lon}&radius=100`
      ),
    ]);

    const probData = await probResponse.json();
    const obsData = await obsResponse.json();

    return NextResponse.json({
      success: true,
      cellId,
      cell: {
        centerLat: lat,
        centerLon: lon,
        zoomLevel: zoom,
      },
      probability: probData.probability || null,
      observations: obsData.observations || [],
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Cell data error:", error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
