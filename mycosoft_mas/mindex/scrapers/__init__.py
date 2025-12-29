"""
MINDEX Scrapers

Data scrapers for various fungal and mycological databases:
- iNaturalist: Species observations and citizen science data
- FungiDB: Genomic and molecular biology data
- MycoBank: Taxonomic nomenclature and classification
- GBIF: Global biodiversity occurrence data
- GenBank: NCBI genomic data and sequences
- MushroomWorld: Comprehensive mushroom database
"""

from .inaturalist import INaturalistScraper
from .fungidb import FungiDBScraper
from .mycobank import MycoBankScraper
from .gbif import GBIFScraper
from .genbank import GenBankScraper
from .mushroomworld import MushroomWorldScraper
from .base import BaseScraper

__all__ = [
    "BaseScraper",
    "INaturalistScraper",
    "FungiDBScraper",
    "MycoBankScraper",
    "GBIFScraper",
    "GenBankScraper",
    "MushroomWorldScraper",
]
