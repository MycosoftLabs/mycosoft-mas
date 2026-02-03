"use client";
import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { DeviceGrid } from "@/components/widgets/devices";
import { TelemetryChart } from "@/components/widgets/devices";
import { EnvironmentDashboard, CommandCenter, EventFeed } from "@/components/widgets/natureos";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function DevicesPage() {
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">NatureOS Devices</h1>
          <p className="text-muted-foreground">Manage and monitor all connected devices</p>
        </div>
        <Button>Register Device</Button>
      </div>

      <Tabs defaultValue="devices" className="space-y-4">
        <TabsList>
          <TabsTrigger value="devices">Devices</TabsTrigger>
          <TabsTrigger value="environment">Environment</TabsTrigger>
          <TabsTrigger value="commands">Command Center</TabsTrigger>
          <TabsTrigger value="events">Events</TabsTrigger>
        </TabsList>

        <TabsContent value="devices" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Total Devices</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">24</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Online</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-500">21</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Offline</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-500">2</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Errors</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-500">1</div>
              </CardContent>
            </Card>
          </div>

          <DeviceGrid onDeviceSelect={setSelectedDevice} />

          {selectedDevice && (
            <div className="grid gap-4 md:grid-cols-2">
              <TelemetryChart deviceId={selectedDevice} sensorType="temperature" />
              <TelemetryChart deviceId={selectedDevice} sensorType="humidity" />
            </div>
          )}
        </TabsContent>

        <TabsContent value="environment">
          <EnvironmentDashboard />
        </TabsContent>

        <TabsContent value="commands">
          <CommandCenter />
        </TabsContent>

        <TabsContent value="events">
          <EventFeed />
        </TabsContent>
      </Tabs>
    </div>
  );
}
