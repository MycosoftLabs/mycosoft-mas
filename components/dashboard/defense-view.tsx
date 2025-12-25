"use client";

import { useState, useEffect } from "react";
import {
  Shield,
  Lock,
  Eye,
  Radio,
  Satellite,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Activity,
  Globe,
  Server,
  Database,
  Network,
  Zap,
  Target,
  Radar,
  Map,
  Users,
  FileText,
  BarChart3,
  RefreshCw,
  Settings,
  Key,
  Clock,
  Cpu,
  HardDrive,
  Wifi,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";

interface PlatformStatus {
  name: string;
  status: "connected" | "disconnected" | "error" | "restricted";
  lastSync: string;
  features: string[];
  securityLevel: string;
}

interface ThreatAlert {
  id: string;
  severity: "critical" | "high" | "medium" | "low";
  source: string;
  description: string;
  timestamp: string;
  status: "active" | "investigating" | "resolved";
}

interface DataSource {
  name: string;
  type: string;
  records: number;
  lastUpdate: string;
  status: "online" | "offline" | "syncing";
}

export function DefenseView() {
  const [activeTab, setActiveTab] = useState("overview");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [platformStatuses, setPlatformStatuses] = useState<PlatformStatus[]>([
    {
      name: "Palantir Foundry",
      status: "connected",
      lastSync: new Date().toISOString(),
      features: ["Data Fusion", "Ontology", "Object Explorer", "Code Workbooks", "Quiver"],
      securityLevel: "TOP SECRET//SCI"
    },
    {
      name: "Anduril Lattice",
      status: "connected",
      lastSync: new Date().toISOString(),
      features: ["Sentry Towers", "Ghost UAS", "Anvil", "Menace", "Dive-LD"],
      securityLevel: "SECRET//NOFORN"
    },
    {
      name: "Platform One",
      status: "connected",
      lastSync: new Date().toISOString(),
      features: ["Big Bang", "Iron Bank", "Party Bus", "Repo One", "SSO"],
      securityLevel: "UNCLASSIFIED//FOUO"
    },
    {
      name: "Tactical Data Link",
      status: "restricted",
      lastSync: new Date().toISOString(),
      features: ["Link 16", "Link 22", "SADL", "VMF", "JREAP"],
      securityLevel: "SECRET//REL TO USA, FVEY"
    }
  ]);

  const [threatAlerts, setThreatAlerts] = useState<ThreatAlert[]>([
    {
      id: "TA-001",
      severity: "high",
      source: "Palantir Gotham",
      description: "Anomalous network traffic detected in sector 7-G",
      timestamp: new Date(Date.now() - 300000).toISOString(),
      status: "investigating"
    },
    {
      id: "TA-002",
      severity: "medium",
      source: "Anduril Sentry",
      description: "Perimeter intrusion alert - Zone Alpha",
      timestamp: new Date(Date.now() - 600000).toISOString(),
      status: "active"
    },
    {
      id: "TA-003",
      severity: "low",
      source: "Platform One SIEM",
      description: "Routine audit event - CAC authentication spike",
      timestamp: new Date(Date.now() - 1800000).toISOString(),
      status: "resolved"
    }
  ]);

  const [dataSources, setDataSources] = useState<DataSource[]>([
    { name: "SIGINT Feed", type: "Intelligence", records: 2547893, lastUpdate: "2 min ago", status: "online" },
    { name: "GEOINT Imagery", type: "Imagery", records: 847293, lastUpdate: "5 min ago", status: "online" },
    { name: "HUMINT Reports", type: "Intelligence", records: 12847, lastUpdate: "15 min ago", status: "syncing" },
    { name: "OSINT Aggregator", type: "Open Source", records: 9847562, lastUpdate: "1 min ago", status: "online" },
    { name: "Cyber Threat Intel", type: "Cyber", records: 458721, lastUpdate: "30 sec ago", status: "online" },
    { name: "Biometric Database", type: "Identity", records: 4582741, lastUpdate: "1 hr ago", status: "offline" }
  ]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500));
    setIsRefreshing(false);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "connected":
      case "online":
      case "resolved":
        return "bg-green-500";
      case "disconnected":
      case "offline":
        return "bg-gray-500";
      case "error":
      case "critical":
        return "bg-red-500";
      case "restricted":
      case "syncing":
      case "investigating":
        return "bg-yellow-500";
      case "high":
        return "bg-orange-500";
      case "medium":
        return "bg-yellow-500";
      case "low":
        return "bg-blue-500";
      case "active":
        return "bg-red-500";
      default:
        return "bg-gray-500";
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "critical":
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case "high":
        return <AlertTriangle className="h-4 w-4 text-orange-500" />;
      case "medium":
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      case "low":
        return <Activity className="h-4 w-4 text-blue-500" />;
      default:
        return <Activity className="h-4 w-4 text-gray-500" />;
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-gradient-to-br from-red-600 to-orange-600">
            <Shield className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Defense Command Center</h1>
            <p className="text-sm text-gray-400">Secure Integration Hub for Defense & Government Systems</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="border-green-500 text-green-500">
            <Lock className="mr-1 h-3 w-3" />
            Secure Connection
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Security Status Banner */}
      <Card className="border-yellow-600/50 bg-yellow-900/20">
        <CardContent className="flex items-center justify-between p-4">
          <div className="flex items-center gap-3">
            <Lock className="h-5 w-5 text-yellow-500" />
            <span className="text-sm text-yellow-200">
              Classification Level: <strong>UNCLASSIFIED // FOR OFFICIAL USE ONLY</strong>
            </span>
          </div>
          <div className="flex items-center gap-4 text-sm text-gray-400">
            <span className="flex items-center gap-1">
              <Key className="h-4 w-4" />
              CAC Required for elevated access
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-4 w-4" />
              Session: 47:23 remaining
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-5 bg-gray-800">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <Globe className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="palantir" className="flex items-center gap-2">
            <Database className="h-4 w-4" />
            Palantir
          </TabsTrigger>
          <TabsTrigger value="anduril" className="flex items-center gap-2">
            <Radar className="h-4 w-4" />
            Anduril
          </TabsTrigger>
          <TabsTrigger value="platform-one" className="flex items-center gap-2">
            <Server className="h-4 w-4" />
            Platform One
          </TabsTrigger>
          <TabsTrigger value="tactical" className="flex items-center gap-2">
            <Radio className="h-4 w-4" />
            Tactical
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          {/* Platform Status Grid */}
          <div className="grid grid-cols-4 gap-4">
            {platformStatuses.map((platform) => (
              <Card key={platform.name} className="bg-gray-800/50 border-gray-700">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm font-medium">{platform.name}</CardTitle>
                    <div className={`h-2 w-2 rounded-full ${getStatusColor(platform.status)}`} />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <Badge variant="outline" className="text-xs">
                      {platform.securityLevel}
                    </Badge>
                    <p className="text-xs text-gray-400">
                      {platform.features.length} features available
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Metrics Row */}
          <div className="grid grid-cols-4 gap-4">
            <Card className="bg-gradient-to-br from-blue-900/50 to-blue-800/30 border-blue-700/50">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-blue-300">Active Sensors</p>
                    <p className="text-2xl font-bold text-white">2,847</p>
                  </div>
                  <Satellite className="h-8 w-8 text-blue-400" />
                </div>
              </CardContent>
            </Card>
            <Card className="bg-gradient-to-br from-green-900/50 to-green-800/30 border-green-700/50">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-green-300">Data Streams</p>
                    <p className="text-2xl font-bold text-white">156</p>
                  </div>
                  <Activity className="h-8 w-8 text-green-400" />
                </div>
              </CardContent>
            </Card>
            <Card className="bg-gradient-to-br from-yellow-900/50 to-yellow-800/30 border-yellow-700/50">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-yellow-300">Active Alerts</p>
                    <p className="text-2xl font-bold text-white">12</p>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-yellow-400" />
                </div>
              </CardContent>
            </Card>
            <Card className="bg-gradient-to-br from-purple-900/50 to-purple-800/30 border-purple-700/50">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-purple-300">Operations</p>
                    <p className="text-2xl font-bold text-white">7</p>
                  </div>
                  <Target className="h-8 w-8 text-purple-400" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Two Column Layout */}
          <div className="grid grid-cols-2 gap-6">
            {/* Threat Alerts */}
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-yellow-500" />
                  Threat Alerts
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-64">
                  <div className="space-y-3">
                    {threatAlerts.map((alert) => (
                      <div
                        key={alert.id}
                        className="flex items-start gap-3 rounded-lg bg-gray-900/50 p-3"
                      >
                        {getSeverityIcon(alert.severity)}
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-white">{alert.id}</span>
                            <Badge variant="outline" className={`text-xs ${getStatusColor(alert.status)} bg-opacity-20`}>
                              {alert.status}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-400">{alert.description}</p>
                          <p className="text-xs text-gray-500 mt-1">
                            Source: {alert.source} • {new Date(alert.timestamp).toLocaleTimeString()}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Data Sources */}
            <Card className="bg-gray-800/50 border-gray-700">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5 text-blue-500" />
                  Data Sources
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-64">
                  <div className="space-y-3">
                    {dataSources.map((source) => (
                      <div
                        key={source.name}
                        className="flex items-center justify-between rounded-lg bg-gray-900/50 p-3"
                      >
                        <div className="flex items-center gap-3">
                          <div className={`h-2 w-2 rounded-full ${getStatusColor(source.status)}`} />
                          <div>
                            <p className="text-sm font-medium text-white">{source.name}</p>
                            <p className="text-xs text-gray-400">{source.type}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-white">{source.records.toLocaleString()}</p>
                          <p className="text-xs text-gray-400">{source.lastUpdate}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Palantir Tab */}
        <TabsContent value="palantir" className="space-y-6">
          <PalantirDashboard />
        </TabsContent>

        {/* Anduril Tab */}
        <TabsContent value="anduril" className="space-y-6">
          <AndurilDashboard />
        </TabsContent>

        {/* Platform One Tab */}
        <TabsContent value="platform-one" className="space-y-6">
          <PlatformOneDashboard />
        </TabsContent>

        {/* Tactical Tab */}
        <TabsContent value="tactical" className="space-y-6">
          <TacticalDashboard />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Palantir Dashboard Component
function PalantirDashboard() {
  const foundryModules = [
    { name: "Ontology", description: "Data modeling and object definitions", status: "active", icon: Database },
    { name: "Data Fusion", description: "Multi-source data integration", status: "active", icon: Network },
    { name: "Object Explorer", description: "Visual data exploration", status: "active", icon: Eye },
    { name: "Code Workbooks", description: "Python/SQL analytics", status: "active", icon: FileText },
    { name: "Quiver", description: "Geospatial analysis", status: "active", icon: Map },
    { name: "Contour", description: "Analytical dashboards", status: "active", icon: BarChart3 },
    { name: "Vertex", description: "AI/ML modeling", status: "active", icon: Cpu },
    { name: "Pipeline Builder", description: "ETL workflow automation", status: "active", icon: Zap },
  ];

  const ontologyObjects = [
    { type: "Person", count: 2847291, lastSync: "2 min ago" },
    { type: "Organization", count: 458721, lastSync: "5 min ago" },
    { type: "Location", count: 1284573, lastSync: "1 min ago" },
    { type: "Event", count: 847293, lastSync: "30 sec ago" },
    { type: "Vehicle", count: 328471, lastSync: "3 min ago" },
    { type: "Communication", count: 9847562, lastSync: "10 sec ago" },
  ];

  return (
    <div className="space-y-6">
      <Card className="bg-gradient-to-r from-indigo-900/50 to-purple-900/50 border-indigo-700/50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600">
                <Database className="h-5 w-5 text-white" />
              </div>
              <div>
                <CardTitle>Palantir Foundry</CardTitle>
                <CardDescription>Enterprise Data Integration Platform</CardDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className="bg-green-600">Connected</Badge>
              <Button variant="outline" size="sm">
                <Settings className="mr-2 h-4 w-4" />
                Configure
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Foundry Modules Grid */}
      <div className="grid grid-cols-4 gap-4">
        {foundryModules.map((module) => (
          <Card key={module.name} className="bg-gray-800/50 border-gray-700 hover:border-indigo-500/50 transition-colors cursor-pointer">
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <module.icon className="h-8 w-8 text-indigo-400" />
                <Badge variant="outline" className="text-xs bg-green-500/20 border-green-500 text-green-400">
                  {module.status}
                </Badge>
              </div>
              <h3 className="mt-3 font-semibold text-white">{module.name}</h3>
              <p className="text-xs text-gray-400 mt-1">{module.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Ontology Overview */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Network className="h-5 w-5 text-indigo-400" />
            Ontology Overview
          </CardTitle>
          <CardDescription>Object types and record counts in the data model</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-6 gap-4">
            {ontologyObjects.map((obj) => (
              <div key={obj.type} className="rounded-lg bg-gray-900/50 p-4 text-center">
                <p className="text-2xl font-bold text-indigo-400">{(obj.count / 1000000).toFixed(2)}M</p>
                <p className="text-sm font-medium text-white">{obj.type}</p>
                <p className="text-xs text-gray-500">{obj.lastSync}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-3 gap-4">
        <Button className="h-auto py-4 bg-indigo-600 hover:bg-indigo-700">
          <div className="flex flex-col items-center gap-2">
            <Eye className="h-6 w-6" />
            <span>Open Object Explorer</span>
          </div>
        </Button>
        <Button className="h-auto py-4 bg-indigo-600 hover:bg-indigo-700">
          <div className="flex flex-col items-center gap-2">
            <FileText className="h-6 w-6" />
            <span>New Code Workbook</span>
          </div>
        </Button>
        <Button className="h-auto py-4 bg-indigo-600 hover:bg-indigo-700">
          <div className="flex flex-col items-center gap-2">
            <Map className="h-6 w-6" />
            <span>Launch Quiver Map</span>
          </div>
        </Button>
      </div>
    </div>
  );
}

// Anduril Dashboard Component
function AndurilDashboard() {
  const latticeAssets = [
    { name: "Sentry Tower Alpha", type: "Ground Sensor", status: "online", location: "Zone 1", battery: 98 },
    { name: "Sentry Tower Bravo", type: "Ground Sensor", status: "online", location: "Zone 2", battery: 87 },
    { name: "Ghost 40 - Unit 1", type: "UAS", status: "mission", location: "Sector 7", battery: 72 },
    { name: "Ghost 40 - Unit 2", type: "UAS", status: "charging", location: "Base", battery: 45 },
    { name: "Anvil CUAS-1", type: "Counter-UAS", status: "online", location: "Perimeter", battery: 100 },
    { name: "Dive-LD Alpha", type: "AUV", status: "offline", location: "Dock", battery: 0 },
  ];

  const detections = [
    { id: "DET-001", type: "Vehicle", confidence: 94, location: "Grid 4521", time: "2 min ago" },
    { id: "DET-002", type: "Person", confidence: 87, location: "Grid 4522", time: "5 min ago" },
    { id: "DET-003", type: "Aircraft", confidence: 99, location: "Grid 4518", time: "12 min ago" },
    { id: "DET-004", type: "Vessel", confidence: 76, location: "Grid 4530", time: "18 min ago" },
  ];

  return (
    <div className="space-y-6">
      <Card className="bg-gradient-to-r from-orange-900/50 to-red-900/50 border-orange-700/50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-600">
                <Radar className="h-5 w-5 text-white" />
              </div>
              <div>
                <CardTitle>Anduril Lattice</CardTitle>
                <CardDescription>Autonomous Defense Platform</CardDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className="bg-green-600">6 Assets Online</Badge>
              <Button variant="outline" size="sm">
                <Target className="mr-2 h-4 w-4" />
                Command
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Asset Grid */}
      <div className="grid grid-cols-3 gap-4">
        {latticeAssets.map((asset) => (
          <Card key={asset.name} className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-white">{asset.name}</h3>
                  <p className="text-xs text-gray-400">{asset.type}</p>
                </div>
                <Badge 
                  variant="outline" 
                  className={`text-xs ${
                    asset.status === "online" ? "border-green-500 text-green-400" :
                    asset.status === "mission" ? "border-blue-500 text-blue-400" :
                    asset.status === "charging" ? "border-yellow-500 text-yellow-400" :
                    "border-gray-500 text-gray-400"
                  }`}
                >
                  {asset.status}
                </Badge>
              </div>
              <div className="mt-3 flex items-center justify-between text-sm">
                <span className="text-gray-400">{asset.location}</span>
                <div className="flex items-center gap-1">
                  <div className="h-2 w-16 rounded-full bg-gray-700">
                    <div 
                      className={`h-full rounded-full ${
                        asset.battery > 70 ? "bg-green-500" :
                        asset.battery > 30 ? "bg-yellow-500" : "bg-red-500"
                      }`}
                      style={{ width: `${asset.battery}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-400">{asset.battery}%</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Detection Feed */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Eye className="h-5 w-5 text-orange-400" />
            Recent Detections
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {detections.map((det) => (
              <div key={det.id} className="flex items-center justify-between rounded-lg bg-gray-900/50 p-3">
                <div className="flex items-center gap-3">
                  <Target className="h-4 w-4 text-orange-400" />
                  <div>
                    <span className="text-sm font-medium text-white">{det.id}</span>
                    <span className="ml-2 text-sm text-gray-400">{det.type}</span>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <Badge variant="outline" className={det.confidence > 90 ? "border-green-500 text-green-400" : "border-yellow-500 text-yellow-400"}>
                    {det.confidence}% conf
                  </Badge>
                  <span className="text-xs text-gray-400">{det.location}</span>
                  <span className="text-xs text-gray-500">{det.time}</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Platform One Dashboard Component
function PlatformOneDashboard() {
  const p1Services = [
    { name: "Big Bang", description: "DevSecOps platform deployment", status: "healthy", version: "2.8.0" },
    { name: "Iron Bank", description: "Hardened container registry", status: "healthy", version: "1.12.3" },
    { name: "Party Bus", description: "Service mesh and API gateway", status: "healthy", version: "3.1.0" },
    { name: "Repo One", description: "Git repository hosting", status: "healthy", version: "15.4.2" },
    { name: "SSO/SAML", description: "CAC authentication", status: "healthy", version: "2.0.1" },
    { name: "Keycloak", description: "Identity management", status: "warning", version: "22.0.1" },
  ];

  const deployments = [
    { name: "mission-app-prod", namespace: "mission", pods: "3/3", status: "Running", cpu: "45%", memory: "62%" },
    { name: "analytics-svc", namespace: "analytics", pods: "5/5", status: "Running", cpu: "72%", memory: "81%" },
    { name: "intel-fusion", namespace: "intel", pods: "2/3", status: "Degraded", cpu: "89%", memory: "95%" },
    { name: "c2-gateway", namespace: "command", pods: "4/4", status: "Running", cpu: "23%", memory: "44%" },
  ];

  return (
    <div className="space-y-6">
      <Card className="bg-gradient-to-r from-blue-900/50 to-cyan-900/50 border-blue-700/50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600">
                <Server className="h-5 w-5 text-white" />
              </div>
              <div>
                <CardTitle>Platform One</CardTitle>
                <CardDescription>DoD Enterprise DevSecOps Platform</CardDescription>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className="bg-green-600">IL4 Certified</Badge>
              <Button variant="outline" size="sm">
                <HardDrive className="mr-2 h-4 w-4" />
                Deploy
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Platform Services */}
      <div className="grid grid-cols-3 gap-4">
        {p1Services.map((svc) => (
          <Card key={svc.name} className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-white">{svc.name}</h3>
                  <p className="text-xs text-gray-400">{svc.description}</p>
                </div>
                <Badge 
                  variant="outline" 
                  className={svc.status === "healthy" ? "border-green-500 text-green-400" : "border-yellow-500 text-yellow-400"}
                >
                  {svc.status}
                </Badge>
              </div>
              <p className="mt-2 text-xs text-gray-500">v{svc.version}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Deployments Table */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-blue-400" />
            Active Deployments
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {deployments.map((dep) => (
              <div key={dep.name} className="flex items-center justify-between rounded-lg bg-gray-900/50 p-3">
                <div className="flex items-center gap-3">
                  <Server className="h-4 w-4 text-blue-400" />
                  <div>
                    <span className="text-sm font-medium text-white">{dep.name}</span>
                    <span className="ml-2 text-xs text-gray-500">ns/{dep.namespace}</span>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <Badge variant="outline" className={dep.status === "Running" ? "border-green-500 text-green-400" : "border-yellow-500 text-yellow-400"}>
                    {dep.pods} pods
                  </Badge>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-gray-400">CPU: {dep.cpu}</span>
                    <span className="text-gray-400">MEM: {dep.memory}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Tactical Dashboard Component
function TacticalDashboard() {
  const dataLinks = [
    { name: "Link 16", protocol: "TADIL-J", status: "active", messages: 12847, latency: "2ms" },
    { name: "Link 22", protocol: "NATO", status: "active", messages: 8472, latency: "5ms" },
    { name: "SADL", protocol: "USAF", status: "standby", messages: 0, latency: "-" },
    { name: "VMF", protocol: "USMC", status: "active", messages: 3847, latency: "8ms" },
  ];

  return (
    <div className="space-y-6">
      <Card className="bg-gradient-to-r from-green-900/50 to-emerald-900/50 border-green-700/50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-600">
                <Radio className="h-5 w-5 text-white" />
              </div>
              <div>
                <CardTitle>Tactical Data Links</CardTitle>
                <CardDescription>Real-time Military Communication Systems</CardDescription>
              </div>
            </div>
            <Badge className="bg-yellow-600">RESTRICTED ACCESS</Badge>
          </div>
        </CardHeader>
      </Card>

      {/* Data Links Grid */}
      <div className="grid grid-cols-4 gap-4">
        {dataLinks.map((link) => (
          <Card key={link.name} className="bg-gray-800/50 border-gray-700">
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-white">{link.name}</h3>
                  <p className="text-xs text-gray-400">{link.protocol}</p>
                </div>
                <Badge 
                  variant="outline" 
                  className={link.status === "active" ? "border-green-500 text-green-400" : "border-gray-500 text-gray-400"}
                >
                  {link.status}
                </Badge>
              </div>
              <div className="mt-3 space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Messages</span>
                  <span className="text-white">{link.messages.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-400">Latency</span>
                  <span className="text-green-400">{link.latency}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Restricted Access Notice */}
      <Card className="border-red-700/50 bg-red-900/20">
        <CardContent className="flex items-center gap-3 p-4">
          <Lock className="h-6 w-6 text-red-500" />
          <div>
            <p className="font-medium text-red-200">CAC Authentication Required</p>
            <p className="text-sm text-red-300/70">
              Tactical data link access requires valid DoD CAC card and appropriate clearance level.
              Contact your security officer for access provisioning.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
