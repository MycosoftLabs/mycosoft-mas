"""
Real-Time Paper Monitor Agent

Watches arXiv, bioRxiv, medRxiv, and ChemRxiv for new papers
in domains relevant to Mycosoft (mycology, biotech, AI, physics,
chemistry, synthetic biology, quantum computing).

Classifies papers by domain relevance, summarises abstracts,
and alerts on breakthrough publications.

Leverages the preprint_watcher_client for feed polling.
"""

import logging
from typing import Any, Dict, List, Optional

from mycosoft_mas.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

WATCH_DOMAINS = [
    "mycology",
    "fungi",
    "mushroom",
    "mycelium",
    "synthetic biology",
    "protein folding",
    "AlphaFold",
    "large language model",
    "transformer",
    "diffusion model",
    "quantum computing",
    "qubit",
    "CRISPR",
    "gene editing",
    "metagenomics",
    "earth observation",
    "remote sensing",
    "bioreactor",
    "fermentation",
    "LoRa",
    "ESP32",
    "edge computing",
    "nature learning model",
]


class PaperMonitorAgent(BaseAgent):
    """Monitors preprint servers and classifies new papers."""

    def __init__(
        self,
        agent_id: str = "paper-monitor",
        name: str = "Paper Monitor Agent",
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(agent_id=agent_id, name=name, config=config or {})
        self.capabilities = [
            "watch_preprints",
            "classify_paper",
            "summarize_paper",
            "alert_breakthrough",
        ]
        self._watcher = None

    def _get_watcher(self):
        if self._watcher is None:
            from mycosoft_mas.integrations.preprint_watcher_client import PreprintWatcherClient

            self._watcher = PreprintWatcherClient(self.config)
        return self._watcher

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        task_type = task.get("type", "")

        if task_type == "scan_arxiv":
            return await self._scan_arxiv(task)
        elif task_type == "scan_biorxiv":
            return await self._scan_biorxiv(task)
        elif task_type == "classify":
            return await self._classify_paper(task)
        elif task_type == "full_scan":
            return await self._full_scan(task)

        return {"status": "error", "message": f"Unknown task type: {task_type}"}

    async def _scan_arxiv(self, task: Dict[str, Any]) -> Dict[str, Any]:
        watcher = self._get_watcher()
        categories = task.get("categories", ["cs.AI", "cs.LG", "q-bio", "physics.bio-ph"])
        max_results = task.get("max_results", 50)
        results = []
        for cat in categories:
            papers = await watcher.search_arxiv(query=f"cat:{cat}", max_results=max_results)
            results.extend(papers if isinstance(papers, list) else [papers])
        relevant = self._filter_relevant(results)
        return {"status": "success", "total": len(results), "relevant": relevant}

    async def _scan_biorxiv(self, task: Dict[str, Any]) -> Dict[str, Any]:
        watcher = self._get_watcher()
        interval = task.get("interval", "2d")
        server = task.get("server", "biorxiv")
        papers = await watcher.recent_biorxiv(server=server, interval=interval)
        items = papers.get("collection", []) if isinstance(papers, dict) else []
        relevant = self._filter_relevant(items)
        return {"status": "success", "total": len(items), "relevant": relevant}

    async def _full_scan(self, task: Dict[str, Any]) -> Dict[str, Any]:
        arxiv_result = await self._scan_arxiv(task)
        biorxiv_result = await self._scan_biorxiv(task)
        medrxiv = await self._scan_biorxiv({**task, "server": "medrxiv"})
        all_relevant = (
            arxiv_result.get("relevant", [])
            + biorxiv_result.get("relevant", [])
            + medrxiv.get("relevant", [])
        )
        return {
            "status": "success",
            "arxiv_total": arxiv_result.get("total", 0),
            "biorxiv_total": biorxiv_result.get("total", 0),
            "medrxiv_total": medrxiv.get("total", 0),
            "relevant_count": len(all_relevant),
            "relevant": all_relevant[:100],
        }

    async def _classify_paper(self, task: Dict[str, Any]) -> Dict[str, Any]:
        title = task.get("title", "")
        abstract = task.get("abstract", "")
        text = f"{title} {abstract}".lower()
        matches = [d for d in WATCH_DOMAINS if d.lower() in text]
        return {
            "status": "success",
            "title": title,
            "relevant": len(matches) > 0,
            "matched_domains": matches,
            "relevance_score": min(len(matches) / 3.0, 1.0),
        }

    def _filter_relevant(self, papers: List[Any]) -> List[Dict[str, Any]]:
        relevant = []
        for p in papers:
            title = ""
            abstract = ""
            if isinstance(p, dict):
                title = p.get("title", "") or p.get("rel_title", "")
                abstract = p.get("abstract", "") or p.get("rel_abs", "") or p.get("summary", "")
            text = f"{title} {abstract}".lower()
            matches = [d for d in WATCH_DOMAINS if d.lower() in text]
            if matches:
                relevant.append(
                    {
                        "title": title,
                        "matched_domains": matches,
                        "score": min(len(matches) / 3.0, 1.0),
                        "source": p if isinstance(p, dict) else str(p),
                    }
                )
        relevant.sort(key=lambda x: x["score"], reverse=True)
        return relevant
