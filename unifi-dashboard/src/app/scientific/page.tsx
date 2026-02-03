import { Metadata } from "next";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LabMonitor } from "@/components/scientific/LabMonitor";
import { SimulationPanel } from "@/components/scientific/SimulationPanel";
import { ExperimentTracker } from "@/components/scientific/ExperimentTracker";
import { HypothesisBoard } from "@/components/scientific/HypothesisBoard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Scientific Dashboard | MYCA",
  description: "Autonomous scientific research and experimentation platform",
};

export default function ScientificPage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Scientific Dashboard</h1>
          <p className="text-muted-foreground">Autonomous scientific research and experimentation</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Active Experiments</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-muted-foreground">3 running, 9 pending</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Simulations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">5</div>
            <p className="text-xs text-muted-foreground">2 AlphaFold, 3 Mycelium</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Lab Instruments</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">8</div>
            <p className="text-xs text-muted-foreground">7 online, 1 maintenance</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Hypotheses</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">24</div>
            <p className="text-xs text-muted-foreground">6 validated, 4 testing</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="lab">Lab</TabsTrigger>
          <TabsTrigger value="simulations">Simulations</TabsTrigger>
          <TabsTrigger value="experiments">Experiments</TabsTrigger>
          <TabsTrigger value="hypotheses">Hypotheses</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <LabMonitor />
            <SimulationPanel />
          </div>
        </TabsContent>
        
        <TabsContent value="lab">
          <LabMonitor />
        </TabsContent>
        
        <TabsContent value="simulations">
          <SimulationPanel />
        </TabsContent>
        
        <TabsContent value="experiments">
          <ExperimentTracker />
        </TabsContent>
        
        <TabsContent value="hypotheses">
          <HypothesisBoard />
        </TabsContent>
      </Tabs>
    </div>
  );
}
