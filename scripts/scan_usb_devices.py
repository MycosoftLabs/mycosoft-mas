#!/usr/bin/env python3
"""
Windows USB Device Scanner for MycoBrain ESP32 Devices
Scans for USB serial devices and identifies ESP32-based MycoBrain boards
"""

import sys
import json
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import serial.tools.list_ports
except ImportError:
    print("ERROR: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)


def get_wmic_usb_info() -> List[Dict[str, Any]]:
    """Get detailed USB device information using WMIC (Windows Management Instrumentation)."""
    devices = []
    
    try:
        # Get USB devices with detailed info
        cmd = ['wmic', 'path', 'Win32_USBControllerDevice', 'get', 'Dependent,Antecedent', '/format:csv']
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Skip header
                if line.strip():
                    parts = line.split(',')
                    if len(parts) >= 2:
                        dependent = parts[-2].strip() if len(parts) >= 2 else ""
                        antecedent = parts[-1].strip() if len(parts) >= 1 else ""
                        if dependent and antecedent:
                            devices.append({
                                "dependent": dependent,
                                "antecedent": antecedent
                            })
    except Exception as e:
        print(f"Warning: Could not get WMIC USB info: {e}", file=sys.stderr)
    
    return devices


def get_serial_ports() -> List[Dict[str, Any]]:
    """Get all available serial ports with detailed information."""
    ports = []
    
    for port in serial.tools.list_ports.comports():
        port_info = {
            "port": port.device,
            "description": port.description,
            "manufacturer": port.manufacturer if hasattr(port, 'manufacturer') else None,
            "vid": hex(port.vid) if port.vid else None,
            "pid": hex(port.pid) if port.pid else None,
            "serial_number": port.serial_number if hasattr(port, 'serial_number') else None,
            "hwid": port.hwid if hasattr(port, 'hwid') else None,
            "location": port.location if hasattr(port, 'location') else None,
        }
        
        # Detect ESP32 devices
        is_esp32 = False
        is_mycobrain = False
        
        # ESP32-S3 typically has VID 0x303A (Espressif)
        if port.vid == 0x303A:
            is_esp32 = True
            is_mycobrain = True
        # Also check description
        elif port.description:
            desc_lower = port.description.lower()
            if "esp32" in desc_lower or "espressif" in desc_lower:
                is_esp32 = True
            if "mycobrain" in desc_lower or "mycosoft" in desc_lower:
                is_mycobrain = True
        
        port_info["is_esp32"] = is_esp32
        port_info["is_mycobrain"] = is_mycobrain
        port_info["likely_side"] = None
        
        # Try to determine which side (A or B) based on port number or description
        if is_esp32:
            port_num = port.device.replace("COM", "").replace("com", "")
            try:
                port_num_int = int(port_num)
                # Heuristic: lower COM numbers might be Side-A, higher might be Side-B
                # This is just a guess - actual assignment should be done manually
                if "side" in port.description.lower():
                    if "side-a" in port.description.lower() or "side a" in port.description.lower():
                        port_info["likely_side"] = "side-a"
                    elif "side-b" in port.description.lower() or "side b" in port.description.lower():
                        port_info["likely_side"] = "side-b"
            except ValueError:
                pass
        
        ports.append(port_info)
    
    return ports


def get_mac_address_from_port(port: str) -> Optional[str]:
    """Try to get MAC address from a serial port (requires device communication)."""
    # This would require actually connecting to the device and querying it
    # For now, return None - MAC will be obtained when device connects
    return None


def scan_devices() -> Dict[str, Any]:
    """Scan for all USB devices and identify MycoBrain ESP32 boards."""
    print("Scanning for USB devices...", file=sys.stderr)
    
    serial_ports = get_serial_ports()
    wmic_devices = get_wmic_usb_info()
    
    # Find ESP32 devices
    esp32_devices = [p for p in serial_ports if p.get("is_esp32", False)]
    mycobrain_devices = [p for p in serial_ports if p.get("is_mycobrain", False)]
    
    result = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "total_ports": len(serial_ports),
        "esp32_devices": esp32_devices,
        "mycobrain_devices": mycobrain_devices,
        "all_ports": serial_ports,
        "recommendations": []
    }
    
    # Generate recommendations
    if len(esp32_devices) >= 2:
        result["recommendations"].append({
            "type": "info",
            "message": f"Found {len(esp32_devices)} ESP32 devices. These are likely Side-A and Side-B."
        })
        
        # Try to identify which is which
        for i, device in enumerate(esp32_devices[:2]):
            side = device.get("likely_side") or ("side-a" if i == 0 else "side-b")
            result["recommendations"].append({
                "type": "suggestion",
                "message": f"Port {device['port']} ({device['description']}) - Likely {side.upper()}"
            })
    elif len(esp32_devices) == 1:
        result["recommendations"].append({
            "type": "warning",
            "message": f"Found only 1 ESP32 device on {esp32_devices[0]['port']}. Expected 2 (Side-A and Side-B)."
        })
    else:
        result["recommendations"].append({
            "type": "error",
            "message": "No ESP32 devices found. Please check USB connections."
        })
    
    return result


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        result = scan_devices()
        print(json.dumps(result, indent=2))
    else:
        result = scan_devices()
        print("\n=== USB Device Scan Results ===\n", file=sys.stderr)
        print(f"Total Serial Ports: {result['total_ports']}", file=sys.stderr)
        print(f"ESP32 Devices Found: {len(result['esp32_devices'])}", file=sys.stderr)
        print(f"MycoBrain Devices Found: {len(result['mycobrain_devices'])}\n", file=sys.stderr)
        
        if result['esp32_devices']:
            print("ESP32 Devices:", file=sys.stderr)
            for device in result['esp32_devices']:
                print(f"  - {device['port']}: {device['description']}", file=sys.stderr)
                print(f"    VID: {device['vid']}, PID: {device['pid']}", file=sys.stderr)
                if device.get('serial_number'):
                    print(f"    Serial: {device['serial_number']}", file=sys.stderr)
                if device.get('likely_side'):
                    print(f"    Likely Side: {device['likely_side'].upper()}", file=sys.stderr)
                print("", file=sys.stderr)
        
        print("\nRecommendations:", file=sys.stderr)
        for rec in result['recommendations']:
            print(f"  [{rec['type'].upper()}] {rec['message']}", file=sys.stderr)
        
        # Also output JSON for programmatic use
        print("\n=== JSON Output ===", file=sys.stderr)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

