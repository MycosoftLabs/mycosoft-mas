"use client";

import { useState, useRef, useEffect } from "react";
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react";

// MAS Entity Types
export interface MASEntity {
  id: string;
  name: string;
  type: 'orchestrator' | 'agent' | 'operator' | 'database' | 'program' | 'user';
  category?: string;
  status: 'online' | 'offline' | 'idle' | 'active' | 'error';
  x: number;
  y: number;
  connections?: string[]; // IDs of connected entities
  metadata?: {
    ip?: string;
    uptime?: string;
    tasksCompleted?: number;
    tasksInProgress?: number;
    downloadSpeed?: number;
    uploadSpeed?: number;
    experience?: 'Excellent' | 'Good' | 'Fair' | 'Poor';
  };
}

interface Connection {
  from: string;
  to: string;
  type: 'agent-to-agent' | 'agent-to-orchestrator' | 'agent-to-operator' | 'agent-to-program' | 'agent-to-database' | 'user-to-orchestrator' | 'operator-to-database';
  status: 'active' | 'idle' | 'error';
}

interface MASTopologyViewProps {
  entities?: MASEntity[];
  connections?: Connection[];
  onEntityClick?: (entity: MASEntity) => void;
}

export function MASTopologyView({ entities = [], connections = [], onEntityClick }: MASTopologyViewProps) {
  const [zoom, setZoom] = useState(1);
  const [dragging, setDragging] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null);
  const [localEntities, setLocalEntities] = useState<MASEntity[]>(entities);
  const [showConnections, setShowConnections] = useState(true);
  const canvasRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLocalEntities(entities);
  }, [entities]);

  const handleMouseDown = (e: React.MouseEvent, entityId: string) => {
    e.preventDefault();
    const entity = localEntities.find((e) => e.id === entityId);
    if (!entity) return;

    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    setDragging(entityId);
    setDragOffset({
      x: (e.clientX - rect.left) / zoom - entity.x,
      y: (e.clientY - rect.top) / zoom - entity.y,
    });
    setSelectedEntity(entityId);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragging) return;

    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;

    const newX = (e.clientX - rect.left) / zoom - dragOffset.x;
    const newY = (e.clientY - rect.top) / zoom - dragOffset.y;

    setLocalEntities((prev) =>
      prev.map((entity) =>
        entity.id === dragging ? { ...entity, x: newX, y: newY } : entity
      )
    );
  };

  const handleMouseUp = () => {
    setDragging(null);
  };

  const getEntityIcon = (type: MASEntity['type'], status: MASEntity['status']) => {
    const baseClasses = "transition-all";
    const statusColor = status === 'active' ? 'text-green-400' : status === 'idle' ? 'text-yellow-400' : status === 'error' ? 'text-red-400' : 'text-gray-500';

    switch (type) {
      case 'orchestrator':
        return (
          <svg className={`h-12 w-12 ${statusColor}`} fill="currentColor" viewBox="0 0 24 24">
            <rect x="2" y="4" width="20" height="16" rx="2" />
            <circle cx="6" cy="8" r="1.5" />
            <circle cx="6" cy="12" r="1.5" />
            <circle cx="6" cy="16" r="1.5" />
            <path d="M12 8h6M12 12h6M12 16h6" stroke="currentColor" strokeWidth="2" />
          </svg>
        );
      case 'agent':
        return (
          <svg className={`h-10 w-10 ${statusColor}`} fill="currentColor" viewBox="0 0 24 24">
            <rect x="4" y="4" width="16" height="16" rx="2" />
            <rect x="8" y="8" width="8" height="8" />
            <circle cx="6" cy="6" r="1" />
            <circle cx="18" cy="6" r="1" />
            <circle cx="6" cy="18" r="1" />
            <circle cx="18" cy="18" r="1" />
          </svg>
        );
      case 'operator':
        return (
          <svg className={`h-10 w-10 ${statusColor}`} fill="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="8" r="4" />
            <path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2" />
          </svg>
        );
      case 'database':
        return (
          <svg className={`h-10 w-10 ${statusColor}`} fill="currentColor" viewBox="0 0 24 24">
            <ellipse cx="12" cy="5" rx="9" ry="3" />
            <path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5" />
            <path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3" />
          </svg>
        );
      case 'program':
        return (
          <svg className={`h-10 w-10 ${statusColor}`} fill="currentColor" viewBox="0 0 24 24">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M9 9h6v6H9z" fill="currentColor" opacity="0.3" />
            <path d="M9 3v6M15 3v6M9 15v6M15 15v6" stroke="currentColor" strokeWidth="2" />
          </svg>
        );
      case 'user':
        return (
          <svg className={`h-10 w-10 ${statusColor}`} fill="currentColor" viewBox="0 0 24 24">
            <circle cx="12" cy="7" r="3" />
            <path d="M5 21v-2a7 7 0 0 1 14 0v2" />
          </svg>
        );
      default:
        return <div className={`h-8 w-8 rounded bg-gray-600 ${statusColor}`} />;
    }
  };

  const getEntityColor = (type: MASEntity['type']) => {
    switch (type) {
      case 'orchestrator':
        return 'border-blue-500 bg-blue-500/20';
      case 'agent':
        return 'border-purple-500 bg-purple-500/20';
      case 'operator':
        return 'border-green-500 bg-green-500/20';
      case 'database':
        return 'border-cyan-500 bg-cyan-500/20';
      case 'program':
        return 'border-orange-500 bg-orange-500/20';
      case 'user':
        return 'border-yellow-500 bg-yellow-500/20';
      default:
        return 'border-gray-500 bg-gray-500/20';
    }
  };

  // Auto-layout entities if not positioned (only if entities have default positions)
  useEffect(() => {
    // Use entities prop directly to avoid stale closure
    // This effect runs whenever entities array reference changes or entity properties change
    if (entities.length > 0) {
      const needsLayout = entities.some(e => e.x === 0 && e.y === 0);
      
      if (needsLayout) {
        const orchestrator = entities.find(e => e.type === 'orchestrator');
        const agents = entities.filter(e => e.type === 'agent');
        const operators = entities.filter(e => e.type === 'operator');
        const databases = entities.filter(e => e.type === 'database');
        const programs = entities.filter(e => e.type === 'program');
        const users = entities.filter(e => e.type === 'user');

        const newEntities = entities.map(entity => ({ ...entity }));
        
        // Position orchestrator at center top
        const orchestratorEntity = newEntities.find(e => e.type === 'orchestrator');
        if (orchestratorEntity && orchestratorEntity.x === 0 && orchestratorEntity.y === 0) {
          orchestratorEntity.x = 400;
          orchestratorEntity.y = 100;
        }

        // Position agents in a circle around orchestrator
        newEntities.filter(e => e.type === 'agent' && e.x === 0 && e.y === 0).forEach((agent, i) => {
          const angle = (i / agents.length) * Math.PI * 2;
          agent.x = 400 + Math.cos(angle) * 200;
          agent.y = 300 + Math.sin(angle) * 150;
        });

        // Position operators below agents
        newEntities.filter(e => e.type === 'operator' && e.x === 0 && e.y === 0).forEach((op, i) => {
          op.x = 200 + (i * 150);
          op.y = 500;
        });

        // Position databases on the left
        newEntities.filter(e => e.type === 'database' && e.x === 0 && e.y === 0).forEach((db, i) => {
          db.x = 100;
          db.y = 200 + (i * 120);
        });

        // Position programs on the right
        newEntities.filter(e => e.type === 'program' && e.x === 0 && e.y === 0).forEach((prog, i) => {
          prog.x = 700;
          prog.y = 200 + (i * 120);
        });

        // Position users at bottom
        newEntities.filter(e => e.type === 'user' && e.x === 0 && e.y === 0).forEach((user, i) => {
          user.x = 300 + (i * 150);
          user.y = 600;
        });

        setLocalEntities(newEntities);
      } else {
        // Update local entities when props change but layout not needed
        // Preserve positions from localEntities if they exist, otherwise use entities
        setLocalEntities(prev => {
          return entities.map(entity => {
            const existing = prev.find(e => e.id === entity.id);
            // Preserve position if entity was manually moved (not at 0,0)
            if (existing && (existing.x !== 0 || existing.y !== 0)) {
              return { ...entity, x: existing.x, y: existing.y };
            }
            return entity;
          });
        });
      }
    } else {
      // Clear entities if empty
      setLocalEntities([]);
    }
  }, [entities]); // Track all entity changes - dependency on full array ensures re-run when entities, IDs, or properties change

  return (
    <div className="flex h-full flex-col">
      {/* Top Bar */}
      <div className="flex items-center gap-4 border-b border-gray-800 bg-[#1E293B] px-6 py-4">
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-gray-600 bg-gray-700 cursor-pointer"
            checked={showConnections}
            onChange={(e) => setShowConnections(e.target.checked)}
          />
          <span>Show Connections</span>
        </label>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.1))}
            className="rounded-lg p-2 hover:bg-gray-700"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <span className="min-w-[60px] text-center text-sm">{Math.round(zoom * 100)}%</span>
          <button
            onClick={() => setZoom((z) => Math.min(2, z + 0.1))}
            className="rounded-lg p-2 hover:bg-gray-700"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="rounded-lg p-2 hover:bg-gray-700"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div
        ref={canvasRef}
        className="relative flex-1 overflow-hidden bg-[#0F172A]"
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <div style={{ transform: `scale(${zoom})`, transformOrigin: "0 0" }}>
          {/* Grid background */}
          <div
            className="absolute inset-0 opacity-10"
            style={{
              backgroundImage: 'radial-gradient(circle, #3b82f6 1px, transparent 1px)',
              backgroundSize: '30px 30px'
            }}
          />

          {/* Connection Lines */}
          {showConnections && (
            <svg className="absolute left-0 top-0 h-full w-full pointer-events-none">
              <defs>
                <linearGradient id="connectionGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.6" />
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.6" />
                </linearGradient>
              </defs>
              {connections.map((conn, i) => {
                const fromEntity = localEntities.find(e => e.id === conn.from);
                const toEntity = localEntities.find(e => e.id === conn.to);
                if (!fromEntity || !toEntity) return null;

                const strokeColor = conn.status === 'active' ? '#3b82f6' : conn.status === 'idle' ? '#6b7280' : '#ef4444';
                const strokeDash = conn.status === 'active' ? '0' : '5,5';

                return (
                  <line
                    key={i}
                    x1={fromEntity.x}
                    y1={fromEntity.y}
                    x2={toEntity.x}
                    y2={toEntity.y}
                    stroke={strokeColor}
                    strokeWidth="2"
                    strokeDasharray={strokeDash}
                    opacity="0.6"
                  />
                );
              })}
              {/* Draw connections from entity.connections */}
              {localEntities.map((entity) => {
                if (!entity.connections) return null;
                return entity.connections.map((targetId, i) => {
                  const targetEntity = localEntities.find(e => e.id === targetId);
                  if (!targetEntity) return null;
                  return (
                    <line
                      key={`${entity.id}-${targetId}-${i}`}
                      x1={entity.x}
                      y1={entity.y}
                      x2={targetEntity.x}
                      y2={targetEntity.y}
                      stroke="#3b82f6"
                      strokeWidth="2"
                      strokeDasharray="3,3"
                      opacity="0.4"
                    />
                  );
                });
              })}
            </svg>
          )}

          {/* Entities */}
          {localEntities.map((entity) => (
            <div
              key={entity.id}
              className={`absolute cursor-move transition-shadow ${
                selectedEntity === entity.id ? "ring-2 ring-blue-500" : ""
              } ${dragging === entity.id ? "cursor-grabbing" : "cursor-grab"}`}
              style={{
                left: entity.x,
                top: entity.y,
                transform: "translate(-50%, -50%)",
              }}
              onMouseDown={(e) => handleMouseDown(e, entity.id)}
              onClick={() => {
                setSelectedEntity(entity.id);
                onEntityClick?.(entity);
              }}
            >
              <div
                className={`rounded-lg bg-[#1E293B] p-3 shadow-lg hover:shadow-xl border-2 ${getEntityColor(entity.type)} ${
                  entity.status === 'online' || entity.status === 'active' ? 'border-opacity-100' : 'border-opacity-50'
                }`}
              >
                <div className="mb-2 flex justify-center">
                  {getEntityIcon(entity.type, entity.status)}
                </div>
                <div className="max-w-[120px] truncate text-center text-xs font-medium text-white">
                  {entity.name}
                </div>
                {entity.category && (
                  <div className="mt-1 text-center text-[10px] text-gray-400 capitalize">
                    {entity.category}
                  </div>
                )}
                {entity.metadata?.downloadSpeed !== undefined && (
                  <div className="mt-1 flex items-center justify-center gap-2 text-[9px]">
                    <span className="text-cyan-400">↓ {entity.metadata.downloadSpeed}</span>
                    <span className="text-green-400">↑ {entity.metadata.uploadSpeed || 0}</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Legend */}
        <div className="absolute bottom-4 left-4 rounded-lg bg-[#1E293B] p-3 text-xs border border-gray-800">
          <div className="mb-2 font-medium text-gray-300">Entity Types</div>
          <div className="space-y-1">
            {[
              { type: 'orchestrator', label: 'Orchestrator' },
              { type: 'agent', label: 'Agent' },
              { type: 'operator', label: 'Operator' },
              { type: 'database', label: 'Database' },
              { type: 'program', label: 'Program' },
              { type: 'user', label: 'User' },
            ].map((item) => {
              // Use static class names that Tailwind can extract at build time
              const getLegendClasses = (type: MASEntity['type']) => {
                switch (type) {
                  case 'orchestrator':
                    return 'border-blue-500 bg-blue-500/20';
                  case 'agent':
                    return 'border-purple-500 bg-purple-500/20';
                  case 'operator':
                    return 'border-green-500 bg-green-500/20';
                  case 'database':
                    return 'border-cyan-500 bg-cyan-500/20';
                  case 'program':
                    return 'border-orange-500 bg-orange-500/20';
                  case 'user':
                    return 'border-yellow-500 bg-yellow-500/20';
                  default:
                    return 'border-gray-500 bg-gray-500/20';
                }
              };
              
              return (
                <div key={item.type} className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded border-2 ${getLegendClasses(item.type)}`} />
                  <span className="text-gray-400">{item.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Controls */}
        <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 flex items-center gap-2 bg-[#1E293B] rounded-lg p-1 border border-gray-800">
          <div className="px-2 text-xs text-gray-400">
            {localEntities.length} entities
          </div>
        </div>
      </div>
    </div>
  );
}
