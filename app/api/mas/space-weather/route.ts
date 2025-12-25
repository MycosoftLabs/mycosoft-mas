import { NextRequest, NextResponse } from "next/server";

const NASA_API_KEY = process.env.NASA_API_KEY || "DEMO_KEY";
const NOAA_SWPC_URL = "https://services.swpc.noaa.gov";

interface SpaceWeatherRequest {
  action: string;
  params?: {
    start_date?: string;
    end_date?: string;
    period?: string;
  };
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const action = searchParams.get("action") || "solar_wind";
  const period = searchParams.get("period") || "1-day";

  try {
    let data;

    switch (action) {
      case "solar_wind":
        data = await fetchSolarWind(period);
        break;
      case "kp_index":
        data = await fetchKpIndex();
        break;
      case "xray_flux":
        data = await fetchXrayFlux();
        break;
      case "alerts":
        data = await fetchSpaceWeatherAlerts();
        break;
      case "aurora":
        data = await fetchAuroraForecast();
        break;
      default:
        data = await fetchSolarWind(period);
    }

    return NextResponse.json({
      success: true,
      action,
      data,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: SpaceWeatherRequest = await request.json();
    const { action, params } = body;

    let data;

    switch (action) {
      case "cme":
        data = await fetchNasaDonki("CME", params);
        break;
      case "flares":
        data = await fetchNasaDonki("FLR", params);
        break;
      case "geomagnetic_storms":
        data = await fetchNasaDonki("GST", params);
        break;
      case "neo_feed":
        data = await fetchNeoFeed(params);
        break;
      default:
        return NextResponse.json(
          { success: false, error: `Unknown action: ${action}` },
          { status: 400 }
        );
    }

    return NextResponse.json({
      success: true,
      action,
      data,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

async function fetchSolarWind(period: string) {
  const response = await fetch(
    `${NOAA_SWPC_URL}/products/solar-wind/plasma-${period}.json`
  );
  if (!response.ok) throw new Error(`NOAA API error: ${response.status}`);
  return response.json();
}

async function fetchKpIndex() {
  const response = await fetch(
    `${NOAA_SWPC_URL}/products/noaa-planetary-k-index.json`
  );
  if (!response.ok) throw new Error(`NOAA API error: ${response.status}`);
  return response.json();
}

async function fetchXrayFlux() {
  const response = await fetch(
    `${NOAA_SWPC_URL}/json/goes/primary/xrays-7-day.json`
  );
  if (!response.ok) throw new Error(`NOAA API error: ${response.status}`);
  return response.json();
}

async function fetchSpaceWeatherAlerts() {
  const response = await fetch(`${NOAA_SWPC_URL}/products/alerts.json`);
  if (!response.ok) throw new Error(`NOAA API error: ${response.status}`);
  return response.json();
}

async function fetchAuroraForecast() {
  const response = await fetch(
    `${NOAA_SWPC_URL}/json/ovation_aurora_latest.json`
  );
  if (!response.ok) throw new Error(`NOAA API error: ${response.status}`);
  return response.json();
}

async function fetchNasaDonki(
  endpoint: string,
  params?: { start_date?: string; end_date?: string }
) {
  const url = new URL(`https://api.nasa.gov/DONKI/${endpoint}`);
  url.searchParams.set("api_key", NASA_API_KEY);
  if (params?.start_date) url.searchParams.set("startDate", params.start_date);
  if (params?.end_date) url.searchParams.set("endDate", params.end_date);

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`NASA API error: ${response.status}`);
  return response.json();
}

async function fetchNeoFeed(params?: {
  start_date?: string;
  end_date?: string;
}) {
  const url = new URL("https://api.nasa.gov/neo/rest/v1/feed");
  url.searchParams.set("api_key", NASA_API_KEY);
  if (params?.start_date) url.searchParams.set("start_date", params.start_date);
  if (params?.end_date) url.searchParams.set("end_date", params.end_date);

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`NASA API error: ${response.status}`);
  return response.json();
}
