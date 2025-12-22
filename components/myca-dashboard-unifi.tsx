"use client";

/**
 * MYCA Dashboard UniFi-Style Component
 * 
 * This component serves as a bridge to the full unifi-dashboard application.
 * For the complete dashboard experience, run the unifi-dashboard separately:
 *   cd unifi-dashboard && bun dev
 * 
 * This simplified version provides core functionality within the main Next.js app.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';

// ============== TYPES ==============
interface Agent {
  id: string;
  name: string;
  displayName: string;
  category: string;
  status: 'active' | 'idle' | 'error' | 'offline';
  lastActivity: string;
  tasksCompleted: number;
  tasksInProgress: number;
  downloadSpeed: number;
  uploadSpeed: number;
  experience: 'Excellent' | 'Good' | 'Fair' | 'Poor';
  uptime: string;
  ipAddress: string;
}

interface TopologyNode {
  id: string;
  type: 'orchestrator' | 'agent' | 'person' | 'database' | 'service' | 'external' | 'internet';
  name: string;
  x: number;
  y: number;
  status: 'online' | 'offline' | 'idle';
  category?: string;
}

interface TopologyConnection {
  source: string;
  target: string;
  type: 'data' | 'control' | 'command' | 'interaction';
  active: boolean;
  bandwidth?: number;
}

interface Flow {
  id: string;
  source: string;
  destination: string;
  service: string;
  risk: 'Low' | 'Medium' | 'High';
  direction: 'in' | 'out' | 'both';
  inBytes: string;
  outBytes: string;
  action: 'Allow' | 'Block';
  timestamp: string;
}

// ============== ICONS ==============
const Icons = {
  Brain: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.54"/>
      <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.54"/>
    </svg>
  ),
  Cpu: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/>
      <path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>
    </svg>
  ),
  Network: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="16" y="16" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/>
      <rect x="9" y="2" width="6" height="6" rx="1"/><path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3"/><line x1="12" y1="12" x2="12" y2="8"/>
    </svg>
  ),
  Activity: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  ),
  Mic: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
    </svg>
  ),
  Globe: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
    </svg>
  ),
  Person: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
    </svg>
  ),
  Database: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
    </svg>
  ),
};

// ============== TOPOLOGY MAP ==============
function TopologyMap({ 
  nodes, 
  connections, 
  onNodeClick 
}: { 
  nodes: TopologyNode[];
  connections: TopologyConnection[];
  onNodeClick: (node: TopologyNode) => void;
}) {
  const canvasRef = useRef<HTMLDivElement>(null);

  const getNodeIcon = (type: string, status: string) => {
    const isOnline = status === 'online';
    const color = isOnline ? 'text-blue-400' : 'text-gray-500';
    
    switch (type) {
      case 'internet':
        return <div className={`${color}`}><Icons.Globe /></div>;
      case 'orchestrator':
        return <div className={`${isOnline ? 'text-purple-400' : 'text-gray-500'}`}><Icons.Brain /></div>;
      case 'agent':
        return <div className={`${isOnline ? 'text-cyan-400' : 'text-gray-500'}`}><Icons.Cpu /></div>;
      case 'person':
        return <div className={`${isOnline ? 'text-green-400' : 'text-gray-500'}`}><Icons.Person /></div>;
      case 'database':
        return <div className={`${isOnline ? 'text-orange-400' : 'text-gray-500'}`}><Icons.Database /></div>;
      default:
        return <div className={color}><Icons.Network /></div>;
    }
  };

  return (
    <div ref={canvasRef} className="relative h-[600px] bg-[#040d19] rounded-lg overflow-hidden">
      {/* Grid background */}
      <div className="absolute inset-0 opacity-20" 
        style={{
          backgroundImage: 'radial-gradient(circle, #1e3a5f 1px, transparent 1px)',
          backgroundSize: '30px 30px'
        }}
      />
      
      {/* Connection lines */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none">
        <defs>
          <linearGradient id="flowGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.2"/>
            <stop offset="50%" stopColor="#3b82f6" stopOpacity="0.8"/>
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.2"/>
          </linearGradient>
        </defs>
        
        {connections.map((conn, index) => {
          const sourceNode = nodes.find(n => n.id === conn.source);
          const targetNode = nodes.find(n => n.id === conn.target);
          if (!sourceNode || !targetNode) return null;

          return (
            <g key={`${conn.source}-${conn.target}-${index}`}>
              <line
                x1={`${sourceNode.x}%`}
                y1={`${sourceNode.y}%`}
                x2={`${targetNode.x}%`}
                y2={`${targetNode.y}%`}
                stroke={conn.active ? '#3b82f6' : '#4b5563'}
                strokeWidth="2"
                strokeDasharray={conn.active ? '0' : '5,5'}
                opacity={conn.active ? 0.6 : 0.3}
              />
              {conn.active && (
                <circle r="4" fill="#22d3ee">
                  <animateMotion
                    dur="2s"
                    repeatCount="indefinite"
                    path={`M ${sourceNode.x * 10},${sourceNode.y * 6} L ${targetNode.x * 10},${targetNode.y * 6}`}
                  />
                </circle>
              )}
            </g>
          );
        })}
      </svg>

      {/* Nodes */}
      {nodes.map((node) => (
        <div
          key={node.id}
          className="absolute cursor-pointer transition-transform hover:scale-110"
          style={{
            left: `${node.x}%`,
            top: `${node.y}%`,
            transform: 'translate(-50%, -50%)',
          }}
          onClick={() => onNodeClick(node)}
        >
          <div className={`flex flex-col items-center ${
            node.type === 'orchestrator' 
              ? 'w-20 h-20' 
              : node.type === 'internet'
              ? 'w-16 h-16'
              : 'w-14 h-14'
          }`}>
            <div className={`flex items-center justify-center rounded-lg p-3 ${
              node.type === 'orchestrator'
                ? 'bg-gradient-to-br from-purple-500/30 to-blue-600/30 border-2 border-purple-500'
                : node.type === 'internet'
                ? 'bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/50 rounded-full'
                : node.type === 'person'
                ? 'bg-gradient-to-br from-green-500/20 to-emerald-600/20 border border-green-500/50 rounded-full'
                : 'bg-[#1a2744] border border-gray-600'
            }`}>
              {getNodeIcon(node.type, node.status)}
            </div>
            <div className={`absolute -bottom-1 -right-1 w-3 h-3 rounded-full border-2 border-[#040d19] ${
              node.status === 'online' ? 'bg-green-500' :
              node.status === 'idle' ? 'bg-yellow-500' : 'bg-gray-500'
            }`} />
          </div>
          <div className="mt-2 text-center">
            <div className="text-[10px] font-medium text-white max-w-[80px] truncate">{node.name}</div>
            {node.category && (
              <div className="text-[8px] text-gray-400 capitalize">{node.category}</div>
            )}
          </div>
        </div>
      ))}

      {/* Legend */}
      <div className="absolute bottom-4 left-4 flex gap-4 text-[10px]">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-gray-500">Online</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-yellow-500" />
          <span className="text-gray-500">Idle</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-gray-500" />
          <span className="text-gray-500">Offline</span>
        </div>
      </div>
    </div>
  );
}

