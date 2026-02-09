"""
Platform API Router
Multi-tenant organization management, federation, and audit logging
"""

from fastapi import APIRouter, HTTPException, Body, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Enums ---

class PlanType(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class OrgStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"


class MemberRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    SCIENTIST = "scientist"
    VIEWER = "viewer"


class MemberStatus(str, Enum):
    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"


class PeerStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    PENDING = "pending"


# --- Models ---

class ResourceQuota(BaseModel):
    maxUsers: int
    maxExperiments: int
    maxSimulations: int
    maxStorageGB: int
    maxComputeHours: int
    currentUsage: Dict[str, int]


class OrganizationSettings(BaseModel):
    allowedModules: List[str]
    dataRetentionDays: int
    auditLogging: bool
    ssoEnabled: bool
    apiAccessEnabled: bool


class Organization(BaseModel):
    id: str
    name: str
    slug: str
    plan: PlanType
    status: OrgStatus
    createdAt: str
    memberCount: int
    resourceQuota: ResourceQuota
    settings: OrganizationSettings


class OrganizationCreate(BaseModel):
    name: str
    plan: PlanType = PlanType.FREE


class Member(BaseModel):
    id: str
    email: str
    name: str
    role: MemberRole
    status: MemberStatus
    joinedAt: str
    lastActiveAt: Optional[str] = None


class MemberInvite(BaseModel):
    email: str
    role: MemberRole = MemberRole.SCIENTIST


class DataSharingPolicy(BaseModel):
    shareExperiments: bool = True
    shareSimulations: bool = True
    shareSpecies: bool = True
    requireApproval: bool = True
    allowedCategories: List[str] = []


class FederationPeer(BaseModel):
    id: str
    name: str
    endpoint: str
    status: PeerStatus
    dataSharing: DataSharingPolicy
    lastSync: str


class PeerConnect(BaseModel):
    endpoint: str
    policy: DataSharingPolicy


class AuditLog(BaseModel):
    id: str
    timestamp: str
    userId: str
    action: str
    resource: str
    resourceId: str
    details: Dict[str, Any]
    ipAddress: str


class UsageMetrics(BaseModel):
    organizationId: str
    period: str
    experiments: int
    simulations: int
    computeHours: float
    storageGB: float
    apiCalls: int
    activeUsers: int


# --- In-memory storage ---

_organizations: Dict[str, Organization] = {}
_members: Dict[str, List[Member]] = {}
_peers: Dict[str, List[FederationPeer]] = {}
_audit_logs: Dict[str, List[AuditLog]] = {}


def _init_sample_data():
    global _organizations, _members, _peers, _audit_logs
    
    org = Organization(
        id="org-001",
        name="Mycosoft Research Lab",
        slug="mycosoft-research",
        plan=PlanType.ENTERPRISE,
        status=OrgStatus.ACTIVE,
        createdAt="2025-01-01T00:00:00Z",
        memberCount=12,
        resourceQuota=ResourceQuota(
            maxUsers=100,
            maxExperiments=1000,
            maxSimulations=500,
            maxStorageGB=1000,
            maxComputeHours=10000,
            currentUsage={
                "users": 12,
                "experiments": 156,
                "simulations": 89,
                "storageGB": 234,
                "computeHours": 1245
            }
        ),
        settings=OrganizationSettings(
            allowedModules=["scientific", "bio", "autonomous", "platform"],
            dataRetentionDays=365,
            auditLogging=True,
            ssoEnabled=True,
            apiAccessEnabled=True
        )
    )
    _organizations[org.id] = org
    
    _members[org.id] = [
        Member(id="m-001", email="sarah@mycosoft.com", name="Dr. Sarah Chen", role=MemberRole.OWNER, status=MemberStatus.ACTIVE, joinedAt="2025-01-01T00:00:00Z", lastActiveAt="2026-02-03T10:00:00Z"),
        Member(id="m-002", email="james@mycosoft.com", name="James Wilson", role=MemberRole.ADMIN, status=MemberStatus.ACTIVE, joinedAt="2025-01-15T00:00:00Z", lastActiveAt="2026-02-03T09:30:00Z"),
        Member(id="m-003", email="maya@mycosoft.com", name="Dr. Maya Patel", role=MemberRole.SCIENTIST, status=MemberStatus.ACTIVE, joinedAt="2025-02-01T00:00:00Z", lastActiveAt="2026-02-03T08:00:00Z"),
        Member(id="m-004", email="alex@mycosoft.com", name="Alex Kim", role=MemberRole.SCIENTIST, status=MemberStatus.ACTIVE, joinedAt="2025-03-01T00:00:00Z"),
        Member(id="m-005", email="new@mycosoft.com", name="New Researcher", role=MemberRole.VIEWER, status=MemberStatus.INVITED, joinedAt="2026-02-03T00:00:00Z"),
    ]
    
    _peers[org.id] = [
        FederationPeer(id="peer-001", name="University of Mycology", endpoint="https://mycology.edu/api", status=PeerStatus.CONNECTED, dataSharing=DataSharingPolicy(), lastSync="2026-02-03T09:55:00Z"),
        FederationPeer(id="peer-002", name="Fungal Research Institute", endpoint="https://fri.org/api", status=PeerStatus.CONNECTED, dataSharing=DataSharingPolicy(), lastSync="2026-02-03T09:00:00Z"),
        FederationPeer(id="peer-003", name="Bio-Compute Consortium", endpoint="https://biocompute.org/api", status=PeerStatus.PENDING, dataSharing=DataSharingPolicy(), lastSync="Never"),
    ]
    
    _audit_logs[org.id] = [
        AuditLog(id="log-001", timestamp="2026-02-03T10:30:00Z", userId="sarah@mycosoft.com", action="experiment.create", resource="experiment", resourceId="E-044", details={"name": "New Experiment"}, ipAddress="192.168.1.100"),
        AuditLog(id="log-002", timestamp="2026-02-03T10:25:00Z", userId="james@mycosoft.com", action="member.invite", resource="member", resourceId="new@mycosoft.com", details={"role": "viewer"}, ipAddress="192.168.1.101"),
        AuditLog(id="log-003", timestamp="2026-02-03T10:20:00Z", userId="maya@mycosoft.com", action="simulation.start", resource="simulation", resourceId="sim-008", details={"type": "alphafold"}, ipAddress="192.168.1.102"),
        AuditLog(id="log-004", timestamp="2026-02-03T10:15:00Z", userId="system", action="federation.sync", resource="peer", resourceId="peer-001", details={"records": 150}, ipAddress="0.0.0.0"),
        AuditLog(id="log-005", timestamp="2026-02-03T10:10:00Z", userId="alex@mycosoft.com", action="data.export", resource="dataset", resourceId="dataset-023", details={"format": "csv"}, ipAddress="192.168.1.103"),
    ]

_init_sample_data()


# --- Organization API ---

@router.get("/organizations")
async def list_organizations():
    return {"organizations": list(_organizations.values())}


@router.get("/organizations/{org_id}")
async def get_organization(org_id: str):
    if org_id not in _organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _organizations[org_id]


@router.post("/organizations")
async def create_organization(data: OrganizationCreate):
    org_id = f"org-{uuid.uuid4().hex[:6]}"
    slug = data.name.lower().replace(" ", "-")
    
    # Set quotas based on plan
    quotas = {
        PlanType.FREE: {"users": 3, "experiments": 10, "simulations": 5, "storage": 1, "compute": 10},
        PlanType.STARTER: {"users": 10, "experiments": 100, "simulations": 50, "storage": 10, "compute": 100},
        PlanType.PROFESSIONAL: {"users": 50, "experiments": 500, "simulations": 200, "storage": 100, "compute": 500},
        PlanType.ENTERPRISE: {"users": 100, "experiments": 1000, "simulations": 500, "storage": 1000, "compute": 10000},
    }
    q = quotas[data.plan]
    
    org = Organization(
        id=org_id,
        name=data.name,
        slug=slug,
        plan=data.plan,
        status=OrgStatus.ACTIVE,
        createdAt=datetime.utcnow().isoformat(),
        memberCount=1,
        resourceQuota=ResourceQuota(
            maxUsers=q["users"],
            maxExperiments=q["experiments"],
            maxSimulations=q["simulations"],
            maxStorageGB=q["storage"],
            maxComputeHours=q["compute"],
            currentUsage={"users": 1, "experiments": 0, "simulations": 0, "storageGB": 0, "computeHours": 0}
        ),
        settings=OrganizationSettings(
            allowedModules=["scientific"],
            dataRetentionDays=30 if data.plan == PlanType.FREE else 365,
            auditLogging=data.plan in [PlanType.PROFESSIONAL, PlanType.ENTERPRISE],
            ssoEnabled=data.plan == PlanType.ENTERPRISE,
            apiAccessEnabled=data.plan != PlanType.FREE
        )
    )
    
    _organizations[org_id] = org
    _members[org_id] = []
    _peers[org_id] = []
    _audit_logs[org_id] = []
    
    return org


@router.patch("/organizations/{org_id}")
async def update_organization(org_id: str, updates: Dict[str, Any] = Body(...)):
    if org_id not in _organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org = _organizations[org_id]
    for key, value in updates.items():
        if hasattr(org, key):
            setattr(org, key, value)
    
    return org


@router.delete("/organizations/{org_id}")
async def delete_organization(org_id: str):
    if org_id not in _organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    del _organizations[org_id]
    _members.pop(org_id, None)
    _peers.pop(org_id, None)
    _audit_logs.pop(org_id, None)
    
    return {"deleted": True}


# --- Member API ---

@router.get("/organizations/{org_id}/members")
async def list_members(org_id: str):
    if org_id not in _organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"members": _members.get(org_id, [])}


