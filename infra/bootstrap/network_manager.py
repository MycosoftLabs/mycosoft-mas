#!/usr/bin/env python3
"""
Mycosoft Network Manager
Master script for managing all network infrastructure remotely

Credentials are loaded from HashiCorp Vault - never stored in files.
"""

import json
import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
import urllib3

# Import clients
sys.path.insert(0, str(Path(__file__).parent))
from proxmox_client import ProxmoxClient
from unifi_client import UniFiClient

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Infrastructure IPs - no secrets here
PROXMOX_HOSTS = [
    {"name": "build", "ip": "192.168.0.202", "port": 8006},
    {"name": "dc1", "ip": "192.168.0.2", "port": 8006},
    {"name": "dc2", "ip": "192.168.0.131", "port": 8006},
]

UNIFI_HOST = {"ip": "192.168.0.1", "port": 443}

VAULT_ADDR = os.environ.get("VAULT_ADDR", "http://127.0.0.1:8200")


def get_vault_secret(path: str) -> Optional[Dict[str, Any]]:
    """Get secret from Vault"""
    try:
        result = subprocess.run(
            ["vault", "kv", "get", "-format=json", path],
            capture_output=True, text=True,
            env={**os.environ, "VAULT_ADDR": VAULT_ADDR}
        )
        
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        return data.get("data", {}).get("data", {})
        
    except Exception as e:
        print(f"Warning: Could not read from Vault: {e}")
        return None


class NetworkManager:
    """Master network management class - uses Vault for credentials"""
    
    def __init__(self):
        """Initialize network manager with Vault credentials"""
        self.proxmox_clients: Dict[str, ProxmoxClient] = {}
        self.unifi_client: Optional[UniFiClient] = None
        
        # Load Proxmox credentials from Vault
        proxmox_creds = get_vault_secret("mycosoft/proxmox")
        if proxmox_creds:
            token_id = proxmox_creds.get("token_id")
            token_secret = proxmox_creds.get("token_secret")
            
            if token_id and token_secret:
                for host in PROXMOX_HOSTS:
            try:
                        self.proxmox_clients[host["name"]] = ProxmoxClient(
                            host["ip"],
                            port=host["port"],
                            token_id=token_id,
                            token_secret=token_secret
                )
            except Exception as e:
                print(f"Warning: Could not initialize Proxmox client for {host['name']}: {e}")
            else:
                print("Warning: Proxmox credentials incomplete in Vault")
        else:
            print("Warning: Proxmox credentials not found in Vault")
            print("  Run: ./bootstrap_mycosoft.sh --apply")
        
        # Load UniFi credentials from Vault
        unifi_creds = get_vault_secret("mycosoft/unifi")
        if unifi_creds:
            api_key = unifi_creds.get("api_key")
            
            if api_key:
                try:
            self.unifi_client = UniFiClient(
                        UNIFI_HOST["ip"],
                        port=UNIFI_HOST["port"],
                        token=api_key
            )
        except Exception as e:
            print(f"Warning: Could not initialize UniFi client: {e}")
            else:
                print("Warning: UniFi API key not found in Vault")
        else:
            print("Warning: UniFi credentials not found in Vault")
    
    def list_proxmox_nodes(self) -> Dict[str, List[Dict]]:
        """List all nodes across all Proxmox hosts"""
        results = {}
        
        if not self.proxmox_clients:
            print("No Proxmox clients initialized. Check Vault configuration.")
            return results
        
        for name, client in self.proxmox_clients.items():
            try:
                nodes = client.get_nodes()
                results[name] = nodes
                print(f"\n{name} ({client.host}):")
                for node in nodes:
                    try:
                        status = client.get_node_status(node["node"])
                        cpu_pct = status.get("cpu", 0) * 100
                        mem_pct = (status.get("mem", 0) / status.get("maxmem", 1)) * 100 if status.get("maxmem", 0) > 0 else 0
                        print(f"  - {node['node']}: {status.get('status', 'unknown')} "
                              f"(CPU: {cpu_pct:.1f}%, Memory: {mem_pct:.1f}%)")
                    except Exception as e:
                        print(f"  - {node['node']}: {node.get('status', 'unknown')} (status error: {e})")
            except Exception as e:
                print(f"  Error connecting to {name}: {e}")
                results[name] = []
        return results
    
    def list_vms(self, host_name: Optional[str] = None) -> Dict[str, List[Dict]]:
        """List all VMs across Proxmox hosts"""
        results = {}
        
        if not self.proxmox_clients:
            print("No Proxmox clients initialized. Check Vault configuration.")
            return results
        
        hosts = {host_name: self.proxmox_clients[host_name]} if host_name and host_name in self.proxmox_clients else self.proxmox_clients
        
        for name, client in hosts.items():
            try:
                vms = client.get_vms()
                results[name] = vms
                print(f"\n{name} ({client.host}):")
                if vms:
                    for vm in vms:
                        mem_gb = vm.get("mem", 0) / 1024 / 1024 / 1024 if vm.get("mem", 0) > 0 else 0
                        print(f"  - {vm.get('name', 'unnamed')} (ID: {vm['vmid']}, "
                              f"Status: {vm.get('status', 'unknown')}, "
                              f"CPU: {vm.get('cpus', 'N/A')}, "
                              f"Memory: {mem_gb:.1f}GB)")
                else:
                    print("  No VMs found")
            except Exception as e:
                print(f"  Error connecting to {name}: {e}")
                results[name] = []
        return results
    
    def list_unifi_devices(self) -> List[Dict]:
        """List all UniFi devices"""
        if not self.unifi_client:
            print("UniFi client not initialized. Check Vault configuration.")
            return []
        try:
            devices = self.unifi_client.get_devices()
            print(f"\nUniFi Devices ({self.unifi_client.host}):")
            if devices:
                for device in devices:
                    print(f"  - {device.get('name', 'unnamed')} "
                          f"({device.get('model', 'unknown')}) - "
                          f"{device.get('state', 'unknown')}")
            else:
                print("  No devices found")
            return devices
        except Exception as e:
            print(f"Error connecting to UniFi: {e}")
            return []
    
    def list_unifi_clients(self) -> List[Dict]:
        """List all UniFi clients"""
        if not self.unifi_client:
            print("UniFi client not initialized. Check Vault configuration.")
            return []
        try:
            clients = self.unifi_client.get_clients()
            print(f"\nUniFi Clients ({self.unifi_client.host}):")
            if clients:
                for client_info in clients:
                    print(f"  - {client_info.get('hostname', 'unknown')} "
                          f"({client_info.get('ip', 'no IP')}) - "
                          f"MAC: {client_info.get('mac', 'unknown')}")
            else:
                print("  No clients found")
            return clients
        except Exception as e:
            print(f"Error connecting to UniFi: {e}")
            return []
    
    def get_network_status(self):
        """Get overall network status"""
        print("=" * 60)
        print("Mycosoft Network Status")
        print("=" * 60)
        
        print("\n[Proxmox Hosts]")
        self.list_proxmox_nodes()
        
        print("\n[VMs]")
        self.list_vms()
        
        if self.unifi_client:
        print("\n[UniFi Devices]")
        self.list_unifi_devices()
        
        print("\n[UniFi Clients]")
        self.list_unifi_clients()


