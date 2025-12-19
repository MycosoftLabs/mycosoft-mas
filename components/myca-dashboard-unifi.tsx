"use client";

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';

// ============== ICONS (UniFi-style) ==============
const Icons = {
  Brain: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 4.44-2.54"/>
      <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-4.44-2.54"/>
    </svg>
  ),
  Server: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/>
      <circle cx="6" cy="6" r="1"/><circle cx="6" cy="18" r="1"/>
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
  Router: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="2" y="14" width="20" height="8" rx="2"/><path d="M12 6v8"/><path d="M8 6h8"/>
      <circle cx="6" cy="18" r="1"/><circle cx="10" cy="18" r="1"/>
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
  ChevronDown: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="6 9 12 15 18 9"/>
    </svg>
  ),
  ChevronRight: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="9 18 15 12 9 6"/>
    </svg>
  ),
  ArrowDown: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/>
    </svg>
  ),
  ArrowUp: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
    </svg>
  ),
  Activity: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  ),
  Settings: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>
  ),
  Search: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
  ),
  Check: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  ),
};

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
  downloadSpeed: number; // Kbps
  uploadSpeed: number; // Kbps
  experience: 'Excellent' | 'Good' | 'Fair' | 'Poor';
  uptime: string;
  ipAddress: string;
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

interface TopItem {
  name: string;
  icon?: string;
  value: string;
  count?: number;
}

// ============== SIDEBAR SECTION COMPONENT ==============
function SidebarSection({ 
  title, 
  children, 
  defaultOpen = true 
}: { 
  title: string; 
  children: React.ReactNode; 
  defaultOpen?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <div className="border-b border-[#1e3a5f] py-2">
      <button 
        className="flex items-center justify-between w-full px-4 py-2 text-xs text-gray-400 uppercase tracking-wider hover:text-white"
        onClick={() => setIsOpen(!isOpen)}
      >
        {title}
        {isOpen ? <Icons.ChevronDown /> : <Icons.ChevronRight />}
      </button>
      {isOpen && <div className="px-4 py-1">{children}</div>}
    </div>
  );
}

