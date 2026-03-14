"""
On-device Jetson operator runtime (between Side A and Side B).

Responsibilities:
- MDP command arbitration to Side A and Side B
- Audit logging for all hardware commands
- Approval-gated mutation proposals (firmware/code/config)
- Optional OpenClaw task execution
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Literal, Optional
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .mdp_serial_bridge import build_side_a_bridge, build_side_b_bridge, MdpResponse
from .opclaw_client import OpenClawClient
from .telemetry_pipeline import TelemetryPipeline

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class MutationProposal:
    proposal_id: str
    proposal_type: Literal["firmware", "script", "config"]
    target: Literal["side_a", "side_b", "jetson"]
    content_hash: str
    risk: Literal["low", "medium", "high", "critical"]
    submitted_at: str
    status: Literal["pending", "approved", "rejected", "applied"] = "pending"
    approved_by: Optional[str] = None
    decision_at: Optional[str] = None


class AuditLogger:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def write(self, event_type: str, payload: Dict[str, Any]) -> None:
        entry = {
            "ts": _utc_now(),
            "event_type": event_type,
            "payload": payload,
        }
        line = json.dumps(entry, separators=(",", ":")) + "\n"
        async with self._lock:
            await asyncio.to_thread(self._append_line, line)

    def _append_line(self, line: str) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line)


class CommandRequest(BaseModel):
    command: str
    params: Dict[str, Any] = Field(default_factory=dict)
    ack_requested: bool = True
    source: str = "operator_api"


class ProposalRequest(BaseModel):
    proposal_type: Literal["firmware", "script", "config"]
    target: Literal["side_a", "side_b", "jetson"]
    content: str
    risk: Literal["low", "medium", "high", "critical"] = "medium"
    source: str = "operator_api"


class ApprovalRequest(BaseModel):
    approver: str
    decision: Literal["approve", "reject"]
    reason: Optional[str] = None


class OpenClawTaskRequest(BaseModel):
    task: Dict[str, Any]
    source: str = "operator_api"


class OnDeviceOperator:
    def __init__(self) -> None:
        side_a_port = os.getenv("ONDEVICE_SIDE_A_PORT", "/dev/ttyTHS1")
        side_b_port = os.getenv("ONDEVICE_SIDE_B_PORT", "/dev/ttyTHS2")
        baud = int(os.getenv("ONDEVICE_MDP_BAUD", "115200"))

        audit_path = Path(os.getenv("ONDEVICE_AUDIT_LOG", "data/edge/ondevice_audit.jsonl"))
        self.audit = AuditLogger(audit_path)
        self.side_a = build_side_a_bridge(side_a_port, baud)
        self.side_b = build_side_b_bridge(side_b_port, baud)
        self.proposals: Dict[str, MutationProposal] = {}
        self.estop_active = False
        self.opclaw_url = os.getenv("OPENCLAW_BASE_URL", "").strip()
        self.opclaw_api_key = os.getenv("OPENCLAW_API_KEY", "").strip() or None
        self.opclaw = OpenClawClient(self.opclaw_url) if self.opclaw_url else None

    async def request_side_a(self, req: CommandRequest) -> Dict[str, Any]:
        if self.estop_active and req.command not in {"health", "clear_estop", "hello"}:
            raise HTTPException(status_code=409, detail="estop_active")
        response = await asyncio.to_thread(self.side_a.request, req.command, req.params, ack_requested=req.ack_requested)
        await self.audit.write(
            "side_a_command",
            {"source": req.source, "command": req.command, "params": req.params, "response": _response_dict(response)},
        )
        if req.command == "estop":
            self.estop_active = True
        if req.command == "clear_estop":
            self.estop_active = False
        return _response_dict(response)

    async def request_side_b(self, req: CommandRequest) -> Dict[str, Any]:
        if self.estop_active and req.command not in {"transport_status", "hello"}:
            raise HTTPException(status_code=409, detail="estop_active")
        response = await asyncio.to_thread(self.side_b.request, req.command, req.params, ack_requested=req.ack_requested)
        await self.audit.write(
            "side_b_command",
            {"source": req.source, "command": req.command, "params": req.params, "response": _response_dict(response)},
        )
        return _response_dict(response)

    async def submit_proposal(self, req: ProposalRequest) -> MutationProposal:
        proposal = MutationProposal(
            proposal_id=str(uuid.uuid4()),
            proposal_type=req.proposal_type,
            target=req.target,
            content_hash=_sha256(req.content),
            risk=req.risk,
            submitted_at=_utc_now(),
        )
        self.proposals[proposal.proposal_id] = proposal
        await self.audit.write("mutation_proposed", {"source": req.source, **asdict(proposal)})
        return proposal

    async def decide_proposal(self, proposal_id: str, req: ApprovalRequest) -> MutationProposal:
        if proposal_id not in self.proposals:
            raise HTTPException(status_code=404, detail="proposal_not_found")
        proposal = self.proposals[proposal_id]
        proposal.status = "approved" if req.decision == "approve" else "rejected"
        proposal.approved_by = req.approver
        proposal.decision_at = _utc_now()
        await self.audit.write("mutation_decision", {"proposal_id": proposal_id, "decision": req.decision, "approver": req.approver, "reason": req.reason})
        return proposal

    async def apply_proposal(self, proposal_id: str, source: str) -> MutationProposal:
        if proposal_id not in self.proposals:
            raise HTTPException(status_code=404, detail="proposal_not_found")
        proposal = self.proposals[proposal_id]
        if proposal.status != "approved":
            raise HTTPException(status_code=409, detail="proposal_not_approved")
        proposal.status = "applied"
        await self.audit.write("mutation_applied", {"source": source, **asdict(proposal)})
        return proposal

    async def run_opclaw_task(self, req: OpenClawTaskRequest) -> Dict[str, Any]:
        if not self.opclaw:
            raise HTTPException(status_code=400, detail="openclaw_not_configured")
        result = await self.opclaw.run_task(req.task, api_key=self.opclaw_api_key)
        await self.audit.write("openclaw_task", {"source": req.source, "task": req.task, "result": result})
        return result


def _response_dict(response: MdpResponse) -> Dict[str, Any]:
    return {"header": response.header, "payload": response.payload}


operator = OnDeviceOperator()


async def _side_a_request_for_pipeline(cmd: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Adapter for TelemetryPipeline: (cmd, params) -> request_side_a result."""
    return await operator.request_side_a(CommandRequest(command=cmd, params=params))


