"""
Proxmox Integration for Mycosoft MAS
Provides VM management capabilities for MYCA
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import requests
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


@dataclass
class ProxmoxNode:
    """Represents a Proxmox node"""
    name: str
    ip: str
    port: int = 8006
    
    @property
    def url(self) -> str:
        return f"https://{self.ip}:{self.port}"


@dataclass
class ProxmoxVM:
    """Represents a VM on Proxmox"""
    vmid: int
    name: str
    status: str
    node: str
    cpus: int = 0
    memory_mb: int = 0
    disk_gb: float = 0


class ProxmoxIntegration:
    """
    Proxmox Integration for MYCA
    Manages VMs across the Mycosoft Proxmox cluster
    """
    
    # Default nodes
    DEFAULT_NODES = [
        ProxmoxNode("build", "192.168.0.202", 8006),
        ProxmoxNode("dc1", "192.168.0.2", 8006),
        ProxmoxNode("dc2", "192.168.0.131", 8006),
    ]
    
    def __init__(
        self,
        token_id: Optional[str] = None,
        token_secret: Optional[str] = None,
        nodes: Optional[List[ProxmoxNode]] = None,
        verify_ssl: bool = False
    ):
        """
        Initialize Proxmox integration
        
        Args:
            token_id: API token ID (e.g., myca@pve!mas)
            token_secret: API token secret
            nodes: List of Proxmox nodes (defaults to Mycosoft cluster)
            verify_ssl: Whether to verify SSL certificates
        """
        self.token_id = token_id or os.getenv("PROXMOX_TOKEN_ID", "myca@pve!mas")
        self.token_secret = token_secret or os.getenv("PROXMOX_TOKEN_SECRET", "")
        self.nodes = nodes or self.DEFAULT_NODES
        self.verify_ssl = verify_ssl
        
        if not self.token_secret:
            logger.warning("PROXMOX_TOKEN_SECRET not set - API calls will fail")
        
        self._session = requests.Session()
        self._session.verify = self.verify_ssl
        self._session.headers.update({
            "Authorization": f"PVEAPIToken={self.token_id}={self.token_secret}"
        })
    
    def _request(self, node: ProxmoxNode, endpoint: str, method: str = "GET", 
                 data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make API request to Proxmox node"""
        url = f"{node.url}/api2/json/{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self._session.get(url, timeout=30)
            elif method.upper() == "POST":
                response = self._session.post(url, data=data, timeout=30)
            elif method.upper() == "PUT":
                response = self._session.put(url, data=data, timeout=30)
            elif method.upper() == "DELETE":
                response = self._session.delete(url, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Proxmox API error on {node.name}: {e}")
            raise
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster-wide status"""
        for node in self.nodes:
            try:
                result = self._request(node, "cluster/status")
                return {"status": "ok", "data": result.get("data", []), "source": node.name}
            except Exception as e:
                logger.warning(f"Failed to get cluster status from {node.name}: {e}")
                continue
        
        return {"status": "error", "message": "All nodes unreachable"}
    
    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get all nodes in the cluster"""
        for node in self.nodes:
            try:
                result = self._request(node, "nodes")
                return result.get("data", [])
            except Exception:
                continue
        return []
    
    def get_node_status(self, node_name: str) -> Dict[str, Any]:
        """Get status of a specific node"""
        for node in self.nodes:
            try:
                result = self._request(node, f"nodes/{node_name}/status")
                return result.get("data", {})
            except Exception:
                continue
        return {}
    
    def get_all_vms(self) -> List[ProxmoxVM]:
        """Get all VMs across all nodes"""
        vms = []
        
        for node in self.nodes:
            try:
                result = self._request(node, f"nodes/{node.name}/qemu")
                for vm_data in result.get("data", []):
                    vms.append(ProxmoxVM(
                        vmid=vm_data.get("vmid"),
                        name=vm_data.get("name", f"VM {vm_data.get('vmid')}"),
                        status=vm_data.get("status", "unknown"),
                        node=node.name,
                        cpus=vm_data.get("cpus", 0),
                        memory_mb=vm_data.get("mem", 0) // (1024 * 1024),
                        disk_gb=vm_data.get("disk", 0) / (1024 ** 3)
                    ))
            except Exception as e:
                logger.warning(f"Failed to get VMs from {node.name}: {e}")
                continue
        
        return vms
    
    def get_vm(self, vmid: int) -> Optional[ProxmoxVM]:
        """Get a specific VM by ID"""
        for vm in self.get_all_vms():
            if vm.vmid == vmid:
                return vm
        return None
    
    def get_vm_config(self, node_name: str, vmid: int) -> Dict[str, Any]:
        """Get VM configuration"""
        for node in self.nodes:
            if node.name == node_name:
                try:
                    result = self._request(node, f"nodes/{node_name}/qemu/{vmid}/config")
                    return result.get("data", {})
                except Exception:
                    pass
        return {}
    
    def start_vm(self, node_name: str, vmid: int) -> bool:
        """Start a VM"""
        for node in self.nodes:
            if node.name == node_name:
                try:
                    self._request(node, f"nodes/{node_name}/qemu/{vmid}/status/start", "POST")
                    logger.info(f"Started VM {vmid} on {node_name}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to start VM {vmid}: {e}")
                    return False
        return False
    
    def stop_vm(self, node_name: str, vmid: int) -> bool:
        """Stop a VM"""
        for node in self.nodes:
            if node.name == node_name:
                try:
                    self._request(node, f"nodes/{node_name}/qemu/{vmid}/status/stop", "POST")
                    logger.info(f"Stopped VM {vmid} on {node_name}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to stop VM {vmid}: {e}")
                    return False
        return False
    
    def shutdown_vm(self, node_name: str, vmid: int) -> bool:
        """Gracefully shutdown a VM"""
        for node in self.nodes:
            if node.name == node_name:
                try:
                    self._request(node, f"nodes/{node_name}/qemu/{vmid}/status/shutdown", "POST")
                    logger.info(f"Shutdown VM {vmid} on {node_name}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to shutdown VM {vmid}: {e}")
                    return False
        return False
    
    def reboot_vm(self, node_name: str, vmid: int) -> bool:
        """Reboot a VM"""
        for node in self.nodes:
            if node.name == node_name:
                try:
                    self._request(node, f"nodes/{node_name}/qemu/{vmid}/status/reboot", "POST")
                    logger.info(f"Rebooted VM {vmid} on {node_name}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to reboot VM {vmid}: {e}")
                    return False
        return False
    
    def clone_vm(self, node_name: str, vmid: int, new_vmid: int, 
                 name: str, full: bool = True) -> bool:
        """Clone a VM"""
        for node in self.nodes:
            if node.name == node_name:
                try:
                    data = {
                        "newid": new_vmid,
                        "name": name,
                        "full": 1 if full else 0,
                    }
                    self._request(node, f"nodes/{node_name}/qemu/{vmid}/clone", "POST", data)
                    logger.info(f"Cloned VM {vmid} to {new_vmid} ({name}) on {node_name}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to clone VM {vmid}: {e}")
                    return False
        return False
    
    def get_storage(self) -> List[Dict[str, Any]]:
        """Get storage information"""
        for node in self.nodes:
            try:
                result = self._request(node, "storage")
                return result.get("data", [])
            except Exception:
                continue
        return []
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of all Proxmox nodes"""
        results = {
            "healthy": True,
            "nodes": {}
        }
        
        for node in self.nodes:
            try:
                response = self._session.get(
                    f"{node.url}/api2/json/version",
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    results["nodes"][node.name] = {
                        "status": "online",
                        "version": data.get("version"),
                        "ip": node.ip
                    }
                else:
                    results["nodes"][node.name] = {
                        "status": "error",
                        "code": response.status_code,
                        "ip": node.ip
                    }
                    results["healthy"] = False
            except requests.exceptions.Timeout:
                results["nodes"][node.name] = {
                    "status": "timeout",
                    "ip": node.ip
                }
                results["healthy"] = False
            except Exception as e:
                results["nodes"][node.name] = {
                    "status": "unreachable",
                    "error": str(e),
                    "ip": node.ip
                }
                results["healthy"] = False
        
        return results


# Singleton instance for easy import
_instance: Optional[ProxmoxIntegration] = None


def get_proxmox() -> ProxmoxIntegration:
    """Get or create the Proxmox integration instance"""
    global _instance
    if _instance is None:
        _instance = ProxmoxIntegration()
    return _instance


# Quick test when run directly
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(".env.local")
    
    proxmox = get_proxmox()
    
    print("=== Proxmox Health Check ===")
    health = proxmox.health_check()
    for node_name, status in health["nodes"].items():
        print(f"  {node_name}: {status['status']} ({status.get('ip', 'N/A')})")
    
    print("\n=== VMs ===")
    for vm in proxmox.get_all_vms():
        print(f"  [{vm.vmid}] {vm.name}: {vm.status} on {vm.node}")
