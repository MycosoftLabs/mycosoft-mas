from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Dict, Optional

from mycosoft_mas.services.sensor_fusion import NaturePacket


@dataclass
class ReplayRecord:
    ts: datetime
    packet: Dict[str, object]


class NatureReplayStore:
    """Persist and replay synchronized NaturePackets for replayable-day verification."""

    def __init__(self, root: str = "data/first_light/replay") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, day_key: str) -> Path:
        return self.root / f"{day_key}.jsonl"

    async def append_packet(self, day_key: str, packet: NaturePacket) -> None:
        line = {
            "ts": packet.timestamp.isoformat(),
            "packet": packet.to_dict(),
        }
        path = self._path(day_key)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    async def replay(
        self,
        day_key: str,
        from_ts: Optional[datetime] = None,
        until_ts: Optional[datetime] = None,
    ) -> AsyncIterator[ReplayRecord]:
        path = self._path(day_key)
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as f:
            for raw in f:
                row = json.loads(raw)
                ts = datetime.fromisoformat(row["ts"])
                if from_ts and ts < from_ts:
                    continue
                if until_ts and ts > until_ts:
                    continue
                yield ReplayRecord(ts=ts, packet=row["packet"])

    async def verify_replayable_day(self, day_key: str) -> Dict[str, object]:
        path = self._path(day_key)
        if not path.exists():
            return {"ok": False, "reason": "missing_day_file", "day_key": day_key}

        total = 0
        with path.open("r", encoding="utf-8") as f:
            for _ in f:
                total += 1
        return {
            "ok": total > 0,
            "day_key": day_key,
            "records": total,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