def main():
    """CLI interface"""
    parser = argparse.ArgumentParser(
        description="Mycosoft Network Manager",
        epilog="Credentials are loaded from HashiCorp Vault (mycosoft/proxmox, mycosoft/unifi)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Status command
    subparsers.add_parser("status", help="Show network status")
    
    # Proxmox commands
    proxmox_parser = subparsers.add_parser("proxmox", help="Proxmox operations")
    proxmox_subparsers = proxmox_parser.add_subparsers(dest="proxmox_action")
    proxmox_subparsers.add_parser("nodes", help="List all nodes")
    proxmox_subparsers.add_parser("vms", help="List all VMs")
    
    # UniFi commands
    unifi_parser = subparsers.add_parser("unifi", help="UniFi operations")
    unifi_subparsers = unifi_parser.add_subparsers(dest="unifi_action")
    unifi_subparsers.add_parser("devices", help="List devices")
    unifi_subparsers.add_parser("clients", help="List clients")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        print()
        print("First, ensure Vault is configured:")
        print("  ./bootstrap_mycosoft.sh --apply")
        print()
        print("Then, set VAULT_ADDR if not using default:")
        print("  export VAULT_ADDR=http://127.0.0.1:8200")
        return
    
    manager = NetworkManager()
    
    if args.command == "status":
        manager.get_network_status()
    
    elif args.command == "proxmox":
        if args.proxmox_action == "nodes":
            manager.list_proxmox_nodes()
        elif args.proxmox_action == "vms":
            manager.list_vms()
        else:
            print("Usage: network_manager.py proxmox [nodes|vms]")
    
    elif args.command == "unifi":
        if args.unifi_action == "devices":
            manager.list_unifi_devices()
        elif args.unifi_action == "clients":
            manager.list_unifi_clients()
        else:
            print("Usage: network_manager.py unifi [devices|clients]")


if __name__ == "__main__":
    main()
