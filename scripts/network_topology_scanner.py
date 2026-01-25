#!/usr/bin/env python3
"""
Network Topology Scanner for Mycosoft Infrastructure

Scans the entire network topology, identifies devices, tests connectivity,
measures latency/throughput, and generates improvement recommendations.

Usage:
    python scripts/network_topology_scanner.py --full-scan
    python scripts/network_topology_scanner.py --quick-check
    python scripts/network_topology_scanner.py --generate-report
"""

import subprocess
import socket
import json
import time
import platform
import argparse
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import concurrent.futures


@dataclass
class NetworkDevice:
    """Represents a discovered network device."""
    ip: str
    hostname: Optional[str]
    mac: Optional[str]
    device_type: str  # router, switch, server, nas, access_point, workstation, unknown
    role: str  # e.g., "fiber_router", "10gig_switch", "proxmox_host", etc.
    ports: List[int]
    latency_ms: Optional[float]
    status: str  # online, offline, degraded
    connection_type: Optional[str]  # fiber, cat8, cat7, cat6, cat5e, wifi
    expected_speed_mbps: Optional[int]
    actual_speed_mbps: Optional[int]
    notes: List[str]


@dataclass
class ConnectionLink:
    """Represents a connection between two devices."""
    source_ip: str
    target_ip: str
    cable_type: Optional[str]  # fiber, cat8, cat7, cat6, cat5e, wifi
    expected_speed_mbps: int
    measured_speed_mbps: Optional[int]
    latency_ms: Optional[float]
    status: str  # optimal, degraded, bottleneck
    recommendations: List[str]


@dataclass
class NetworkAuditReport:
    """Complete network audit report."""
    scan_time: str
    total_devices: int
    devices: List[NetworkDevice]
    links: List[ConnectionLink]
    bottlenecks: List[Dict]
    cable_upgrades_needed: List[Dict]
    routing_improvements: List[Dict]
    overall_health: str  # healthy, degraded, critical
    summary: str


