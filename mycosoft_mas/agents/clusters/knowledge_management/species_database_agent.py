"""
Species Database Agent for Mycology BioAgent System

This agent manages species taxonomy, handles species metadata, coordinates with DNA data,
and maintains species relationships.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import json
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.enums import AgentStatus, TaskType, TaskStatus, TaskPriority

class TaxonomicRank(Enum):
    """Taxonomic ranks in biological classification"""
    DOMAIN = auto()
    KINGDOM = auto()
    PHYLUM = auto()
    CLASS = auto()
    ORDER = auto()
    FAMILY = auto()
    GENUS = auto()
    SPECIES = auto()
    SUBSPECIES = auto()
    VARIETY = auto()
    FORM = auto()

class RelationshipType(Enum):
    """Types of relationships between species"""
    PARENT = auto()
    CHILD = auto()
    SYNONYM = auto()
    HOST = auto()
    PARASITE = auto()
    SYMBIOTIC = auto()
    SIMILAR = auto()

@dataclass
class TaxonomicEntry:
    """Taxonomic information for a species"""
    entry_id: str
    scientific_name: str
    common_names: List[str] = field(default_factory=list)
    rank: TaxonomicRank = TaxonomicRank.SPECIES
    parent_id: Optional[str] = None
    authority: Optional[str] = None
    year_described: Optional[int] = None
    type_specimen: Optional[str] = None
    type_locality: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class SpeciesMetadata:
    """Metadata for a species"""
    species_id: str
    description: Optional[str] = None
    habitat: Optional[str] = None
    distribution: Optional[str] = None
    ecology: Optional[str] = None
    morphology: Optional[str] = None
    uses: List[str] = field(default_factory=list)
    threats: List[str] = field(default_factory=list)
    conservation_status: Optional[str] = None
    references: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class SpeciesRelationship:
    """Relationship between species"""
    relationship_id: str
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    description: Optional[str] = None
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

class SpeciesDatabaseAgent(BaseAgent):
    """Agent for managing species taxonomy and metadata"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.taxonomic_entries: Dict[str, TaxonomicEntry] = {}
        self.species_metadata: Dict[str, SpeciesMetadata] = {}
        self.species_relationships: Dict[str, SpeciesRelationship] = {}
        self.update_queue: asyncio.Queue = asyncio.Queue()
        
        # Create necessary directories
        self.data_dir = Path("data/species")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics
        self.metrics.update({
            "species_entries": 0,
            "metadata_entries": 0,
            "relationships": 0,
            "updates_processed": 0,
            "update_errors": 0
        })
    
    async def initialize(self) -> None:
        """Initialize the agent"""
        await super().initialize()
        await self._load_data()
        self.status = AgentStatus.READY
        self.logger.info("Species Database Agent initialized")
    
    async def stop(self) -> None:
        """Stop the agent"""
        self.status = AgentStatus.STOPPING
        self.logger.info("Stopping Species Database Agent")
        await self._save_data()
        await super().stop()
    
    async def add_taxonomic_entry(
        self,
        scientific_name: str,
        common_names: Optional[List[str]] = None,
        rank: TaxonomicRank = TaxonomicRank.SPECIES,
        parent_id: Optional[str] = None,
        authority: Optional[str] = None,
        year_described: Optional[int] = None,
        type_specimen: Optional[str] = None,
        type_locality: Optional[str] = None
    ) -> str:
        """Add a new taxonomic entry"""
        entry_id = f"tax_{len(self.taxonomic_entries)}"
        
        entry = TaxonomicEntry(
            entry_id=entry_id,
            scientific_name=scientific_name,
            common_names=common_names or [],
            rank=rank,
            parent_id=parent_id,
            authority=authority,
            year_described=year_described,
            type_specimen=type_specimen,
            type_locality=type_locality
        )
        
        self.taxonomic_entries[entry_id] = entry
        await self.update_queue.put({"type": "taxonomic", "data": entry})
        
        self.metrics["species_entries"] += 1
        return entry_id
    
    async def add_species_metadata(
        self,
        species_id: str,
        description: Optional[str] = None,
        habitat: Optional[str] = None,
        distribution: Optional[str] = None,
        ecology: Optional[str] = None,
        morphology: Optional[str] = None,
        uses: Optional[List[str]] = None,
        threats: Optional[List[str]] = None,
        conservation_status: Optional[str] = None,
        references: Optional[List[str]] = None,
        images: Optional[List[str]] = None
    ) -> str:
        """Add metadata for a species"""
        if species_id not in self.taxonomic_entries:
            raise ValueError(f"Species {species_id} does not exist")
        
        metadata = SpeciesMetadata(
            species_id=species_id,
            description=description,
            habitat=habitat,
            distribution=distribution,
            ecology=ecology,
            morphology=morphology,
            uses=uses or [],
            threats=threats or [],
            conservation_status=conservation_status,
            references=references or [],
            images=images or []
        )
        
        self.species_metadata[species_id] = metadata
        await self.update_queue.put({"type": "metadata", "data": metadata})
        
        self.metrics["metadata_entries"] += 1
        return species_id
    
    async def add_species_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        description: Optional[str] = None,
        confidence: float = 1.0
    ) -> str:
        """Add a relationship between species"""
        if source_id not in self.taxonomic_entries or target_id not in self.taxonomic_entries:
            raise ValueError("Source or target species does not exist")
        
        relationship_id = f"rel_{len(self.species_relationships)}"
        
        relationship = SpeciesRelationship(
            relationship_id=relationship_id,
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            description=description,
            confidence=confidence
        )
        
        self.species_relationships[relationship_id] = relationship
        await self.update_queue.put({"type": "relationship", "data": relationship})
        
        self.metrics["relationships"] += 1
        return relationship_id
    
    async def get_taxonomic_entry(self, entry_id: str) -> Optional[TaxonomicEntry]:
        """Get a taxonomic entry by ID"""
        return self.taxonomic_entries.get(entry_id)
    
    async def get_species_metadata(self, species_id: str) -> Optional[SpeciesMetadata]:
        """Get metadata for a species"""
        return self.species_metadata.get(species_id)
    
    async def get_species_relationships(self, species_id: str) -> List[SpeciesRelationship]:
        """Get relationships for a species"""
        return [
            rel for rel in self.species_relationships.values()
            if rel.source_id == species_id or rel.target_id == species_id
        ]
    
    async def search_species(
        self,
        query: str,
        rank: Optional[TaxonomicRank] = None,
        limit: Optional[int] = None
    ) -> List[TaxonomicEntry]:
        """Search for species by name or other criteria"""
        results = []
        
        for entry in self.taxonomic_entries.values():
            if rank and entry.rank != rank:
                continue
            
            if (
                query.lower() in entry.scientific_name.lower() or
                any(query.lower() in name.lower() for name in entry.common_names)
            ):
                results.append(entry)
                
                if limit and len(results) >= limit:
                    break
        
        return results
    
    async def _load_data(self) -> None:
        """Load data from disk"""
        # Load taxonomic entries
        entries_file = self.data_dir / "taxonomic_entries.json"
        if entries_file.exists():
            with open(entries_file, "r") as f:
                entries_data = json.load(f)
                
                for entry_data in entries_data:
                    entry = TaxonomicEntry(
                        entry_id=entry_data["entry_id"],
                        scientific_name=entry_data["scientific_name"],
                        common_names=entry_data["common_names"],
                        rank=TaxonomicRank[entry_data["rank"]],
                        parent_id=entry_data.get("parent_id"),
                        authority=entry_data.get("authority"),
                        year_described=entry_data.get("year_described"),
                        type_specimen=entry_data.get("type_specimen"),
                        type_locality=entry_data.get("type_locality"),
                        created_at=datetime.fromisoformat(entry_data["created_at"]),
                        updated_at=datetime.fromisoformat(entry_data["updated_at"])
                    )
                    
                    self.taxonomic_entries[entry.entry_id] = entry
        
        # Load species metadata
        metadata_file = self.data_dir / "species_metadata.json"
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                metadata_data = json.load(f)
                
                for meta_data in metadata_data:
                    metadata = SpeciesMetadata(
                        species_id=meta_data["species_id"],
                        description=meta_data.get("description"),
                        habitat=meta_data.get("habitat"),
                        distribution=meta_data.get("distribution"),
                        ecology=meta_data.get("ecology"),
                        morphology=meta_data.get("morphology"),
                        uses=meta_data.get("uses", []),
                        threats=meta_data.get("threats", []),
                        conservation_status=meta_data.get("conservation_status"),
                        references=meta_data.get("references", []),
                        images=meta_data.get("images", []),
                        created_at=datetime.fromisoformat(meta_data["created_at"]),
                        updated_at=datetime.fromisoformat(meta_data["updated_at"])
                    )
                    
                    self.species_metadata[metadata.species_id] = metadata
        
        # Load species relationships
        relationships_file = self.data_dir / "species_relationships.json"
        if relationships_file.exists():
            with open(relationships_file, "r") as f:
                relationships_data = json.load(f)
                
                for rel_data in relationships_data:
                    relationship = SpeciesRelationship(
                        relationship_id=rel_data["relationship_id"],
                        source_id=rel_data["source_id"],
                        target_id=rel_data["target_id"],
                        relationship_type=RelationshipType[rel_data["relationship_type"]],
                        description=rel_data.get("description"),
                        confidence=rel_data.get("confidence", 1.0),
                        created_at=datetime.fromisoformat(rel_data["created_at"]),
                        updated_at=datetime.fromisoformat(rel_data["updated_at"])
                    )
                    
                    self.species_relationships[relationship.relationship_id] = relationship
        
        # Update metrics
        self.metrics["species_entries"] = len(self.taxonomic_entries)
        self.metrics["metadata_entries"] = len(self.species_metadata)
        self.metrics["relationships"] = len(self.species_relationships)
    
    async def _save_data(self) -> None:
        """Save data to disk"""
        # Save taxonomic entries
        entries_file = self.data_dir / "taxonomic_entries.json"
        entries_data = []
        
        for entry in self.taxonomic_entries.values():
            entry_data = {
                "entry_id": entry.entry_id,
                "scientific_name": entry.scientific_name,
                "common_names": entry.common_names,
                "rank": entry.rank.name,
                "parent_id": entry.parent_id,
                "authority": entry.authority,
                "year_described": entry.year_described,
                "type_specimen": entry.type_specimen,
                "type_locality": entry.type_locality,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat()
            }
            entries_data.append(entry_data)
        
        with open(entries_file, "w") as f:
            json.dump(entries_data, f, indent=2)
        
        # Save species metadata
        metadata_file = self.data_dir / "species_metadata.json"
        metadata_data = []
        
        for metadata in self.species_metadata.values():
            meta_data = {
                "species_id": metadata.species_id,
                "description": metadata.description,
                "habitat": metadata.habitat,
                "distribution": metadata.distribution,
                "ecology": metadata.ecology,
                "morphology": metadata.morphology,
                "uses": metadata.uses,
                "threats": metadata.threats,
                "conservation_status": metadata.conservation_status,
                "references": metadata.references,
                "images": metadata.images,
                "created_at": metadata.created_at.isoformat(),
                "updated_at": metadata.updated_at.isoformat()
            }
            metadata_data.append(meta_data)
        
        with open(metadata_file, "w") as f:
            json.dump(metadata_data, f, indent=2)
        
        # Save species relationships
        relationships_file = self.data_dir / "species_relationships.json"
        relationships_data = []
        
        for relationship in self.species_relationships.values():
            rel_data = {
                "relationship_id": relationship.relationship_id,
                "source_id": relationship.source_id,
                "target_id": relationship.target_id,
                "relationship_type": relationship.relationship_type.name,
                "description": relationship.description,
                "confidence": relationship.confidence,
                "created_at": relationship.created_at.isoformat(),
                "updated_at": relationship.updated_at.isoformat()
            }
            relationships_data.append(rel_data)
        
        with open(relationships_file, "w") as f:
            json.dump(relationships_data, f, indent=2)
    
    async def _process_update_queue(self) -> None:
        """Process the update queue"""
        while self.status == AgentStatus.RUNNING:
            try:
                # Get next update
                update = await self.update_queue.get()
                
                # Process update
                if update["type"] == "taxonomic":
                    await self._process_taxonomic_update(update["data"])
                elif update["type"] == "metadata":
                    await self._process_metadata_update(update["data"])
                elif update["type"] == "relationship":
                    await self._process_relationship_update(update["data"])
                
                # Update metrics
                self.metrics["updates_processed"] += 1
                
                # Mark task as complete
                self.update_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing update: {str(e)}")
                self.metrics["update_errors"] += 1
                continue
    
    async def _process_taxonomic_update(self, entry: TaxonomicEntry) -> None:
        """Process a taxonomic entry update"""
        # Implementation for taxonomic update
        pass
    
    async def _process_metadata_update(self, metadata: SpeciesMetadata) -> None:
        """Process a metadata update"""
        # Implementation for metadata update
        pass
    
    async def _process_relationship_update(self, relationship: SpeciesRelationship) -> None:
        """Process a relationship update"""
        # Implementation for relationship update
        pass 