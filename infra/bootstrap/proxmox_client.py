#!/usr/bin/env python3
"""
Proxmox API Client for Mycosoft Infrastructure
Provides programmatic access to Proxmox hosts
"""

import json
import requests
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ProxmoxClient:
    """Client for interacting with Proxmox API"""
    
    def __init__(self, host: str, port: int = 8006, username: str = "root", 
                 password: Optional[str] = None, token_id: Optional[str] = None,
                 token_secret: Optional[str] = None):
        """
        Initialize Proxmox client
        
        Args:
            host: Proxmox host IP or hostname
            port: Proxmox API port (default: 8006)
            username: Username for authentication
            password: Password (if using password auth)
            token_id: API token ID (if using token auth)
            token_secret: API token secret (if using token auth)
        """
        self.host = host
        self.port = port
        self.base_url = f"https://{host}:{port}/api2/json"
        self.username = username
        self.password = password
        self.token_id = token_id
        self.token_secret = token_secret
        self.ticket = None
        self.csrf_token = None
        
        if token_id and token_secret:
            self.auth_method = "token"
        elif password:
            self.auth_method = "password"
        else:
            raise ValueError("Must provide either password or token credentials")
    
    def _authenticate(self) -> None:
        """Authenticate with Proxmox API"""
        if self.auth_method == "token":
            # Token auth - no need to authenticate
            return
        
        # Password auth
        auth_url = f"{self.base_url}/access/ticket"
        data = {
            "username": self.username,
            "password": self.password
        }
        
        response = requests.post(auth_url, data=data, verify=False, timeout=10)
        response.raise_for_status()
        
        result = response.json()["data"]
        self.ticket = result["ticket"]
        self.csrf_token = result["CSRFPreventionToken"]
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        if self.auth_method == "token":
            # Correct format: PVEAPIToken=USER@REALM!TOKENID=SECRET
            return {
                "Authorization": f"PVEAPIToken={self.token_id}={self.token_secret}"
            }
        else:
            if not self.ticket:
                self._authenticate()
            return {
                "Cookie": f"PVEAuthCookie={self.ticket}",
                "CSRFPreventionToken": self.csrf_token
            }
    
    @classmethod
    def from_vault(cls, host: str, port: int = 8006, 
                   vault_addr: str = "http://127.0.0.1:8200",
                   vault_path: str = "mycosoft/proxmox") -> "ProxmoxClient":
        """
        Create client with credentials from HashiCorp Vault
        
        Args:
            host: Proxmox host IP
            port: Proxmox API port
            vault_addr: Vault server address
            vault_path: Path to Proxmox credentials in Vault
        
        Returns:
            Configured ProxmoxClient instance
        """
        import os
        import subprocess
        
        # Get token from Vault
        env = os.environ.copy()
        env["VAULT_ADDR"] = vault_addr
        
        result = subprocess.run(
            ["vault", "kv", "get", "-format=json", vault_path],
            capture_output=True, text=True, env=env
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get credentials from Vault: {result.stderr}")
        
        data = json.loads(result.stdout)["data"]["data"]
        
        return cls(
            host=host,
            port=port,
            token_id=data["token_id"],
            token_secret=data["token_secret"]
        )
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                 data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request"""
        url = f"{self.base_url}/{endpoint}"
        headers = self._get_headers()
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, verify=False, timeout=30)
        elif method.upper() == "POST":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            response = requests.post(url, headers=headers, params=params, data=data, verify=False, timeout=30)
        elif method.upper() == "PUT":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            response = requests.put(url, headers=headers, params=params, data=data, verify=False, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, params=params, verify=False, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get list of nodes"""
        result = self._request("GET", "nodes")
        return result.get("data", [])
    
    def get_node_status(self, node: str) -> Dict[str, Any]:
        """Get node status"""
        result = self._request("GET", f"nodes/{node}/status")
        return result.get("data", {})
    
    def get_vms(self, node: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of VMs"""
        vms = []
        nodes = [node] if node else [n["node"] for n in self.get_nodes()]
        
        for n in nodes:
            result = self._request("GET", f"nodes/{n}/qemu")
            vms.extend(result.get("data", []))
        
        return vms
    
    def get_containers(self, node: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of containers"""
        containers = []
        nodes = [node] if node else [n["node"] for n in self.get_nodes()]
        
        for n in nodes:
            result = self._request("GET", f"nodes/{n}/lxc")
            containers.extend(result.get("data", []))
        
        return containers
    
    def create_vm(self, node: str, vmid: int, name: str, **kwargs) -> Dict[str, Any]:
        """Create a new VM"""
        params = {
            "vmid": vmid,
            "name": name,
            **kwargs
        }
        result = self._request("POST", f"nodes/{node}/qemu", data=params)
        return result.get("data", {})
    
    def clone_vm(self, node: str, vmid: int, newid: int, name: str, **kwargs) -> Dict[str, Any]:
        """Clone a VM"""
        params = {
            "newid": newid,
            "name": name,
            **kwargs
        }
        result = self._request("POST", f"nodes/{node}/qemu/{vmid}/clone", data=params)
        return result.get("data", {})
    
    def get_vm_config(self, node: str, vmid: int) -> Dict[str, Any]:
        """Get VM configuration"""
        result = self._request("GET", f"nodes/{node}/qemu/{vmid}/config")
        return result.get("data", {})
    
    def start_vm(self, node: str, vmid: int) -> Dict[str, Any]:
        """Start a VM"""
        result = self._request("POST", f"nodes/{node}/qemu/{vmid}/status/start")
        return result.get("data", {})
    
    def stop_vm(self, node: str, vmid: int) -> Dict[str, Any]:
        """Stop a VM"""
        result = self._request("POST", f"nodes/{node}/qemu/{vmid}/status/stop")
        return result.get("data", {})
    
    def get_storage(self) -> List[Dict[str, Any]]:
        """Get storage information"""
        result = self._request("GET", "storage")
        return result.get("data", [])
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status"""
        result = self._request("GET", "cluster/status")
        return result.get("data", [])


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: proxmox_client.py <host> [username] [password]")
        sys.exit(1)
    
    host = sys.argv[1]
    username = sys.argv[2] if len(sys.argv) > 2 else "root"
    password = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not password:
        import getpass
        password = getpass.getpass(f"Password for {username}@{host}: ")
    
    client = ProxmoxClient(host, username=username, password=password)
    
    print(f"\nConnecting to Proxmox at {host}...")
    print("\nNodes:")
    for node in client.get_nodes():
        print(f"  - {node['node']}: {node.get('status', 'unknown')}")
    
    print("\nVMs:")
    for vm in client.get_vms():
        print(f"  - {vm.get('name', 'unnamed')} (ID: {vm['vmid']}, Status: {vm.get('status', 'unknown')})")
