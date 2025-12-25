"use client";

import { useState } from "react";
import { Responsive as ResponsiveGridLayout } from "react-grid-layout";
import { Plus, X, GripVertical } from "lucide-react";
import { TrafficIdentification } from "./TrafficIdentification";
import { WiFiTechnology } from "./WiFiTechnology";
import { MostActiveClients } from "./MostActiveClients";
import { MostActiveAccessPoints } from "./MostActiveAccessPoints";
import { InternetActivity } from "./InternetActivity";
import "react-grid-layout/css/styles.css";
import "react-resizable/css/styles.css";

interface LayoutItem {
  i: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

interface Widget {
  id: string;
  type: string;
  title: string;
  component: React.ComponentType;
}

const availableWidgets: Widget[] = [
  {
    id: "traffic",
    type: "traffic-identification",
    title: "Traffic Identification",
    component: TrafficIdentification,
  },
  {
    id: "wifi",
    type: "wifi-technology",
    title: "WiFi Technology",
    component: WiFiTechnology,
  },
  {
    id: "clients",
    type: "active-clients",
    title: "Most Active Clients",
    component: MostActiveClients,
  },
  {
    id: "aps",
    type: "active-aps",
    title: "Most Active Access Points",
    component: MostActiveAccessPoints,
  },
  {
    id: "internet",
    type: "internet-activity",
    title: "Internet Activity",
    component: InternetActivity,
  },
];

export function CustomizableDashboard() {
  const [layout, setLayout] = useState([
    { i: "traffic", x: 0, y: 0, w: 6, h: 4 },
    { i: "wifi", x: 6, y: 0, w: 6, h: 4 },
    { i: "clients", x: 0, y: 4, w: 6, h: 3 },
    { i: "aps", x: 6, y: 4, w: 6, h: 3 },
    { i: "internet", x: 0, y: 7, w: 12, h: 4 },
  ]);

  const [activeWidgets, setActiveWidgets] = useState(["traffic", "wifi", "clients", "aps", "internet"]);
  const [isAddingWidget, setIsAddingWidget] = useState(false);

  const handleLayoutChange = (newLayout: LayoutItem[]) => {
    setLayout(newLayout.map(item => ({
      i: item.i,
      x: item.x,
      y: item.y,
      w: item.w,
      h: item.h,
    })));
  };

  const removeWidget = (widgetId: string) => {
    setActiveWidgets(activeWidgets.filter((id) => id !== widgetId));
    setLayout(layout.filter((item) => item.i !== widgetId));
  };

  const addWidget = (widgetId: string) => {
    if (activeWidgets.includes(widgetId)) return;

    setActiveWidgets([...activeWidgets, widgetId]);
    setLayout([
      ...layout,
      {
        i: widgetId,
        x: 0,
        y: Infinity,
        w: 6,
        h: 4,
      },
    ]);
    setIsAddingWidget(false);
  };

  return (
    <div className="relative p-6">
      {/* Add Widget Button */}
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold">Dashboard Widgets</h2>
        <button
          onClick={() => setIsAddingWidget(!isAddingWidget)}
          className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium hover:bg-blue-600"
        >
          <Plus className="h-4 w-4" />
          Add Widget
        </button>
      </div>

      {/* Widget Selector */}
      {isAddingWidget && (
        <div className="mb-4 rounded-lg border border-gray-700 bg-[#1E293B] p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Available Widgets</h3>
            <button
              onClick={() => setIsAddingWidget(false)}
              className="rounded p-1 hover:bg-gray-700"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {availableWidgets.map((widget) => (
              <button
                key={widget.id}
                onClick={() => addWidget(widget.id)}
                disabled={activeWidgets.includes(widget.id)}
                className={`rounded-lg border-2 p-4 text-left transition-colors ${
                  activeWidgets.includes(widget.id)
                    ? "border-gray-700 bg-gray-800 text-gray-500"
                    : "border-gray-600 bg-gray-700 hover:border-blue-500 hover:bg-gray-600"
                }`}
              >
                <div className="mb-2 flex items-center gap-2">
                  <GripVertical className="h-4 w-4" />
                  <span className="text-sm font-medium">{widget.title}</span>
                </div>
                {activeWidgets.includes(widget.id) && (
                  <span className="text-xs text-gray-500">Already added</span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Grid Layout */}
      <div className="grid grid-cols-2 gap-6">
        {activeWidgets.map((widgetId) => {
          const widget = availableWidgets.find((w) => w.id === widgetId);
          if (!widget) return null;

          const WidgetComponent = widget.component;

          return (
            <div
              key={widgetId}
              className={`rounded-lg border border-gray-700 bg-[#1E293B] ${
                widgetId === "internet" ? "col-span-2" : ""
              }`}
            >
              <div className="flex items-center justify-between border-b border-gray-700 p-3">
                <div className="flex cursor-move items-center gap-2">
                  <GripVertical className="h-4 w-4 text-gray-400" />
                  <span className="text-sm font-medium">{widget.title}</span>
                </div>
                <button
                  onClick={() => removeWidget(widgetId)}
                  className="rounded p-1 hover:bg-gray-700"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="overflow-hidden">
                <WidgetComponent />
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 text-center text-xs text-gray-400">
        Drag widgets to rearrange • Resize by dragging corners • Remove widgets with the X button
      </div>
    </div>
  );
}
