"""Role-Based Access Control. Created: February 3, 2026"""
from typing import Any, Dict, List, Set
from uuid import UUID, uuid4
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    SCIENTIST = "scientist"
    TECHNICIAN = "technician"
    VIEWER = "viewer"

class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"

class RBACManager:
    """Role-based access control manager."""
    
    def __init__(self):
        self._roles: Dict[str, Set[Permission]] = {
            Role.ADMIN.value: {Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.ADMIN},
            Role.SCIENTIST.value: {Permission.READ, Permission.WRITE, Permission.EXECUTE},
            Role.TECHNICIAN.value: {Permission.READ, Permission.EXECUTE},
            Role.VIEWER.value: {Permission.READ},
        }
        self._user_roles: Dict[UUID, Set[str]] = {}
    
    def assign_role(self, user_id: UUID, role: str) -> bool:
        if role not in self._roles:
            return False
        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()
        self._user_roles[user_id].add(role)
        return True
    
    def check_permission(self, user_id: UUID, permission: Permission) -> bool:
        roles = self._user_roles.get(user_id, set())
        for role in roles:
            if permission in self._roles.get(role, set()):
                return True
        return False
    
    def get_user_permissions(self, user_id: UUID) -> Set[Permission]:
        permissions = set()
        for role in self._user_roles.get(user_id, set()):
            permissions.update(self._roles.get(role, set()))
        return permissions
