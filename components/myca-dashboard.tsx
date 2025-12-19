"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';

// Icons (using simple SVG for UniFi-like look)
const IconActivity = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
  </svg>
);

const IconServer = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
    <line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/>
  </svg>
);

const IconCpu = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="4" y="4" width="16" height="16" rx="2" ry="2"/>
    <rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/>
    <line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/>
    <line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/>
    <line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>
  </svg>
);

const IconBrain = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.54"/>
    <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.54"/>
  </svg>
);

const IconMic = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
  </svg>
);

const IconNetwork = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="16" y="16" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/>
    <rect x="9" y="2" width="6" height="6" rx="1"/><path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3"/>
    <line x1="12" y1="12" x2="12" y2="8"/>
  </svg>
);

// Types
interface Agent {
  id: string;
  name: string;
  displayName: string;
  category: string;
  status: 'active' | 'idle' | 'error' | 'offline';
  lastActivity: string;
  tasksCompleted: number;
  tasksInProgress: number;
  cpuUsage: number;
  memoryUsage: number;
}

interface Message {
  id: string;
  from: string;
  to: string;
  type: 'request' | 'response' | 'event' | 'notification';
  content: string;
  timestamp: string;
}

interface SystemMetrics {
  totalAgents: number;
  activeAgents: number;
  totalTasks: number;
  completedTasks: number;
  messagesPerSecond: number;
  uptime: string;
  cpuUsage: number;
  memoryUsage: number;
}

interface Insight {
  id: string;
  type: 'info' | 'warning' | 'success' | 'error';
  title: string;
  description: string;
  timestamp: string;
  agent?: string;
}