// ============== FILTER CHECKBOX COMPONENT ==============
function FilterCheckbox({ 
  label, 
  count, 
  checked = false, 
  onChange 
}: { 
  label: string; 
  count?: number; 
  checked?: boolean; 
  onChange?: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between py-1.5 cursor-pointer hover:bg-[#1e3a5f]/30 px-2 rounded">
      <div className="flex items-center gap-2">
        <input 
          type="checkbox" 
          checked={checked} 
          onChange={(e) => onChange?.(e.target.checked)}
          className="w-4 h-4 rounded border-gray-600 bg-transparent text-blue-500 focus:ring-blue-500"
        />
        <span className="text-sm text-gray-300">{label}</span>
      </div>
      {count !== undefined && (
        <span className="text-xs text-gray-500">({count})</span>
      )}
    </label>
  );
}

// ============== TOPOLOGY MAP COMPONENT ==============
function TopologyMap({ agents, onAgentClick }: { agents: Agent[]; onAgentClick: (agent: Agent) => void }) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const [animationFrame, setAnimationFrame] = useState(0);

  // Animate connection lines
  useEffect(() => {
    const interval = setInterval(() => {
      setAnimationFrame(f => (f + 1) % 100);
    }, 50);
    return () => clearInterval(interval);
  }, []);

  const activeAgents = agents.filter(a => a.status === 'active' || a.status === 'idle');
  
  return (
    <div ref={canvasRef} className="relative h-[500px] bg-[#040d19] rounded-lg overflow-hidden">
      {/* Grid background */}
      <div className="absolute inset-0 opacity-20" 
        style={{
          backgroundImage: 'radial-gradient(circle, #1e3a5f 1px, transparent 1px)',
          backgroundSize: '30px 30px'
        }}
      />
      
      {/* Internet/Cloud icon at top */}
      <div className="absolute top-8 left-1/2 transform -translate-x-1/2">
        <div className="text-center">
          <div className="w-20 h-20 mx-auto mb-2 rounded-full bg-gradient-to-br from-cyan-400/20 to-blue-600/20 border border-cyan-500/50 flex items-center justify-center text-cyan-400">
            <Icons.Globe />
          </div>
          <span className="text-xs text-cyan-400">Wyyerd Fiber</span>
        </div>
      </div>
      
      {/* Connection line from Internet to MYCA */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none">
        <defs>
          <linearGradient id="flowGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.8"/>
            <stop offset="50%" stopColor="#3b82f6" stopOpacity="0.6"/>
            <stop offset="100%" stopColor="#22d3ee" stopOpacity="0.8"/>
          </linearGradient>
        </defs>
        <line x1="50%" y1="120" x2="50%" y2="200" stroke="url(#flowGradient)" strokeWidth="3" strokeDasharray="8,4">
          <animate attributeName="stroke-dashoffset" from="0" to="-24" dur="1s" repeatCount="indefinite"/>
        </line>
      </svg>
      
      {/* MYCA Central Node (like Dream Machine Pro Max) */}
      <div className="absolute top-[180px] left-1/2 transform -translate-x-1/2">
        <div className="text-center cursor-pointer group" onClick={() => onAgentClick(agents[0] || {} as Agent)}>
          <div className="relative">
            <div className="w-24 h-24 mx-auto mb-2 rounded-lg bg-gradient-to-br from-blue-500/30 to-purple-600/30 border-2 border-blue-500 flex items-center justify-center shadow-lg shadow-blue-500/30 group-hover:scale-105 transition-transform">
              <Icons.Router />
            </div>
            {/* Pulse animation */}
            <div className="absolute inset-0 w-24 h-24 mx-auto rounded-lg bg-blue-500/20 animate-ping" style={{animationDuration: '2s'}}/>
          </div>
          <span className="text-sm font-medium text-white">MYCA Orchestrator</span>
          <div className="flex items-center justify-center gap-3 text-xs text-gray-400 mt-1">
            <span className="flex items-center gap-1 text-cyan-400">
              <Icons.ArrowDown /> {(agents.reduce((sum, a) => sum + a.downloadSpeed, 0) / 1000).toFixed(1)} Kbps
            </span>
            <span className="flex items-center gap-1 text-green-400">
              <Icons.ArrowUp /> {(agents.reduce((sum, a) => sum + a.uploadSpeed, 0) / 1000).toFixed(1)} Kbps
            </span>
          </div>
        </div>
      </div>
      
      {/* Connection lines to agents */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none">
        {activeAgents.slice(0, 8).map((agent, i) => {
          const totalAgents = Math.min(activeAgents.length, 8);
          const startX = ((i + 1) / (totalAgents + 1)) * 100;
          return (
            <g key={agent.id}>
              <line 
                x1="50%" 
                y1="310" 
                x2={`${startX}%`} 
                y2="400"
                stroke={agent.status === 'active' ? '#3b82f6' : '#6b7280'}
                strokeWidth="2"
                strokeDasharray={agent.status === 'active' ? '0' : '5,5'}
                opacity="0.6"
              />
              {agent.status === 'active' && (
                <circle r="3" fill="#22d3ee">
                  <animateMotion 
                    dur="2s" 
                    repeatCount="indefinite"
                    path={`M ${canvasRef.current?.clientWidth ? canvasRef.current.clientWidth / 2 : 400},310 L ${(startX / 100) * (canvasRef.current?.clientWidth || 800)},400`}
                  />
                </circle>
              )}
            </g>
          );
        })}
      </svg>
      
      {/* Agent Nodes */}
      <div className="absolute bottom-8 left-0 right-0 flex justify-around px-8">
        {activeAgents.slice(0, 8).map((agent) => (
          <div 
            key={agent.id} 
            className="text-center cursor-pointer group"
            onClick={() => onAgentClick(agent)}
          >
            <div className={`w-16 h-16 mx-auto mb-2 rounded-lg flex items-center justify-center transition-all group-hover:scale-110 ${
              agent.status === 'active' 
                ? 'bg-[#1a2744] border border-blue-500/50 shadow-lg shadow-blue-500/20' 
                : 'bg-[#1a2744] border border-gray-600'
            }`}>
              <div className="text-gray-300">
                <Icons.Cpu />
              </div>
            </div>
            <span className="text-[10px] text-gray-300 block max-w-[80px] truncate">{agent.displayName}</span>
            {agent.status === 'active' && (
              <div className="flex items-center justify-center gap-2 text-[9px] mt-0.5">
                <span className="text-cyan-400 flex items-center">↓ {agent.downloadSpeed}</span>
                <span className="text-green-400 flex items-center">↑ {agent.uploadSpeed}</span>
              </div>
            )}
          </div>
        ))}
      </div>
      
      {/* Legend */}
      <div className="absolute bottom-4 left-4 flex gap-4 text-[10px]">
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-gray-500">Active</span>
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
      
      {/* Controls */}
      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex items-center gap-2 bg-[#0d2137] rounded-lg p-1 border border-[#1e3a5f]">
        <button className="p-1.5 rounded hover:bg-[#1e3a5f] text-gray-400 hover:text-white">
          <Icons.Network />
        </button>
        <button className="p-1.5 rounded hover:bg-[#1e3a5f] text-gray-400 hover:text-white">+</button>
        <button className="p-1.5 rounded hover:bg-[#1e3a5f] text-gray-400 hover:text-white">−</button>
      </div>
    </div>
  );
}

// ============== FLOWS TABLE COMPONENT ==============
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
            <th className="py-3 px-4 font-medium text-gray-400">Dir.</th>
            <th className="py-3 px-4 font-medium text-gray-400">In</th>
            <th className="py-3 px-4 font-medium text-gray-400">Out</th>
            <th className="py-3 px-4 font-medium text-gray-400">Action</th>
            <th className="py-3 px-4 font-medium text-gray-400">Date / Time</th>
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
                <span className={`flex items-center gap-1 ${
                  flow.risk === 'Low' ? 'text-green-400' : 
                  flow.risk === 'Medium' ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  <span className="w-2 h-2 rounded-full bg-current" />
                  <span className="w-2 h-2 rounded-full bg-current opacity-60" />
                </span>
              </td>
              <td className="py-3 px-4 text-gray-400">{flow.direction === 'in' ? '↓' : flow.direction === 'out' ? '↑' : '↕'}</td>
              <td className="py-3 px-4 text-gray-400">{flow.inBytes}</td>
              <td className="py-3 px-4 text-gray-400">{flow.outBytes}</td>
              <td className="py-3 px-4">
                <span className={`text-xs ${flow.action === 'Allow' ? 'text-green-400' : 'text-red-400'}`}>
                  {flow.action}
                </span>
              </td>
              <td className="py-3 px-4 text-gray-500 text-xs">{flow.timestamp}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============== CLIENT LIST TABLE ==============
function ClientList({ agents, onAgentClick }: { agents: Agent[]; onAgentClick: (agent: Agent) => void }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#1e3a5f] text-left">
            <th className="py-3 px-4 font-medium text-gray-400">Name</th>
            <th className="py-3 px-4 font-medium text-gray-400">Category</th>
            <th className="py-3 px-4 font-medium text-gray-400">Connection</th>
            <th className="py-3 px-4 font-medium text-gray-400">Experience</th>
            <th className="py-3 px-4 font-medium text-gray-400">Activity</th>
            <th className="py-3 px-4 font-medium text-gray-400">Download</th>
            <th className="py-3 px-4 font-medium text-gray-400">Upload</th>
            <th className="py-3 px-4 font-medium text-gray-400">Uptime</th>
          </tr>
        </thead>
        <tbody>
          {agents.map((agent) => (
            <tr 
              key={agent.id} 
              className="border-b border-[#1e3a5f]/50 hover:bg-[#1e3a5f]/30 cursor-pointer"
              onClick={() => onAgentClick(agent)}
            >
              <td className="py-3 px-4">
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${
                    agent.status === 'active' ? 'bg-green-500' : 
                    agent.status === 'idle' ? 'bg-yellow-500' : 'bg-gray-500'
                  }`} />
                  <span className="text-white">{agent.displayName}</span>
                </div>
              </td>
              <td className="py-3 px-4 text-gray-400 capitalize">{agent.category}</td>
              <td className="py-3 px-4 text-gray-400">MYCA Orchestrator</td>
              <td className="py-3 px-4">
                <span className={`${
                  agent.experience === 'Excellent' ? 'text-green-400' :
                  agent.experience === 'Good' ? 'text-blue-400' :
                  agent.experience === 'Fair' ? 'text-yellow-400' : 'text-red-400'
                }`}>{agent.experience}</span>
              </td>
              <td className="py-3 px-4">
                {agent.status === 'active' ? (
                  <span className="text-green-400">● Active</span>
                ) : (
                  <span className="text-gray-500">○ Idle</span>
                )}
              </td>
              <td className="py-3 px-4">
                <span className="text-cyan-400">↓ {agent.downloadSpeed} bps</span>
              </td>
              <td className="py-3 px-4">
                <span className="text-green-400">↑ {agent.uploadSpeed} bps</span>
              </td>
              <td className="py-3 px-4 text-gray-400">{agent.uptime}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============== TOP ITEMS GRID ==============
function TopItemsGrid({ title, items, showMore }: { title: string; items: TopItem[]; showMore?: boolean }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-400">{title}</h3>
        {showMore && <span className="text-xs text-blue-400 cursor-pointer hover:underline">See More</span>}
      </div>
      <div className="flex flex-wrap gap-2">
        {items.map((item, i) => (
          <div key={i} className="flex items-center gap-2 bg-[#1a2744] px-3 py-2 rounded-lg border border-[#1e3a5f] hover:border-blue-500/50 cursor-pointer transition-colors">
            <div className="w-8 h-8 rounded bg-[#0d2137] flex items-center justify-center text-gray-400 text-xs">
              {item.icon || item.name.charAt(0)}
            </div>
            <div className="text-xs">
              <div className="text-white truncate max-w-[80px]">{item.name}</div>
              <div className="text-gray-500">{item.value}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============== MAIN DASHBOARD COMPONENT ==============
export default function MycaDashboardUnifi() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [flows, setFlows] = useState<Flow[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'topology' | 'clients' | 'flows'>('overview');
  const [sidebarFilters, setSidebarFilters] = useState({
    showOnline: true,
    showOffline: false,
    showActive: true,
    showIdle: true,
  });

  // Initialize with mock data
  useEffect(() => {
    setAgents([
      { id: 'myca', name: 'MYCA', displayName: 'MYCA Orchestrator', category: 'core', status: 'active', lastActivity: 'Just now', tasksCompleted: 1247, tasksInProgress: 3, downloadSpeed: 159, uploadSpeed: 136, experience: 'Excellent', uptime: '2w 4d 4h 0m', ipAddress: '192.168.0.1' },
      { id: 'financial', name: 'FinancialAgent', displayName: 'Financial Agent', category: 'financial', status: 'active', lastActivity: '2m ago', tasksCompleted: 89, tasksInProgress: 1, downloadSpeed: 49.4, uploadSpeed: 5.36, experience: 'Excellent', uptime: '8d 20m 11s', ipAddress: '192.168.0.172' },
      { id: 'mycology', name: 'MycologyBioAgent', displayName: 'Mycology Research', category: 'mycology', status: 'active', lastActivity: '1m ago', tasksCompleted: 234, tasksInProgress: 2, downloadSpeed: 36.1, uploadSpeed: 49.4, experience: 'Excellent', uptime: '8d 20m 11s', ipAddress: '192.168.0.248' },
      { id: 'project', name: 'ProjectManagerAgent', displayName: 'Project Manager', category: 'core', status: 'active', lastActivity: '30s ago', tasksCompleted: 412, tasksInProgress: 5, downloadSpeed: 0, uploadSpeed: 0, experience: 'Excellent', uptime: '17d 47m 31s', ipAddress: '192.168.0.248' },
      { id: 'opportunity', name: 'OpportunityScout', displayName: 'Opportunity Scout', category: 'research', status: 'active', lastActivity: '5m ago', tasksCompleted: 78, tasksInProgress: 1, downloadSpeed: 0, uploadSpeed: 0, experience: 'Good', uptime: '6d 1h 33m 28s', ipAddress: '192.168.0.90' },
      { id: 'marketing', name: 'MarketingAgent', displayName: 'Marketing Agent', category: 'communication', status: 'idle', lastActivity: '15m ago', tasksCompleted: 56, tasksInProgress: 0, downloadSpeed: 0, uploadSpeed: 0, experience: 'Good', uptime: '1d 3h 37m 6s', ipAddress: '192.168.0.228' },
      { id: 'dao', name: 'MycoDAOAgent', displayName: 'MycoDAO Agent', category: 'dao', status: 'idle', lastActivity: '1h ago', tasksCompleted: 23, tasksInProgress: 0, downloadSpeed: 32, uploadSpeed: 48, experience: 'Excellent', uptime: '18d 3h 59m 58s', ipAddress: '192.168.0.105' },
      { id: 'dashboard', name: 'DashboardAgent', displayName: 'Dashboard Agent', category: 'core', status: 'active', lastActivity: 'Just now', tasksCompleted: 890, tasksInProgress: 1, downloadSpeed: 0, uploadSpeed: 24, experience: 'Excellent', uptime: '17d 45m 51s', ipAddress: '192.168.0.184' },
    ]);

    setFlows([
      { id: '1', source: 'MYCA Orchestrator', destination: 'FinancialAgent', service: 'HTTPS', risk: 'Low', direction: 'out', inBytes: '-', outBytes: '-', action: 'Allow', timestamp: 'Dec 18, 5:43:51.792 PM' },
      { id: '2', source: 'MYCA Orchestrator', destination: 'MycologyBioAgent', service: 'HTTPS', risk: 'Low', direction: 'out', inBytes: '-', outBytes: '-', action: 'Allow', timestamp: 'Dec 18, 5:43:51.523 PM' },
      { id: '3', source: 'OpportunityScout', destination: 'External API', service: 'HTTPS', risk: 'Low', direction: 'out', inBytes: '-', outBytes: '-', action: 'Allow', timestamp: 'Dec 18, 5:43:50.732 PM' },
      { id: '4', source: 'MYCA Orchestrator', destination: 'n8n Workflow', service: 'HTTP', risk: 'Low', direction: 'both', inBytes: '4.6 KB', outBytes: '1.2 KB', action: 'Allow', timestamp: 'Dec 18, 5:43:48.993 PM' },
      { id: '5', source: 'ProjectManager', destination: 'Database', service: 'SQL', risk: 'Low', direction: 'both', inBytes: '3.2 KB', outBytes: '0.5 KB', action: 'Allow', timestamp: 'Dec 18, 5:43:47.683 PM' },
    ]);
  }, []);

  const topClients: TopItem[] = [
    { name: 'MYCA', value: '4,318' },
    { name: 'Financial', value: '1,534' },
    { name: 'Mycology', value: '645' },
    { name: 'Project', value: '459' },
    { name: 'Opportunity', value: '405' },
  ];

  const topApps: TopItem[] = [
    { name: 'SSL/TLS', value: '3.10 GB' },
    { name: 'HTTP', value: '188 MB' },
    { name: 'WebSocket', value: '91.3 MB' },
    { name: 'gRPC', value: '72.9 MB' },
    { name: 'Redis', value: '45.2 MB' },
  ];

  const activeAgents = agents.filter(a => a.status === 'active').length;
  const totalTraffic = agents.reduce((sum, a) => sum + a.downloadSpeed + a.uploadSpeed, 0);

  return (
    <div className="min-h-screen bg-[#0a1929] text-white flex">
      {/* Left Sidebar - UniFi Style */}
      <aside className="w-60 bg-[#0d2137] border-r border-[#1e3a5f] flex flex-col">
        {/* Logo */}
        <div className="p-4 border-b border-[#1e3a5f]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-purple-600 flex items-center justify-center">
              <Icons.Brain />
            </div>
            <div>
              <div className="text-sm font-semibold">MYCA Dashboard</div>
              <div className="text-[10px] text-gray-500">Network 10.0.162</div>
            </div>
          </div>
        </div>

        {/* Search */}
        <div className="p-3 border-b border-[#1e3a5f]">
          <div className="flex items-center gap-2 bg-[#081422] rounded px-3 py-2 border border-[#1e3a5f]">
            <Icons.Search />
            <input 
              type="text" 
              placeholder="Search" 
              className="bg-transparent text-sm flex-1 outline-none placeholder-gray-500"
            />
          </div>
        </div>

        {/* Nav Tabs */}
        <div className="flex border-b border-[#1e3a5f]">
          <button 
            className={`flex-1 py-3 text-sm ${activeTab === 'topology' || activeTab === 'overview' ? 'bg-[#1e3a5f]/50 text-white' : 'text-gray-400'}`}
            onClick={() => setActiveTab('topology')}
          >
            Main
          </button>
          <button 
            className={`flex-1 py-3 text-sm ${activeTab === 'clients' ? 'bg-[#1e3a5f]/50 text-white' : 'text-gray-400'}`}
            onClick={() => setActiveTab('clients')}
          >
            <Icons.Server /> List
          </button>
        </div>

        {/* Filters */}
        <ScrollArea className="flex-1">
          <div className="py-2">
            <SidebarSection title="Status">
              <FilterCheckbox label="Online" count={activeAgents} checked={sidebarFilters.showOnline} />
              <FilterCheckbox label="Offline" count={agents.length - activeAgents} checked={sidebarFilters.showOffline} />
            </SidebarSection>

            <SidebarSection title="Connection">
              <FilterCheckbox label="Active" count={activeAgents} checked={sidebarFilters.showActive} />
              <FilterCheckbox label="Idle" count={agents.filter(a => a.status === 'idle').length} checked={sidebarFilters.showIdle} />
            </SidebarSection>

            <SidebarSection title="Categories">
              <FilterCheckbox label="Core" count={agents.filter(a => a.category === 'core').length} />
              <FilterCheckbox label="Financial" count={agents.filter(a => a.category === 'financial').length} />
              <FilterCheckbox label="Mycology" count={agents.filter(a => a.category === 'mycology').length} />
              <FilterCheckbox label="Research" count={agents.filter(a => a.category === 'research').length} />
              <FilterCheckbox label="DAO" count={agents.filter(a => a.category === 'dao').length} />
            </SidebarSection>

            <SidebarSection title="Agent Types" defaultOpen={false}>
              <FilterCheckbox label="Orchestrator" count={1} />
              <FilterCheckbox label="Worker" count={agents.length - 1} />
              <FilterCheckbox label="Monitor" count={2} />
            </SidebarSection>
          </div>
        </ScrollArea>

        {/* Bottom Actions */}
        <div className="p-4 border-t border-[#1e3a5f]">
          <button className="w-full text-left text-sm text-gray-400 hover:text-white py-2">Clear Filters</button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        {/* Top Header */}
        <header className="bg-[#0d2137] border-b border-[#1e3a5f] px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
              <TabsList className="bg-transparent gap-1">
                <TabsTrigger value="overview" className="data-[state=active]:bg-[#1e3a5f] text-sm">Overview</TabsTrigger>
                <TabsTrigger value="topology" className="data-[state=active]:bg-[#1e3a5f] text-sm">Topology</TabsTrigger>
                <TabsTrigger value="flows" className="data-[state=active]:bg-[#1e3a5f] text-sm">Flows</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm">
              <span className="text-gray-400">Agent Activity</span>
              <span className="text-white font-medium">{totalTraffic.toFixed(0)} Kbps</span>
            </div>
            <Button 
              variant="default"
              size="sm"
              className="bg-blue-600 hover:bg-blue-700 flex items-center gap-2"
            >
              <Icons.Mic />
              Talk to MYCA
            </Button>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 overflow-auto p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Top Stats Row */}
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-[#0d2137] rounded-lg p-4 border border-[#1e3a5f]">
                  <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">Active Agents</div>
                  <div className="text-3xl font-bold">{activeAgents}</div>
                  <div className="text-xs text-gray-500">of {agents.length} total</div>
                </div>
                <div className="bg-[#0d2137] rounded-lg p-4 border border-[#1e3a5f]">
                  <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">Tasks/Hour</div>
                  <div className="text-3xl font-bold">124</div>
                  <div className="text-xs text-green-400">↑ 12% from yesterday</div>
                </div>
                <div className="bg-[#0d2137] rounded-lg p-4 border border-[#1e3a5f]">
                  <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">System Uptime</div>
                  <div className="text-3xl font-bold">2w 4d</div>
                  <div className="text-xs text-gray-500">100% availability</div>
                </div>
                <div className="bg-[#0d2137] rounded-lg p-4 border border-[#1e3a5f]">
                  <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">Latency</div>
                  <div className="text-3xl font-bold">5ms</div>
                  <div className="text-xs text-green-400">Excellent</div>
                </div>
              </div>

              {/* Top Items */}
              <div className="grid grid-cols-3 gap-6">
                <TopItemsGrid title="Top Clients" items={topClients} showMore />
                <TopItemsGrid title="Top Apps" items={topApps} showMore />
                <TopItemsGrid title="Top Destinations" items={[
                  { name: 'n8n Workflows', value: '4,608' },
                  { name: 'Database', value: '4,300' },
                  { name: 'Redis Cache', value: '3,266' },
                ]} showMore />
              </div>

              {/* Recent Flows */}
              <div className="bg-[#0d2137] rounded-lg border border-[#1e3a5f]">
                <div className="p-4 border-b border-[#1e3a5f] flex items-center justify-between">
                  <h3 className="font-medium">Recent Agent Flows</h3>
                  <button className="text-sm text-blue-400 hover:underline" onClick={() => setActiveTab('flows')}>View All</button>
                </div>
                <FlowsTable flows={flows.slice(0, 5)} />
              </div>
            </div>
          )}

          {activeTab === 'topology' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-medium">Agent Topology</h2>
                <div className="flex items-center gap-2">
                  <label className="flex items-center gap-2 text-sm text-gray-400">
                    <input type="checkbox" defaultChecked className="rounded bg-transparent border-gray-600" />
                    Show Traffic
                  </label>
                </div>
              </div>
              <TopologyMap agents={agents} onAgentClick={setSelectedAgent} />
            </div>
          )}

          {activeTab === 'clients' && (
            <div className="bg-[#0d2137] rounded-lg border border-[#1e3a5f]">
              <div className="p-4 border-b border-[#1e3a5f]">
                <h3 className="font-medium">All Agents ({agents.length})</h3>
              </div>
              <ClientList agents={agents} onAgentClick={setSelectedAgent} />
            </div>
          )}

          {activeTab === 'flows' && (
            <div className="space-y-4">
              {/* Flow Summary */}
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-[#0d2137] rounded-lg p-4 border border-[#1e3a5f]">
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <Icons.Activity /> Total
                  </div>
                  <div className="text-2xl font-bold mt-1">50,896</div>
                </div>
                <div className="bg-[#0d2137] rounded-lg p-4 border border-[#1e3a5f]">
                  <div className="flex items-center gap-2 text-sm text-green-400">
                    <span className="w-2 h-2 rounded-full bg-green-400" /> Low Risk
                  </div>
                  <div className="text-2xl font-bold mt-1">50,896 (100%)</div>
                </div>
                <div className="bg-[#0d2137] rounded-lg p-4 border border-[#1e3a5f]">
                  <div className="flex items-center gap-2 text-sm text-yellow-400">
                    <span className="w-2 h-2 rounded-full bg-yellow-400" /> Suspicious
                  </div>
                  <div className="text-2xl font-bold mt-1">0 (0%)</div>
                </div>
                <div className="bg-[#0d2137] rounded-lg p-4 border border-[#1e3a5f]">
                  <div className="flex items-center gap-2 text-sm text-red-400">
                    <span className="w-2 h-2 rounded-full bg-red-400" /> Concerning
                  </div>
                  <div className="text-2xl font-bold mt-1">0 (0%)</div>
                </div>
              </div>

              {/* Flows Table */}
              <div className="bg-[#0d2137] rounded-lg border border-[#1e3a5f]">
                <div className="p-4 border-b border-[#1e3a5f] flex items-center justify-between">
                  <h3 className="font-medium">All Flows</h3>
                  <span className="text-sm text-gray-400">1-100 of 10000+ Flows</span>
                </div>
                <FlowsTable flows={flows} />
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Right Sidebar - Agent Details */}
      {selectedAgent && (
        <aside className="w-72 bg-[#0d2137] border-l border-[#1e3a5f] p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-medium">Agent Details</h2>
            <button onClick={() => setSelectedAgent(null)} className="text-gray-400 hover:text-white">×</button>
          </div>
          
          <div className="space-y-4">
            <div className="text-center p-4 bg-[#081422] rounded-lg">
              <div className={`w-16 h-16 rounded-lg mx-auto mb-3 flex items-center justify-center ${
                selectedAgent.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
              }`}>
                <Icons.Cpu />
              </div>
              <h3 className="font-bold">{selectedAgent.displayName}</h3>
              <Badge className={`mt-2 ${
                selectedAgent.status === 'active' ? 'bg-green-500' : 'bg-gray-500'
              }`}>
                {selectedAgent.status}
              </Badge>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between py-2 border-b border-[#1e3a5f]">
                <span className="text-gray-400">Category</span>
                <span className="capitalize">{selectedAgent.category}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1e3a5f]">
                <span className="text-gray-400">IP Address</span>
                <span>{selectedAgent.ipAddress}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1e3a5f]">
                <span className="text-gray-400">Experience</span>
                <span className={selectedAgent.experience === 'Excellent' ? 'text-green-400' : ''}>{selectedAgent.experience}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1e3a5f]">
                <span className="text-gray-400">Uptime</span>
                <span>{selectedAgent.uptime}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1e3a5f]">
                <span className="text-gray-400">Tasks Completed</span>
                <span>{selectedAgent.tasksCompleted}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1e3a5f]">
                <span className="text-gray-400">Download</span>
                <span className="text-cyan-400">↓ {selectedAgent.downloadSpeed} Kbps</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1e3a5f]">
                <span className="text-gray-400">Upload</span>
                <span className="text-green-400">↑ {selectedAgent.uploadSpeed} Kbps</span>
              </div>
            </div>

            <Button className="w-full bg-blue-600 hover:bg-blue-700">
              Send Command
            </Button>
          </div>
        </aside>
      )}
    </div>
  );
}