telemetry_pipeline = TelemetryPipeline(
    side_a_request_fn=_side_a_request_for_pipeline,
    device_id=os.getenv("ONDEVICE_DEVICE_ID", "mycobrain-001"),
    mas_api_url=os.getenv("MAS_API_URL", "http://192.168.0.188:8001"),
    nlm_api_url=os.getenv("NLM_API_URL") or None,
    mindex_api_url=os.getenv("MINDEX_API_URL") or None,
    role=os.getenv("ONDEVICE_ROLE", "mushroom1"),
    poll_interval_seconds=float(os.getenv("ONDEVICE_POLL_INTERVAL", "5.0")),
)

app = FastAPI(title="MycoBrain On-Device Operator", version="1.0.0")


@app.on_event("startup")
async def startup() -> None:
    telemetry_pipeline.start()


@app.on_event("shutdown")
async def shutdown() -> None:
    await telemetry_pipeline.stop()


@app.get("/health")
async def health() -> Dict[str, Any]:
    openclaw_health: Optional[Dict[str, Any]] = None
    if operator.opclaw:
        try:
            openclaw_health = await operator.opclaw.health()
        except Exception as exc:  # noqa: BLE001
            openclaw_health = {"status": "unreachable", "error": str(exc)}
    return {
        "status": "healthy",
        "service": "ondevice-operator",
        "side_a_port": operator.side_a.port,
        "side_b_port": operator.side_b.port,
        "estop_active": operator.estop_active,
        "openclaw": openclaw_health,
        "pending_proposals": sum(1 for p in operator.proposals.values() if p.status == "pending"),
    }


@app.post("/side-a/command")
async def side_a_command(req: CommandRequest) -> Dict[str, Any]:
    return await operator.request_side_a(req)


@app.post("/side-b/command")
async def side_b_command(req: CommandRequest) -> Dict[str, Any]:
    return await operator.request_side_b(req)


@app.post("/mutations/propose")
async def propose_mutation(req: ProposalRequest) -> Dict[str, Any]:
    proposal = await operator.submit_proposal(req)
    return {"proposal": asdict(proposal)}


@app.post("/mutations/{proposal_id}/decision")
async def mutation_decision(proposal_id: str, req: ApprovalRequest) -> Dict[str, Any]:
    proposal = await operator.decide_proposal(proposal_id, req)
    return {"proposal": asdict(proposal)}


@app.post("/mutations/{proposal_id}/apply")
async def mutation_apply(proposal_id: str, source: str = "operator_api") -> Dict[str, Any]:
    proposal = await operator.apply_proposal(proposal_id, source)
    return {"proposal": asdict(proposal)}


@app.post("/openclaw/task")
async def openclaw_task(req: OpenClawTaskRequest) -> Dict[str, Any]:
    return await operator.run_opclaw_task(req)


@app.get("/mutations")
async def list_mutations() -> Dict[str, Any]:
    return {"proposals": [asdict(p) for p in operator.proposals.values()]}


@app.get("/telemetry/latest")
async def telemetry_latest(n: int = 10) -> Dict[str, Any]:
    """Return last n telemetry entries from the pipeline buffer."""
    entries = await telemetry_pipeline.get_latest(n)
    return {"telemetry": entries, "device_id": telemetry_pipeline.device_id}


@app.get("/telemetry/stream")
async def telemetry_stream() -> StreamingResponse:
    """SSE stream of live telemetry from the pipeline."""

    async def event_gen() -> AsyncIterator[str]:
        async for entry in telemetry_pipeline.stream():
            yield f"data: {json.dumps(asdict(entry))}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
