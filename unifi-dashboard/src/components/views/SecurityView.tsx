"use client";

import { useState } from "react";
import { Shield, Plus, Edit, Trash2, Lock, Globe, Server } from "lucide-react";

interface FirewallRule {
  id: string;
  name: string;
  type: "allow" | "deny";
  source: string;
  destination: string;
  port: string;
  protocol: string;
  enabled: boolean;
}

interface PortForward {
  id: string;
  name: string;
  externalPort: string;
  internalIp: string;
  internalPort: string;
  protocol: string;
  enabled: boolean;
}

interface VPNConfig {
  id: string;
  name: string;
  type: "L2TP" | "OpenVPN" | "WireGuard";
  status: "active" | "inactive";
  clients: number;
}

const firewallRules: FirewallRule[] = [
  {
    id: "1",
    name: "Block Malicious IPs",
    type: "deny",
    source: "Any",
    destination: "192.168.1.0/24",
    port: "Any",
    protocol: "All",
    enabled: true,
  },
  {
    id: "2",
    name: "Allow HTTPS",
    type: "allow",
    source: "Any",
    destination: "Any",
    port: "443",
    protocol: "TCP",
    enabled: true,
  },
  {
    id: "3",
    name: "Allow DNS",
    type: "allow",
    source: "LAN",
    destination: "Any",
    port: "53",
    protocol: "UDP",
    enabled: true,
  },
];

const portForwards: PortForward[] = [
  {
    id: "1",
    name: "Web Server",
    externalPort: "80",
    internalIp: "192.168.1.100",
    internalPort: "80",
    protocol: "TCP",
    enabled: true,
  },
  {
    id: "2",
    name: "SSH Server",
    externalPort: "2222",
    internalIp: "192.168.1.50",
    internalPort: "22",
    protocol: "TCP",
    enabled: true,
  },
];

const vpnConfigs: VPNConfig[] = [
  {
    id: "1",
    name: "Remote Access VPN",
    type: "OpenVPN",
    status: "active",
    clients: 3,
  },
  {
    id: "2",
    name: "Site-to-Site VPN",
    type: "WireGuard",
    status: "active",
    clients: 1,
  },
];

