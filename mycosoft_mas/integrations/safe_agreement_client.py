"""
SAFE agreement generation and storage service.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4


class SafeAgreementClient:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.safe_dir = self.data_dir / "safe_agreements"
        self.safe_dir.mkdir(parents=True, exist_ok=True)

    async def create_safe_agreement(self, details: Dict[str, Any]) -> Dict[str, Any]:
        agreement_id = f"safe-{uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc).isoformat()
        record = {
            "agreement_id": agreement_id,
            "created_at": created_at,
            "investor": details.get("investor"),
            "investor_id": details.get("investor_id"),
            "amount": details.get("amount"),
            "valuation_cap": details.get("valuation_cap"),
            "discount": details.get("discount"),
            "terms": details.get("terms", {}),
            "issue_date": details.get("issue_date", created_at.split("T")[0]),
            "notes": details.get("notes", ""),
            "currency": details.get("currency", "USD"),
            "status": "draft",
        }

        json_path = self.safe_dir / f"{agreement_id}.json"
        md_path = self.safe_dir / f"{agreement_id}.md"

        json_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        md_path.write_text(self._render_markdown(record), encoding="utf-8")
        return record

    def _render_markdown(self, record: Dict[str, Any]) -> str:
        return (
            f"# SAFE Agreement {record['agreement_id']}\n\n"
            f"- Created At: {record['created_at']}\n"
            f"- Investor: {record.get('investor', 'unknown')}\n"
            f"- Amount: {record.get('amount', 0)} {record.get('currency', 'USD')}\n"
            f"- Valuation Cap: {record.get('valuation_cap', 'n/a')}\n"
            f"- Discount: {record.get('discount', 'n/a')}\n"
            f"- Issue Date: {record.get('issue_date', 'n/a')}\n"
            f"- Status: {record.get('status', 'draft')}\n\n"
            f"## Notes\n{record.get('notes', '')}\n\n"
            f"## Terms (JSON)\n```json\n{json.dumps(record.get('terms', {}), indent=2)}\n```\n"
        )
