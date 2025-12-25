"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Sun,
  Cloud,
  Activity,
  DollarSign,
  Zap,
  Globe,
  Thermometer,
  Wind,
  Waves,
  TrendingUp,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";

interface SpaceWeatherData {
  kp_index?: number;
  solar_wind_speed?: number;
  solar_wind_density?: number;
  alerts?: Array<{ message: string; issue_time: string }>;
}

interface EnvironmentalData {
  aqi?: number;
  pm25?: number;
  pm10?: number;
  location?: string;
}

interface EarthquakeData {
  magnitude: number;
  place: string;
  time: number;
  depth: number;
}

interface CryptoPrice {
  id: string;
  symbol: string;
  current_price: number;
  price_change_24h: number;
  market_cap: number;
}

export function GlobalIntegrationsPanel() {
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [spaceWeather, setSpaceWeather] = useState<SpaceWeatherData | null>(null);
  const [environmental, setEnvironmental] = useState<EnvironmentalData | null>(null);
  const [earthquakes, setEarthquakes] = useState<EarthquakeData[]>([]);
  const [crypto, setCrypto] = useState<CryptoPrice[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    setLoading(true);
    await Promise.all([
      fetchSpaceWeather(),
      fetchEnvironmental(),
      fetchEarthquakes(),
      fetchCrypto(),
    ]);
    setLastUpdate(new Date());
    setLoading(false);
  };

  const fetchSpaceWeather = async () => {
    try {
      const response = await fetch("/api/mas/space-weather?action=kp_index");
      const data = await response.json();
      if (data.success && Array.isArray(data.data) && data.data.length > 1) {
        const latest = data.data[data.data.length - 1];
        setSpaceWeather({
          kp_index: parseFloat(latest[1]) || 0,
        });
      }
    } catch (error) {
      console.error("Failed to fetch space weather:", error);
    }
  };

  const fetchEnvironmental = async () => {
    try {
      const response = await fetch("/api/mas/environmental?action=countries");
      const data = await response.json();
      if (data.success) {
        setEnvironmental({ location: "Global", aqi: 50 }); // Placeholder
      }
    } catch (error) {
      console.error("Failed to fetch environmental data:", error);
    }
  };

  const fetchEarthquakes = async () => {
    try {
      const response = await fetch("/api/mas/earth-science?action=earthquakes&min_magnitude=4.5&limit=5");
      const data = await response.json();
      if (data.success && data.data?.features) {
        setEarthquakes(
          data.data.features.map((f: { properties: { mag: number; place: string; time: number }; geometry: { coordinates: number[] } }) => ({
            magnitude: f.properties.mag,
            place: f.properties.place,
            time: f.properties.time,
            depth: f.geometry.coordinates[2],
          }))
        );
      }
    } catch (error) {
      console.error("Failed to fetch earthquakes:", error);
    }
  };

  const fetchCrypto = async () => {
    try {
      const response = await fetch("/api/mas/financial?action=crypto_markets");
      const data = await response.json();
      if (data.success && Array.isArray(data.data)) {
        setCrypto(data.data.slice(0, 5));
      }
    } catch (error) {
      console.error("Failed to fetch crypto:", error);
    }
  };

  const getKpColor = (kp: number) => {
    if (kp <= 3) return "text-green-500";
    if (kp <= 5) return "text-yellow-500";
    if (kp <= 7) return "text-orange-500";
    return "text-red-500";
  };

  const getKpStatus = (kp: number) => {
    if (kp <= 3) return "Quiet";
    if (kp <= 5) return "Unsettled";
    if (kp <= 7) return "Storm";
    return "Severe Storm";
  };

  return (
    <Card className="border-gray-800 bg-[#1E293B]">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-2 text-lg font-semibold">
          <Globe className="h-5 w-5 text-blue-500" />
          Global Integrations
        </CardTitle>
        <div className="flex items-center gap-2">
          {lastUpdate && (
            <span className="text-xs text-gray-500">
              Updated: {lastUpdate.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={fetchAllData}
            disabled={loading}
            className="rounded p-1 hover:bg-gray-700"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-5 bg-[#0F172A]">
            <TabsTrigger value="overview" className="text-xs">Overview</TabsTrigger>
            <TabsTrigger value="space" className="text-xs">Space</TabsTrigger>
            <TabsTrigger value="earth" className="text-xs">Earth</TabsTrigger>
            <TabsTrigger value="env" className="text-xs">Env</TabsTrigger>
            <TabsTrigger value="finance" className="text-xs">Finance</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-4">
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              {/* Space Weather Card */}
              <div className="rounded-lg bg-[#0F172A] p-3">
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <Sun className="h-4 w-4 text-yellow-500" />
                  Space Weather
                </div>
                {spaceWeather ? (
                  <>
                    <div className={`text-xl font-bold ${getKpColor(spaceWeather.kp_index || 0)}`}>
                      Kp {spaceWeather.kp_index?.toFixed(0) || "N/A"}
                    </div>
                    <div className="text-xs text-gray-500">
                      {getKpStatus(spaceWeather.kp_index || 0)}
                    </div>
                  </>
                ) : (
                  <div className="text-sm text-gray-500">Loading...</div>
                )}
              </div>

              {/* Air Quality Card */}
              <div className="rounded-lg bg-[#0F172A] p-3">
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <Wind className="h-4 w-4 text-cyan-500" />
                  Air Quality
                </div>
                <div className="text-xl font-bold text-green-500">
                  {environmental?.aqi || "—"}
                </div>
                <div className="text-xs text-gray-500">AQI Index</div>
              </div>

              {/* Seismic Card */}
              <div className="rounded-lg bg-[#0F172A] p-3">
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <Activity className="h-4 w-4 text-orange-500" />
                  Seismic
                </div>
                {earthquakes.length > 0 ? (
                  <>
                    <div className="text-xl font-bold text-orange-500">
                      M{earthquakes[0].magnitude.toFixed(1)}
                    </div>
                    <div className="truncate text-xs text-gray-500">
                      {earthquakes[0].place}
                    </div>
                  </>
                ) : (
                  <div className="text-sm text-gray-500">No recent quakes</div>
                )}
              </div>

              {/* Crypto Card */}
              <div className="rounded-lg bg-[#0F172A] p-3">
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <DollarSign className="h-4 w-4 text-green-500" />
                  Bitcoin
                </div>
                {crypto.length > 0 ? (
                  <>
                    <div className="text-xl font-bold">
                      ${crypto[0].current_price?.toLocaleString() || "—"}
                    </div>
                    <div className={`text-xs ${crypto[0].price_change_24h >= 0 ? "text-green-500" : "text-red-500"}`}>
                      {crypto[0].price_change_24h >= 0 ? "+" : ""}
                      {crypto[0].price_change_24h?.toFixed(2)}%
                    </div>
                  </>
                ) : (
                  <div className="text-sm text-gray-500">Loading...</div>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="space" className="mt-4">
            <SpaceWeatherWidget data={spaceWeather} />
          </TabsContent>

          <TabsContent value="earth" className="mt-4">
            <EarthScienceWidget earthquakes={earthquakes} />
          </TabsContent>

          <TabsContent value="env" className="mt-4">
            <EnvironmentalWidget data={environmental} />
          </TabsContent>

          <TabsContent value="finance" className="mt-4">
            <FinancialWidget crypto={crypto} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

function SpaceWeatherWidget({ data }: { data: SpaceWeatherData | null }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg bg-[#0F172A] p-4">
          <div className="text-xs text-gray-400">Kp Index</div>
          <div className="text-3xl font-bold text-yellow-500">
            {data?.kp_index?.toFixed(0) || "—"}
          </div>
          <div className="text-xs text-gray-500">Geomagnetic Activity</div>
        </div>
        <div className="rounded-lg bg-[#0F172A] p-4">
          <div className="text-xs text-gray-400">Solar Wind</div>
          <div className="text-3xl font-bold text-blue-500">
            {data?.solar_wind_speed?.toFixed(0) || "—"}
          </div>
          <div className="text-xs text-gray-500">km/s</div>
        </div>
        <div className="rounded-lg bg-[#0F172A] p-4">
          <div className="text-xs text-gray-400">Density</div>
          <div className="text-3xl font-bold text-purple-500">
            {data?.solar_wind_density?.toFixed(1) || "—"}
          </div>
          <div className="text-xs text-gray-500">p/cm³</div>
        </div>
      </div>
      <div className="text-center text-xs text-gray-500">
        Data from NOAA Space Weather Prediction Center
      </div>
    </div>
  );
}

function EarthScienceWidget({ earthquakes }: { earthquakes: EarthquakeData[] }) {
  return (
    <div className="space-y-2">
      <div className="text-sm font-medium text-gray-400">Recent Earthquakes (M4.5+)</div>
      {earthquakes.length > 0 ? (
        earthquakes.map((eq, i) => (
          <div key={i} className="flex items-center justify-between rounded bg-[#0F172A] p-3">
            <div className="flex items-center gap-3">
              <div className={`text-lg font-bold ${
                eq.magnitude >= 6 ? "text-red-500" : 
                eq.magnitude >= 5 ? "text-orange-500" : "text-yellow-500"
              }`}>
                M{eq.magnitude.toFixed(1)}
              </div>
              <div>
                <div className="text-sm">{eq.place}</div>
                <div className="text-xs text-gray-500">
                  Depth: {eq.depth.toFixed(0)}km • {new Date(eq.time).toLocaleString()}
                </div>
              </div>
            </div>
          </div>
        ))
      ) : (
        <div className="text-center text-gray-500">No recent significant earthquakes</div>
      )}
      <div className="text-center text-xs text-gray-500">
        Data from USGS Earthquake Hazards Program
      </div>
    </div>
  );
}

function EnvironmentalWidget({ data }: { data: EnvironmentalData | null }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-lg bg-[#0F172A] p-4 text-center">
          <div className="text-xs text-gray-400">AQI</div>
          <div className="text-3xl font-bold text-green-500">{data?.aqi || "—"}</div>
          <div className="text-xs text-gray-500">Good</div>
        </div>
        <div className="rounded-lg bg-[#0F172A] p-4 text-center">
          <div className="text-xs text-gray-400">PM2.5</div>
          <div className="text-3xl font-bold text-blue-500">{data?.pm25 || "—"}</div>
          <div className="text-xs text-gray-500">µg/m³</div>
        </div>
        <div className="rounded-lg bg-[#0F172A] p-4 text-center">
          <div className="text-xs text-gray-400">PM10</div>
          <div className="text-3xl font-bold text-cyan-500">{data?.pm10 || "—"}</div>
          <div className="text-xs text-gray-500">µg/m³</div>
        </div>
        <div className="rounded-lg bg-[#0F172A] p-4 text-center">
          <div className="text-xs text-gray-400">Location</div>
          <div className="text-lg font-bold">{data?.location || "—"}</div>
          <div className="text-xs text-gray-500">Monitoring</div>
        </div>
      </div>
      <div className="text-center text-xs text-gray-500">
        Data from OpenAQ global air quality network
      </div>
    </div>
  );
}

function FinancialWidget({ crypto }: { crypto: CryptoPrice[] }) {
  return (
    <div className="space-y-2">
      <div className="text-sm font-medium text-gray-400">Top Cryptocurrencies</div>
      {crypto.length > 0 ? (
        crypto.map((coin) => (
          <div key={coin.id} className="flex items-center justify-between rounded bg-[#0F172A] p-3">
            <div className="flex items-center gap-3">
              <div className="text-lg font-bold uppercase">{coin.symbol}</div>
            </div>
            <div className="text-right">
              <div className="font-medium">${coin.current_price?.toLocaleString()}</div>
              <div className={`text-xs ${coin.price_change_24h >= 0 ? "text-green-500" : "text-red-500"}`}>
                {coin.price_change_24h >= 0 ? "+" : ""}
                {coin.price_change_24h?.toFixed(2)}%
              </div>
            </div>
          </div>
        ))
      ) : (
        <div className="text-center text-gray-500">Loading market data...</div>
      )}
      <div className="text-center text-xs text-gray-500">
        Data from CoinGecko
      </div>
    </div>
  );
}

export default GlobalIntegrationsPanel;
