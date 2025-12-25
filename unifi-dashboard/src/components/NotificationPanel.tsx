"use client";

import { useState, useEffect } from "react";
import { Bell, X, AlertCircle, Info, CheckCircle, AlertTriangle } from "lucide-react";
import { notificationService, type NetworkAlert } from "@/lib/notification-service";

export function NotificationPanel() {
  const [alerts, setAlerts] = useState<NetworkAlert[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const unsubscribe = notificationService.subscribe((newAlerts) => {
      setAlerts(newAlerts);
    });

    return unsubscribe;
  }, []);

  const getIcon = (severity: string) => {
    switch (severity) {
      case "error":
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case "warning":
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case "success":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      default:
        return <Info className="h-5 w-5 text-blue-500" />;
    }
  };

  const getTimeAgo = (date: Date) => {
    const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative rounded-lg p-2 hover:bg-gray-700"
      >
        <Bell className="h-5 w-5" />
        {alerts.length > 0 && (
          <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold">
            {alerts.length > 9 ? "9+" : alerts.length}
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-12 z-50 w-96 rounded-lg border border-gray-700 bg-[#1E293B] shadow-2xl">
            <div className="flex items-center justify-between border-b border-gray-700 p-4">
              <h3 className="font-semibold">Notifications</h3>
              <button
                onClick={() => setIsOpen(false)}
                className="rounded p-1 hover:bg-gray-700"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="max-h-96 overflow-auto">
              {alerts.length === 0 ? (
                <div className="p-8 text-center text-sm text-gray-400">
                  No new notifications
                </div>
              ) : (
                alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className="border-b border-gray-700 p-4 hover:bg-gray-700/50 last:border-b-0"
                  >
                    <div className="flex gap-3">
                      <div className="mt-0.5">{getIcon(alert.severity)}</div>
                      <div className="flex-1">
                        <div className="mb-1 flex items-start justify-between">
                          <h4 className="text-sm font-semibold">{alert.title}</h4>
                          <button
                            onClick={() => notificationService.dismissAlert(alert.id)}
                            className="ml-2 rounded p-0.5 hover:bg-gray-600"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </div>
                        <p className="mb-2 text-xs text-gray-400">{alert.message}</p>
                        <div className="flex items-center justify-between text-xs text-gray-500">
                          {alert.deviceName && (
                            <span className="rounded bg-gray-700 px-2 py-0.5">
                              {alert.deviceName}
                            </span>
                          )}
                          <span>{getTimeAgo(alert.timestamp)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            {alerts.length > 0 && (
              <div className="border-t border-gray-700 p-2">
                <button
                  onClick={() => {
                    alerts.forEach((alert) => notificationService.dismissAlert(alert.id));
                  }}
                  className="w-full rounded py-2 text-center text-xs text-blue-500 hover:bg-gray-700"
                >
                  Clear All
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
