"use client";

/**
 * HUD Overlay for cinematic dashboard
 * Pure HTML/CSS overlay that doesn't impact WebGL performance
 */

import { useEffect, useState } from "react";
import { Activity, Wifi, Cpu, Database, Radio, Thermometer } from "lucide-react";

interface HUDProps {
  title?: string;
  subtitle?: string;
}

interface SystemMetrics {
  devices: { online: number; total: number };
  agents: { active: number; total: number };
  uptime: string;
  dataRate: { up: string; down: string };
  temperature: number;
  humidity: number;
}

export function HUD({ title = "NATUREOS", subtitle = "Observation & Environmental Intelligence" }: HUDProps) {
  const [metrics, setMetrics] = useState<SystemMetrics>({
    devices: { online: 14, total: 20 },
    agents: { active: 7, total: 42 },
    uptime: "99.7%",
    dataRate: { up: "12.4 kbps", down: "8.2 kbps" },
    temperature: 23.5,
    humidity: 65,
  });

  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => {
      setTime(new Date());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch real metrics from API
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch("/api/metrics");
        if (res.ok) {
          const data = await res.json();
          if (data) {
            setMetrics((prev) => ({
              ...prev,
              ...data,
            }));
          }
        }
      } catch {
        // Use default metrics on error
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="hud-container">
      {/* Top Left Panel */}
      <div className="hud-panel top-left">
        <div className="hud-header">
          <Activity className="hud-icon" />
          <div>
            <h1 className="hud-title">{title}</h1>
            <p className="hud-subtitle">{subtitle}</p>
          </div>
        </div>
        <div className="hud-divider" />
        <div className="hud-metrics">
          <div className="hud-metric">
            <Cpu className="hud-metric-icon" />
            <span className="hud-metric-label">Devices</span>
            <span className="hud-metric-value">
              {metrics.devices.online}/{metrics.devices.total}
            </span>
          </div>
          <div className="hud-metric">
            <Database className="hud-metric-icon" />
            <span className="hud-metric-label">Agents</span>
            <span className="hud-metric-value">
              {metrics.agents.active} Active
            </span>
          </div>
          <div className="hud-metric">
            <Wifi className="hud-metric-icon" />
            <span className="hud-metric-label">Network</span>
            <span className="hud-metric-value">
              ↑{metrics.dataRate.up} ↓{metrics.dataRate.down}
            </span>
          </div>
        </div>
        <div className="hud-bar">
          <div
            className="hud-bar-fill"
            style={{ width: `${(metrics.devices.online / metrics.devices.total) * 100}%` }}
          />
        </div>
      </div>

      {/* Top Right Panel */}
      <div className="hud-panel top-right">
        <div className="hud-time">
          {time.toLocaleTimeString("en-US", { hour12: false })}
        </div>
        <div className="hud-date">
          {time.toLocaleDateString("en-US", {
            weekday: "short",
            month: "short",
            day: "numeric",
          })}
        </div>
        <div className="hud-divider" />
        <div className="hud-env">
          <div className="hud-env-item">
            <Thermometer className="hud-env-icon" />
            <span>{metrics.temperature.toFixed(1)}°C</span>
          </div>
          <div className="hud-env-item">
            <Radio className="hud-env-icon" />
            <span>{metrics.humidity}%</span>
          </div>
        </div>
      </div>

      {/* Bottom Status Bar */}
      <div className="hud-panel bottom-center">
        <div className="hud-status">
          <span className="hud-status-dot online" />
          <span>System Operational</span>
          <span className="hud-status-separator">|</span>
          <span>Uptime: {metrics.uptime}</span>
          <span className="hud-status-separator">|</span>
          <span>MycoBrain: Connected</span>
        </div>
      </div>

      <style jsx>{`
        .hud-container {
          position: fixed;
          inset: 0;
          pointer-events: none;
          font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
          z-index: 100;
        }

        .hud-panel {
          position: absolute;
          padding: 16px 20px;
          border: 1px solid rgba(0, 212, 255, 0.2);
          background: linear-gradient(
            135deg,
            rgba(0, 20, 40, 0.85),
            rgba(0, 10, 30, 0.75)
          );
          backdrop-filter: blur(8px);
          border-radius: 12px;
          box-shadow: 0 0 0 1px rgba(0, 212, 255, 0.1) inset,
            0 8px 32px rgba(0, 0, 0, 0.4);
          color: #c9f2ff;
          pointer-events: auto;
        }

        .top-left {
          top: 24px;
          left: 24px;
          min-width: 280px;
        }

        .top-right {
          top: 24px;
          right: 24px;
          text-align: right;
          min-width: 160px;
        }

        .bottom-center {
          bottom: 24px;
          left: 50%;
          transform: translateX(-50%);
        }

        .hud-header {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .hud-icon {
          width: 24px;
          height: 24px;
          color: #00d4ff;
        }

        .hud-title {
          margin: 0;
          font-size: 14px;
          font-weight: 700;
          letter-spacing: 0.15em;
          color: #00d4ff;
        }

        .hud-subtitle {
          margin: 2px 0 0;
          font-size: 10px;
          color: #7aa8c0;
          letter-spacing: 0.05em;
        }

        .hud-divider {
          height: 1px;
          margin: 12px 0;
          background: linear-gradient(90deg, #00d4ff33, transparent);
        }

        .hud-metrics {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .hud-metric {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 12px;
        }

        .hud-metric-icon {
          width: 14px;
          height: 14px;
          color: #5ab8d4;
        }

        .hud-metric-label {
          color: #7aa8c0;
          min-width: 60px;
        }

        .hud-metric-value {
          color: #e0f7ff;
          font-weight: 500;
        }

        .hud-bar {
          height: 4px;
          margin-top: 12px;
          background: rgba(0, 20, 40, 0.8);
          border-radius: 2px;
          overflow: hidden;
        }

        .hud-bar-fill {
          height: 100%;
          background: linear-gradient(90deg, #00d4ff, #7fffcc);
          border-radius: 2px;
          transition: width 0.5s ease;
        }

        .hud-time {
          font-size: 24px;
          font-weight: 600;
          color: #e0f7ff;
          letter-spacing: 0.1em;
        }

        .hud-date {
          font-size: 11px;
          color: #7aa8c0;
          margin-top: 4px;
        }

        .hud-env {
          display: flex;
          justify-content: flex-end;
          gap: 16px;
        }

        .hud-env-item {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 12px;
        }

        .hud-env-icon {
          width: 14px;
          height: 14px;
          color: #5ab8d4;
        }

        .hud-status {
          display: flex;
          align-items: center;
          gap: 12px;
          font-size: 11px;
          color: #a0d4e8;
        }

        .hud-status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #00ff88;
          box-shadow: 0 0 8px #00ff8866;
        }

        .hud-status-dot.offline {
          background: #ff4466;
          box-shadow: 0 0 8px #ff446666;
        }

        .hud-status-separator {
          color: #3a5a70;
        }
      `}</style>
    </div>
  );
}
