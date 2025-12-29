"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Activity, AlertCircle, RefreshCw } from "lucide-react";

interface LiveDataResponse {
  stats: {
    totalEvents: number;
    activeDevices: number;
    speciesDetected: number;
    onlineUsers: number;
  };
  liveData: {
    readings: Array<{
      sourceDevice: string;
      kingdomDomain: string;
      timestamp: string;
    }>;
    lastUpdate: string;
  };
  insights: {
    trendingCompounds: string[];
    recentDiscoveries: Array<{
      kingdomDomain: string;
      timestamp: string;
    }>;
  };
}

interface RealtimeEvent {
  eventId: string;
  timestamp: string;
  sourceDevice: string;
  kingdomDomain: string;
  decodedMeaning?: {
    type: string;
    confidence: number;
  };
}

interface LiveDataFeedProps {
  refreshInterval?: number;
  showEvents?: boolean;
  maxEvents?: number;
  className?: string;
}

export function LiveDataFeed({
  refreshInterval = 5000,
  showEvents = true,
  maxEvents = 10,
  className = "",
}: LiveDataFeedProps) {
  const [data, setData] = useState<LiveDataResponse | null>(null);
  const [events, setEvents] = useState<RealtimeEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const formatTimestamp = (timestamp: string): string => {
    return new Date(timestamp).toLocaleString();
  };

  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + "M";
    }
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + "K";
    }
    return num.toString();
  };

  const handleEventUpdate = useCallback((newEvents: RealtimeEvent[]) => {
    setEvents((prevEvents) => {
      const combined = [...newEvents, ...prevEvents];
      return combined.slice(0, maxEvents);
    });
  }, [maxEvents]);

  const handleDataUpdate = useCallback((newData: LiveDataResponse) => {
    setData(newData);
    setIsLoading(false);
    setError(null);
  }, []);

  const handleError = useCallback((error: Event) => {
    console.error("Live data connection error:", error);
    setError("Connection lost. Attempting to reconnect...");
    setIsConnected(false);
  }, []);

  const fetchDashboardData = useCallback(async () => {
    try {
      // Try to fetch from NatureOS API or MAS backend
      const response = await fetch("/api/natureos/dashboard");
      if (!response.ok) {
        throw new Error(`Failed to fetch: ${response.status}`);
      }
      const dashboardData = await response.json();
      handleDataUpdate(dashboardData);
      setIsConnected(true);
    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
      setError("Failed to load live data");
      setIsLoading(false);
    }
  }, [handleDataUpdate]);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchDashboardData, refreshInterval]);

  if (isLoading && !data) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center py-12">
          <div className="text-center">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-green-500" />
            <p className="text-sm text-gray-500">Loading live data...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error && !data) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center py-12">
          <div className="text-center">
            <AlertCircle className="w-8 h-8 mx-auto mb-4 text-red-500" />
            <h3 className="font-semibold mb-2">Connection Error</h3>
            <p className="text-sm text-gray-500 mb-4">{error}</p>
            <Button onClick={fetchDashboardData} variant="outline" size="sm">
              Retry Connection
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Connection Status */}
      <div className="flex items-center gap-2 text-sm">
        <div
          className={`h-2 w-2 rounded-full ${
            isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
          }`}
        />
        <span className={isConnected ? "text-green-500" : "text-red-500"}>
          {isConnected ? "Live" : "Reconnecting..."}
        </span>
      </div>

      {/* Stats Overview */}
      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">
                Total Events
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatNumber(data.stats.totalEvents)}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">
                Active Devices
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {data.stats.activeDevices}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">
                Species Detected
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {data.stats.speciesDetected}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-500">
                Online Users
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{data.stats.onlineUsers}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Live Readings */}
      {data?.liveData && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Latest Readings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {data.liveData.readings.map((reading, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between py-2 border-b border-gray-200 last:border-0"
                >
                  <div className="flex-1">
                    <div className="font-medium text-sm">{reading.sourceDevice}</div>
                    <div className="text-xs text-gray-500">
                      {reading.kingdomDomain}
                    </div>
                  </div>
                  <div className="text-xs text-gray-400">
                    {formatTimestamp(reading.timestamp)}
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-4">
              Last updated: {formatTimestamp(data.liveData.lastUpdate)}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Real-time Events */}
      {showEvents && events.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Live Events</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {events.map((event) => (
                <div
                  key={event.eventId}
                  className="p-3 bg-gray-50 rounded-lg space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm">{event.sourceDevice}</span>
                    <span className="text-xs text-gray-400">
                      {formatTimestamp(event.timestamp)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{event.kingdomDomain}</Badge>
                    {event.decodedMeaning && (
                      <Badge
                        variant="secondary"
                        className="text-xs"
                      >
                        {Math.round(event.decodedMeaning.confidence * 100)}%
                        confidence
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Insights */}
      {data?.insights && (
        <Card>
          <CardHeader>
            <CardTitle>Current Insights</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="text-sm font-medium mb-2">Trending Compounds</h4>
              <div className="flex flex-wrap gap-2">
                {data.insights.trendingCompounds.map((compound, index) => (
                  <Badge key={index} variant="outline">
                    {compound}
                  </Badge>
                ))}
              </div>
            </div>
            {data.insights.recentDiscoveries.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-2">Recent Discoveries</h4>
                <ul className="space-y-1">
                  {data.insights.recentDiscoveries.map((discovery, index) => (
                    <li key={index} className="text-sm text-gray-600">
                      {discovery.kingdomDomain} - {formatTimestamp(discovery.timestamp)}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