// ============== FLOWS TABLE ==============
function FlowsTable({ flows }: { flows: Flow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#1e3a5f] text-left">
            <th className="py-3 px-4 font-medium text-gray-400">Source</th>
            <th className="py-3 px-4 font-medium text-gray-400">Destination</th>
            <th className="py-3 px-4 font-medium text-gray-400">Service</th>
            <th className="py-3 px-4 font-medium text-gray-400">Risk</th>
            <th className="py-3 px-4 font-medium text-gray-400">Action</th>
            <th className="py-3 px-4 font-medium text-gray-400">Time</th>
          </tr>
        </thead>
        <tbody>
          {flows.map((flow) => (
            <tr key={flow.id} className="border-b border-[#1e3a5f]/50 hover:bg-[#1e3a5f]/30">
              <td className="py-3 px-4 text-white">{flow.source}</td>
              <td className="py-3 px-4 text-gray-300">{flow.destination}</td>
              <td className="py-3 px-4">
                <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs">{flow.service}</span>
              </td>
              <td className="py-3 px-4">
                <span className={`${
                  flow.risk === 'Low' ? 'text-green-400' :
                  flow.risk === 'Medium' ? 'text-yellow-400' : 'text-red-400'
                }`}>{flow.risk}</span>
              </td>
              <td className="py-3 px-4">
                <span className={`${flow.action === 'Allow' ? 'text-green-400' : 'text-red-400'}`}>{flow.action}</span>
              </td>
              <td className="py-3 px-4 text-gray-500 text-xs">{new Date(flow.timestamp).toLocaleTimeString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============== MAIN COMPONENT ==============
export default function MycaDashboardUnifi() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [nodes, setNodes] = useState<TopologyNode[]>([]);
  const [connections, setConnections] = useState<TopologyConnection[]>([]);
  const [flows, setFlows] = useState<Flow[]>([]);
  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'topology' | 'flows'>('overview');

  useEffect(() => {
    // Initialize with demo data
    setAgents([
      { id: 'myca', name: 'MYCA', displayName: 'MYCA Orchestrator', category: 'core', status: 'active', lastActivity: 'Just now', tasksCompleted: 1247, tasksInProgress: 3, downloadSpeed: 159, uploadSpeed: 136, experience: 'Excellent', uptime: '2w 4d 4h 0m', ipAddress: '10.0.0.1' },
      { id: 'financial', name: 'FinancialAgent', displayName: 'Financial Agent', category: 'financial', status: 'active', lastActivity: '2m ago', tasksCompleted: 89, tasksInProgress: 1, downloadSpeed: 49.4, uploadSpeed: 5.36, experience: 'Excellent', uptime: '8d 20m 11s', ipAddress: '10.0.0.172' },
      { id: 'mycology', name: 'MycologyBioAgent', displayName: 'Mycology Research', category: 'mycology', status: 'active', lastActivity: '1m ago', tasksCompleted: 234, tasksInProgress: 2, downloadSpeed: 36.1, uploadSpeed: 49.4, experience: 'Excellent', uptime: '8d 20m 11s', ipAddress: '10.0.0.248' },
      { id: 'project', name: 'ProjectManagerAgent', displayName: 'Project Manager', category: 'core', status: 'active', lastActivity: '30s ago', tasksCompleted: 412, tasksInProgress: 5, downloadSpeed: 0, uploadSpeed: 0, experience: 'Excellent', uptime: '17d 47m 31s', ipAddress: '10.0.0.90' },
      { id: 'opportunity', name: 'OpportunityScout', displayName: 'Opportunity Scout', category: 'research', status: 'active', lastActivity: '5m ago', tasksCompleted: 78, tasksInProgress: 1, downloadSpeed: 25, uploadSpeed: 12, experience: 'Good', uptime: '6d 1h 33m 28s', ipAddress: '10.0.0.91' },
      { id: 'marketing', name: 'MarketingAgent', displayName: 'Marketing Agent', category: 'communication', status: 'idle', lastActivity: '15m ago', tasksCompleted: 56, tasksInProgress: 0, downloadSpeed: 0, uploadSpeed: 0, experience: 'Good', uptime: '1d 3h 37m 6s', ipAddress: '10.0.0.228' },
      { id: 'dao', name: 'MycoDAOAgent', displayName: 'MycoDAO Agent', category: 'dao', status: 'active', lastActivity: '1h ago', tasksCompleted: 23, tasksInProgress: 0, downloadSpeed: 32, uploadSpeed: 48, experience: 'Excellent', uptime: '18d 3h 59m 58s', ipAddress: '10.0.0.105' },
      { id: 'dashboard', name: 'DashboardAgent', displayName: 'Dashboard Agent', category: 'core', status: 'active', lastActivity: 'Just now', tasksCompleted: 890, tasksInProgress: 1, downloadSpeed: 0, uploadSpeed: 24, experience: 'Excellent', uptime: '17d 45m 51s', ipAddress: '10.0.0.184' },
    ]);

    setNodes([
      { id: 'internet', type: 'internet', name: 'Wyyerd Fiber', x: 50, y: 8, status: 'online' },
      { id: 'myca', type: 'orchestrator', name: 'MYCA Orchestrator', x: 50, y: 28, status: 'online' },
      { id: 'database', type: 'database', name: 'PostgreSQL', x: 20, y: 50, status: 'online' },
      { id: 'n8n', type: 'service', name: 'n8n Workflows', x: 50, y: 50, status: 'online' },
      { id: 'human', type: 'person', name: 'Human Operator', x: 80, y: 50, status: 'online' },
      { id: 'financial', type: 'agent', name: 'Financial Agent', x: 15, y: 75, status: 'online', category: 'financial' },
      { id: 'mycology', type: 'agent', name: 'Mycology Research', x: 30, y: 78, status: 'online', category: 'mycology' },
      { id: 'project', type: 'agent', name: 'Project Manager', x: 45, y: 80, status: 'online', category: 'core' },
      { id: 'opportunity', type: 'agent', name: 'Opportunity Scout', x: 55, y: 80, status: 'online', category: 'research' },
      { id: 'marketing', type: 'agent', name: 'Marketing Agent', x: 70, y: 78, status: 'idle', category: 'communication' },
      { id: 'dao', type: 'agent', name: 'MycoDAO Agent', x: 85, y: 75, status: 'online', category: 'dao' },
    ]);

    setConnections([
      { source: 'internet', target: 'myca', type: 'data', active: true, bandwidth: 1000 },
      { source: 'myca', target: 'database', type: 'data', active: true, bandwidth: 500 },
      { source: 'myca', target: 'n8n', type: 'control', active: true, bandwidth: 100 },
      { source: 'myca', target: 'human', type: 'interaction', active: true, bandwidth: 50 },
      { source: 'myca', target: 'financial', type: 'control', active: true, bandwidth: 55 },
      { source: 'myca', target: 'mycology', type: 'control', active: true, bandwidth: 85 },
      { source: 'myca', target: 'project', type: 'control', active: true, bandwidth: 0 },
      { source: 'myca', target: 'opportunity', type: 'control', active: true, bandwidth: 37 },
      { source: 'myca', target: 'marketing', type: 'control', active: false, bandwidth: 0 },
      { source: 'myca', target: 'dao', type: 'control', active: true, bandwidth: 80 },
      { source: 'human', target: 'myca', type: 'command', active: true, bandwidth: 5 },
    ]);

    setFlows([
      { id: '1', source: 'MYCA Orchestrator', destination: 'Financial Agent', service: 'HTTPS', risk: 'Low', direction: 'out', inBytes: '4.6 KB', outBytes: '1.2 KB', action: 'Allow', timestamp: new Date().toISOString() },
      { id: '2', source: 'MYCA Orchestrator', destination: 'Mycology Research', service: 'HTTPS', risk: 'Low', direction: 'out', inBytes: '2.1 KB', outBytes: '0.8 KB', action: 'Allow', timestamp: new Date().toISOString() },
      { id: '3', source: 'Human Operator', destination: 'MYCA Orchestrator', service: 'WebSocket', risk: 'Low', direction: 'both', inBytes: '1.5 KB', outBytes: '2.8 KB', action: 'Allow', timestamp: new Date().toISOString() },
      { id: '4', source: 'Project Manager', destination: 'n8n Workflows', service: 'HTTP', risk: 'Low', direction: 'both', inBytes: '8.9 KB', outBytes: '3.2 KB', action: 'Allow', timestamp: new Date().toISOString() },
      { id: '5', source: 'Financial Agent', destination: 'PostgreSQL', service: 'SQL', risk: 'Low', direction: 'both', inBytes: '15.2 KB', outBytes: '0.3 KB', action: 'Allow', timestamp: new Date().toISOString() },
    ]);
  }, []);

  const activeAgents = agents.filter(a => a.status === 'active').length;
  const totalTraffic = agents.reduce((sum, a) => sum + a.downloadSpeed + a.uploadSpeed, 0);

  return (
    <div className="min-h-screen bg-[#0a1929] text-white flex">
      {/* Left Sidebar */}
      <aside className="w-64 bg-[#0d2137] border-r border-[#1e3a5f] flex flex-col">
        <div className="p-4 border-b border-[#1e3a5f]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
              <Icons.Brain />
            </div>
            <div>
              <div className="text-sm font-semibold">MYCA Dashboard</div>
              <div className="text-[10px] text-gray-500">MAS v10.0.162</div>
            </div>
          </div>
        </div>

        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4">
            <div>
              <div className="text-xs text-gray-400 mb-2">Active Agents</div>
              <div className="text-2xl font-bold text-green-500">{activeAgents}</div>
              <div className="text-xs text-gray-500">of {agents.length} total</div>
            </div>

            <div className="border-t border-[#1e3a5f] pt-4">
              <div className="text-xs text-gray-400 mb-2">System Traffic</div>
              <div className="flex gap-2 text-sm">
                <span className="text-cyan-400">↓ {totalTraffic.toFixed(1)} Kbps</span>
              </div>
            </div>

            <div className="border-t border-[#1e3a5f] pt-4">
              <div className="text-xs font-semibold mb-2">Recent Agents</div>
              {agents.slice(0, 5).map(agent => (
                <div key={agent.id} className="flex items-center gap-2 py-1 text-xs">
                  <div className={`w-2 h-2 rounded-full ${
                    agent.status === 'active' ? 'bg-green-500' : 'bg-yellow-500'
                  }`} />
                  <span className="truncate flex-1">{agent.displayName}</span>
                </div>
              ))}
            </div>
          </div>
        </ScrollArea>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        <header className="bg-[#0d2137] border-b border-[#1e3a5f] px-6 py-4 flex items-center justify-between">
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
            <TabsList className="bg-transparent gap-1">
              <TabsTrigger value="overview" className="data-[state=active]:bg-[#1e3a5f]">Overview</TabsTrigger>
              <TabsTrigger value="topology" className="data-[state=active]:bg-[#1e3a5f]">Topology</TabsTrigger>
              <TabsTrigger value="flows" className="data-[state=active]:bg-[#1e3a5f]">Flows</TabsTrigger>
            </TabsList>
          </Tabs>
          
          <Button className="bg-purple-600 hover:bg-purple-700 flex items-center gap-2">
            <Icons.Mic />
            Talk to MYCA
          </Button>
        </header>

        <div className="flex-1 overflow-auto p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div className="grid grid-cols-4 gap-4">
                <Card className="bg-[#0d2137] border-[#1e3a5f]">
                  <CardContent className="p-4">
                    <div className="text-xs text-gray-400 uppercase">Active Agents</div>
                    <div className="text-3xl font-bold text-green-500">{activeAgents}</div>
                  </CardContent>
                </Card>
                <Card className="bg-[#0d2137] border-[#1e3a5f]">
                  <CardContent className="p-4">
                    <div className="text-xs text-gray-400 uppercase">Tasks/Hour</div>
                    <div className="text-3xl font-bold">124</div>
                  </CardContent>
                </Card>
                <Card className="bg-[#0d2137] border-[#1e3a5f]">
                  <CardContent className="p-4">
                    <div className="text-xs text-gray-400 uppercase">Uptime</div>
                    <div className="text-3xl font-bold">2w 4d</div>
                  </CardContent>
                </Card>
                <Card className="bg-[#0d2137] border-[#1e3a5f]">
                  <CardContent className="p-4">
                    <div className="text-xs text-gray-400 uppercase">Latency</div>
                    <div className="text-3xl font-bold text-green-500">5ms</div>
                  </CardContent>
                </Card>
              </div>

              <Card className="bg-[#0d2137] border-[#1e3a5f]">
                <CardHeader>
                  <CardTitle className="text-sm">Agent Topology Preview</CardTitle>
                </CardHeader>
                <CardContent>
                  <TopologyMap nodes={nodes} connections={connections} onNodeClick={setSelectedNode} />
                </CardContent>
              </Card>
            </div>
          )}

          {activeTab === 'topology' && (
            <TopologyMap nodes={nodes} connections={connections} onNodeClick={setSelectedNode} />
          )}

          {activeTab === 'flows' && (
            <Card className="bg-[#0d2137] border-[#1e3a5f]">
              <CardHeader>
                <CardTitle className="text-sm">Agent Communication Flows</CardTitle>
              </CardHeader>
              <CardContent>
                <FlowsTable flows={flows} />
              </CardContent>
            </Card>
          )}
        </div>
      </main>

      {/* Right Sidebar - Selected Node Details */}
      {selectedNode && (
        <aside className="w-72 bg-[#0d2137] border-l border-[#1e3a5f] p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-medium">Node Details</h2>
            <button onClick={() => setSelectedNode(null)} className="text-gray-400 hover:text-white">×</button>
          </div>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between py-2 border-b border-[#1e3a5f]">
              <span className="text-gray-400">Name</span>
              <span>{selectedNode.name}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#1e3a5f]">
              <span className="text-gray-400">Type</span>
              <span className="capitalize">{selectedNode.type}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-[#1e3a5f]">
              <span className="text-gray-400">Status</span>
              <Badge className={selectedNode.status === 'online' ? 'bg-green-500' : 'bg-yellow-500'}>
                {selectedNode.status}
              </Badge>
            </div>
            {selectedNode.category && (
              <div className="flex justify-between py-2 border-b border-[#1e3a5f]">
                <span className="text-gray-400">Category</span>
                <span className="capitalize">{selectedNode.category}</span>
              </div>
            )}
          </div>
          <Button className="w-full mt-4 bg-purple-600 hover:bg-purple-700">
            Send Command
          </Button>
        </aside>
      )}
    </div>
  );
}
