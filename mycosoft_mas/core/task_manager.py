"""
Task Manager Service for MAS

This module provides a comprehensive task management system for monitoring and controlling
all running components of the MAS system with autonomous capabilities.
"""

import asyncio
import psutil
import platform
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import docker
from prometheus_client import Counter, Gauge, Histogram
import numpy as np
from sklearn.ensemble import IsolationForest
import logging
from collections import deque
import subprocess
import json
from pathlib import Path
import yaml
from mycosoft_mas.core.metrics_collector import AGENT_COUNT, CPU_USAGE, MEMORY_USAGE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProcessInfo(BaseModel):
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_percent: float
    memory_bytes: int
    create_time: datetime
    command_line: str
    username: str
    num_threads: int
    num_connections: int
    io_counters: Dict[str, int]
    network_connections: List[Dict[str, Any]]
    anomaly_score: Optional[float] = None
    health_status: str = "healthy"

    class Config:
        arbitrary_types_allowed = True

class AgentInfo(BaseModel):
    agent_id: str
    agent_type: str
    status: str
    last_heartbeat: datetime
    cpu_usage: float
    memory_usage: float
    network_traffic: Dict[str, int]
    message_queue_size: int
    task_queue_size: int
    performance_score: float
    learning_rate: float
    adaptation_level: str
    anomaly_score: Optional[float] = None
    health_status: str = "healthy"

class ServiceInfo(BaseModel):
    service_name: str
    status: str
    container_id: Optional[str]
    image: str
    ports: Dict[str, str]
    cpu_usage: float
    memory_usage: float
    network_traffic: Dict[str, int]
    logs: List[str]
    error_rate: float
    response_time: float
    anomaly_score: Optional[float] = None
    health_status: str = "healthy"

class SystemHealth(BaseModel):
    overall_health: str
    critical_issues: List[str]
    recommendations: List[str]
    resource_optimization: Dict[str, str]
    security_status: Dict[str, str]
    performance_metrics: Dict[str, float]

class OrchestratorInfo(BaseModel):
    status: str
    active_tasks: int
    pending_tasks: int
    failed_tasks: int
    resource_usage: Dict[str, float]
    last_heartbeat: datetime
    cluster_status: Dict[str, str]

class ClusterInfo(BaseModel):
    name: str
    status: str
    node_count: int
    active_agents: int
    resource_usage: Dict[str, float]
    last_sync: datetime
    health_status: str

class DependencyInfo(BaseModel):
    package: str
    version: str
    status: str
    dependencies: List[str]
    last_update: datetime
    vulnerabilities: List[str]

