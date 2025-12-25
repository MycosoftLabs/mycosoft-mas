"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertCircle,
  Zap,
  Database,
  Globe,
  Satellite,
  Cloud,
  Activity,
  DollarSign,
  Workflow,
} from "lucide-react";

interface IntegrationCategory {
  name: string;
  icon: React.ReactNode;
  integrations: Array<{
    name: string;
    status: "active" | "inactive" | "error" | "pending";
    lastCheck?: string;
  }>;
}

export function IntegrationStatusWidget() {
  const [categories, setCategories] = useState<IntegrationCategory[]>([
    {
      name: "Space & Weather",
      icon: <Satellite className="h-4 w-4 text-yellow-500" />,
      integrations: [
        { name: "NASA DONKI", status: "active" },
        { name: "NOAA SWPC", status: "active" },
        { name: "GOES Satellite", status: "active" },
        { name: "NOAA Weather", status: "active" },
      ],
    },
    {
      name: "Environmental",
      icon: <Cloud className="h-4 w-4 text-cyan-500" />,
      integrations: [
        { name: "OpenAQ", status: "active" },
        { name: "EPA AirNow", status: "pending" },
        { name: "PurpleAir", status: "pending" },
        { name: "Safecast", status: "active" },
      ],
    },
    {
      name: "Earth Science",
      icon: <Activity className="h-4 w-4 text-orange-500" />,
      integrations: [
        { name: "USGS Earthquake", status: "active" },
        { name: "NOAA Tides", status: "active" },
        { name: "NDBC Buoys", status: "active" },
        { name: "USGS Water", status: "active" },
      ],
    },
    {
      name: "Financial",
      icon: <DollarSign className="h-4 w-4 text-green-500" />,
      integrations: [
        { name: "CoinGecko", status: "active" },
        { name: "CoinMarketCap", status: "pending" },
        { name: "Alpha Vantage", status: "pending" },
        { name: "Finnhub", status: "pending" },
      ],
    },
    {
      name: "Automation",
      icon: <Workflow className="h-4 w-4 text-purple-500" />,
      integrations: [
        { name: "n8n", status: "active" },
        { name: "Zapier", status: "pending" },
        { name: "IFTTT", status: "pending" },
        { name: "Make", status: "pending" },
      ],
    },
  ]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "active":
        return <CheckCircle2 className="h-3 w-3 text-green-500" />;
      case "inactive":
        return <XCircle className="h-3 w-3 text-gray-500" />;
      case "error":
        return <AlertCircle className="h-3 w-3 text-red-500" />;
      case "pending":
        return <Clock className="h-3 w-3 text-yellow-500" />;
      default:
        return <Clock className="h-3 w-3 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return <Badge className="bg-green-500/10 text-green-500 text-[10px]">Active</Badge>;
      case "inactive":
        return <Badge className="bg-gray-500/10 text-gray-500 text-[10px]">Inactive</Badge>;
      case "error":
        return <Badge className="bg-red-500/10 text-red-500 text-[10px]">Error</Badge>;
      case "pending":
        return <Badge className="bg-yellow-500/10 text-yellow-500 text-[10px]">Setup Required</Badge>;
      default:
        return null;
    }
  };

  const totalActive = categories.reduce(
    (sum, cat) => sum + cat.integrations.filter((i) => i.status === "active").length,
    0
  );
  const totalIntegrations = categories.reduce(
    (sum, cat) => sum + cat.integrations.length,
    0
  );

  return (
    <Card className="border-gray-800 bg-[#1E293B]">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-lg font-semibold">
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-blue-500" />
            Integration Status
          </div>
          <Badge className="bg-blue-500/10 text-blue-500">
            {totalActive}/{totalIntegrations} Active
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {categories.map((category) => (
            <div key={category.name} className="rounded-lg bg-[#0F172A] p-3">
              <div className="mb-2 flex items-center gap-2">
                {category.icon}
                <span className="text-sm font-medium">{category.name}</span>
                <span className="text-xs text-gray-500">
                  ({category.integrations.filter((i) => i.status === "active").length}/
                  {category.integrations.length})
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {category.integrations.map((integration) => (
                  <div
                    key={integration.name}
                    className="flex items-center justify-between rounded bg-[#1E293B] px-2 py-1"
                  >
                    <div className="flex items-center gap-2">
                      {getStatusIcon(integration.status)}
                      <span className="text-xs">{integration.name}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default IntegrationStatusWidget;