@router.post("/organizations/{org_id}/members")
async def invite_member(org_id: str, data: MemberInvite):
    if org_id not in _organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    member_id = f"m-{uuid.uuid4().hex[:6]}"
    member = Member(
        id=member_id,
        email=data.email,
        name=data.email.split("@")[0].title(),
        role=data.role,
        status=MemberStatus.INVITED,
        joinedAt=datetime.utcnow().isoformat()
    )
    
    if org_id not in _members:
        _members[org_id] = []
    _members[org_id].append(member)
    
    # Update member count
    _organizations[org_id].memberCount = len(_members[org_id])
    
    return member


@router.patch("/organizations/{org_id}/members/{member_id}")
async def update_member(org_id: str, member_id: str, role: MemberRole = Body(...)):
    if org_id not in _members:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    for member in _members[org_id]:
        if member.id == member_id:
            member.role = role
            return member
    
    raise HTTPException(status_code=404, detail="Member not found")


@router.delete("/organizations/{org_id}/members/{member_id}")
async def remove_member(org_id: str, member_id: str):
    if org_id not in _members:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    _members[org_id] = [m for m in _members[org_id] if m.id != member_id]
    _organizations[org_id].memberCount = len(_members[org_id])
    
    return {"deleted": True}


# --- Usage API ---

