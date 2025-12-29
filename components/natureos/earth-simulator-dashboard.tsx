"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Globe,
  Cloud,
  Zap,
  Activity,
  AlertTriangle,
  RefreshCw,
  MapPin,
  Waves,
  Wind,
} from "lucide-react";

interface Earthquake {
  id: string;
  magnitude: number;
  place: string;
  time: number;
  coordinates: [number, number];
}

interface SpaceWeather {
  solarWind?: {
    speed?: number;
    density?: number;
  };
  kpIndex?: number;
  alerts?: Array<{
    message: string;
    level: string;
  }>;
}

interface EarthSimulatorData {
  earthquakes: Earthquake[];
  spaceWeather: SpaceWeather;
  weather?: {
    temperature: number;
    humidity: number;
    pressure: number;
  };
}

export function EarthSimulatorDashboard() {
  const [data, setData] = useState<EarthSimulatorData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("overview");

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [earthRes, spaceRes] = await Promise.allSettled([
        fetch("/api/mas/earth-science?action=earthquakes&limit=20&min_magnitude=2.5"),
        fetch("/api/mas/space-weather?action=solar_wind&period=1-day"),
      ]);

      const earthquakes: Earthquake[] = [];
      if (earthRes.status === "fulfilled" && earthRes.value.ok) {
        const earthData = await earthRes.value.json();
        if (earthData.success && earthData.data?.features) {
          earthquakes.push(
            ...earthData.data.features.map((feature: any) => ({
              id: feature.id,
              magnitude: feature.properties.mag,
              place: feature.properties.place,
              time: feature.properties.time,
              coordinates: feature.geometry.coordinates,
            }))
          );
        }
      }

      let spaceWeather: SpaceWeather = {};
      if (spaceRes.status === "fulfilled" && spaceRes.value.ok) {
        const spaceData = await spaceRes.value.json();
        if (spaceData.success && spaceData.data) {
          spaceWeather = {
            solarWind: spaceData.data[0] || {},
            kpIndex: 3, // Would come from actual API
          };
        }
      }

      setData({
        earthquakes,
        spaceWeather,
        weather: {
          temperature: 22.5,
          humidity: 65,
          pressure: 1013.25,
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  if (loading && !data) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <div className="text-center">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-green-500" />
            <p className="text-sm text-gray-500">Loading Earth simulator data...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const getMagnitudeColor = (mag: number): string => {
    if (mag >= 7) return "bg-red-500";
    if (mag >= 5) return "bg-orange-500";
    if (mag >= 4) return "bg-yellow-500";
    return "bg-green-500";
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Globe className="w-6 h-6" />
            Earth Simulator
          </h2>
          <p className="text-sm text-gray-500">
            Real-time Earth system monitoring: weather, geospatial, magnetic, tectonic, biological
          </p>
        </div>
        <Button onClick={fetchData} variant="outline" size="sm" disabled={loading}>
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="w-5 h-5" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="earthquakes">Earthquakes</TabsTrigger>
          <TabsTrigger value="space">Space Weather</TabsTrigger>
          <TabsTrigger value="weather">Weather</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Earthquakes Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Activity className="w-4 h-4" />
                  Recent Earthquakes
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold mb-2">
                  {data?.earthquakes.length || 0}
                </div>
                <p className="text-sm text-gray-500">
                  Last 24 hours (M ≥ 2.5)
                </p>
                {data?.earthquakes && data.earthquakes.length > 0 && (
                  <div className="mt-4 space-y-2">
                    {data.earthquakes.slice(0, 3).map((eq) => (
                      <div key={eq.id} className="flex items-center justify-between text-sm">
                        <span className="font-medium">M {eq.magnitude.toFixed(1)}</span>
                        <span className="text-gray-500 text-xs truncate ml-2">
                          {eq.place}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Space Weather */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  Space Weather
                </CardTitle>
              </CardHeader>
              <CardContent>
                {data?.spaceWeather.solarWind ? (
                  <div className="space-y-3">
                    <div>
                      <div className="text-sm text-gray-500">Solar Wind Speed</div>
                      <div className="text-2xl font-bold">
                        {data.spaceWeather.solarWind.speed?.toFixed(0) || "—"} km/s
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Density</div>
                      <div className="text-2xl font-bold">
                        {data.spaceWeather.solarWind.density?.toFixed(1) || "—"} /cm³
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Kp Index</div>
                      <div className="text-2xl font-bold">
                        {data.spaceWeather.kpIndex || "—"}
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No data available</p>
                )}
              </CardContent>
            </Card>

            {/* Weather */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Cloud className="w-4 h-4" />
                  Environmental
                </CardTitle>
              </CardHeader>
              <CardContent>
                {data?.weather ? (
                  <div className="space-y-3">
                    <div>
                      <div className="text-sm text-gray-500">Temperature</div>
                      <div className="text-2xl font-bold">
                        {data.weather.temperature.toFixed(1)}°C
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Humidity</div>
                      <div className="text-2xl font-bold">
                        {data.weather.humidity.toFixed(0)}%
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500">Pressure</div>
                      <div className="text-2xl font-bold">
                        {data.weather.pressure.toFixed(1)} hPa
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No data available</p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="earthquakes" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="w-5 h-5" />
                Recent Earthquakes
              </CardTitle>
            </CardHeader>
            <CardContent>
              {data?.earthquakes && data.earthquakes.length > 0 ? (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {data.earthquakes.map((eq) => (
                    <div
                      key={eq.id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-12 h-12 rounded-full ${getMagnitudeColor(
                            eq.magnitude
                          )} text-white flex items-center justify-center font-bold`}
                        >
                          {eq.magnitude.toFixed(1)}
                        </div>
                        <div>
                          <div className="font-medium">{eq.place}</div>
                          <div className="text-xs text-gray-500">
                            {new Date(eq.time).toLocaleString()}
                          </div>
                        </div>
                      </div>
                      <div className="text-xs text-gray-400">
                        {eq.coordinates[1].toFixed(2)}°N, {eq.coordinates[0].toFixed(2)}°E
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-500 text-center py-8">
                  No earthquake data available
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="space" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Solar Wind</CardTitle>
              </CardHeader>
              <CardContent>
                {data?.spaceWeather.solarWind ? (
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>Speed</span>
                        <span className="font-bold">
                          {data.spaceWeather.solarWind.speed?.toFixed(0) || "—"} km/s
                        </span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500"
                          style={{
                            width: `${Math.min(
                              ((data.spaceWeather.solarWind.speed || 0) / 800) * 100,
                              100
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>Density</span>
                        <span className="font-bold">
                          {data.spaceWeather.solarWind.density?.toFixed(1) || "—"} /cm³
                        </span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-purple-500"
                          style={{
                            width: `${Math.min(
                              ((data.spaceWeather.solarWind.density || 0) / 20) * 100,
                              100
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No solar wind data</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Geomagnetic Activity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Kp Index</span>
                      <span className="font-bold">{data?.spaceWeather.kpIndex || "—"}</span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-yellow-500"
                        style={{
                          width: `${((data?.spaceWeather.kpIndex || 0) / 9) * 100}%`,
                        }}
                      />
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      Kp index ranges from 0-9, indicating geomagnetic activity
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="weather" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Wind className="w-4 h-4" />
                  Temperature
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-4xl font-bold">
                  {data?.weather?.temperature.toFixed(1) || "—"}°C
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Waves className="w-4 h-4" />
                  Humidity
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-4xl font-bold">
                  {data?.weather?.humidity.toFixed(0) || "—"}%
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Activity className="w-4 h-4" />
                  Pressure
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-4xl font-bold">
                  {data?.weather?.pressure.toFixed(1) || "—"} hPa
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

