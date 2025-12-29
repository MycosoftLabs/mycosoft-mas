#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COM Port Scanner for MycoBrain Devices

This script scans for available COM ports and identifies potential ESP32/MycoBrain devices.
It provides detailed information about each port including VID/PID, description, and status.
"""

import serial.tools.list_ports
import sys
import os
from typing import List, Dict, Optional
import json

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass


def get_port_info(port) -> Dict:
    """Extract detailed information about a COM port."""
    info = {
        "port": port.device,
        "description": port.description or "Unknown",
        "manufacturer": port.manufacturer or "Unknown",
        "vid": f"{port.vid:04X}" if port.vid else None,
        "pid": f"{port.pid:04X}" if port.pid else None,
        "serial_number": port.serial_number or None,
        "location": port.location or None,
        "hwid": port.hwid or None,
    }
    
    # Check if it's likely an ESP32 device
    is_esp32 = False
    is_mycobrain = False
    
    if port.vid and port.pid:
        # Common ESP32 VID/PID combinations
        esp32_vid_pids = [
            (0x10C4, 0xEA60),  # Silicon Labs CP210x
            (0x1A86, 0x7523),  # CH340
            (0x303A, 0x1001),  # ESP32-S3
            (0x303A, 0x0001),  # ESP32
        ]
        
        if (port.vid, port.pid) in esp32_vid_pids:
            is_esp32 = True
            
        # Check description for MycoBrain indicators
        desc_lower = (port.description or "").lower()
        if "mycobrain" in desc_lower or "esp32" in desc_lower:
            is_mycobrain = True
    
    info["is_esp32"] = is_esp32
    info["is_mycobrain"] = is_mycobrain or is_esp32
    
    return info


def check_port_availability(port_name: str) -> Dict:
    """Check if a port is available and can be opened."""
    result = {
        "port": port_name,
        "available": False,
        "error": None,
        "can_open": False,
    }
    
    try:
        # Try to open the port
        ser = serial.Serial(port_name, timeout=1)
        result["can_open"] = True
        result["available"] = True
        ser.close()
    except serial.SerialException as e:
        result["error"] = str(e)
        if "Access is denied" in str(e) or "Permission denied" in str(e):
            result["error"] = "Port is in use by another application"
        elif "could not open port" in str(e).lower():
            result["error"] = "Port does not exist or is not accessible"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
    
    return result


def scan_ports() -> List[Dict]:
    """Scan all available COM ports."""
    print("Scanning for COM ports...")
    print("=" * 80)
    
    ports = serial.tools.list_ports.comports()
    port_info_list = []
    
    if not ports:
        print("No COM ports found.")
        return []
    
    print(f"\nFound {len(ports)} COM port(s):\n")
    
    for i, port in enumerate(ports, 1):
        info = get_port_info(port)
        availability = check_port_availability(port.device)
        info.update(availability)
        port_info_list.append(info)
        
        # Print formatted output
        print(f"{i}. {info['port']}")
        print(f"   Description: {info['description']}")
        print(f"   Manufacturer: {info['manufacturer']}")
        if info['vid'] and info['pid']:
            print(f"   VID/PID: {info['vid']}/{info['pid']}")
        if info['serial_number']:
            print(f"   Serial: {info['serial_number']}")
        if info['location']:
            print(f"   Location: {info['location']}")
        
        # Status indicators (using ASCII-safe characters for Windows)
        status_indicators = []
        if info['is_esp32']:
            status_indicators.append("[ESP32] ESP32-like device")
        if info['is_mycobrain']:
            status_indicators.append("[MYCOBRAIN] Potential MycoBrain")
        if info['can_open']:
            status_indicators.append("[OK] Available")
        else:
            status_indicators.append(f"[ERROR] {info['error'] or 'Unavailable'}")
        
        if status_indicators:
            print(f"   Status: {' | '.join(status_indicators)}")
        
        print()
    
    return port_info_list


def identify_mycobrain_ports(port_info_list: List[Dict]) -> Dict:
    """Identify which ports are likely Side-A and Side-B."""
    esp32_ports = [p for p in port_info_list if p.get('is_esp32')]
    available_esp32 = [p for p in esp32_ports if p.get('can_open')]
    
    recommendations = {
        "side_a": None,
        "side_b": None,
        "other_ports": [],
        "notes": []
    }
    
    if len(available_esp32) >= 2:
        # If we have 2 ESP32 ports, recommend them as Side-A and Side-B
        recommendations["side_a"] = available_esp32[0]["port"]
        recommendations["side_b"] = available_esp32[1]["port"]
        recommendations["notes"].append(
            f"Found 2 ESP32-like ports: {recommendations['side_a']} and {recommendations['side_b']}"
        )
    elif len(available_esp32) == 1:
        recommendations["side_a"] = available_esp32[0]["port"]
        recommendations["notes"].append(
            f"Found 1 ESP32-like port: {recommendations['side_a']}. "
            "Connect the second USB-C cable to detect Side-B."
        )
    else:
        recommendations["notes"].append(
            "No ESP32-like devices detected. Make sure MycoBrain is connected via USB-C."
        )
    
    # Add other available ports
    other_ports = [p for p in port_info_list if p.get('can_open') and not p.get('is_esp32')]
    recommendations["other_ports"] = [p["port"] for p in other_ports]
    
    return recommendations


def main():
    """Main function."""
    print("MycoBrain COM Port Scanner")
    print("=" * 80)
    print()
    
    # Scan ports
    port_info_list = scan_ports()
    
    if not port_info_list:
        print("\nNo ports found. Please check USB connections.")
        return 1
    
    # Identify MycoBrain ports
    print("\n" + "=" * 80)
    print("MycoBrain Port Recommendations:")
    print("=" * 80)
    
    recommendations = identify_mycobrain_ports(port_info_list)
    
    if recommendations["side_a"]:
        print(f"\n[OK] Side-A (Sensor MCU): {recommendations['side_a']}")
    else:
        print("\n[ERROR] Side-A: Not detected")
    
    if recommendations["side_b"]:
        print(f"[OK] Side-B (Router MCU): {recommendations['side_b']}")
    else:
        print("[ERROR] Side-B: Not detected")
    
    if recommendations["other_ports"]:
        print(f"\nOther available ports: {', '.join(recommendations['other_ports'])}")
    
    if recommendations["notes"]:
        print("\nNotes:")
        for note in recommendations["notes"]:
            print(f"  • {note}")
    
    # Output JSON for programmatic use
    output = {
        "ports": port_info_list,
        "recommendations": recommendations,
        "summary": {
            "total_ports": len(port_info_list),
            "esp32_ports": len([p for p in port_info_list if p.get('is_esp32')]),
            "available_ports": len([p for p in port_info_list if p.get('can_open')]),
        }
    }
    
    # Save to file
    output_file = "com_ports_scan.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n[INFO] Detailed scan results saved to: {output_file}")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