export function SecurityView() {
  const [activeTab, setActiveTab] = useState<"firewall" | "portforward" | "vpn">("firewall");
  const [isAddingRule, setIsAddingRule] = useState(false);

  return (
    <div className="flex h-full flex-col overflow-auto bg-[#0F172A] p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-500/20">
            <Shield className="h-6 w-6 text-blue-500" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Network Security</h1>
            <p className="text-sm text-gray-400">
              Firewall rules, port forwarding, and VPN configuration
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 border-b border-gray-700">
          <button
            onClick={() => setActiveTab("firewall")}
            className={`flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "firewall"
                ? "border-blue-500 text-blue-500"
                : "border-transparent text-gray-400 hover:text-white"
            }`}
          >
            <Shield className="h-4 w-4" />
            Firewall Rules
          </button>
          <button
            onClick={() => setActiveTab("portforward")}
            className={`flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "portforward"
                ? "border-blue-500 text-blue-500"
                : "border-transparent text-gray-400 hover:text-white"
            }`}
          >
            <Globe className="h-4 w-4" />
            Port Forwarding
          </button>
          <button
            onClick={() => setActiveTab("vpn")}
            className={`flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === "vpn"
                ? "border-blue-500 text-blue-500"
                : "border-transparent text-gray-400 hover:text-white"
            }`}
          >
            <Lock className="h-4 w-4" />
            VPN
          </button>
        </div>
      </div>

      {/* Firewall Rules Tab */}
      {activeTab === "firewall" && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Firewall Rules</h2>
              <p className="text-xs text-gray-400">
                {firewallRules.filter((r) => r.enabled).length} active rules
              </p>
            </div>
            <button
              onClick={() => setIsAddingRule(true)}
              className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium hover:bg-blue-600"
            >
              <Plus className="h-4 w-4" />
              Add Rule
            </button>
          </div>

          <div className="overflow-hidden rounded-lg border border-gray-700 bg-[#1E293B]">
            <table className="w-full">
              <thead className="border-b border-gray-700 bg-gray-800/50 text-left text-xs text-gray-400">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Source</th>
                  <th className="px-4 py-3">Destination</th>
                  <th className="px-4 py-3">Port</th>
                  <th className="px-4 py-3">Protocol</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {firewallRules.map((rule) => (
                  <tr
                    key={rule.id}
                    className="border-b border-gray-700 text-sm last:border-0"
                  >
                    <td className="px-4 py-3 font-medium">{rule.name}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded px-2 py-1 text-xs font-medium ${
                          rule.type === "allow"
                            ? "bg-green-500/20 text-green-500"
                            : "bg-red-500/20 text-red-500"
                        }`}
                      >
                        {rule.type.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400">{rule.source}</td>
                    <td className="px-4 py-3 text-gray-400">{rule.destination}</td>
                    <td className="px-4 py-3 text-gray-400">{rule.port}</td>
                    <td className="px-4 py-3 text-gray-400">{rule.protocol}</td>
                    <td className="px-4 py-3">
                      <div
                        className={`h-2 w-2 rounded-full ${
                          rule.enabled ? "bg-green-500" : "bg-gray-500"
                        }`}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button className="rounded p-1 hover:bg-gray-700">
                          <Edit className="h-4 w-4" />
                        </button>
                        <button className="rounded p-1 text-red-500 hover:bg-gray-700">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Port Forwarding Tab */}
      {activeTab === "portforward" && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Port Forwarding Rules</h2>
              <p className="text-xs text-gray-400">
                {portForwards.filter((p) => p.enabled).length} active forwards
              </p>
            </div>
            <button
              onClick={() => setIsAddingRule(true)}
              className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium hover:bg-blue-600"
            >
              <Plus className="h-4 w-4" />
              Add Forward
            </button>
          </div>

          <div className="overflow-hidden rounded-lg border border-gray-700 bg-[#1E293B]">
            <table className="w-full">
              <thead className="border-b border-gray-700 bg-gray-800/50 text-left text-xs text-gray-400">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">External Port</th>
                  <th className="px-4 py-3">Internal IP</th>
                  <th className="px-4 py-3">Internal Port</th>
                  <th className="px-4 py-3">Protocol</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody>
                {portForwards.map((forward) => (
                  <tr
                    key={forward.id}
                    className="border-b border-gray-700 text-sm last:border-0"
                  >
                    <td className="px-4 py-3 font-medium">{forward.name}</td>
                    <td className="px-4 py-3 font-mono text-blue-500">
                      :{forward.externalPort}
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-400">
                      {forward.internalIp}
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-400">
                      :{forward.internalPort}
                    </td>
                    <td className="px-4 py-3 text-gray-400">{forward.protocol}</td>
                    <td className="px-4 py-3">
                      <div
                        className={`h-2 w-2 rounded-full ${
                          forward.enabled ? "bg-green-500" : "bg-gray-500"
                        }`}
                      />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button className="rounded p-1 hover:bg-gray-700">
                          <Edit className="h-4 w-4" />
                        </button>
                        <button className="rounded p-1 text-red-500 hover:bg-gray-700">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 rounded-lg bg-yellow-500/10 p-4 text-sm">
            <div className="mb-2 font-medium text-yellow-500">Security Warning</div>
            <p className="text-xs text-gray-400">
              Port forwarding exposes internal services to the internet. Ensure proper security
              measures are in place.
            </p>
          </div>
        </div>
      )}

      {/* VPN Tab */}
      {activeTab === "vpn" && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">VPN Servers</h2>
              <p className="text-xs text-gray-400">
                {vpnConfigs.filter((v) => v.status === "active").length} active VPN servers
              </p>
            </div>
            <button
              onClick={() => setIsAddingRule(true)}
              className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium hover:bg-blue-600"
            >
              <Plus className="h-4 w-4" />
              Add VPN Server
            </button>
          </div>

          <div className="grid gap-4">
            {vpnConfigs.map((vpn) => (
              <div
                key={vpn.id}
                className="rounded-lg border border-gray-700 bg-[#1E293B] p-6"
              >
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/20">
                      <Server className="h-5 w-5 text-blue-500" />
                    </div>
                    <div>
                      <h3 className="font-semibold">{vpn.name}</h3>
                      <p className="text-xs text-gray-400">{vpn.type}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span
                      className={`rounded px-3 py-1 text-xs font-medium ${
                        vpn.status === "active"
                          ? "bg-green-500/20 text-green-500"
                          : "bg-gray-500/20 text-gray-500"
                      }`}
                    >
                      {vpn.status.toUpperCase()}
                    </span>
                    <div className="flex gap-2">
                      <button className="rounded p-2 hover:bg-gray-700">
                        <Edit className="h-4 w-4" />
                      </button>
                      <button className="rounded p-2 text-red-500 hover:bg-gray-700">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <div className="mb-1 text-xs text-gray-400">Connected Clients</div>
                    <div className="text-2xl font-bold text-blue-500">{vpn.clients}</div>
                  </div>
                  <div>
                    <div className="mb-1 text-xs text-gray-400">Server IP</div>
                    <div className="font-mono text-sm">10.8.0.1</div>
                  </div>
                  <div>
                    <div className="mb-1 text-xs text-gray-400">Subnet</div>
                    <div className="font-mono text-sm">10.8.0.0/24</div>
                  </div>
                </div>

                {vpn.status === "active" && (
                  <div className="mt-4 flex gap-2">
                    <button className="rounded-lg bg-gray-700 px-4 py-2 text-xs font-medium hover:bg-gray-600">
                      Download Config
                    </button>
                    <button className="rounded-lg bg-gray-700 px-4 py-2 text-xs font-medium hover:bg-gray-600">
                      View QR Code
                    </button>
                    <button className="rounded-lg bg-gray-700 px-4 py-2 text-xs font-medium hover:bg-gray-600">
                      Manage Clients
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
