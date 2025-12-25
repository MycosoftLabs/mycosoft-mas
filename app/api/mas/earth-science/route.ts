import { NextRequest, NextResponse } from "next/server";

interface EarthScienceRequest {
  action: string;
  params?: {
    start_time?: string;
    end_time?: string;
    min_magnitude?: number;
    max_magnitude?: number;
    lat?: number;
    lon?: number;
    radius_km?: number;
    limit?: number;
    station_id?: string;
    begin_date?: string;
    end_date?: string;
    site_id?: string;
    state?: string;
    period?: string;
  };
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const action = searchParams.get("action") || "earthquakes";
  const limit = parseInt(searchParams.get("limit") || "100");
  const minMagnitude = parseFloat(searchParams.get("min_magnitude") || "2.5");

  try {
    let data;

    switch (action) {
      case "earthquakes":
        data = await fetchEarthquakes({ min_magnitude: minMagnitude, limit });
        break;
      case "earthquake_count":
        data = await fetchEarthquakeCount(minMagnitude);
        break;
      case "tide_stations":
        data = await fetchTideStations(searchParams.get("state"));
        break;
      default:
        data = await fetchEarthquakes({ min_magnitude: minMagnitude, limit });
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
    const body: EarthScienceRequest = await request.json();
    const { action, params } = body;

    let data;

    switch (action) {
      case "earthquakes":
        data = await fetchEarthquakes(params);
        break;
      case "tide_predictions":
        if (!params?.station_id) {
          return NextResponse.json(
            { success: false, error: "station_id required" },
            { status: 400 }
          );
        }
        data = await fetchTidePredictions({
          station_id: params.station_id,
          begin_date: params.begin_date,
          end_date: params.end_date,
        });
        break;
      case "water_levels":
        if (!params?.station_id) {
          return NextResponse.json(
            { success: false, error: "station_id required" },
            { status: 400 }
          );
        }
        data = await fetchWaterLevels({
          station_id: params.station_id,
          begin_date: params.begin_date,
          end_date: params.end_date,
        });
        break;
      case "streamflow":
        data = await fetchStreamflow(params);
        break;
      case "buoy_data":
        if (!params?.station_id) {
          return NextResponse.json(
            { success: false, error: "station_id required" },
            { status: 400 }
          );
        }
        data = await fetchBuoyData(params.station_id);
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

async function fetchEarthquakes(params?: {
  start_time?: string;
  end_time?: string;
  min_magnitude?: number;
  max_magnitude?: number;
  lat?: number;
  lon?: number;
  radius_km?: number;
  limit?: number;
}) {
  const url = new URL("https://earthquake.usgs.gov/fdsnws/event/1/query");
  url.searchParams.set("format", "geojson");
  url.searchParams.set("minmagnitude", (params?.min_magnitude || 2.5).toString());
  url.searchParams.set("limit", (params?.limit || 100).toString());

  if (params?.start_time) url.searchParams.set("starttime", params.start_time);
  if (params?.end_time) url.searchParams.set("endtime", params.end_time);
  if (params?.max_magnitude)
    url.searchParams.set("maxmagnitude", params.max_magnitude.toString());
  if (params?.lat && params?.lon) {
    url.searchParams.set("latitude", params.lat.toString());
    url.searchParams.set("longitude", params.lon.toString());
    if (params?.radius_km)
      url.searchParams.set("maxradiuskm", params.radius_km.toString());
  }

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`USGS API error: ${response.status}`);
  return response.json();
}

async function fetchEarthquakeCount(minMagnitude: number) {
  const url = new URL("https://earthquake.usgs.gov/fdsnws/event/1/count");
  url.searchParams.set("format", "text");
  url.searchParams.set("minmagnitude", minMagnitude.toString());

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`USGS API error: ${response.status}`);
  const count = await response.text();
  return { count: parseInt(count.trim()) };
}

async function fetchTideStations(state: string | null) {
  const url = new URL(
    "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json"
  );
  url.searchParams.set("type", "tidepredictions");
  url.searchParams.set("units", "metric");

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`NOAA API error: ${response.status}`);
  const data = await response.json();

  if (state && data.stations) {
    data.stations = data.stations.filter(
      (s: { state?: string }) => s.state?.toUpperCase() === state.toUpperCase()
    );
  }

  return data;
}

async function fetchTidePredictions(params: {
  station_id: string;
  begin_date?: string;
  end_date?: string;
}) {
  const url = new URL(
    "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
  );
  url.searchParams.set("product", "predictions");
  url.searchParams.set("application", "MycoSoft_MAS");
  url.searchParams.set("station", params.station_id);
  url.searchParams.set("datum", "MLLW");
  url.searchParams.set("units", "metric");
  url.searchParams.set("time_zone", "gmt");
  url.searchParams.set("format", "json");

  if (params.begin_date) url.searchParams.set("begin_date", params.begin_date);
  if (params.end_date) url.searchParams.set("end_date", params.end_date);

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`NOAA API error: ${response.status}`);
  return response.json();
}

async function fetchWaterLevels(params: {
  station_id: string;
  begin_date?: string;
  end_date?: string;
}) {
  const url = new URL(
    "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
  );
  url.searchParams.set("product", "water_level");
  url.searchParams.set("application", "MycoSoft_MAS");
  url.searchParams.set("station", params.station_id);
  url.searchParams.set("datum", "MLLW");
  url.searchParams.set("units", "metric");
  url.searchParams.set("time_zone", "gmt");
  url.searchParams.set("format", "json");

  if (params.begin_date) url.searchParams.set("begin_date", params.begin_date);
  if (params.end_date) url.searchParams.set("end_date", params.end_date);

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`NOAA API error: ${response.status}`);
  return response.json();
}

async function fetchStreamflow(params?: {
  site_id?: string;
  state?: string;
  period?: string;
}) {
  const url = new URL("https://waterservices.usgs.gov/nwis/iv/");
  url.searchParams.set("format", "json");
  url.searchParams.set("parameterCd", "00060"); // Discharge
  url.searchParams.set("period", params?.period || "P7D");

  if (params?.site_id) url.searchParams.set("sites", params.site_id);
  if (params?.state) url.searchParams.set("stateCd", params.state);

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`USGS API error: ${response.status}`);
  return response.json();
}

async function fetchBuoyData(stationId: string) {
  const response = await fetch(
    `https://www.ndbc.noaa.gov/data/realtime2/${stationId}.txt`
  );
  if (!response.ok) throw new Error(`NDBC API error: ${response.status}`);
  const text = await response.text();

  // Parse the buoy data text format
  const lines = text.trim().split("\n");
  const headers = lines[0].replace(/#/g, "").trim().split(/\s+/);
  const units = lines[1].replace(/#/g, "").trim().split(/\s+/);
  const data = lines.slice(2).map((line) => {
    const values = line.trim().split(/\s+/);
    const row: Record<string, string> = {};
    headers.forEach((header, i) => {
      row[header] = values[i];
    });
    return row;
  });

  return { station_id: stationId, headers, units, data: data.slice(0, 24) };
}
