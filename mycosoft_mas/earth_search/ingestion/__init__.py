"""
Earth Search Ingestion — pipeline to scrape external data into local MINDEX + Supabase.

Every search result can be optionally ingested into local storage for:
1. Low-latency re-query (MINDEX Postgres + Qdrant vectors)
2. NLM training data (JSONL sink)
3. Supabase persistence (cloud backup + web dashboard access)

Created: March 15, 2026
"""

from mycosoft_mas.earth_search.ingestion.pipeline import IngestionPipeline

__all__ = ["IngestionPipeline"]