// MYCA Dashboard Component - UniFi Style
export default function MycaDashboard() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [voiceTranscript, setVoiceTranscript] = useState('');

  // Fetch data from API
  const fetchData = useCallback(async () => {
    try {
      // Fetch agents from registry
      const agentsRes = await fetch('/api/agents/registry');
      if (agentsRes.ok) {
        const data = await agentsRes.json();
        setAgents(data.agents || []);
      }

      // Fetch system metrics
      const metricsRes = await fetch('/api/metrics');
      if (metricsRes.ok) {
        const data = await metricsRes.json();
        setMetrics(data);
      }

      // Fetch recent messages/activity
      const activityRes = await fetch('/api/activity/recent');
      if (activityRes.ok) {
        const data = await activityRes.json();
        setMessages(data.messages || []);
        setInsights(data.insights || []);
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [fetchData]);

  // Mock data for initial display
  useEffect(() => {
    if (agents.length === 0) {
      setAgents([
        { id: 'myca', name: 'MYCA', displayName: 'MYCA Orchestrator', category: 'core', status: 'active', lastActivity: 'Just now', tasksCompleted: 1247, tasksInProgress: 3, cpuUsage: 12, memoryUsage: 45 },
        { id: 'financial', name: 'FinancialAgent', displayName: 'Financial Agent', category: 'financial', status: 'active', lastActivity: '2m ago', tasksCompleted: 89, tasksInProgress: 1, cpuUsage: 5, memoryUsage: 23 },
        { id: 'marketing', name: 'MarketingAgent', displayName: 'Marketing Agent', category: 'communication', status: 'idle', lastActivity: '15m ago', tasksCompleted: 56, tasksInProgress: 0, cpuUsage: 0, memoryUsage: 18 },
        { id: 'mycology', name: 'MycologyBioAgent', displayName: 'Mycology Research', category: 'mycology', status: 'active', lastActivity: '1m ago', tasksCompleted: 234, tasksInProgress: 2, cpuUsage: 28, memoryUsage: 67 },
        { id: 'project', name: 'ProjectManagerAgent', displayName: 'Project Manager', category: 'core', status: 'active', lastActivity: '30s ago', tasksCompleted: 412, tasksInProgress: 5, cpuUsage: 8, memoryUsage: 31 },
        { id: 'opportunity', name: 'OpportunityScout', displayName: 'Opportunity Scout', category: 'research', status: 'active', lastActivity: '5m ago', tasksCompleted: 78, tasksInProgress: 1, cpuUsage: 15, memoryUsage: 42 },
        { id: 'dao', name: 'MycoDAOAgent', displayName: 'MycoDAO Agent', category: 'dao', status: 'idle', lastActivity: '1h ago', tasksCompleted: 23, tasksInProgress: 0, cpuUsage: 0, memoryUsage: 12 },
        { id: 'dashboard', name: 'DashboardAgent', displayName: 'Dashboard Agent', category: 'core', status: 'active', lastActivity: 'Just now', tasksCompleted: 890, tasksInProgress: 1, cpuUsage: 3, memoryUsage: 15 },
      ]);
      setMetrics({
        totalAgents: 42,
        activeAgents: 6,
        totalTasks: 3029,
        completedTasks: 2987,
        messagesPerSecond: 12.4,
        uptime: '3d 14h 22m',
        cpuUsage: 23,
        memoryUsage: 47,
      });
      setInsights([
        { id: '1', type: 'success', title: 'Task Completed', description: 'OpportunityScout found 3 new business opportunities', timestamp: '2m ago', agent: 'OpportunityScout' },
        { id: '2', type: 'info', title: 'Research Update', description: 'MycologyBioAgent added 12 new species to database', timestamp: '15m ago', agent: 'MycologyBioAgent' },
        { id: '3', type: 'warning', title: 'High Memory Usage', description: 'MycologyBioAgent using 67% memory during analysis', timestamp: '20m ago', agent: 'MycologyBioAgent' },
        { id: '4', type: 'success', title: 'Voice Command', description: 'Successfully processed Morgan\'s voice request', timestamp: '1h ago', agent: 'MYCA' },
      ]);
      setMessages([
        { id: '1', from: 'Morgan', to: 'MYCA', type: 'request', content: 'What is the status of all agents?', timestamp: '1m ago' },
        { id: '2', from: 'MYCA', to: 'Morgan', type: 'response', content: 'All 6 active agents are running normally. 42 total agents registered.', timestamp: '1m ago' },
        { id: '3', from: 'MYCA', to: 'FinancialAgent', type: 'request', content: 'Generate monthly expense report', timestamp: '5m ago' },
        { id: '4', from: 'FinancialAgent', to: 'MYCA', type: 'response', content: 'Report generated: Total expenses $12,450.00', timestamp: '4m ago' },
      ]);
    }
  }, [agents.length]);

  // Status badge color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500';
      case 'idle': return 'bg-yellow-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getInsightColor = (type: string) => {
    switch (type) {
      case 'success': return 'border-green-500 bg-green-500/10';
      case 'warning': return 'border-yellow-500 bg-yellow-500/10';
      case 'error': return 'border-red-500 bg-red-500/10';
      default: return 'border-blue-500 bg-blue-500/10';
    }
  };

  return (
    <div className="min-h-screen bg-[#0a1929] text-white">
      {/* Header - UniFi style */}
      <header className="bg-[#0d2137] border-b border-[#1e3a5f] px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-purple-600 flex items-center justify-center">
                <IconBrain />
              </div>
              <div>
                <h1 className="text-xl font-semibold">MYCA Dashboard</h1>
                <p className="text-xs text-gray-400">Mycosoft Multi-Agent System</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <Button 
              variant={isVoiceActive ? "destructive" : "default"}
              size="sm"
              onClick={() => setIsVoiceActive(!isVoiceActive)}
              className="flex items-center gap-2"
            >
              <IconMic />
              {isVoiceActive ? 'Listening...' : 'Talk to MYCA'}
            </Button>
            <Badge variant="outline" className="bg-green-500/20 text-green-400 border-green-500">
              System Online
            </Badge>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Main Content */}
        <main className="flex-1 p-6">
          {/* Metrics Overview - UniFi style cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <Card className="bg-[#0d2137] border-[#1e3a5f]">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wide">Active Agents</p>
                    <p className="text-3xl font-bold text-white">{metrics?.activeAgents || 0}</p>
                    <p className="text-xs text-gray-500">of {metrics?.totalAgents || 0} total</p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400">
                    <IconServer />
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-[#0d2137] border-[#1e3a5f]">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wide">Tasks Completed</p>
                    <p className="text-3xl font-bold text-white">{metrics?.completedTasks?.toLocaleString() || 0}</p>
                    <p className="text-xs text-gray-500">{(metrics?.totalTasks || 0) - (metrics?.completedTasks || 0)} in progress</p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center text-green-400">
                    <IconActivity />
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-[#0d2137] border-[#1e3a5f]">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wide">Messages/sec</p>
                    <p className="text-3xl font-bold text-white">{metrics?.messagesPerSecond?.toFixed(1) || 0}</p>
                    <p className="text-xs text-gray-500">Inter-agent communication</p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400">
                    <IconNetwork />
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card className="bg-[#0d2137] border-[#1e3a5f]">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wide">System Uptime</p>
                    <p className="text-3xl font-bold text-white">{metrics?.uptime || '0h'}</p>
                    <p className="text-xs text-gray-500">CPU: {metrics?.cpuUsage || 0}% | RAM: {metrics?.memoryUsage || 0}%</p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-cyan-500/20 flex items-center justify-center text-cyan-400">
                    <IconCpu />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Tabs for different views */}
          <Tabs defaultValue="topology" className="space-y-4">
            <TabsList className="bg-[#0d2137] border border-[#1e3a5f]">
              <TabsTrigger value="topology" className="data-[state=active]:bg-blue-600">Topology</TabsTrigger>
              <TabsTrigger value="agents" className="data-[state=active]:bg-blue-600">Agents</TabsTrigger>
              <TabsTrigger value="activity" className="data-[state=active]:bg-blue-600">Activity</TabsTrigger>
              <TabsTrigger value="insights" className="data-[state=active]:bg-blue-600">Insights</TabsTrigger>
            </TabsList>

            {/* Topology View */}
            <TabsContent value="topology">
              <Card className="bg-[#0d2137] border-[#1e3a5f] min-h-[500px]">
                <CardHeader>
                  <CardTitle className="text-white">Agent Topology</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="relative h-[450px] bg-[#081422] rounded-lg overflow-hidden">
                    {/* MYCA Central Node */}
                    <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-10">
                      <div 
                        className="w-24 h-24 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center cursor-pointer hover:scale-110 transition-transform shadow-lg shadow-blue-500/30"
                        onClick={() => setSelectedAgent(agents.find(a => a.id === 'myca') || null)}
                      >
                        <div className="text-center">
                          <IconBrain />
                          <span className="text-xs font-bold block mt-1">MYCA</span>
                        </div>
                      </div>
                      {/* Pulse animation */}
                      <div className="absolute inset-0 rounded-full bg-blue-500/30 animate-ping" style={{ animationDuration: '2s' }} />
                    </div>

                    {/* Agent Nodes arranged in circle */}
                    {agents.filter(a => a.id !== 'myca').map((agent, i) => {
                      const totalAgents = agents.length - 1;
                      const angle = (i * 2 * Math.PI) / totalAgents - Math.PI / 2;
                      const radius = 180;
                      const x = Math.cos(angle) * radius;
                      const y = Math.sin(angle) * radius;
                      
                      return (
                        <React.Fragment key={agent.id}>
                          {/* Connection line to MYCA */}
                          <svg className="absolute inset-0 w-full h-full pointer-events-none">
                            <line
                              x1="50%"
                              y1="50%"
                              x2={`calc(50% + ${x}px)`}
                              y2={`calc(50% + ${y}px)`}
                              stroke={agent.status === 'active' ? '#3b82f6' : '#4b5563'}
                              strokeWidth="2"
                              strokeDasharray={agent.status === 'active' ? 'none' : '5,5'}
                              opacity="0.5"
                            />
                          </svg>
                          
                          {/* Agent Node */}
                          <div
                            className="absolute transform -translate-x-1/2 -translate-y-1/2 cursor-pointer hover:scale-110 transition-transform"
                            style={{
                              left: `calc(50% + ${x}px)`,
                              top: `calc(50% + ${y}px)`,
                            }}
                            onClick={() => setSelectedAgent(agent)}
                          >
                            <div className={`w-16 h-16 rounded-full flex items-center justify-center ${
                              agent.status === 'active' ? 'bg-green-600/80' : 
                              agent.status === 'idle' ? 'bg-yellow-600/80' : 'bg-gray-600/80'
                            } shadow-lg`}>
                              <div className="text-center">
                                <IconServer />
                                <span className="text-[10px] font-medium block mt-0.5 truncate max-w-[50px]">
                                  {agent.displayName.split(' ')[0]}
                                </span>
                              </div>
                            </div>
                            {agent.tasksInProgress > 0 && (
                              <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-blue-500 flex items-center justify-center text-[10px] font-bold">
                                {agent.tasksInProgress}
                              </div>
                            )}
                          </div>
                        </React.Fragment>
                      );
                    })}

                    {/* Legend */}
                    <div className="absolute bottom-4 left-4 flex gap-4 text-xs">
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full bg-green-500" />
                        <span className="text-gray-400">Active</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full bg-yellow-500" />
                        <span className="text-gray-400">Idle</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-3 h-3 rounded-full bg-gray-500" />
                        <span className="text-gray-400">Offline</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Agents List View */}
            <TabsContent value="agents">
              <Card className="bg-[#0d2137] border-[#1e3a5f]">
                <CardHeader>
                  <CardTitle className="text-white">All Agents</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {agents.map(agent => (
                      <div 
                        key={agent.id}
                        className="flex items-center justify-between p-4 bg-[#081422] rounded-lg hover:bg-[#0d2137] cursor-pointer transition-colors"
                        onClick={() => setSelectedAgent(agent)}
                      >
                        <div className="flex items-center gap-4">
                          <div className={`w-10 h-10 rounded-full ${getStatusColor(agent.status)} flex items-center justify-center`}>
                            <IconServer />
                          </div>
                          <div>
                            <h3 className="font-medium text-white">{agent.displayName}</h3>
                            <p className="text-xs text-gray-400">{agent.category} • {agent.lastActivity}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-6 text-sm">
                          <div className="text-right">
                            <p className="text-white">{agent.tasksCompleted}</p>
                            <p className="text-xs text-gray-400">completed</p>
                          </div>
                          <div className="text-right">
                            <p className="text-white">{agent.tasksInProgress}</p>
                            <p className="text-xs text-gray-400">in progress</p>
                          </div>
                          <div className="w-20">
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-gray-400">CPU</span>
                              <span className="text-white">{agent.cpuUsage}%</span>
                            </div>
                            <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-blue-500 rounded-full transition-all"
                                style={{ width: `${agent.cpuUsage}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Activity Feed */}
            <TabsContent value="activity">
              <Card className="bg-[#0d2137] border-[#1e3a5f]">
                <CardHeader>
                  <CardTitle className="text-white">Live Activity</CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[400px]">
                    <div className="space-y-3">
                      {messages.map(msg => (
                        <div key={msg.id} className="flex items-start gap-3 p-3 bg-[#081422] rounded-lg">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                            msg.type === 'request' ? 'bg-blue-600' : 
                            msg.type === 'response' ? 'bg-green-600' : 
                            msg.type === 'event' ? 'bg-purple-600' : 'bg-yellow-600'
                          }`}>
                            {msg.from.charAt(0)}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-medium text-white">{msg.from}</span>
                              <span className="text-gray-500">→</span>
                              <span className="text-gray-400">{msg.to}</span>
                              <Badge variant="outline" className="text-[10px] ml-auto">
                                {msg.type}
                              </Badge>
                            </div>
                            <p className="text-sm text-gray-300">{msg.content}</p>
                            <p className="text-xs text-gray-500 mt-1">{msg.timestamp}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Insights */}
            <TabsContent value="insights">
              <Card className="bg-[#0d2137] border-[#1e3a5f]">
                <CardHeader>
                  <CardTitle className="text-white">System Insights</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {insights.map(insight => (
                      <div 
                        key={insight.id} 
                        className={`p-4 rounded-lg border-l-4 ${getInsightColor(insight.type)}`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <h4 className="font-medium text-white">{insight.title}</h4>
                          <span className="text-xs text-gray-500">{insight.timestamp}</span>
                        </div>
                        <p className="text-sm text-gray-300">{insight.description}</p>
                        {insight.agent && (
                          <Badge variant="outline" className="mt-2 text-xs">
                            {insight.agent}
                          </Badge>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </main>

        {/* Right Sidebar - Agent Details */}
        {selectedAgent && (
          <aside className="w-80 bg-[#0d2137] border-l border-[#1e3a5f] p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-lg">Agent Details</h2>
              <Button variant="ghost" size="sm" onClick={() => setSelectedAgent(null)}>×</Button>
            </div>
            
            <div className="space-y-4">
              <div className="text-center p-4 bg-[#081422] rounded-lg">
                <div className={`w-20 h-20 rounded-full ${getStatusColor(selectedAgent.status)} mx-auto mb-3 flex items-center justify-center`}>
                  <IconServer />
                </div>
                <h3 className="font-bold text-xl">{selectedAgent.displayName}</h3>
                <p className="text-sm text-gray-400">{selectedAgent.category}</p>
                <Badge className={`mt-2 ${getStatusColor(selectedAgent.status)}`}>
                  {selectedAgent.status}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#081422] p-3 rounded-lg text-center">
                  <p className="text-2xl font-bold text-white">{selectedAgent.tasksCompleted}</p>
                  <p className="text-xs text-gray-400">Tasks Completed</p>
                </div>
                <div className="bg-[#081422] p-3 rounded-lg text-center">
                  <p className="text-2xl font-bold text-blue-400">{selectedAgent.tasksInProgress}</p>
                  <p className="text-xs text-gray-400">In Progress</p>
                </div>
              </div>

              <div className="bg-[#081422] p-3 rounded-lg">
                <p className="text-xs text-gray-400 mb-2">Resource Usage</p>
                <div className="space-y-2">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span>CPU</span>
                      <span>{selectedAgent.cpuUsage}%</span>
                    </div>
                    <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-blue-500 rounded-full"
                        style={{ width: `${selectedAgent.cpuUsage}%` }}
                      />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span>Memory</span>
                      <span>{selectedAgent.memoryUsage}%</span>
                    </div>
                    <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-green-500 rounded-full"
                        style={{ width: `${selectedAgent.memoryUsage}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-[#081422] p-3 rounded-lg">
                <p className="text-xs text-gray-400 mb-1">Last Activity</p>
                <p className="text-sm text-white">{selectedAgent.lastActivity}</p>
              </div>

              <Button className="w-full bg-blue-600 hover:bg-blue-700">
                Send Command
              </Button>
            </div>
          </aside>
        )}
      </div>

      {/* Voice Overlay */}
      {isVoiceActive && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="text-center">
            <div className="w-32 h-32 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 mx-auto mb-6 flex items-center justify-center animate-pulse">
              <IconMic />
            </div>
            <h2 className="text-2xl font-bold mb-2">Listening...</h2>
            <p className="text-gray-400 mb-4">Speak to MYCA</p>
            {voiceTranscript && (
              <p className="text-white bg-white/10 p-3 rounded-lg max-w-md mx-auto">{voiceTranscript}</p>
            )}
            <Button 
              variant="destructive" 
              className="mt-6"
              onClick={() => setIsVoiceActive(false)}
            >
              Stop Listening
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
