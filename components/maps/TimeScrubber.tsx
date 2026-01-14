"use client";

/**
 * TimeScrubber - Time control with alert timeline for device tracking
 * Allows playback, scrubbing, and visualizes alerts on timeline
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { Play, Pause, SkipBack, SkipForward, Clock } from "lucide-react";

interface Alert {
  id: string;
  timestamp: number;
  level: "info" | "warning" | "critical";
  message: string;
  device_id?: string;
}

interface TimeScrubberProps {
  startTime: number; // Unix timestamp (seconds)
  endTime: number;   // Unix timestamp (seconds)
  currentTime: number;
  onTimeChange: (time: number) => void;
  alerts?: Alert[];
  playbackSpeed?: number; // 1x, 2x, etc.
  onAlertClick?: (alert: Alert) => void;
}

const ALERT_COLORS = {
  info: "#3b82f6",     // blue
  warning: "#f59e0b",   // amber
  critical: "#ef4444",  // red
};

export function TimeScrubber({
  startTime,
  endTime,
  currentTime,
  onTimeChange,
  alerts = [],
  playbackSpeed = 1,
  onAlertClick,
}: TimeScrubberProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [localSpeed, setLocalSpeed] = useState(playbackSpeed);
  const animationRef = useRef<number>();
  const lastTimeRef = useRef<number>(performance.now());

  const duration = endTime - startTime;
  const progress = duration > 0 ? ((currentTime - startTime) / duration) * 100 : 0;

  // Playback loop
  useEffect(() => {
    if (!isPlaying) {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      return;
    }

    const animate = () => {
      const now = performance.now();
      const delta = (now - lastTimeRef.current) / 1000; // seconds
      lastTimeRef.current = now;

      const newTime = currentTime + delta * localSpeed;
      
      if (newTime >= endTime) {
        onTimeChange(startTime); // Loop back
      } else {
        onTimeChange(newTime);
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    lastTimeRef.current = performance.now();
    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isPlaying, localSpeed, currentTime, startTime, endTime, onTimeChange]);

  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = parseFloat(e.target.value);
      const newTime = startTime + (value / 100) * duration;
      onTimeChange(newTime);
    },
    [startTime, duration, onTimeChange]
  );

  const skipBackward = () => {
    const newTime = Math.max(startTime, currentTime - 60);
    onTimeChange(newTime);
  };

  const skipForward = () => {
    const newTime = Math.min(endTime, currentTime + 60);
    onTimeChange(newTime);
  };

  const cycleSpeed = () => {
    const speeds = [1, 2, 5, 10];
    const currentIndex = speeds.indexOf(localSpeed);
    const nextIndex = (currentIndex + 1) % speeds.length;
    setLocalSpeed(speeds[nextIndex]);
  };

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  };

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="time-scrubber">
      <div className="scrubber-header">
        <div className="time-display">
          <Clock className="time-icon" />
          <span className="current-time">{formatTime(currentTime)}</span>
          <span className="current-date">{formatDate(currentTime)}</span>
        </div>
        <div className="controls">
          <button onClick={skipBackward} className="control-btn" title="Skip back 1 min">
            <SkipBack className="control-icon" />
          </button>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="control-btn play-btn"
            title={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? <Pause className="control-icon" /> : <Play className="control-icon" />}
          </button>
          <button onClick={skipForward} className="control-btn" title="Skip forward 1 min">
            <SkipForward className="control-icon" />
          </button>
          <button onClick={cycleSpeed} className="speed-btn" title="Playback speed">
            {localSpeed}x
          </button>
        </div>
        <div className="time-range">
          <span className="range-time">{formatTime(startTime)}</span>
          <span className="range-separator">→</span>
          <span className="range-time">{formatTime(endTime)}</span>
        </div>
      </div>

      <div className="slider-container">
        <input
          type="range"
          min={0}
          max={100}
          step={0.1}
          value={progress}
          onChange={handleSliderChange}
          className="slider"
        />
        <div className="slider-track" />
        <div className="slider-progress" style={{ width: `${progress}%` }} />
        
        {/* Alert markers */}
        <div className="alert-markers">
          {alerts.map((alert) => {
            const alertProgress = ((alert.timestamp - startTime) / duration) * 100;
            if (alertProgress < 0 || alertProgress > 100) return null;
            return (
              <button
                key={alert.id}
                className="alert-marker"
                style={{
                  left: `${alertProgress}%`,
                  backgroundColor: ALERT_COLORS[alert.level],
                }}
                title={`${alert.message} (${formatTime(alert.timestamp)})`}
                onClick={() => onAlertClick?.(alert)}
              />
            );
          })}
        </div>
      </div>

      <style jsx>{`
        .time-scrubber {
          position: absolute;
          left: 16px;
          right: 16px;
          bottom: 16px;
          background: rgba(0, 0, 0, 0.75);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          padding: 16px 20px;
          font-family: ui-monospace, monospace;
        }

        .scrubber-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 12px;
        }

        .time-display {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .time-icon {
          width: 16px;
          height: 16px;
          color: #6b7280;
        }

        .current-time {
          font-size: 18px;
          font-weight: 600;
          color: #e5e7eb;
          letter-spacing: 0.05em;
        }

        .current-date {
          font-size: 12px;
          color: #6b7280;
          margin-left: 8px;
        }

        .controls {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .control-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 36px;
          height: 36px;
          border: 1px solid rgba(255, 255, 255, 0.15);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.05);
          color: #9ca3af;
          cursor: pointer;
          transition: all 0.2s;
        }

        .control-btn:hover {
          background: rgba(255, 255, 255, 0.1);
          color: #e5e7eb;
          border-color: rgba(255, 255, 255, 0.25);
        }

        .play-btn {
          background: rgba(59, 130, 246, 0.2);
          border-color: rgba(59, 130, 246, 0.3);
          color: #60a5fa;
        }

        .play-btn:hover {
          background: rgba(59, 130, 246, 0.3);
          border-color: rgba(59, 130, 246, 0.5);
        }

        .control-icon {
          width: 16px;
          height: 16px;
        }

        .speed-btn {
          padding: 6px 12px;
          font-size: 12px;
          font-weight: 500;
          border: 1px solid rgba(255, 255, 255, 0.15);
          border-radius: 6px;
          background: rgba(255, 255, 255, 0.05);
          color: #9ca3af;
          cursor: pointer;
          transition: all 0.2s;
        }

        .speed-btn:hover {
          background: rgba(255, 255, 255, 0.1);
          color: #e5e7eb;
        }

        .time-range {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 11px;
          color: #6b7280;
        }

        .range-separator {
          color: #4b5563;
        }

        .slider-container {
          position: relative;
          height: 20px;
        }

        .slider {
          position: absolute;
          width: 100%;
          height: 20px;
          opacity: 0;
          cursor: pointer;
          z-index: 10;
        }

        .slider-track {
          position: absolute;
          top: 8px;
          left: 0;
          right: 0;
          height: 4px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 2px;
        }

        .slider-progress {
          position: absolute;
          top: 8px;
          left: 0;
          height: 4px;
          background: linear-gradient(90deg, #3b82f6, #60a5fa);
          border-radius: 2px;
          pointer-events: none;
        }

        .alert-markers {
          position: absolute;
          top: 4px;
          left: 0;
          right: 0;
          height: 12px;
          pointer-events: none;
        }

        .alert-marker {
          position: absolute;
          width: 3px;
          height: 12px;
          border: none;
          border-radius: 1px;
          cursor: pointer;
          pointer-events: auto;
          transition: transform 0.2s;
        }

        .alert-marker:hover {
          transform: scaleY(1.5);
        }
      `}</style>
    </div>
  );
}
