import { Metadata } from "next";
import { SimulationPanel } from "@/components/scientific/SimulationPanel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

export const metadata: Metadata = {
  title: "Simulations | MYCA Scientific",
  description: "Scientific simulations and computational experiments",
};

export default function SimulationPage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Simulation Center</h1>
          <p className="text-muted-foreground">Run and manage scientific simulations</p>
        </div>
        <Button>New Simulation</Button>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">GPU Utilization</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">78%</div>
            <Progress value={78} className="mt-2" />
            <p className="text-xs text-muted-foreground mt-1">RTX 5090 - 24GB VRAM</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Active Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3</div>
            <p className="text-xs text-muted-foreground">Queue: 7 pending</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Completed Today</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-muted-foreground">Avg time: 45 min</p>
          </CardContent>
        </Card>
      </div>

      <SimulationPanel />

      <Card>
        <CardHeader>
          <CardTitle>Running Simulations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="p-4 border rounded">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="font-medium">AlphaFold - Psilocybin Synthase</p>
                  <p className="text-sm text-muted-foreground">Protein structure prediction</p>
                </div>
                <span className="text-sm">67%</span>
              </div>
              <Progress value={67} />
              <p className="text-xs text-muted-foreground mt-1">ETA: 23 minutes</p>
            </div>
            <div className="p-4 border rounded">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="font-medium">Mycelium Network Growth</p>
                  <p className="text-sm text-muted-foreground">10,000 time steps</p>
                </div>
                <span className="text-sm">34%</span>
              </div>
              <Progress value={34} />
              <p className="text-xs text-muted-foreground mt-1">ETA: 1 hour 12 minutes</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