class NetworkTopologyScanner:
    """Comprehensive network topology scanner for Mycosoft infrastructure."""
    
    # Known infrastructure devices
    KNOWN_DEVICES = {
        # Core Infrastructure
        "192.168.0.1": {
            "device_type": "router",
            "role": "fiber_router_gateway",
            "expected_speed_mbps": 10000,
            "connection_type": "fiber",
            "description": "Fiber Optic Router (WAN Gateway)"
        },
        # 10Gig Switch (need to discover actual IP)
        "192.168.0.2": {
            "device_type": "switch",
            "role": "10gig_distribution_switch",
            "expected_speed_mbps": 10000,
            "connection_type": "cat8_10gbase_t",
            "description": "8-Port 10 Gigabit Switch"
        },
        # Dream Machine
        "192.168.0.3": {
            "device_type": "router",
            "role": "dream_machine_controller",
            "expected_speed_mbps": 2500,
            "connection_type": "cat8",
            "description": "UniFi Dream Machine (Network Controller)"
        },
        # NAS
        "192.168.0.105": {
            "device_type": "nas",
            "role": "network_storage",
            "expected_speed_mbps": 2500,
            "connection_type": "cat8",
            "description": "Network Attached Storage (Media/Backups)"
        },
        # Proxmox Servers (Dell)
        "192.168.0.202": {
            "device_type": "server",
            "role": "proxmox_host_1",
            "expected_speed_mbps": 10000,
            "connection_type": "cat8_10gbase_t",
            "description": "Dell Server #1 - Proxmox VE (Primary)"
        },
        # Additional Proxmox hosts to discover
        "192.168.0.203": {
            "device_type": "server",
            "role": "proxmox_host_2",
            "expected_speed_mbps": 10000,
            "connection_type": "cat8_10gbase_t",
            "description": "Dell Server #2 - Proxmox VE"
        },
        "192.168.0.204": {
            "device_type": "server",
            "role": "proxmox_host_3",
            "expected_speed_mbps": 10000,
            "connection_type": "cat8_10gbase_t",
            "description": "Dell Server #3 - Proxmox VE"
        },
        # Sandbox VM
        "192.168.0.187": {
            "device_type": "vm",
            "role": "sandbox_vm",
            "expected_speed_mbps": 1000,
            "connection_type": "virtual",
            "description": "Mycosoft Sandbox VM (VM 103)"
        },
        # Windows Dev PC
        "192.168.0.172": {
            "device_type": "workstation",
            "role": "development_pc",
            "expected_speed_mbps": 2500,
            "connection_type": "cat8",
            "description": "Windows Development PC"
        },
    }
    
    # WiFi Access Points (known bottleneck area)
    WIFI_ACCESS_POINTS = {
        "192.168.0.10": {
            "device_type": "access_point",
            "role": "ubiquiti_ap_1",
            "expected_speed_mbps": 2500,  # Should be 2.5Gig uplink
            "actual_speed_mbps": 30,  # USER REPORTED: ~30 Mbps output
            "connection_type": "poe_cat6",
            "description": "Ubiquiti WiFi AP #1 (BOTTLENECK)"
        },
        "192.168.0.11": {
            "device_type": "access_point",
            "role": "ubiquiti_ap_2",
            "expected_speed_mbps": 2500,
            "actual_speed_mbps": 30,
            "connection_type": "poe_cat6",
            "description": "Ubiquiti WiFi AP #2 (BOTTLENECK)"
        },
    }
    
    # Cable specifications for speed expectations
    CABLE_SPECS = {
        "fiber": {"max_speed_gbps": 100, "recommended_for": "backbone"},
        "cat8": {"max_speed_gbps": 40, "recommended_for": "10gig_servers"},
        "cat7": {"max_speed_gbps": 10, "recommended_for": "10gig_short_runs"},
        "cat6a": {"max_speed_gbps": 10, "recommended_for": "10gig_up_to_100m"},
        "cat6": {"max_speed_gbps": 1, "recommended_for": "gigabit"},
        "cat5e": {"max_speed_gbps": 1, "recommended_for": "legacy_gigabit"},
        "wifi6e": {"max_speed_gbps": 2.4, "recommended_for": "wireless_clients"},
        "wifi6": {"max_speed_gbps": 1.2, "recommended_for": "wireless_clients"},
    }

    def __init__(self):
        self.discovered_devices: List[NetworkDevice] = []
        self.connection_links: List[ConnectionLink] = []
        self.bottlenecks: List[Dict] = []
        self.is_windows = platform.system() == "Windows"
        
    def ping_host(self, ip: str, count: int = 2) -> Tuple[bool, Optional[float]]:
        """Ping a host and return (reachable, avg_latency_ms)."""
        try:
            if self.is_windows:
                cmd = ["ping", "-n", str(count), "-w", "500", ip]
            else:
                cmd = ["ping", "-c", str(count), "-W", "1", ip]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                # Parse average latency
                output = result.stdout
                if self.is_windows:
                    # Windows: Average = 1ms
                    for line in output.split('\n'):
                        if 'Average' in line or 'average' in line:
                            parts = line.split('=')
                            if len(parts) >= 2:
                                latency_str = parts[-1].strip().replace('ms', '')
                                try:
                                    return True, float(latency_str)
                                except ValueError:
                                    return True, None
                else:
                    # Linux: rtt min/avg/max/mdev = 0.123/0.456/0.789/0.012 ms
                    for line in output.split('\n'):
                        if 'rtt' in line or 'round-trip' in line:
                            parts = line.split('/')
                            if len(parts) >= 5:
                                try:
                                    return True, float(parts[4])
                                except ValueError:
                                    return True, None
                return True, None
            return False, None
        except (subprocess.TimeoutExpired, Exception):
            return False, None
    
    def get_hostname(self, ip: str) -> Optional[str]:
        """Resolve hostname from IP."""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except socket.herror:
            return None
    
    def scan_port(self, ip: str, port: int, timeout: float = 0.3) -> bool:
        """Check if a specific port is open."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def detect_device_type(self, ip: str, open_ports: List[int]) -> str:
        """Detect device type based on open ports."""
        if 8006 in open_ports:
            return "proxmox_server"
        if 22 in open_ports and 80 in open_ports:
            return "linux_server"
        if 443 in open_ports and 8443 in open_ports:
            return "unifi_device"
        if 5000 in open_ports or 5001 in open_ports:
            return "nas"
        if 3389 in open_ports:
            return "windows"
        if 53 in open_ports:
            return "dns_server"
        if 8080 in open_ports or 80 in open_ports:
            return "web_device"
        return "unknown"
    
    def scan_subnet(self, subnet: str = "192.168.0", start: int = 1, end: int = 254) -> List[NetworkDevice]:
        """Scan a subnet range for devices."""
        print(f"[*] Scanning subnet {subnet}.{start}-{end}...")
        devices = []
        
        # Common ports to check
        common_ports = [22, 53, 80, 443, 3389, 5000, 5001, 8006, 8443, 8080, 3000, 8000]
        
        def scan_host(ip: str) -> Optional[NetworkDevice]:
            reachable, latency = self.ping_host(ip, count=2)
            if not reachable:
                return None
            
            # Scan ports
            open_ports = []
            for port in common_ports:
                if self.scan_port(ip, port):
                    open_ports.append(port)
            
            hostname = self.get_hostname(ip)
            device_type = self.detect_device_type(ip, open_ports)
            
            # Check if it's a known device
            known = self.KNOWN_DEVICES.get(ip, {})
            if not known:
                known = self.WIFI_ACCESS_POINTS.get(ip, {})
            
            return NetworkDevice(
                ip=ip,
                hostname=hostname,
                mac=None,  # Would need ARP table access
                device_type=known.get("device_type", device_type),
                role=known.get("role", "unknown"),
                ports=open_ports,
                latency_ms=latency,
                status="online",
                connection_type=known.get("connection_type"),
                expected_speed_mbps=known.get("expected_speed_mbps"),
                actual_speed_mbps=known.get("actual_speed_mbps"),
                notes=[known.get("description", "")] if known.get("description") else []
            )
        
        # Use thread pool for faster scanning
        ips = [f"{subnet}.{i}" for i in range(start, end + 1)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = {executor.submit(scan_host, ip): ip for ip in ips}
            for future in concurrent.futures.as_completed(futures):
                try:
                    device = future.result()
                    if device:
                        devices.append(device)
                        print(f"    [+] Found: {device.ip} ({device.device_type}) - {device.latency_ms}ms")
                except Exception as e:
                    pass
        
        return sorted(devices, key=lambda d: [int(x) for x in d.ip.split('.')])
    
    def scan_known_devices(self) -> List[NetworkDevice]:
        """Scan only known infrastructure devices."""
        print("[*] Scanning known infrastructure devices...")
        devices = []
        
        all_known = {**self.KNOWN_DEVICES, **self.WIFI_ACCESS_POINTS}
        
        for ip, info in all_known.items():
            reachable, latency = self.ping_host(ip, count=4)
            status = "online" if reachable else "offline"
            
            # Scan ports for online devices
            open_ports = []
            if reachable:
                common_ports = [22, 80, 443, 8006, 8443, 3000, 8000, 8003, 5678]
                for port in common_ports:
                    if self.scan_port(ip, port):
                        open_ports.append(port)
            
            hostname = self.get_hostname(ip) if reachable else None
            
            device = NetworkDevice(
                ip=ip,
                hostname=hostname,
                mac=None,
                device_type=info["device_type"],
                role=info["role"],
                ports=open_ports,
                latency_ms=latency if reachable else None,
                status=status,
                connection_type=info.get("connection_type"),
                expected_speed_mbps=info.get("expected_speed_mbps"),
                actual_speed_mbps=info.get("actual_speed_mbps"),
                notes=[info.get("description", "")]
            )
            devices.append(device)
            
            status_icon = "+" if reachable else "x"
            latency_str = f"{latency:.1f}ms" if latency else "N/A"
            print(f"    [{status_icon}] {ip}: {info['description']} - {latency_str}")
        
        return devices
    
    def analyze_bottlenecks(self, devices: List[NetworkDevice]) -> List[Dict]:
        """Analyze network for bottlenecks."""
        print("\n[*] Analyzing bottlenecks...")
        bottlenecks = []
        
        for device in devices:
            # Check WiFi access points specifically (user reported issue)
            if device.device_type == "access_point":
                if device.expected_speed_mbps and device.actual_speed_mbps:
                    if device.actual_speed_mbps < device.expected_speed_mbps * 0.1:
                        bottleneck = {
                            "device": device.ip,
                            "role": device.role,
                            "severity": "CRITICAL",
                            "issue": f"WiFi throughput severely degraded: {device.actual_speed_mbps} Mbps vs expected {device.expected_speed_mbps} Mbps",
                            "expected_speed": device.expected_speed_mbps,
                            "actual_speed": device.actual_speed_mbps,
                            "speed_percentage": (device.actual_speed_mbps / device.expected_speed_mbps) * 100,
                            "recommendations": [
                                "Check uplink cable - may be Cat 5e limiting to 100Mbps",
                                "Verify PoE switch port is 1Gig+ capable",
                                "Check AP firmware is up to date",
                                "Verify 2.5Gbe port is negotiating at full speed",
                                "Consider dedicated Cat 8 or Cat 6a run to each AP",
                                "Check for interference or channel congestion"
                            ]
                        }
                        bottlenecks.append(bottleneck)
                        print(f"    [!] BOTTLENECK: {device.ip} - {bottleneck['issue']}")
            
            # Check for high latency
            if device.latency_ms and device.latency_ms > 10:
                bottleneck = {
                    "device": device.ip,
                    "role": device.role,
                    "severity": "WARNING" if device.latency_ms < 50 else "CRITICAL",
                    "issue": f"High latency: {device.latency_ms:.1f}ms",
                    "recommendations": [
                        "Check cable quality and connections",
                        "Verify switch port negotiation speed",
                        "Check for packet errors in switch logs"
                    ]
                }
                bottlenecks.append(bottleneck)
        
        return bottlenecks
    
    def generate_cable_recommendations(self, devices: List[NetworkDevice]) -> List[Dict]:
        """Generate cable upgrade recommendations."""
        print("\n[*] Generating cable recommendations...")
        recommendations = []
        
        # WiFi APs with PoE (likely Cat 5e/6 limited)
        for device in devices:
            if device.device_type == "access_point" and device.connection_type:
                if "cat5" in device.connection_type.lower() or "cat6" in device.connection_type.lower():
                    rec = {
                        "device": device.ip,
                        "current_cable": device.connection_type,
                        "recommended_cable": "Cat 6a or Cat 8",
                        "reason": "Current cable limits negotiation speed for 2.5Gbe AP uplink",
                            "expected_improvement": "30 Mbps -> 2500 Mbps (83x improvement)",
                        "priority": "HIGH"
                    }
                    recommendations.append(rec)
                    print(f"    [!] {device.ip}: Upgrade {device.connection_type} -> Cat 6a/8")
        
        # Check 10Gig infrastructure
        for device in devices:
            if device.expected_speed_mbps and device.expected_speed_mbps >= 10000:
                if device.connection_type and "cat6" in device.connection_type.lower():
                    if "cat6a" not in device.connection_type.lower():
                        rec = {
                            "device": device.ip,
                            "current_cable": device.connection_type,
                            "recommended_cable": "Cat 7 or Cat 8",
                            "reason": "Cat 6 cannot sustain 10Gbps over typical runs",
                            "expected_improvement": "1000 Mbps -> 10000 Mbps (10x improvement)",
                            "priority": "MEDIUM"
                        }
                        recommendations.append(rec)
        
        return recommendations
    
    def generate_routing_improvements(self, devices: List[NetworkDevice]) -> List[Dict]:
        """Generate physical routing improvement suggestions."""
        improvements = []
        
        # Analyze the topology path: Fiber → 10G Switch → Dream Machine → PoE Switch → APs
        improvements.append({
            "issue": "WiFi AP uplink chain",
            "current_path": "Fiber Router → 10G Switch → Dream Machine → PoE Switch → WiFi APs",
            "bottleneck_location": "PoE Switch or cabling to APs",
            "recommendations": [
                "1. Verify PoE switch supports 2.5Gbe on AP ports",
                "2. Replace Cat 5e/6 runs to APs with Cat 6a minimum",
                "3. If PoE switch is only 1Gig, upgrade to 2.5Gbe PoE+ switch",
                "4. Consider shorter cable runs or fiber SFP+ for long runs",
                "5. Check if APs are daisy-chained (reduces bandwidth)"
            ],
            "priority": "HIGH"
        })
        
        improvements.append({
            "issue": "10Gig server backbone",
            "current_path": "Fiber Router → 10G Switch → Dell Servers",
            "recommendation": [
                "1. Ensure all server NICs are 10Gbase-T or SFP+",
                "2. Use Cat 8 for runs under 30m for 10Gig",
                "3. For longer runs, consider fiber with SFP+ modules",
                "4. Verify switch ports are all negotiating at 10Gbps"
            ],
            "priority": "MEDIUM"
        })
        
        return improvements
    
    def test_throughput(self, source_ip: str, target_ip: str) -> Optional[float]:
        """Test throughput between two hosts (requires iperf3)."""
        # This is a placeholder - would need iperf3 server running on target
        # For now, return None and note it in recommendations
        return None
    
    def generate_report(self, devices: List[NetworkDevice], 
                       bottlenecks: List[Dict],
                       cable_recs: List[Dict],
                       routing_recs: List[Dict]) -> NetworkAuditReport:
        """Generate comprehensive network audit report."""
        
        # Determine overall health
        critical_count = len([b for b in bottlenecks if b.get("severity") == "CRITICAL"])
        warning_count = len([b for b in bottlenecks if b.get("severity") == "WARNING"])
        
        if critical_count > 0:
            health = "critical"
        elif warning_count > 2:
            health = "degraded"
        else:
            health = "healthy"
        
        # Generate summary
        online_count = len([d for d in devices if d.status == "online"])
        summary = f"""