@router.get("/organizations/{org_id}/usage")
async def get_usage_metrics(org_id: str, period: str = "month"):
    if org_id not in _organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return UsageMetrics(
        organizationId=org_id,
        period=period,
        experiments=156,
        simulations=89,
        computeHours=1245.5,
        storageGB=234.2,
        apiCalls=12847,
        activeUsers=8
    )


@router.get("/organizations/{org_id}/quota")
async def get_quota(org_id: str):
    if org_id not in _organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _organizations[org_id].resourceQuota


@router.post("/organizations/{org_id}/upgrade")
async def upgrade_plan(org_id: str, plan: PlanType = Body(...)):
    if org_id not in _organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    _organizations[org_id].plan = plan
    return _organizations[org_id]


# --- Federation API ---

@router.get("/organizations/{org_id}/federation/peers")
async def list_peers(org_id: str):
    if org_id not in _organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"peers": _peers.get(org_id, [])}


@router.post("/organizations/{org_id}/federation/peers")
async def connect_peer(org_id: str, data: PeerConnect):
    if org_id not in _organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    peer_id = f"peer-{uuid.uuid4().hex[:6]}"
    peer = FederationPeer(
        id=peer_id,
        name=data.endpoint.split("//")[1].split("/")[0],
        endpoint=data.endpoint,
        status=PeerStatus.PENDING,
        dataSharing=data.policy,
        lastSync="Never"
    )
    
    if org_id not in _peers:
        _peers[org_id] = []
    _peers[org_id].append(peer)
    
    return peer


@router.delete("/organizations/{org_id}/federation/peers/{peer_id}")
async def disconnect_peer(org_id: str, peer_id: str):
    if org_id not in _peers:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    _peers[org_id] = [p for p in _peers[org_id] if p.id != peer_id]
    return {"disconnected": True}


@router.post("/organizations/{org_id}/federation/peers/{peer_id}/sync")
async def sync_peer(org_id: str, peer_id: str):
    if org_id not in _peers:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    for peer in _peers[org_id]:
        if peer.id == peer_id:
            peer.lastSync = datetime.utcnow().isoformat()
            peer.status = PeerStatus.CONNECTED
            return {"synced": True, "timestamp": peer.lastSync}
    
    raise HTTPException(status_code=404, detail="Peer not found")


# --- Audit API ---

@router.post("/organizations/{org_id}/audit")
async def get_audit_logs(org_id: str, filters: Optional[Dict[str, Any]] = Body(None)):
    if org_id not in _organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    logs = _audit_logs.get(org_id, [])
    
    if filters:
        action_filter = filters.get("action")
        if action_filter:
            logs = [l for l in logs if action_filter.replace("*", "") in l.action]
    
    return {"logs": logs}


# --- Settings API ---

@router.get("/organizations/{org_id}/settings")
async def get_settings(org_id: str):
    if org_id not in _organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    return _organizations[org_id].settings


@router.patch("/organizations/{org_id}/settings")
async def update_settings(org_id: str, settings: Dict[str, Any] = Body(...)):
    if org_id not in _organizations:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    current = _organizations[org_id].settings
    for key, value in settings.items():
        if hasattr(current, key):
            setattr(current, key, value)
    
    return current
