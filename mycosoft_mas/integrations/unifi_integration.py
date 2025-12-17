"""
UniFi Integration for Mycosoft MAS
Provides network management capabilities for MYCA
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


@dataclass
class UniFiDevice:
    """Represents a UniFi device"""
    name: str
    model: str
    mac: str
    ip: str
    status: str
    device_type: str


@dataclass  
class UniFiClient:
    """Represents a client connected to UniFi network"""
    name: str
    mac: str
    ip: str
    network: str
    is_wired: bool
    signal: int = 0


class UniFiIntegration:
    """
    UniFi Integration for MYCA
    Manages network devices and clients
    """
    
    def __init__(
        self,
        host: str = None,
        api_key: str = None,
        port: int = 443,
        site: str = "default",
        verify_ssl: bool = False
    ):
        """
        Initialize UniFi integration
        
        Args:
            host: UniFi controller host
            api_key: API key for authentication
            port: API port (default 443)
            site: Site name (default "default")
            verify_ssl: Whether to verify SSL certificates
        """
        self.host = host or os.getenv("UNIFI_HOST", "192.168.0.1")
        self.api_key = api_key or os.getenv("UNIFI_API_KEY", "")
        self.port = port
        self.site = site
        self.verify_ssl = verify_ssl
        
        self.base_url = f"https://{self.host}:{self.port}/proxy/network/api"
        
        if not self.api_key:
            logger.warning("UNIFI_API_KEY not set - API calls will fail")
        
        self._session = requests.Session()
        self._session.verify = self.verify_ssl
        self._session.headers.update({
            "X-API-Key": self.api_key
        })
    
    def _request(self, endpoint: str, method: str = "GET", 
                 data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request to UniFi"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self._session.get(url, timeout=30)
            elif method.upper() == "POST":
                response = self._session.post(url, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"UniFi API error: {e}")
            raise
    
    def get_devices(self) -> List[UniFiDevice]:
        """Get all UniFi devices"""
        try:
            result = self._request(f"s/{self.site}/stat/device")
            devices = []
            
            for d in result.get("data", []):
                status = "online" if d.get("state") == 1 else "offline"
                devices.append(UniFiDevice(
                    name=d.get("name", "unnamed"),
                    model=d.get("model", "unknown"),
                    mac=d.get("mac", ""),
                    ip=d.get("ip", ""),
                    status=status,
                    device_type=d.get("type", "unknown")
                ))
            
            return devices
        except Exception as e:
            logger.error(f"Failed to get devices: {e}")
            return []
    
    def get_clients(self) -> List[UniFiClient]:
        """Get all connected clients"""
        try:
            result = self._request(f"s/{self.site}/stat/sta")
            clients = []
            
            for c in result.get("data", []):
                name = c.get("hostname") or c.get("name") or c.get("mac", "unknown")
                clients.append(UniFiClient(
                    name=name,
                    mac=c.get("mac", ""),
                    ip=c.get("ip", ""),
                    network=c.get("network", ""),
                    is_wired=c.get("is_wired", False),
                    signal=c.get("signal", 0)
                ))
            
            return clients
        except Exception as e:
            logger.error(f"Failed to get clients: {e}")
            return []
    
    def get_networks(self) -> List[Dict[str, Any]]:
        """Get all configured networks"""
        try:
            result = self._request(f"s/{self.site}/rest/networkconf")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get networks: {e}")
            return []
    
    def get_wlans(self) -> List[Dict[str, Any]]:
        """Get all WiFi networks"""
        try:
            result = self._request(f"s/{self.site}/rest/wlanconf")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get WLANs: {e}")
            return []
    
    def get_health(self) -> Dict[str, Any]:
        """Get network health metrics"""
        try:
            result = self._request(f"s/{self.site}/stat/health")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to get health: {e}")
            return {}
    
    def block_client(self, mac: str) -> bool:
        """Block a client by MAC address"""
        try:
            self._request(f"s/{self.site}/cmd/stamgr", "POST", {
                "cmd": "block-sta",
                "mac": mac
            })
            logger.info(f"Blocked client: {mac}")
            return True
        except Exception as e:
            logger.error(f"Failed to block client {mac}: {e}")
            return False
    
    def unblock_client(self, mac: str) -> bool:
        """Unblock a client by MAC address"""
        try:
            self._request(f"s/{self.site}/cmd/stamgr", "POST", {
                "cmd": "unblock-sta",
                "mac": mac
            })
            logger.info(f"Unblocked client: {mac}")
            return True
        except Exception as e:
            logger.error(f"Failed to unblock client {mac}: {e}")
            return False
    
    def reconnect_client(self, mac: str) -> bool:
        """Force a client to reconnect"""
        try:
            self._request(f"s/{self.site}/cmd/stamgr", "POST", {
                "cmd": "kick-sta",
                "mac": mac
            })
            logger.info(f"Kicked client to force reconnect: {mac}")
            return True
        except Exception as e:
            logger.error(f"Failed to kick client {mac}: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check UniFi controller health"""
        try:
            response = self._session.get(
                f"https://{self.host}:{self.port}/proxy/network/api/s/{self.site}/self",
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    "status": "online",
                    "host": self.host,
                    "site": self.site
                }
            else:
                return {
                    "status": "error",
                    "code": response.status_code
                }
        except Exception as e:
            return {
                "status": "unreachable",
                "error": str(e)
            }


# Singleton instance
_instance: Optional[UniFiIntegration] = None


def get_unifi() -> UniFiIntegration:
    """Get or create the UniFi integration instance"""
    global _instance
    if _instance is None:
        _instance = UniFiIntegration()
    return _instance


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(".env.local")
    
    unifi = get_unifi()
    
    print("=== UniFi Health Check ===")
    health = unifi.health_check()
    print(f"  Status: {health['status']}")
    
    print("\n=== Devices ===")
    for device in unifi.get_devices():
        print(f"  [{device.status}] {device.name} ({device.model})")
    
    print("\n=== Clients ===")
    for client in unifi.get_clients():
        print(f"  - {client.name}: {client.ip}")
