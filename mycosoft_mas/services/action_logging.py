from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4


@dataclass
class ActionRecord:
    action_id: str
    action_type: str
    request: Dict[str, Any]
    outcome: Dict[str, Any]
    approved: bool
    created_at: str


class ActionLoggingService:
    def __init__(self, log_path: str = "data/first_light/action_log.jsonl") -> None:
        self.path = Path(log_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def log_action(
        self,
        action_type: str,
        request: Dict[str, Any],
        outcome: Dict[str, Any],
        approved: bool,
    ) -> ActionRecord:
        record = ActionRecord(
            action_id=str(uuid4()),
            action_type=action_type,
            request=request,
            outcome=outcome,
            approved=approved,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.__dict__, ensure_ascii=False) + "\n")
        return record
