from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SporebaseLabel:
    segment_id: str
    start_utc: str
    end_utc: str
    species: Optional[str]
    confidence: float


class SporebaseLabelStore:
    """
    Phase 2.4 supervised labels from tape-segment metadata.
    Expected CSV columns:
    segment_id,start_utc,end_utc,species,confidence
    """

    def __init__(self, csv_path: str = "data/sporebase/labels.csv") -> None:
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

    def load_labels(self) -> List[SporebaseLabel]:
        if not self.csv_path.exists():
            return []
        rows: List[SporebaseLabel] = []
        with self.csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(
                    SporebaseLabel(
                        segment_id=row.get("segment_id", ""),
                        start_utc=row.get("start_utc", ""),
                        end_utc=row.get("end_utc", ""),
                        species=row.get("species") or None,
                        confidence=float(row.get("confidence", "0") or 0),
                    )
                )
        return rows

    def as_supervised_map(self) -> Dict[str, Dict[str, object]]:
        return {
            item.segment_id: {"species": item.species, "confidence": item.confidence}
            for item in self.load_labels()
        }

