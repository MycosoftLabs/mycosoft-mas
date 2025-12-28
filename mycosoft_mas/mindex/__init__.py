"""
MINDEX - Mycological Index Data System

Central knowledge base for fungal information, integrating data from:
- iNaturalist (observations and species data)
- FungiDB (genomic and molecular data)
- MycoBank (taxonomic nomenclature)
- GBIF (global biodiversity information)

The MINDEX system continuously organizes, silos, and compartmentalizes
data to feed all MYCOSOFT systems with instant local access.
"""

from .database import MINDEXDatabase
from .manager import MINDEXManager

__all__ = ["MINDEXDatabase", "MINDEXManager"]
