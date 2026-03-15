#!/usr/bin/env python3
"""Quick test of MYCA Proxmox integration"""
import os
import sys

# Set token directly for testing
os.environ["PROXMOX_TOKEN_ID"] = "myca@pve!mas"
os.environ["PROXMOX_TOKEN_SECRET"] = "{os.environ.get('PROXMOX_TOKEN_SECRET', '')}"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mycosoft_mas.integrations.proxmox_integration import get_proxmox

def main():
    print("=" * 50)
    print("  MYCA Proxmox Connection Test")
    print("=" * 50)
    print()
    
    proxmox = get_proxmox()
    
    # Health check
    print("Checking nodes...")
    health = proxmox.health_check()
    
    print("\nNodes:")
    for name, status in health["nodes"].items():
        icon = "[OK]" if status["status"] == "online" else "[!!]"
        version = status.get("version", "")
        print(f"  {icon} {name} ({status.get('ip', 'N/A')}): {status['status']} {version}")
    
    # VMs
    print("\nVMs:")
    vms = proxmox.get_all_vms()
    if vms:
        for vm in vms:
            status_icon = "🟢" if vm.status == "running" else "⚪"
            print(f"  {status_icon} [{vm.vmid}] {vm.name}: {vm.status}")
    else:
        print("  No VMs found or nodes unreachable")
    
    print()
    print("=" * 50)
    if health["healthy"]:
        print("  ✅ MYCA is connected to Proxmox!")
    else:
        print("  ⚠️  Some nodes unreachable, but connection works")
    print("=" * 50)

if __name__ == "__main__":
    main()
