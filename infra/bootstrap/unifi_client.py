#!/usr/bin/env python3
"""
UniFi API Client for Mycosoft Infrastructure
Provides programmatic access to UniFi Dream Machine
"""

import json
import requests
from typing import Dict, List, Optional, Any
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UniFiClient:
    """Client for interacting with UniFi API"""
    
    def __init__(self, host: str, port: int = 443, username: str = None, 
                 password: str = None, token: Optional[str] = None, site: str = "default"):
        """
        Initialize UniFi client
        
        Args:
            host: UniFi controller host IP or hostname
            port: UniFi API port (default: 443)
            username: Username for authentication
            password: Password for authentication
            token: API token (if already authenticated)
            site: Site name (default: "default")
        """
        self.host = host
        self.port = port
        self.base_url = f"https://{host}:{port}/proxy/network/api"
        self.username = username
        self.password = password
        self.token = token
        self.site = site
        self.session = requests.Session()
        self.session.verify = False
        
        if token:
            # UniFi local API uses X-API-Key header
            self.session.headers.update({"X-API-Key": token})
        elif username and password:
            self._login()
        else:
            raise ValueError("Must provide either username/password or token")
    
    def _login(self) -> None:
        """Login to UniFi API"""
        login_url = f"{self.base_url}/login"
        data = {
            "username": self.username,
            "password": self.password
        }
        
        response = self.session.post(login_url, json=data, timeout=10)
        response.raise_for_status()
        
        # UniFi API returns cookies for authentication
        if response.status_code == 200:
            # Extract CSRF token if present
            csrf_token = response.headers.get("X-CSRF-Token")
            if csrf_token:
                self.session.headers.update({"X-CSRF-Token": csrf_token})
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None,
                 data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request"""
        url = f"{self.base_url}/{endpoint}"
        
        if method.upper() == "GET":
            response = self.session.get(url, params=params, timeout=30)
        elif method.upper() == "POST":
            response = self.session.post(url, json=data, params=params, timeout=30)
        elif method.upper() == "PUT":
            response = self.session.put(url, json=data, params=params, timeout=30)
        elif method.upper() == "DELETE":
            response = self.session.delete(url, params=params, timeout=30)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    def get_self(self) -> Dict[str, Any]:
        """Get current user info"""
        result = self._request("GET", "self")
        return result.get("data", {})
    
    def get_sites(self) -> List[Dict[str, Any]]:
        """Get list of sites"""
        result = self._request("GET", "self/sites")
        return result.get("data", [])
    
    def get_devices(self) -> List[Dict[str, Any]]:
        """Get list of devices"""
        result = self._request("GET", f"s/{self.site}/stat/device")
        return result.get("data", [])
    
    def get_clients(self) -> List[Dict[str, Any]]:
        """Get list of clients"""
        result = self._request("GET", f"s/{self.site}/stat/sta")
        return result.get("data", [])
    
    def get_networks(self) -> List[Dict[str, Any]]:
        """Get list of networks"""
        result = self._request("GET", f"s/{self.site}/rest/networkconf")
        return result.get("data", [])
    
    def get_wlans(self) -> List[Dict[str, Any]]:
        """Get list of WLANs"""
        result = self._request("GET", f"s/{self.site}/rest/wlanconf")
        return result.get("data", [])
    
    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent events"""
        params = {"_limit": limit}
        result = self._request("GET", f"s/{self.site}/stat/event", params=params)
        return result.get("data", [])
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get alerts"""
        result = self._request("GET", f"s/{self.site}/list/alert")
        return result.get("data", [])
    
    def get_health(self) -> List[Dict[str, Any]]:
        """Get health metrics"""
        result = self._request("GET", f"s/{self.site}/stat/health")
        return result.get("data", [])
    
    def block_client(self, mac: str) -> Dict[str, Any]:
        """Block a client by MAC address"""
        data = {"mac": mac, "cmd": "block-sta"}
        result = self._request("POST", f"s/{self.site}/cmd/stamgr", data=data)
        return result.get("data", {})
    
    def unblock_client(self, mac: str) -> Dict[str, Any]:
        """Unblock a client by MAC address"""
        data = {"mac": mac, "cmd": "unblock-sta"}
        result = self._request("POST", f"s/{self.site}/cmd/stamgr", data=data)
        return result.get("data", {})
    
    def restart_device(self, device_id: str) -> Dict[str, Any]:
        """Restart a device"""
        data = {"cmd": "restart", "_id": device_id}
        result = self._request("POST", f"s/{self.site}/cmd/devmgr", data=data)
        return result.get("data", {})
    
    @classmethod
    def from_vault(cls, host: str = "192.168.0.1", port: int = 443,
                   vault_addr: str = "http://127.0.0.1:8200",
                   vault_path: str = "mycosoft/unifi",
                   site: str = "default") -> "UniFiClient":
        """
        Create client with credentials from HashiCorp Vault
        
        Args:
            host: UniFi host IP
            port: UniFi API port
            vault_addr: Vault server address
            vault_path: Path to UniFi credentials in Vault
            site: UniFi site name
        
        Returns:
            Configured UniFiClient instance
        """
        import os
        import subprocess
        
        env = os.environ.copy()
        env["VAULT_ADDR"] = vault_addr
        
        result = subprocess.run(
            ["vault", "kv", "get", "-format=json", vault_path],
            capture_output=True, text=True, env=env
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get credentials from Vault: {result.stderr}")
        
        import json
        data = json.loads(result.stdout)["data"]["data"]
        
        return cls(
            host=host,
            port=port,
            token=data["api_key"],
            site=site
        )


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: unifi_client.py <host> <username> [password]")
        sys.exit(1)
    
    host = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not password:
        import getpass
        password = getpass.getpass(f"Password for {username}@{host}: ")
    
    client = UniFiClient(host, username=username, password=password)
    
    print(f"\nConnecting to UniFi at {host}...")
    
    print("\nCurrent User:")
    user = client.get_self()
    print(f"  - {user.get('name', 'unknown')} ({user.get('email', 'unknown')})")
    
    print("\nDevices:")
    for device in client.get_devices():
        print(f"  - {device.get('name', 'unnamed')} ({device.get('model', 'unknown')}) - {device.get('state', 'unknown')}")
    
    print("\nClients:")
    for client_info in client.get_clients()[:10]:  # Show first 10
        print(f"  - {client_info.get('hostname', 'unknown')} ({client_info.get('ip', 'no IP')})")
