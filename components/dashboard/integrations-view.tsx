"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  Sun,
  Cloud,
  Activity,
  DollarSign,
  Zap,
  Globe,
  Satellite,
  Waves,
  Wind,
  Thermometer,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  RefreshCw,
  ExternalLink,
  Database,
  Workflow,
  Radio,
  Shield,
} from "lucide-react";

interface IntegrationCategory {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  integrations: Integration[];
}

interface Integration {
  id: string;
  name: string;
  status: "active" | "inactive" | "pending" | "error";
  category: string;
  description: string;
  lastCheck?: string;
  apiKeyRequired: boolean;
  hasApiKey: boolean;
  actions: string[];
}

export function IntegrationsView() {
  const [activeCategory, setActiveCategory] = useState("all");
  const [loading, setLoading] = useState(false);
  const [categories] = useState<IntegrationCategory[]>([
    {
      id: "space_weather",
      name: "Space & Weather",
      description: "Solar activity, space weather, and atmospheric data",
      icon: <Satellite className="h-5 w-5" />,
      color: "text-yellow-500",
      integrations: [
        { id: "nasa_donki", name: "NASA DONKI", status: "active", category: "space_weather", description: "Coronal Mass Ejections, Solar Flares, Geomagnetic Storms", apiKeyRequired: true, hasApiKey: true, actions: ["cme", "flare", "geostorm"] },
        { id: "noaa_swpc", name: "NOAA Space Weather", status: "active", category: "space_weather", description: "Real-time space weather data and forecasts", apiKeyRequired: false, hasApiKey: true, actions: ["solar_wind", "kp_index", "alerts"] },
        { id: "goes_satellite", name: "GOES Satellite", status: "active", category: "space_weather", description: "X-ray flux, proton flux, magnetometer data", apiKeyRequired: false, hasApiKey: true, actions: ["xray", "proton", "mag"] },
        { id: "noaa_weather", name: "NOAA Weather", status: "active", category: "space_weather", description: "Weather forecasts and alerts", apiKeyRequired: false, hasApiKey: true, actions: ["forecast", "alerts"] },
        { id: "soho", name: "SOHO Solar Observatory", status: "active", category: "space_weather", description: "Solar and heliospheric observation", apiKeyRequired: false, hasApiKey: true, actions: ["lasco", "eit", "mdi"] },
        { id: "stereo", name: "STEREO A/B", status: "active", category: "space_weather", description: "Solar Terrestrial Relations Observatory", apiKeyRequired: false, hasApiKey: true, actions: ["secchi", "impact"] },
      ],
    },
    {
      id: "environmental",
      name: "Environmental",
      description: "Air quality, pollution, and radiation monitoring",
      icon: <Wind className="h-5 w-5" />,
      color: "text-cyan-500",
      integrations: [
        { id: "openaq", name: "OpenAQ", status: "active", category: "environmental", description: "Global air quality data", apiKeyRequired: true, hasApiKey: false, actions: ["measurements", "locations", "latest"] },
        { id: "epa_airnow", name: "EPA AirNow", status: "pending", category: "environmental", description: "US air quality index", apiKeyRequired: true, hasApiKey: false, actions: ["current", "forecast"] },
        { id: "purpleair", name: "PurpleAir", status: "pending", category: "environmental", description: "Real-time PM2.5 sensors", apiKeyRequired: true, hasApiKey: false, actions: ["sensors", "data"] },
        { id: "safecast", name: "Safecast Radiation", status: "active", category: "environmental", description: "Global radiation monitoring", apiKeyRequired: false, hasApiKey: true, actions: ["measurements", "devices"] },
        { id: "breezometer", name: "BreezoMeter", status: "pending", category: "environmental", description: "Air quality and pollen", apiKeyRequired: true, hasApiKey: false, actions: ["air_quality", "pollen"] },
      ],
    },
    {
      id: "earth_science",
      name: "Earth Science",
      description: "Earthquakes, tides, water levels, and geophysics",
      icon: <Activity className="h-5 w-5" />,
      color: "text-orange-500",
      integrations: [
        { id: "usgs_earthquake", name: "USGS Earthquake", status: "active", category: "earth_science", description: "Real-time earthquake data worldwide", apiKeyRequired: false, hasApiKey: true, actions: ["query", "count", "catalogs"] },
        { id: "noaa_tides", name: "NOAA Tides", status: "active", category: "earth_science", description: "Tide predictions and water levels", apiKeyRequired: false, hasApiKey: true, actions: ["predictions", "water_level", "currents"] },
        { id: "ndbc_buoys", name: "NDBC Buoys", status: "active", category: "earth_science", description: "Ocean buoy observations", apiKeyRequired: false, hasApiKey: true, actions: ["stdmet", "ocean", "spec"] },
        { id: "usgs_water", name: "USGS Water Services", status: "active", category: "earth_science", description: "Streamflow and groundwater", apiKeyRequired: false, hasApiKey: true, actions: ["iv", "dv", "gwlevels"] },
        { id: "iris_seismic", name: "IRIS Seismic", status: "active", category: "earth_science", description: "Seismological data", apiKeyRequired: false, hasApiKey: true, actions: ["event", "station"] },
      ],
    },
    {
      id: "financial",
      name: "Financial Markets",
      description: "Cryptocurrency, stocks, and forex data",
      icon: <DollarSign className="h-5 w-5" />,
      color: "text-green-500",
      integrations: [
        { id: "coingecko", name: "CoinGecko", status: "active", category: "financial", description: "Free cryptocurrency data", apiKeyRequired: false, hasApiKey: true, actions: ["prices", "markets", "coins"] },
        { id: "coinmarketcap", name: "CoinMarketCap", status: "pending", category: "financial", description: "Cryptocurrency rankings", apiKeyRequired: true, hasApiKey: false, actions: ["listings", "quotes", "info"] },
        { id: "alpha_vantage", name: "Alpha Vantage", status: "pending", category: "financial", description: "Stock and forex data", apiKeyRequired: true, hasApiKey: false, actions: ["quote", "daily", "forex"] },
        { id: "finnhub", name: "Finnhub", status: "pending", category: "financial", description: "Stock quotes and news", apiKeyRequired: true, hasApiKey: false, actions: ["quote", "news", "candles"] },
        { id: "polygon", name: "Polygon.io", status: "pending", category: "financial", description: "Market data APIs", apiKeyRequired: true, hasApiKey: false, actions: ["aggs", "trades", "quotes"] },
      ],
    },
    {
      id: "automation",
      name: "Automation",
      description: "Workflow automation and webhooks",
      icon: <Workflow className="h-5 w-5" />,
      color: "text-purple-500",
      integrations: [
        { id: "n8n", name: "n8n", status: "active", category: "automation", description: "Local workflow automation", apiKeyRequired: true, hasApiKey: true, actions: ["workflows", "executions", "webhooks"] },
        { id: "zapier", name: "Zapier", status: "pending", category: "automation", description: "Cloud automation", apiKeyRequired: true, hasApiKey: false, actions: ["trigger", "action"] },
        { id: "ifttt", name: "IFTTT", status: "pending", category: "automation", description: "If This Then That", apiKeyRequired: true, hasApiKey: false, actions: ["trigger"] },
        { id: "make", name: "Make (Integromat)", status: "pending", category: "automation", description: "Visual automation", apiKeyRequired: true, hasApiKey: false, actions: ["webhook", "scenario"] },
      ],
    },
    {
      id: "analytics",
      name: "Analytics",
      description: "Data analysis and tracking",
      icon: <Database className="h-5 w-5" />,
      color: "text-blue-500",
      integrations: [
        { id: "amplitude", name: "Amplitude", status: "pending", category: "analytics", description: "Product analytics", apiKeyRequired: true, hasApiKey: false, actions: ["events", "users", "cohorts"] },
        { id: "mixpanel", name: "Mixpanel", status: "pending", category: "analytics", description: "User analytics", apiKeyRequired: true, hasApiKey: false, actions: ["events", "funnels"] },
        { id: "wolfram", name: "Wolfram Alpha", status: "pending", category: "analytics", description: "Computational intelligence", apiKeyRequired: true, hasApiKey: false, actions: ["query", "short"] },
      ],
    },
    {
      id: "defense",
      name: "Defense & Government",
      description: "Restricted access integrations",
      icon: <Shield className="h-5 w-5" />,
      color: "text-red-500",
      integrations: [
        { id: "palantir", name: "Palantir Foundry", status: "inactive", category: "defense", description: "Enterprise data platform", apiKeyRequired: true, hasApiKey: false, actions: ["datasets", "ontology"] },
        { id: "anduril", name: "Anduril SDK", status: "inactive", category: "defense", description: "Defense technology", apiKeyRequired: true, hasApiKey: false, actions: ["sensors", "assets"] },
        { id: "platform_one", name: "Platform One", status: "inactive", category: "defense", description: "DoD DevSecOps", apiKeyRequired: true, hasApiKey: false, actions: ["auth", "deploy"] },
      ],
    },
  ]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "active":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case "error":
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <XCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge className="bg-green-500/10 text-green-500">Active</Badge>;
      case "pending":
        return <Badge className="bg-yellow-500/10 text-yellow-500">Setup Required</Badge>;
      case "error":
        return <Badge className="bg-red-500/10 text-red-500">Error</Badge>;
      default:
        return <Badge className="bg-gray-500/10 text-gray-500">Inactive</Badge>;
    }
  };

  const filteredCategories = activeCategory === "all" 
    ? categories 
    : categories.filter(c => c.id === activeCategory);

  const totalActive = categories.reduce(
    (sum, cat) => sum + cat.integrations.filter(i => i.status === "active").length,
    0
  );
  const totalIntegrations = categories.reduce(
    (sum, cat) => sum + cat.integrations.length,
    0
  );

  return (
    <div className="h-full overflow-auto p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Global Integrations</h1>
          <p className="text-gray-400">
            {totalActive} of {totalIntegrations} integrations active
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            className="border-gray-700"
            onClick={() => setLoading(true)}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh All
          </Button>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
            <Zap className="mr-2 h-4 w-4" />
            Import Workflows
          </Button>
        </div>
      </div>

      {/* Category Filter */}
      <div className="mb-6 flex flex-wrap gap-2">
        <Button
          variant={activeCategory === "all" ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveCategory("all")}
          className={activeCategory === "all" ? "" : "border-gray-700"}
        >
          All Categories
        </Button>
        {categories.map((cat) => (
          <Button
            key={cat.id}
            variant={activeCategory === cat.id ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveCategory(cat.id)}
            className={activeCategory === cat.id ? "" : "border-gray-700"}
          >
            <span className={cat.color}>{cat.icon}</span>
            <span className="ml-2">{cat.name}</span>
            <Badge className="ml-2 bg-gray-700 text-xs">
              {cat.integrations.filter(i => i.status === "active").length}
            </Badge>
          </Button>
        ))}
      </div>

      {/* Integration Cards */}
      <div className="grid gap-6">
        {filteredCategories.map((category) => (
          <Card key={category.id} className="border-gray-800 bg-[#1E293B]">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2">
                <span className={category.color}>{category.icon}</span>
                {category.name}
                <Badge className="ml-2 bg-blue-500/10 text-blue-500">
                  {category.integrations.filter(i => i.status === "active").length}/
                  {category.integrations.length}
                </Badge>
              </CardTitle>
              <p className="text-sm text-gray-400">{category.description}</p>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {category.integrations.map((integration) => (
                  <div
                    key={integration.id}
                    className="rounded-lg border border-gray-700 bg-[#0F172A] p-4 hover:border-gray-600"
                  >
                    <div className="mb-2 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(integration.status)}
                        <span className="font-medium">{integration.name}</span>
                      </div>
                      {getStatusBadge(integration.status)}
                    </div>
                    <p className="mb-3 text-xs text-gray-400">
                      {integration.description}
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {integration.actions.slice(0, 3).map((action) => (
                        <Badge
                          key={action}
                          variant="outline"
                          className="border-gray-700 text-[10px]"
                        >
                          {action}
                        </Badge>
                      ))}
                      {integration.actions.length > 3 && (
                        <Badge variant="outline" className="border-gray-700 text-[10px]">
                          +{integration.actions.length - 3}
                        </Badge>
                      )}
                    </div>
                    {integration.status === "pending" && (
                      <Button
                        size="sm"
                        variant="outline"
                        className="mt-3 w-full border-yellow-500/50 text-yellow-500 hover:bg-yellow-500/10"
                      >
                        Configure API Key
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* n8n Import Instructions */}
      <Card className="mt-6 border-gray-800 bg-[#1E293B]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Workflow className="h-5 w-5 text-purple-500" />
            Import Workflows to n8n
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg bg-[#0F172A] p-4">
            <p className="mb-4 text-sm text-gray-400">
              Run the import script to add all integration workflows to n8n:
            </p>
            <div className="rounded bg-gray-900 p-3 font-mono text-sm">
              <div className="text-gray-500"># Set your n8n API key</div>
              <div className="text-green-400">$env:N8N_API_KEY = "your_api_key"</div>
              <div className="mt-2 text-gray-500"># Run the import script</div>
              <div className="text-blue-400">cd n8n/scripts</div>
              <div className="text-blue-400">.\import-workflows.ps1</div>
            </div>
            <div className="mt-4 flex gap-4">
              <Button variant="outline" size="sm" className="border-gray-700">
                View Documentation
                <ExternalLink className="ml-2 h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" className="border-gray-700">
                Open n8n
                <ExternalLink className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default IntegrationsView;
