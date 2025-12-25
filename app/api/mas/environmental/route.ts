import { NextRequest, NextResponse } from "next/server";

const OPENAQ_API_KEY = process.env.OPENAQ_API_KEY || "";
const AIRNOW_API_KEY = process.env.EPA_AIRNOW_API_KEY || "";

interface EnvironmentalRequest {
  action: string;
  params?: {
    lat?: number;
    lon?: number;
    country?: string;
    city?: string;
    zip_code?: string;
    limit?: number;
  };
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const action = searchParams.get("action") || "latest";
  const country = searchParams.get("country");
  const city = searchParams.get("city");
  const limit = parseInt(searchParams.get("limit") || "100");

  try {
    let data;

    switch (action) {
      case "latest":
        data = await fetchOpenAQLatest(country, city, limit);
        break;
      case "locations":
        data = await fetchOpenAQLocations(country, city, limit);
        break;
      case "countries":
        data = await fetchOpenAQCountries();
        break;
      default:
        data = await fetchOpenAQLatest(country, city, limit);
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
    const body: EnvironmentalRequest = await request.json();
    const { action, params } = body;

    let data;

    switch (action) {
      case "measurements":
        data = await fetchOpenAQMeasurements(params);
        break;
      case "airnow_current":
        if (!AIRNOW_API_KEY) {
          return NextResponse.json(
            { success: false, error: "EPA_AIRNOW_API_KEY not configured" },
            { status: 500 }
          );
        }
        data = await fetchAirNowCurrent(params);
        break;
      case "airnow_forecast":
        if (!AIRNOW_API_KEY) {
          return NextResponse.json(
            { success: false, error: "EPA_AIRNOW_API_KEY not configured" },
            { status: 500 }
          );
        }
        data = await fetchAirNowForecast(params);
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

async function fetchOpenAQLatest(
  country: string | null,
  city: string | null,
  limit: number
) {
  const url = new URL("https://api.openaq.org/v2/latest");
  url.searchParams.set("limit", limit.toString());
  if (country) url.searchParams.set("country", country);
  if (city) url.searchParams.set("city", city);

  const headers: Record<string, string> = {};
  if (OPENAQ_API_KEY) headers["X-API-Key"] = OPENAQ_API_KEY;

  const response = await fetch(url.toString(), { headers });
  if (!response.ok) throw new Error(`OpenAQ API error: ${response.status}`);
  return response.json();
}

async function fetchOpenAQLocations(
  country: string | null,
  city: string | null,
  limit: number
) {
  const url = new URL("https://api.openaq.org/v2/locations");
  url.searchParams.set("limit", limit.toString());
  if (country) url.searchParams.set("country", country);
  if (city) url.searchParams.set("city", city);

  const headers: Record<string, string> = {};
  if (OPENAQ_API_KEY) headers["X-API-Key"] = OPENAQ_API_KEY;

  const response = await fetch(url.toString(), { headers });
  if (!response.ok) throw new Error(`OpenAQ API error: ${response.status}`);
  return response.json();
}

async function fetchOpenAQCountries() {
  const url = new URL("https://api.openaq.org/v2/countries");

  const headers: Record<string, string> = {};
  if (OPENAQ_API_KEY) headers["X-API-Key"] = OPENAQ_API_KEY;

  const response = await fetch(url.toString(), { headers });
  if (!response.ok) throw new Error(`OpenAQ API error: ${response.status}`);
  return response.json();
}

async function fetchOpenAQMeasurements(params?: {
  country?: string;
  city?: string;
  limit?: number;
}) {
  const url = new URL("https://api.openaq.org/v2/measurements");
  url.searchParams.set("limit", (params?.limit || 100).toString());
  if (params?.country) url.searchParams.set("country", params.country);
  if (params?.city) url.searchParams.set("city", params.city);

  const headers: Record<string, string> = {};
  if (OPENAQ_API_KEY) headers["X-API-Key"] = OPENAQ_API_KEY;

  const response = await fetch(url.toString(), { headers });
  if (!response.ok) throw new Error(`OpenAQ API error: ${response.status}`);
  return response.json();
}

async function fetchAirNowCurrent(params?: {
  lat?: number;
  lon?: number;
  zip_code?: string;
}) {
  let url: URL;

  if (params?.zip_code) {
    url = new URL(
      "https://www.airnowapi.org/aq/observation/zipCode/current/"
    );
    url.searchParams.set("zipCode", params.zip_code);
  } else if (params?.lat && params?.lon) {
    url = new URL(
      "https://www.airnowapi.org/aq/observation/latLong/current/"
    );
    url.searchParams.set("latitude", params.lat.toString());
    url.searchParams.set("longitude", params.lon.toString());
  } else {
    throw new Error("Either zip_code or lat/lon required");
  }

  url.searchParams.set("format", "application/json");
  url.searchParams.set("API_KEY", AIRNOW_API_KEY);
  url.searchParams.set("distance", "25");

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`AirNow API error: ${response.status}`);
  return response.json();
}

async function fetchAirNowForecast(params?: { zip_code?: string }) {
  if (!params?.zip_code) {
    throw new Error("zip_code required for forecast");
  }

  const url = new URL("https://www.airnowapi.org/aq/forecast/zipCode/");
  url.searchParams.set("format", "application/json");
  url.searchParams.set("API_KEY", AIRNOW_API_KEY);
  url.searchParams.set("zipCode", params.zip_code);

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`AirNow API error: ${response.status}`);
  return response.json();
}
