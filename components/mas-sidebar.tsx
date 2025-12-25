"use client";

import { MASEntity } from "./mas-topology-view";

interface SidebarProps {
  entities?: MASEntity[];
}

export function Sidebar({ entities = [] }: SidebarProps) {
  const orchestrator = entities.find(e => e.type === 'orchestrator');
  const activeAgents = entities.filter(e => e.type === 'agent' && (e.status === 'active' || e.status === 'online'));
  const totalTasks = entities.reduce((sum, e) => sum + (e.metadata?.tasksCompleted || 0), 0);

  return (
    <div className="flex w-72 flex-col border-r border-gray-800 bg-[#1E293B]">
      {/* Top Navigation */}
      <div className="flex items-center gap-2 border-b border-gray-800 p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#0F172A]">
          <svg viewBox="0 0 24 24" className="h-6 w-6 fill-white">
            <path d="M12 2L2 7v10c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-10-5z" />
          </svg>
        </div>
        <div className="flex-1 text-xs text-gray-400">
          {new Date().toLocaleTimeString()}
        </div>
      </div>

      {/* Orchestrator Info */}
      <div className="border-b border-gray-800 p-6">
        <div className="mb-4 rounded-lg bg-[#0F172A] p-4">
          <svg viewBox="0 0 200 80" className="h-20 w-full">
            <rect x="20" y="20" width="160" height="40" rx="4" fill="#374151" />
            <rect x="25" y="25" width="150" height="30" rx="2" fill="#1F2937" />
            <circle cx="165" cy="40" r="3" fill="#10B981" />
            <circle cx="175" cy="40" r="3" fill="#10B981" />
            <rect x="30" y="32" width="80" height="2" fill="#4B5563" />
            <rect x="30" y="38" width="60" height="2" fill="#4B5563" />
            <rect x="30" y="44" width="70" height="2" fill="#4B5563" />
          </svg>
        </div>

        <div className="space-y-2">
          <div className="font-semibold">{orchestrator?.name || 'MYCA Orchestrator'}</div>
          <div className="text-xs text-gray-400">MAS System v1.0</div>
        </div>
      </div>

      {/* System Info */}
      <div className="flex-1 overflow-auto p-6">
        <div className="space-y-4">
          <div>
            <div className="text-xs text-gray-400">Orchestrator IP</div>
            <div className="text-sm">{orchestrator?.metadata?.ip || '192.168.0.1'}</div>
          </div>

          <div>
            <div className="text-xs text-gray-400">System Uptime</div>
            <div className="text-sm">{orchestrator?.metadata?.uptime || '2w 4d 4h'}</div>
          </div>

          <div className="border-t border-gray-800 pt-4">
            <div className="mb-2 flex items-center justify-between">
              <div className="text-xs text-gray-400">Active Agents</div>
              <div className="flex items-center gap-1">
                <div className="h-2 w-2 rounded-full bg-green-500" />
                <div className="text-xs text-green-500">{activeAgents.length}</div>
              </div>
            </div>
            <div className="mb-2">
              <div className="text-xs text-gray-400">Total Tasks</div>
              <div className="text-sm text-green-500">{totalTasks}</div>
            </div>
            <div className="mb-2">
              <div className="text-xs text-gray-400">Activity</div>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-cyan-500">↓ {orchestrator?.metadata?.downloadSpeed || 0} Kbps</span>
                <span className="text-purple-500">↑ {orchestrator?.metadata?.uploadSpeed || 0} Kbps</span>
              </div>
            </div>
          </div>

          <div className="border-t border-gray-800 pt-4">
            <div className="mb-2 text-xs font-semibold">System Health</div>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="text-gray-400">-12h</span>
              <span className="text-gray-400">Now</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-gray-700">
              <div className="h-full bg-green-500" style={{ width: "96%" }} />
            </div>
            <div className="mt-2 flex items-center justify-between">
              <button className="text-xs text-blue-500 hover:underline">See All</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
