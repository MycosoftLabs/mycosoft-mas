"use client";

import { useState, useEffect } from "react";
import { MASTopologyView, MASEntity } from "./mas-topology-view";
import { Sidebar } from "./mas-sidebar";
import { Navigation } from "./mas-navigation";
import { SearchBar } from "./mas-search-bar";
import { DeviceModal } from "./mas-entity-modal";
import { GlobalIntegrationsPanel } from "./dashboard/global-integrations";
import { IntegrationStatusWidget } from "./dashboard/integration-status";
import { IntegrationsView } from "./dashboard/integrations-view";

interface Connection {
  from: string;
  to: string;
  type: string;
  status: string;
}

export function MASDashboard() {
  const [currentView, setCurrentView] = useState("topology");
  const [selectedEntity, setSelectedEntity] = useState<MASEntity | null>(null);
  const [entities, setEntities] = useState<MASEntity[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTopology();
    // Refresh every 5 seconds
    const interval = setInterval(fetchTopology, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchTopology = async () => {
    try {
      const response = await fetch('/api/mas/topology');
      const data = await response.json();
      setEntities(data.entities || []);
      setConnections(data.connections || []);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch topology:', error);
      setLoading(false);
    }
  };

  const renderView = () => {
    switch (currentView) {
      case "topology":
        return (
          <MASTopologyView
            entities={entities}
            connections={connections}
            onEntityClick={setSelectedEntity}
          />
        );
      case "dashboard":
        return <DashboardMainView entities={entities} onEntityClick={setSelectedEntity} />;
      case "integrations":
        return <IntegrationsView />;
      default:
        return (
          <MASTopologyView
            entities={entities}
            connections={connections}
            onEntityClick={setSelectedEntity}
          />
        );
    }
  };

  return (
    <div className="flex h-screen bg-[#0F172A] text-white">
      {/* Left Sidebar */}
      {currentView === "dashboard" && <Sidebar entities={entities} />}

      {/* Left Navigation Bar */}
      <div className="flex w-16 flex-col items-center border-r border-gray-800 bg-[#1E293B] py-4">
        <div className="mb-8 flex h-10 w-10 items-center justify-center rounded-lg bg-[#0F172A]">
          <svg viewBox="0 0 24 24" className="h-6 w-6 fill-white">
            <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z" />
          </svg>
        </div>
        <Navigation currentView={currentView} onViewChange={setCurrentView} />
      </div>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Header */}
        <div className="border-b border-gray-800 bg-[#1E293B] px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium hover:bg-gray-700">
                <div className="h-2 w-2 rounded-full bg-green-500" />
                MYCA Orchestrator
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500">
                  <svg viewBox="0 0 24 24" className="h-5 w-5 fill-white">
                    <circle cx="12" cy="12" r="8" />
                  </svg>
                </div>
                <span className="text-sm font-medium text-blue-500">MAS Network</span>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <SearchBar />
              <div className="text-center text-xs text-gray-400">MYCA</div>
            </div>
          </div>
        </div>

        {/* View Content */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-gray-400">Loading topology...</div>
            </div>
          ) : (
            renderView()
          )}
        </div>
      </div>

      {/* Entity Modal */}
      {selectedEntity && (
        <DeviceModal
          entity={selectedEntity}
          onClose={() => setSelectedEntity(null)}
        />
      )}
    </div>
  );
}

function DashboardMainView({ entities, onEntityClick }: { entities: MASEntity[]; onEntityClick: (e: MASEntity) => void }) {
  const activeEntities = entities.filter(e => e.status === 'active' || e.status === 'online');
  const totalAgents = entities.filter(e => e.type === 'agent').length;
  const totalTasks = entities.reduce((sum, e) => sum + (e.metadata?.tasksCompleted || 0), 0);

  return (
    <div className="p-6">
      {/* Main Stats */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">
            System Status: <span className="text-green-500">Operational</span>{" "}
            <span className="text-green-500">96%</span>
          </h1>
        </div>
        <div className="flex gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-green-500" />
            Active
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-yellow-500" />
            Idle
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-red-500" />
            Error
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="mb-6 grid grid-cols-4 gap-4">
        <div className="rounded-lg bg-[#1E293B] p-4">
          <div className="text-xs text-gray-400">Active Entities</div>
          <div className="text-2xl font-bold">{activeEntities.length}</div>
          <div className="text-xs text-gray-500">of {entities.length} total</div>
        </div>
        <div className="rounded-lg bg-[#1E293B] p-4">
          <div className="text-xs text-gray-400">Total Agents</div>
          <div className="text-2xl font-bold">{totalAgents}</div>
        </div>
        <div className="rounded-lg bg-[#1E293B] p-4">
          <div className="text-xs text-gray-400">Tasks Completed</div>
          <div className="text-2xl font-bold">{totalTasks}</div>
        </div>
        <div className="rounded-lg bg-[#1E293B] p-4">
          <div className="text-xs text-gray-400">System Health</div>
          <div className="text-2xl font-bold text-green-500">96%</div>
        </div>
      </div>

      {/* Global Integrations Panel */}
      <div className="mb-6">
        <GlobalIntegrationsPanel />
      </div>

      {/* Two Column Layout: Entities + Integration Status */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Entity List - 2 columns */}
        <div className="lg:col-span-2 rounded-lg bg-[#1E293B] p-4">
          <h3 className="mb-4 text-lg font-semibold">All Entities</h3>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
            {entities.map((entity) => (
              <div
                key={entity.id}
                onClick={() => onEntityClick(entity)}
                className="cursor-pointer rounded-lg border border-gray-700 bg-[#0F172A] p-4 hover:border-blue-500"
              >
                <div className="mb-2 flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${
                    entity.status === 'active' || entity.status === 'online' ? 'bg-green-500' :
                    entity.status === 'idle' ? 'bg-yellow-500' : 'bg-red-500'
                  }`} />
                  <span className="text-sm font-medium">{entity.name}</span>
                </div>
                <div className="text-xs text-gray-400 capitalize">{entity.type}</div>
                {entity.metadata?.tasksCompleted && (
                  <div className="mt-2 text-xs text-gray-500">
                    {entity.metadata.tasksCompleted} tasks
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Integration Status - 1 column */}
        <div className="lg:col-span-1">
          <IntegrationStatusWidget />
        </div>
      </div>
    </div>
  );
}