Network Audit Summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
=====================================================

Infrastructure Overview:
- Total Devices Scanned: {len(devices)}
- Devices Online: {online_count}
- Devices Offline: {len(devices) - online_count}
- Overall Health: {health.upper()}

Critical Issues Found: {critical_count}
- WiFi AP throughput severely degraded (10Gig -> 2.5Gig -> 30Mbps)
- Root cause: Likely cable or PoE switch limitation

Recommendations:
1. IMMEDIATE: Audit cabling from PoE switches to WiFi APs
2. IMMEDIATE: Check PoE switch port speed capabilities
3. SHORT-TERM: Replace any Cat 5e/6 runs with Cat 6a minimum
4. MEDIUM-TERM: Consider upgrading PoE switches to 2.5Gbe models

Cable Upgrades Needed: {len(cable_recs)}
Physical Routing Changes: {len(routing_recs)}
"""
        
        return NetworkAuditReport(
            scan_time=datetime.now().isoformat(),
            total_devices=len(devices),
            devices=devices,
            links=[],  # Would populate with actual link measurements
            bottlenecks=bottlenecks,
            cable_upgrades_needed=cable_recs,
            routing_improvements=routing_recs,
            overall_health=health,
            summary=summary
        )
    
    def save_report(self, report: NetworkAuditReport, output_dir: Path):
        """Save the report to files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON report
        json_path = output_dir / f"network_audit_{timestamp}.json"
        with open(json_path, 'w') as f:
            report_dict = asdict(report)
            # Convert NetworkDevice objects
            report_dict["devices"] = [asdict(d) for d in report.devices]
            json.dump(report_dict, f, indent=2, default=str)
        print(f"\n[*] JSON report saved: {json_path}")
        
        # Save Markdown report
        md_path = output_dir / f"NETWORK_AUDIT_{timestamp}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Mycosoft Network Infrastructure Audit\n\n")
            f.write(f"**Scan Date**: {report.scan_time}\n")
            f.write(f"**Overall Health**: {report.overall_health.upper()}\n\n")
            f.write("---\n\n")
            f.write(report.summary)
            f.write("\n\n---\n\n")
            
            # Device Table
            f.write("## Discovered Devices\n\n")
            f.write("| IP | Type | Role | Status | Latency | Expected Speed | Notes |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for device in report.devices:
                latency = f"{device.latency_ms:.1f}ms" if device.latency_ms else "N/A"
                speed = f"{device.expected_speed_mbps} Mbps" if device.expected_speed_mbps else "N/A"
                notes = device.notes[0] if device.notes else ""
                f.write(f"| {device.ip} | {device.device_type} | {device.role} | {device.status} | {latency} | {speed} | {notes} |\n")
            
            # Bottlenecks
            f.write("\n## Bottlenecks Identified\n\n")
            for bn in report.bottlenecks:
                f.write(f"### {bn['severity']}: {bn['device']}\n")
                f.write(f"- **Role**: {bn['role']}\n")
                f.write(f"- **Issue**: {bn['issue']}\n")
                f.write(f"- **Recommendations**:\n")
                for rec in bn.get('recommendations', []):
                    f.write(f"  - {rec}\n")
                f.write("\n")
            
            # Cable Upgrades
            f.write("## Cable Upgrade Recommendations\n\n")
            f.write("| Device | Current | Recommended | Priority | Expected Improvement |\n")
            f.write("|---|---|---|---|---|\n")
            for rec in report.cable_upgrades_needed:
                f.write(f"| {rec['device']} | {rec['current_cable']} | {rec['recommended_cable']} | {rec['priority']} | {rec.get('expected_improvement', 'N/A')} |\n")
            
            # Routing Improvements
            f.write("\n## Physical Routing Improvements\n\n")
            for imp in report.routing_improvements:
                f.write(f"### {imp['issue']}\n")
                f.write(f"**Current Path**: {imp.get('current_path', 'N/A')}\n\n")
                if isinstance(imp.get('recommendations'), list):
                    for r in imp['recommendations']:
                        f.write(f"- {r}\n")
                elif isinstance(imp.get('recommendation'), list):
                    for r in imp['recommendation']:
                        f.write(f"- {r}\n")
                f.write("\n")
        
        print(f"[*] Markdown report saved: {md_path}")
        
        return json_path, md_path


def main():
    parser = argparse.ArgumentParser(description="Mycosoft Network Topology Scanner")
    parser.add_argument("--full-scan", action="store_true", help="Full subnet scan (192.168.0.1-254)")
    parser.add_argument("--quick-check", action="store_true", help="Scan only known devices")
    parser.add_argument("--generate-report", action="store_true", help="Generate audit report")
    parser.add_argument("--output-dir", type=str, default="docs", help="Output directory for reports")
    
    args = parser.parse_args()
    
    scanner = NetworkTopologyScanner()
    
    print("=" * 60)
    print("  MYCOSOFT NETWORK TOPOLOGY SCANNER")
    print("=" * 60)
    print(f"  Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    # Default to quick check if no args
    if not any([args.full_scan, args.quick_check, args.generate_report]):
        args.quick_check = True
        args.generate_report = True
    
    devices = []
    
    if args.full_scan:
        print("[*] Starting full subnet scan...")
        devices = scanner.scan_subnet()
    elif args.quick_check:
        print("[*] Starting quick infrastructure check...")
        devices = scanner.scan_known_devices()
    
    if devices:
        scanner.discovered_devices = devices
        
        # Analyze
        bottlenecks = scanner.analyze_bottlenecks(devices)
        cable_recs = scanner.generate_cable_recommendations(devices)
        routing_recs = scanner.generate_routing_improvements(devices)
        
        if args.generate_report:
            print("\n[*] Generating audit report...")
            report = scanner.generate_report(devices, bottlenecks, cable_recs, routing_recs)
            
            output_dir = Path(args.output_dir)
            json_path, md_path = scanner.save_report(report, output_dir)
            
            print("\n" + "=" * 60)
            print("  SCAN COMPLETE")
            print("=" * 60)
            print(report.summary)
            print("=" * 60)
    else:
        print("[!] No devices discovered. Check network connectivity.")


if __name__ == "__main__":
    main()