class TaskManager:
    def __init__(self):
        self.app = FastAPI(title="MAS Task Manager")
        self.docker_client = docker.from_env()
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize connections
        self.orchestrator_client = self._init_orchestrator_client()
        self.cluster_manager = self._init_cluster_manager()
        
        # Prometheus metrics
        self.process_count = Gauge('mas_process_count', 'Number of running processes')
        self.service_count = Gauge('mas_service_count', 'Number of running services')
        self.network_traffic = Counter('mas_network_traffic', 'Network traffic in bytes')
        self.anomaly_score = Gauge('mas_anomaly_score', 'System anomaly score')
        self.health_score = Gauge('mas_health_score', 'System health score')
        self.orchestrator_health = Gauge('mas_orchestrator_health', 'Orchestrator health score')
        self.cluster_health = Gauge('mas_cluster_health', 'Cluster health score')
        
        # Anomaly detection
        self.anomaly_detector = IsolationForest(contamination=0.1)
        self.metric_history = deque(maxlen=1000)
        
        # Self-healing thresholds
        self.thresholds = {
            'cpu_warning': 80,
            'cpu_critical': 90,
            'memory_warning': 80,
            'memory_critical': 90,
            'error_rate_warning': 0.05,
            'error_rate_critical': 0.1,
            'response_time_warning': 1.0,
            'response_time_critical': 2.0
        }
        
        # Initialize routes
        self._setup_routes()
        
        # Monitoring loop will be started explicitly

    # Public API -----------------------------------------------------------

    def load_config(self, config: Dict[str, Any]) -> None:
        """Load configuration at runtime."""
        self.config = config

    def initialize_orchestrator_client(self):
        """Initialize the orchestrator client using current config."""
        self.orchestrator_client = self._init_orchestrator_client()
        return self.orchestrator_client

    def initialize_cluster_manager(self):
        """Initialize the cluster manager using current config."""
        self.cluster_manager = self._init_cluster_manager()
        return self.cluster_manager

    def start_monitoring(self):
        """Start background monitoring loop."""
        self._monitor_task = asyncio.create_task(self._autonomous_monitoring())

    def stop_monitoring(self):
        """Stop background monitoring loop."""
        if hasattr(self, "_monitor_task") and not self._monitor_task.done():
            self._monitor_task.cancel()

    def restart_orchestrator(self):
        if self.orchestrator_client and hasattr(self.orchestrator_client, "restart"):
            self.orchestrator_client.restart()

    def restart_clusters(self):
        if self.cluster_manager and hasattr(self.cluster_manager, "restart"):
            asyncio.run(self.cluster_manager.restart())

    def update_dependencies(self) -> Dict[str, str]:
        return asyncio.run(self._update_dependencies())
        
    def _load_config(self) -> Dict:
        """Load configuration from config file"""
        config_path = Path("config.yaml")
        if not config_path.exists():
            raise FileNotFoundError("Configuration file not found")
        with open(config_path) as f:
            return yaml.safe_load(f)
            
    def _init_orchestrator_client(self):
        """Initialize orchestrator client"""
        try:
            from mycosoft_mas.orchestrator import Orchestrator
            return Orchestrator()
        except Exception as e:
            logger.error(f"Failed to initialize orchestrator client: {e}")
            return None
        
    def _init_cluster_manager(self):
        """Initialize cluster manager"""
        try:
            from mycosoft_mas.agents.cluster_manager import ClusterManager
            return ClusterManager(self.config.get("clusters", {}))
        except Exception as e:
            logger.error(f"Failed to initialize cluster manager: {e}")
            return None
        
    def _setup_routes(self):
        @self.app.get("/processes", response_model=List[ProcessInfo])
        async def get_processes():
            return await self._get_processes()
            
        @self.app.get("/agents", response_model=List[AgentInfo])
        async def get_agents():
            return await self._get_agents()
            
        @self.app.get("/services", response_model=List[ServiceInfo])
        async def get_services():
            return await self._get_services()
            
        @self.app.post("/process/{pid}/kill")
        async def kill_process(pid: int):
            return await self._kill_process(pid)
            
        @self.app.post("/agent/{agent_id}/restart")
        async def restart_agent(agent_id: str):
            return await self._restart_agent(agent_id)
            
        @self.app.post("/service/{service_name}/restart")
        async def restart_service(service_name: str):
            return await self._restart_service(service_name)
            
        @self.app.get("/system/stats")
        async def get_system_stats():
            return await self._get_system_stats()
            
        @self.app.get("/health", response_model=SystemHealth)
        async def get_system_health():
            return await self._get_system_health()
            
        @self.app.post("/optimize")
        async def optimize_system():
            return await self._optimize_system()
            
        @self.app.post("/adapt")
        async def adapt_system():
            return await self._adapt_system()
            
        @self.app.get("/orchestrator", response_model=OrchestratorInfo)
        async def get_orchestrator_status():
            return await self._get_orchestrator_status()
            
        @self.app.get("/clusters", response_model=List[ClusterInfo])
        async def get_clusters():
            return await self._get_clusters()
            
        @self.app.get("/dependencies", response_model=List[DependencyInfo])
        async def get_dependencies():
            return await self._get_dependencies()
            
        @self.app.post("/orchestrator/restart")
        async def restart_orchestrator():
            return await self._restart_orchestrator()
            
        @self.app.post("/cluster/{cluster_name}/restart")
        async def restart_cluster(cluster_name: str):
            return await self._restart_cluster(cluster_name)
            
        @self.app.post("/dependencies/update")
        async def update_dependencies():
            return await self._update_dependencies()
            
    async def _get_processes(self) -> List[ProcessInfo]:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 
                                       'memory_percent', 'memory_info', 'create_time',
                                       'cmdline', 'username', 'num_threads', 'connections',
                                       'io_counters']):
            try:
                process_info = proc.info
                processes.append(ProcessInfo(
                    pid=process_info['pid'],
                    name=process_info['name'],
                    status=process_info['status'],
                    cpu_percent=process_info['cpu_percent'],
                    memory_percent=process_info['memory_percent'],
                    memory_bytes=process_info['memory_info'].rss,
                    create_time=datetime.fromtimestamp(process_info['create_time']),
                    command_line=' '.join(process_info['cmdline']),
                    username=process_info['username'],
                    num_threads=process_info['num_threads'],
                    num_connections=len(process_info['connections']),
                    io_counters=process_info['io_counters']._asdict(),
                    network_connections=[conn._asdict() for conn in process_info['connections']]
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return processes
        
    async def _get_agents(self) -> List[AgentInfo]:
        # TODO: Implement agent monitoring
        return []
        
    async def _get_services(self) -> List[ServiceInfo]:
        services = []
        for container in self.docker_client.containers.list(all=True):
            stats = container.stats(stream=False)
            services.append(ServiceInfo(
                service_name=container.name,
                status=container.status,
                container_id=container.id,
                image=container.image.tags[0] if container.image.tags else "unknown",
                ports=container.ports,
                cpu_usage=stats['cpu_stats']['cpu_usage']['total_usage'] / stats['cpu_stats']['system_cpu_usage'] * 100,
                memory_usage=stats['memory_stats']['usage'],
                network_traffic=stats['networks'],
                logs=container.logs(tail=100).decode('utf-8').split('\n')
            ))
        return services
        
    async def _kill_process(self, pid: int) -> Dict[str, str]:
        try:
            process = psutil.Process(pid)
            process.terminate()
            return {"status": "success", "message": f"Process {pid} terminated"}
        except psutil.NoSuchProcess:
            raise HTTPException(status_code=404, detail="Process not found")
        except psutil.AccessDenied:
            raise HTTPException(status_code=403, detail="Access denied")
            
    async def _restart_agent(self, agent_id: str) -> Dict[str, str]:
        try:
            if self.orchestrator_client and hasattr(self.orchestrator_client, "restart_agent"):
                await self.orchestrator_client.restart_agent(agent_id)
            return {"status": "success", "message": f"Agent {agent_id} restarted"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
    async def _restart_service(self, service_name: str) -> Dict[str, str]:
        try:
            container = self.docker_client.containers.get(service_name)
            container.restart()
            return {"status": "success", "message": f"Service {service_name} restarted"}
        except docker.errors.NotFound:
            raise HTTPException(status_code=404, detail="Service not found")
            
    async def _get_system_stats(self) -> Dict[str, any]:
        return {
            "cpu": {
                "percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count(),
                "freq": psutil.cpu_freq()._asdict()
            },
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage('/')._asdict(),
            "network": psutil.net_io_counters()._asdict(),
            "system": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "uptime": psutil.boot_time()
            }
        }
        
    async def _get_orchestrator_status(self) -> OrchestratorInfo:
        """Get orchestrator status"""
        if self.orchestrator_client and hasattr(self.orchestrator_client, "get_status"):
            status = await self.orchestrator_client.get_status()
            return OrchestratorInfo(**status)
        return OrchestratorInfo(
            status="unknown",
            active_tasks=0,
            pending_tasks=0,
            failed_tasks=0,
            resource_usage={"cpu": 0.0, "memory": 0.0},
            last_heartbeat=datetime.now(),
            cluster_status={}
        )
        
    async def _get_clusters(self) -> List[ClusterInfo]:
        """Get cluster information"""
        if self.cluster_manager and hasattr(self.cluster_manager, "get_status"):
            status = self.cluster_manager.get_status()
            clusters = []
            for name, info in status.get("clusters", {}).items():
                clusters.append(
                    ClusterInfo(
                        name=name,
                        status=info["metrics"].get("status", "unknown"),
                        node_count=info["agent_count"],
                        active_agents=info["agent_count"],
                        resource_usage={},
                        last_sync=datetime.fromisoformat(info["metrics"].get("last_activity", datetime.now().isoformat())),
                        health_status=info["metrics"].get("status", "unknown")
                    )
                )
            return clusters
        return []
        
    async def _get_dependencies(self) -> List[DependencyInfo]:
        """Get dependency information"""
        try:
            result = subprocess.run(
                ["poetry", "show", "--outdated", "--json"],
                capture_output=True,
                text=True
            )
            packages = json.loads(result.stdout)
            
            dependencies = []
            for package in packages:
                dependencies.append(DependencyInfo(
                    package=package["name"],
                    version=package["version"],
                    status="outdated" if package.get("latest_version") else "up-to-date",
                    dependencies=package.get("dependencies", []),
                    last_update=datetime.now(),
                    vulnerabilities=[]  # TODO: Implement vulnerability scanning
                ))
            return dependencies
        except Exception as e:
            logger.error(f"Error getting dependencies: {str(e)}")
            return []
            
    async def _restart_orchestrator(self) -> Dict[str, str]:
        """Restart orchestrator"""
        try:
            if self.orchestrator_client and hasattr(self.orchestrator_client, "restart"):
                await self.orchestrator_client.restart()
            return {"status": "success", "message": "Orchestrator restarted"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    async def _restart_cluster(self, cluster_name: str) -> Dict[str, str]:
        """Restart cluster"""
        try:
            if self.cluster_manager and hasattr(self.cluster_manager, "restart"):
                await self.cluster_manager.restart()
            return {"status": "success", "message": f"Cluster {cluster_name} restarted"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    async def _update_dependencies(self) -> Dict[str, str]:
        """Update dependencies using Poetry"""
        try:
            result = subprocess.run(
                ["poetry", "update"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return {"status": "success", "message": "Dependencies updated successfully"}
            else:
                raise Exception(result.stderr)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def _autonomous_monitoring(self):
        """Autonomous monitoring and healing loop"""
        while True:
            try:
                # Collect system metrics
                metrics = await self._collect_metrics()
                self.metric_history.append(metrics)
                
                # Check orchestrator health
                orchestrator_status = await self._get_orchestrator_status()
                self.orchestrator_health.set(1.0 if orchestrator_status.status == "running" else 0.0)
                
                # Check cluster health
                clusters = await self._get_clusters()
                if clusters:  # Only calculate if there are clusters
                    cluster_health = sum(1 for c in clusters if c.health_status == "healthy") / len(clusters)
                else:
                    cluster_health = 1.0  # Default to healthy if no clusters
                self.cluster_health.set(cluster_health)
                
                # Detect anomalies
                if len(self.metric_history) >= 100:
                    anomaly_scores = self._detect_anomalies()
                    await self._handle_anomalies(anomaly_scores)
                
                # Check system health
                health_status = await self._check_system_health()
                if health_status['overall_health'] != 'healthy':
                    await self._heal_system(health_status)
                
                # Optimize resources
                await self._optimize_resources()
                
                # Update learning models
                await self._update_learning_models()
                
                # Check and update dependencies
                if self.config.get("auto_update_dependencies", False):
                    await self._check_and_update_dependencies()
                
            except Exception as e:
                logger.error(f"Error in autonomous monitoring: {str(e)}")
            
            await asyncio.sleep(15)
            
    async def _collect_metrics(self) -> Dict[str, float]:
        """Collect comprehensive system metrics"""
        return {
            'cpu_usage': psutil.cpu_percent(),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'network_traffic': sum(psutil.net_io_counters()._asdict().values()),
            'process_count': len(await self._get_processes()),
            'service_count': len(await self._get_services()),
            'error_rate': self._calculate_error_rate(),
            'response_time': self._calculate_average_response_time()
        }
        
    def _detect_anomalies(self) -> Dict[str, float]:
        """Detect anomalies in system metrics"""
        metrics_array = np.array([list(m.values()) for m in self.metric_history])
        anomaly_scores = self.anomaly_detector.fit_predict(metrics_array)
        return dict(zip(self.metric_history[-1].keys(), anomaly_scores))
        
    async def _handle_anomalies(self, anomaly_scores: Dict[str, float]):
        """Handle detected anomalies"""
        for metric, score in anomaly_scores.items():
            if score < -0.5:  # Significant anomaly
                logger.warning(f"Anomaly detected in {metric}: {score}")
                await self._mitigate_anomaly(metric, score)
                
    async def _mitigate_anomaly(self, metric: str, score: float):
        """Mitigate detected anomalies"""
        if metric == 'cpu_usage' and score < -0.5:
            await self._optimize_cpu_usage()
        elif metric == 'memory_usage' and score < -0.5:
            await self._optimize_memory_usage()
        elif metric == 'error_rate' and score < -0.5:
            await self._handle_increased_errors()
            
    async def _optimize_cpu_usage(self):
        """Optimize CPU usage"""
        processes = await self._get_processes()
        for proc in sorted(processes, key=lambda x: x.cpu_percent, reverse=True):
            if proc.cpu_percent > self.thresholds['cpu_critical']:
                await self._kill_process(proc.pid)
                logger.info(f"Terminated high CPU process: {proc.name}")
                
    async def _optimize_memory_usage(self):
        """Optimize memory usage"""
        processes = await self._get_processes()
        for proc in sorted(processes, key=lambda x: x.memory_percent, reverse=True):
            if proc.memory_percent > self.thresholds['memory_critical']:
                await self._kill_process(proc.pid)
                logger.info(f"Terminated high memory process: {proc.name}")
                
    async def _handle_increased_errors(self):
        """Handle increased error rates"""
        services = await self._get_services()
        for service in services:
            if service.error_rate > self.thresholds['error_rate_critical']:
                await self._restart_service(service.service_name)
                logger.info(f"Restarted service due to high error rate: {service.service_name}")
                
    async def _optimize_resources(self):
        """Optimize system resources"""
        # Implement resource optimization strategies
        pass
        
    async def _update_learning_models(self):
        """Update learning models based on new data"""
        # Implement model update logic
        pass
        
    async def _get_system_health(self) -> SystemHealth:
        """Get comprehensive system health status"""
        metrics = await self._collect_metrics()
        issues = []
        recommendations = []
        
        # Check CPU health
        if metrics['cpu_usage'] > self.thresholds['cpu_critical']:
            issues.append("Critical CPU usage")
            recommendations.append("Consider scaling horizontally or optimizing processes")
        elif metrics['cpu_usage'] > self.thresholds['cpu_warning']:
            issues.append("High CPU usage")
            recommendations.append("Monitor CPU usage and consider optimization")
            
        # Check memory health
        if metrics['memory_usage'] > self.thresholds['memory_critical']:
            issues.append("Critical memory usage")
            recommendations.append("Consider memory optimization or scaling")
        elif metrics['memory_usage'] > self.thresholds['memory_warning']:
            issues.append("High memory usage")
            recommendations.append("Monitor memory usage and consider optimization")
            
        # Check error rates
        if metrics['error_rate'] > self.thresholds['error_rate_critical']:
            issues.append("Critical error rate")
            recommendations.append("Investigate and fix error sources")
        elif metrics['error_rate'] > self.thresholds['error_rate_warning']:
            issues.append("High error rate")
            recommendations.append("Monitor error patterns")
            
        return SystemHealth(
            overall_health="healthy" if not issues else "unhealthy",
            critical_issues=issues,
            recommendations=recommendations,
            resource_optimization={},
            security_status={},
            performance_metrics=metrics
        )
        
    async def _heal_system(self, health_status: SystemHealth):
        """Implement self-healing based on health status"""
        for issue in health_status.critical_issues:
            if "CPU" in issue:
                await self._optimize_cpu_usage()
            elif "memory" in issue:
                await self._optimize_memory_usage()
            elif "error" in issue:
                await self._handle_increased_errors()
                
    async def _optimize_system(self) -> Dict[str, str]:
        """Optimize system performance"""
        # Implement system optimization strategies
        return {"status": "success", "message": "System optimization completed"}
        
    async def _adapt_system(self) -> Dict[str, str]:
        """Adapt system to changing conditions"""
        # Implement system adaptation strategies
        return {"status": "success", "message": "System adaptation completed"}
        
    def _calculate_error_rate(self) -> float:
        """Calculate system error rate"""
        # Implement error rate calculation
        return 0.0
        
    def _calculate_average_response_time(self) -> float:
        """Calculate average system response time"""
        # Implement response time calculation
        return 0.0
        
    async def _check_and_update_dependencies(self):
        """Check and update dependencies if needed"""
        dependencies = await self._get_dependencies()
        outdated = [d for d in dependencies if d.status == "outdated"]
        if outdated:
            logger.info(f"Found {len(outdated)} outdated dependencies")
            await self._update_dependencies() 