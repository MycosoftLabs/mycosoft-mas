import { Metadata } from "next";
import { LabMonitor } from "@/components/scientific/LabMonitor";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export const metadata: Metadata = {
  title: "Laboratory | MYCA Scientific",
  description: "Laboratory instrument control and monitoring",
};

export default function LabPage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Laboratory Control</h1>
          <p className="text-muted-foreground">Monitor and control lab instruments</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">Calibrate All</Button>
          <Button>Add Instrument</Button>
        </div>
      </div>

      <Tabs defaultValue="instruments" className="space-y-4">
        <TabsList>
          <TabsTrigger value="instruments">Instruments</TabsTrigger>
          <TabsTrigger value="protocols">Protocols</TabsTrigger>
          <TabsTrigger value="samples">Samples</TabsTrigger>
          <TabsTrigger value="consumables">Consumables</TabsTrigger>
        </TabsList>
        
        <TabsContent value="instruments">
          <LabMonitor />
        </TabsContent>
        
        <TabsContent value="protocols">
          <Card>
            <CardHeader>
              <CardTitle>Lab Protocols</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center justify-between p-3 border rounded">
                  <div>
                    <p className="font-medium">Fungal Culture Inoculation</p>
                    <p className="text-sm text-muted-foreground">Standard protocol for starting fungal cultures</p>
                  </div>
                  <Badge>Active</Badge>
                </div>
                <div className="flex items-center justify-between p-3 border rounded">
                  <div>
                    <p className="font-medium">DNA Extraction</p>
                    <p className="text-sm text-muted-foreground">Genomic DNA extraction from mycelium</p>
                  </div>
                  <Badge variant="outline">Available</Badge>
                </div>
                <div className="flex items-center justify-between p-3 border rounded">
                  <div>
                    <p className="font-medium">Bioelectric Recording</p>
                    <p className="text-sm text-muted-foreground">FCI electrode recording protocol</p>
                  </div>
                  <Badge variant="outline">Available</Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="samples">
          <Card>
            <CardHeader>
              <CardTitle>Sample Inventory</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">Sample tracking coming soon</p>
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="consumables">
          <Card>
            <CardHeader>
              <CardTitle>Consumables Inventory</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">Consumables tracking coming soon</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
