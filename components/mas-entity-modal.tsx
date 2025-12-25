"use client";

import { MASEntity } from "./mas-topology-view";
import { X } from "lucide-react";

interface DeviceModalProps {
  entity: MASEntity;
  onClose: () => void;
}

export function DeviceModal({ entity, onClose }: DeviceModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="relative w-full max-w-md rounded-lg bg-[#1E293B] p-6 shadow-xl">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-gray-400 hover:text-white"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="mb-4">
          <h2 className="text-xl font-semibold">{entity.name}</h2>
          <p className="text-sm text-gray-400 capitalize">{entity.type}</p>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-gray-800 pb-2">
            <span className="text-sm text-gray-400">Status</span>
            <span
              className={`text-sm font-medium ${
                entity.status === 'active' || entity.status === 'online'
                  ? 'text-green-400'
                  : entity.status === 'idle'
                  ? 'text-yellow-400'
                  : 'text-red-400'
              }`}
            >
              {entity.status}
            </span>
          </div>

          {entity.category && (
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <span className="text-sm text-gray-400">Category</span>
              <span className="text-sm capitalize">{entity.category}</span>
            </div>
          )}

          {entity.metadata?.ip && (
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <span className="text-sm text-gray-400">IP Address</span>
              <span className="text-sm">{entity.metadata.ip}</span>
            </div>
          )}

          {entity.metadata?.uptime && (
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <span className="text-sm text-gray-400">Uptime</span>
              <span className="text-sm">{entity.metadata.uptime}</span>
            </div>
          )}

          {entity.metadata?.tasksCompleted !== undefined && (
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <span className="text-sm text-gray-400">Tasks Completed</span>
              <span className="text-sm">{entity.metadata.tasksCompleted}</span>
            </div>
          )}

          {entity.metadata?.tasksInProgress !== undefined && (
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <span className="text-sm text-gray-400">Tasks In Progress</span>
              <span className="text-sm">{entity.metadata.tasksInProgress}</span>
            </div>
          )}

          {entity.metadata?.experience && (
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <span className="text-sm text-gray-400">Experience</span>
              <span
                className={`text-sm ${
                  entity.metadata.experience === 'Excellent'
                    ? 'text-green-400'
                    : entity.metadata.experience === 'Good'
                    ? 'text-blue-400'
                    : entity.metadata.experience === 'Fair'
                    ? 'text-yellow-400'
                    : 'text-red-400'
                }`}
              >
                {entity.metadata.experience}
              </span>
            </div>
          )}

          {entity.metadata?.downloadSpeed !== undefined && (
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <span className="text-sm text-gray-400">Download</span>
              <span className="text-sm text-cyan-400">
                ↓ {entity.metadata.downloadSpeed} Kbps
              </span>
            </div>
          )}

          {entity.metadata?.uploadSpeed !== undefined && (
            <div className="flex items-center justify-between border-b border-gray-800 pb-2">
              <span className="text-sm text-gray-400">Upload</span>
              <span className="text-sm text-green-400">
                ↑ {entity.metadata.uploadSpeed} Kbps
              </span>
            </div>
          )}

          {entity.connections && entity.connections.length > 0 && (
            <div className="border-b border-gray-800 pb-2">
              <span className="text-sm text-gray-400">Connections</span>
              <div className="mt-2 flex flex-wrap gap-2">
                {entity.connections.map((connId) => (
                  <span
                    key={connId}
                    className="rounded bg-blue-500/20 px-2 py-1 text-xs text-blue-400"
                  >
                    {connId}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
