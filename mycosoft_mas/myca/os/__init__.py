"""
MYCA Operating System — The autonomous employee daemon.

This is MYCA's persistent process running on VM 191.
It ties together consciousness, communication, tools, and executive functions
into a unified 24/7 autonomous loop.

Architecture:
    MycaOS (main loop)
    ├── CommsHub — Discord, Signal, WhatsApp, Asana, Email inbound/outbound
    ├── ToolOrchestrator — Claude Code, Cursor, browser-use, n8n, Git, Docker
    ├── ExecutiveSystem — COO/Co-CEO/Co-CTO decision engine with Morgan sync
    ├── MASBridge — Orchestrator (188:8001), 158+ agents, MAS n8n (188:5678)
    ├── MINDEXBridge — Postgres, Redis, Qdrant, MINDEX API (189)
    └── WebsiteBridge — Website management (187:3000)

Date: 2026-03-04
"""

from mycosoft_mas.myca.os.core import MycaOS

__all__ = ["MycaOS"]
