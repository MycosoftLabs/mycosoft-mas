import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import aiohttp
from pathlib import Path
import networkx as nx
from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import RDFS, XSD, OWL, DCTERMS, SKOS
from SPARQLWrapper import SPARQLWrapper, JSON

# Define namespaces
FUNGI = Namespace("http://mycosoft.org/fungi/")
PLANTS = Namespace("http://mycosoft.org/plants/")
ANIMALS = Namespace("http://mycosoft.org/animals/")
BACTERIA = Namespace("http://mycosoft.org/bacteria/")
VIRUSES = Namespace("http://mycosoft.org/viruses/")
RELATIONS = Namespace("http://mycosoft.org/relations/")

class FungalKnowledgeGraph:
    """A knowledge graph for fungal species and their relationships."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the fungal knowledge graph."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.graph = Graph()
        self.oxigraph_url = config.get("oxigraph_url", "http://localhost:7878")
        self.data_dir = Path(config.get("data_dir", "data/fungal_knowledge"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize SPARQL endpoint
        self.sparql = SPARQLWrapper(f"{self.oxigraph_url}/sparql")
        self.sparql.setReturnFormat(JSON)
        
        # Initialize namespaces
        self.graph.bind("fungi", FUNGI)
        self.graph.bind("plants", PLANTS)
        self.graph.bind("animals", ANIMALS)
        self.graph.bind("bacteria", BACTERIA)
        self.graph.bind("viruses", VIRUSES)
        self.graph.bind("relations", RELATIONS)
        
        # Initialize networkx graph for fast traversal
        self.nx_graph = nx.DiGraph()
        
        # Initialize retry settings
        self.max_retries = 3
        self.retry_delay = 5
        
    async def initialize(self) -> None:
        """Initialize the knowledge graph and load existing data."""
        try:
            self.logger.info("Initializing Fungal Knowledge Graph...")
            
            # Load existing data
            await self._load_existing_data()
            
            # Connect to Oxigraph
            await self._connect_to_oxigraph()
            
            # Load initial data
            await self._load_initial_data()
            
            # Start background tasks
            self.background_tasks = [
                asyncio.create_task(self._sync_with_oxigraph()),
                asyncio.create_task(self._update_networkx_graph())
            ]
            
            self.logger.info("Fungal Knowledge Graph initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Fungal Knowledge Graph: {str(e)}")
            raise
    
    async def _load_initial_data(self) -> None:
        """Load initial data from configuration."""
        try:
            initial_data = self.config.get("initial_data", {})
            for species in initial_data.get("fungal_species", []):
                await self.add_fungal_species(species)
        except Exception as e:
            self.logger.error(f"Error loading initial data: {str(e)}")
            raise
    
    async def _connect_to_oxigraph(self) -> None:
        """Connect to Oxigraph server."""
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    response = await session.get(f"{self.oxigraph_url}/status")
                    if response.status == 200:
                        self.logger.info("Connected to Oxigraph server")
                        return
                raise Exception("Failed to connect to Oxigraph server")
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                self.logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
                await asyncio.sleep(self.retry_delay)
    
    async def add_fungal_species(self, species_data: Dict) -> None:
        """Add a fungal species to the knowledge graph."""
        try:
            species_uri = FUNGI[species_data["id"]]
            
            # Add species information
            self.graph.add((species_uri, RDF.type, FUNGI.FungalSpecies))
            self.graph.add((species_uri, RDFS.label, Literal(species_data["name"])))
            self.graph.add((species_uri, FUNGI.scientificName, Literal(species_data["scientific_name"])))
            self.graph.add((species_uri, FUNGI.taxonomy, Literal(species_data["taxonomy"])))
            
            # Add relationships
            for relationship in species_data.get("relationships", []):
                target_uri = self._get_entity_uri(relationship["target_type"], relationship["target_id"])
                rel_uri = RELATIONS[relationship["type"]]
                self.graph.add((species_uri, rel_uri, target_uri))
                self.graph.add((target_uri, RELATIONS[f"is_{relationship['type']}_by"], species_uri))
            
            # Save to file
            await self._save_to_file(species_uri)
            
            # Sync with Oxigraph
            await self._sync_with_oxigraph()
            
        except Exception as e:
            self.logger.error(f"Error adding fungal species: {str(e)}")
            raise
    
    async def query_relationships(self, species_id: str, relationship_type: Optional[str] = None) -> List[Dict]:
        """Query relationships for a fungal species using SPARQL."""
        try:
            species_uri = FUNGI[species_id]
            query = f"""
            PREFIX fungi: <{FUNGI}>
            PREFIX relations: <{RELATIONS}>
            
            SELECT ?target ?type ?relationship
            WHERE {{
                <{species_uri}> ?relationship ?target .
                ?target a ?type .
                FILTER(STRSTARTS(STR(?relationship), STR(relations:)))
            }}
            """
            
            if relationship_type:
                query += f"FILTER(?relationship = relations:{relationship_type})"
            
            self.sparql.setQuery(query)
            results = self.sparql.query().convert()
            
            return [
                {
                    "target_id": result["target"]["value"].split("/")[-1],
                    "target_type": result["type"]["value"].split("/")[-1],
                    "relationship_type": result["relationship"]["value"].split("/")[-1]
                }
                for result in results["results"]["bindings"]
            ]
            
        except Exception as e:
            self.logger.error(f"Error querying relationships: {str(e)}")
            raise
    
    async def _sync_with_oxigraph(self) -> None:
        """Sync the local graph with Oxigraph server."""
        while True:
            try:
                # Convert graph to turtle format
                turtle_data = self.graph.serialize(format="turtle")
                
                # Send to Oxigraph
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        f"{self.oxigraph_url}/data",
                        data=turtle_data,
                        headers={"Content-Type": "text/turtle"}
                    )
                
                await asyncio.sleep(self.config.get("sync_interval", 60))
                
            except Exception as e:
                self.logger.error(f"Error syncing with Oxigraph: {str(e)}")
                await asyncio.sleep(self.config.get("retry_delay", 300))
    
    async def _update_networkx_graph(self) -> None:
        """Update the networkx graph for fast traversal."""
        while True:
            try:
                self.nx_graph.clear()
                
                # Query all relationships
                query = """
                PREFIX relations: <http://mycosoft.org/relations/>
                
                SELECT ?source ?target ?relationship
                WHERE {
                    ?source ?relationship ?target .
                    FILTER(STRSTARTS(STR(?relationship), STR(relations:)))
                }
                """
                
                self.sparql.setQuery(query)
                results = self.sparql.query().convert()
                
                # Add nodes and edges
                for result in results["results"]["bindings"]:
                    source = result["source"]["value"]
                    target = result["target"]["value"]
                    relationship = result["relationship"]["value"]
                    self.nx_graph.add_edge(source, target, relationship=relationship)
                
                await asyncio.sleep(self.config.get("update_interval", 300))
                
            except Exception as e:
                self.logger.error(f"Error updating networkx graph: {str(e)}")
                await asyncio.sleep(self.config.get("retry_delay", 300))
    
    def _get_entity_uri(self, entity_type: str, entity_id: str) -> URIRef:
        """Get the URI for an entity based on its type and ID."""
        namespace_map = {
            "fungi": FUNGI,
            "plants": PLANTS,
            "animals": ANIMALS,
            "bacteria": BACTERIA,
            "viruses": VIRUSES
        }
        return namespace_map[entity_type][entity_id]
    
    async def _save_to_file(self, entity_uri: URIRef) -> None:
        """Save an entity's data to a file."""
        try:
            # Get all triples for the entity
            triples = list(self.graph.triples((entity_uri, None, None)))
            
            # Create a new graph for this entity
            entity_graph = Graph()
            for s, p, o in triples:
                entity_graph.add((s, p, o))
            
            # Save to file
            file_path = self.data_dir / f"{str(entity_uri).split('/')[-1]}.ttl"
            entity_graph.serialize(destination=str(file_path), format="turtle")
            
        except Exception as e:
            self.logger.error(f"Error saving to file: {str(e)}")
            raise
    
    async def stop(self) -> None:
        """Stop the knowledge graph and clean up resources."""
        try:
            # Cancel background tasks
            for task in self.background_tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Save final state
            self.graph.serialize(
                destination=str(self.data_dir / "final_state.ttl"),
                format="turtle"
            )
            
        except Exception as e:
            self.logger.error(f"Error stopping knowledge graph: {str(e)}")
            raise 