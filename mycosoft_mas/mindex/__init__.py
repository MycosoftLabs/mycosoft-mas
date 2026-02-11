"""
MINDEX - Mycological Index Data System

Central knowledge base for fungal information with taxonomic reconciliation.
"""

from .database import MINDEXDatabase

# Optional imports: some MINDEX scrapers require heavy deps (e.g. bs4) that are
# not installed in all environments (including CI/unit-test runs). Keep package
# import cheap so submodules like `memory_bridge` can be used without extras.
try:  # pragma: no cover
    from .manager import MINDEXManager
except Exception:  # pragma: no cover
    MINDEXManager = None  # type: ignore[assignment]

try:  # pragma: no cover
    from .reconciliation import TaxonomicReconciler, TaxonomicMatch, LicenseInfo
except Exception:  # pragma: no cover
    TaxonomicReconciler = None  # type: ignore[assignment]
    TaxonomicMatch = None  # type: ignore[assignment]
    LicenseInfo = None  # type: ignore[assignment]

try:  # pragma: no cover
    from .reconciliation_integration import ReconciledScraper, reconcile_scraper_output
except Exception:  # pragma: no cover
    ReconciledScraper = None  # type: ignore[assignment]
    reconcile_scraper_output = None  # type: ignore[assignment]

__all__ = [
    "MINDEXDatabase",
    "MINDEXManager",
    "TaxonomicReconciler",
    "TaxonomicMatch",
    "LicenseInfo",
    "ReconciledScraper",
    "reconcile_scraper_output",
]
