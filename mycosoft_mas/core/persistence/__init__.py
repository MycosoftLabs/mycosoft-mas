"""
Durable persistence layer for MAS red-team, economy, and security flows.
Phase 1 of Full Integration Program — replaces in-memory storage with Supabase.

Uses Supabase when NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set;
falls back to in-memory for local dev without Supabase.

Created: March 10, 2026
"""

from mycosoft_mas.core.persistence.redteam_store import redteam_store
from mycosoft_mas.core.persistence.economy_store import economy_store

__all__ = ["redteam_store", "economy_store"]
