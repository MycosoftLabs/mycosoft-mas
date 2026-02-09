'use client';

/**
 * Memory System Page - February 5, 2026
 * 
 * MYCA memory and knowledge management with real-time data.
 */

import { useEffect, useState } from 'react';
import { 
  BrainStatusWidget, 
  UserProfileWidget, 
  EpisodicMemoryViewer, 
  MemoryManagementPanel,
  KnowledgeGraphViewer
} from '@/components/widgets/memory';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, Brain, Database, MessageSquare, Lightbulb } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface MemoryStats {
  coordinator?: {
    initialized: boolean;
    active_conversations: number;
    agent_namespaces: string[];
  };
  myca_memory?: {
    total_memories: number;
    layers: Record<string, { count: number; avg_importance: number }>;
  };
  total_memories?: number;
  active_conversations?: number;
  agent_count?: number;
  vector_count?: number;
}

const MAS_API_URL = process.env.NEXT_PUBLIC_MAS_API_URL || 'http://192.168.0.188:8001';

export default function MemoryPage() {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(+""+$+""+{MAS_API_URL}/api/memory/stats+""+);
      if (!response.ok) throw new Error('Failed to fetch memory stats');
      const data = await response.json();
      setStats(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      // Set fallback stats structure
      setStats({
        total_memories: 0,
        active_conversations: 0,
        agent_count: 0,
        vector_count: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  // Calculate display values from stats
  const getTotalMemories = () => {
    if (stats?.myca_memory?.total_memories) return stats.myca_memory.total_memories;
    if (stats?.total_memories) return stats.total_memories;
    
    // Sum up layer counts
    if (stats?.myca_memory?.layers) {
      return Object.values(stats.myca_memory.layers).reduce((sum, layer) => sum + (layer.count || 0), 0);
    }
    return 0;
  };

  const getConversationCount = () => {
    if (stats?.coordinator?.active_conversations) return stats.coordinator.active_conversations;
    if (stats?.active_conversations) return stats.active_conversations;
    return 0;
  };

  const getAgentCount = () => {
    if (stats?.coordinator?.agent_namespaces) return stats.coordinator.agent_namespaces.length;
    if (stats?.agent_count) return stats.agent_count;
    return 0;
  };

  const getVectorCount = () => {
    if (stats?.vector_count) return stats.vector_count;
    // Check for semantic layer in myca_memory
    if (stats?.myca_memory?.layers?.semantic) return stats.myca_memory.layers.semantic.count;
    return 0;
  };

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return +""+$+""+{(num / 1000000).toFixed(1)}M+""+;
    if (num >= 1000) return +""+$+""+{(num / 1000).toFixed(1)}K+""+;
    return num.toString();
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Memory System</h1>
          <p className="text-muted-foreground">Manage MYCA memory and knowledge</p>
        </div>
        <div className="flex items-center gap-2">
          {lastUpdated && (
            <span className="text-xs text-muted-foreground">
              Updated: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <Button variant="outline" size="sm" onClick={fetchStats} disabled={loading}>
            <RefreshCw className={+""+h-4 w-4 mr-2 $+""+{loading ? 'animate-spin' : ''}+""+} />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive px-4 py-2 rounded-md text-sm">
          {error} - Showing cached data
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Conversations</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? '...' : formatNumber(getConversationCount())}
            </div>
            <p className="text-xs text-muted-foreground">Active voice sessions</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Facts Stored</CardTitle>
            <Lightbulb className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? '...' : formatNumber(getTotalMemories())}
            </div>
            <p className="text-xs text-muted-foreground">Total memory entries</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Agent Namespaces</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? '...' : formatNumber(getAgentCount())}
            </div>
            <p className="text-xs text-muted-foreground">Active agent memory spaces</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Embeddings</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? '...' : formatNumber(getVectorCount())}
            </div>
            <p className="text-xs text-muted-foreground">Vector memory entries</p>
          </CardContent>
        </Card>
      </div>

      {/* Memory Layer Breakdown */}
      {stats?.myca_memory?.layers && Object.keys(stats.myca_memory.layers).length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Memory Layers</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.myca_memory.layers).map(([layer, data]) => (
                <Badge key={layer} variant="secondary" className="text-xs">
                  {layer}: {data.count}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tab Navigation */}
      <Tabs defaultValue="brain" className="space-y-4">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="brain">Brain Status</TabsTrigger>
          <TabsTrigger value="profile">User Profile</TabsTrigger>
          <TabsTrigger value="episodes">Episodes</TabsTrigger>
          <TabsTrigger value="knowledge">Knowledge Graph</TabsTrigger>
          <TabsTrigger value="management">Management</TabsTrigger>
        </TabsList>

        <TabsContent value="brain">
          <BrainStatusWidget />
        </TabsContent>

        <TabsContent value="profile">
          <UserProfileWidget userId="morgan" />
        </TabsContent>

        <TabsContent value="episodes">
          <EpisodicMemoryViewer />
        </TabsContent>

        <TabsContent value="knowledge">
          <KnowledgeGraphViewer />
        </TabsContent>

        <TabsContent value="management">
          <MemoryManagementPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}
