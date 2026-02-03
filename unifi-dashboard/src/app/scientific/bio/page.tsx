"use client";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";

export default function BioPage() {
  const [activeSession, setActiveSession] = useState<string | null>(null);

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Biological Interfaces</h1>
          <p className="text-muted-foreground">FCI, MycoBrain, and genomic systems</p>
        </div>
        <Button>Start FCI Session</Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">FCI Sessions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2</div>
            <p className="text-xs text-muted-foreground">Active recordings</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Electrodes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">64</div>
            <p className="text-xs text-muted-foreground">58 active</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">MycoBrain</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">Online</div>
            <p className="text-xs text-muted-foreground">3 computations queued</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Signal Quality</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">92%</div>
            <Progress value={92} className="mt-1" />
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="fci" className="space-y-4">
        <TabsList>
          <TabsTrigger value="fci">FCI Control</TabsTrigger>
          <TabsTrigger value="mycobrain">MycoBrain</TabsTrigger>
          <TabsTrigger value="signals">Signal Analysis</TabsTrigger>
          <TabsTrigger value="genomics">Genomics</TabsTrigger>
        </TabsList>
        
        <TabsContent value="fci">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Electrode Array</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-8 gap-1">
                  {Array.from({ length: 64 }).map((_, i) => (
                    <div
                      key={i}
                      className={`w-6 h-6 rounded-full ${i < 58 ? "bg-green-500" : "bg-gray-300"}`}
                      title={`Electrode ${i + 1}`}
                    />
                  ))}
                </div>
                <p className="text-sm text-muted-foreground mt-4">58/64 electrodes active</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Active Sessions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="p-3 border rounded">
                    <div className="flex items-center justify-between">
                      <p className="font-medium">Pleurotus ostreatus</p>
                      <Badge className="bg-green-500">Recording</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">Duration: 2h 34m</p>
                  </div>
                  <div className="p-3 border rounded">
                    <div className="flex items-center justify-between">
                      <p className="font-medium">Ganoderma lucidum</p>
                      <Badge className="bg-blue-500">Stimulating</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">Duration: 45m</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        
        <TabsContent value="mycobrain">
          <Card>
            <CardHeader>
              <CardTitle>MycoBrain Neuromorphic Processor</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="p-4 border rounded text-center">
                    <p className="text-2xl font-bold">Graph Solving</p>
                    <p className="text-muted-foreground">Shortest path optimization</p>
                  </div>
                  <div className="p-4 border rounded text-center">
                    <p className="text-2xl font-bold">Pattern Recognition</p>
                    <p className="text-muted-foreground">Signal classification</p>
                  </div>
                  <div className="p-4 border rounded text-center">
                    <p className="text-2xl font-bold">Analog Compute</p>
                    <p className="text-muted-foreground">Bio-digital computation</p>
                  </div>
                </div>
                <Button className="w-full">Submit Computation</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="signals">
          <Card>
            <CardHeader>
              <CardTitle>Signal Visualization</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-64 bg-muted rounded flex items-center justify-center">
                <p className="text-muted-foreground">Real-time signal visualization</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="genomics">
          <Card>
            <CardHeader>
              <CardTitle>Genomic Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">Sequencing and analysis tools coming soon</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
