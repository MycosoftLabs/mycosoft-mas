from datetime import datetime, timedelta
import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, Set
from .base_agent import BaseAgent
from dataclasses import dataclass
from enum import Enum
import json
import networkx as nx
import pandas as pd
import numpy as np
from pathlib import Path
import uuid
import os
import re
from collections import defaultdict
import aiohttp
import aiofiles

try:
    import spacy
except ImportError:  # pragma: no cover - optional dependency
    spacy = None  # type: ignore

from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import RDFS, XSD, OWL, DCTERMS, SKOS

try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:  # pragma: no cover - optional dependency
    SentenceTransformer = None  # type: ignore
    util = None  # type: ignore

class KnowledgeType(Enum):
    SPECIES = "species"
    GENUS = "genus"
    FAMILY = "family"
    COMPOUND = "compound"
    PROPERTY = "property"
    RESEARCH = "research"
    EXPERIMENT = "experiment"
    CULTIVATION = "cultivation"
    APPLICATION = "application"
    PATENT = "patent"

class RelationType(Enum):
    IS_A = "is_a"
    PART_OF = "part_of"
    HAS_PROPERTY = "has_property"
    CONTAINS = "contains"
    PRODUCES = "produces"
    INTERACTS_WITH = "interacts_with"
    STUDIED_IN = "studied_in"
    CITED_BY = "cited_by"
    USED_IN = "used_in"
    PATENTED_BY = "patented_by"

@dataclass
class KnowledgeNode:
    id: str
    type: KnowledgeType
    name: str
    description: str
    metadata: Dict
    sources: List[str]
    created_at: datetime
    updated_at: datetime

@dataclass
class KnowledgeRelation:
    id: str
    source_id: str
    target_id: str
    type: RelationType
    metadata: Dict
    confidence: float
    sources: List[str]
    created_at: datetime
    updated_at: datetime

class MycologyKnowledgeAgent(BaseAgent):
    def __init__(self, agent_id: str, name: str, config: dict):
        super().__init__(agent_id, name, config)
        
        # Initialize knowledge graph
        self.knowledge_graph = nx.DiGraph()
        self.rdf_graph = Graph()
        
        # Initialize namespaces
        self.myco_ns = Namespace("http://mycosoft.ai/ontology/")
        self.rdf_graph.bind("myco", self.myco_ns)
        
        # Initialize data structures
        self.nodes = {}
        self.relations = {}
        self.taxonomies = {}
        self.compounds = {}
        self.research_data = {}
        self.experiments = {}
        self.applications = {}
        self.patents = {}
        
        # Initialize directories
        self.data_directory = Path(config.get('data_directory', 'data/knowledge'))
        self.data_directory.mkdir(parents=True, exist_ok=True)
        self.output_directory = Path(config.get('output_directory', 'output/knowledge'))
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize queues
        self.update_queue = asyncio.Queue()
        self.query_queue = asyncio.Queue()
        self.notification_queue = asyncio.Queue()
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Initialize semantic model lazily in case sentence-transformers is not installed
        if SentenceTransformer:
            self.semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            self.semantic_model = None
            self.logger.warning(
                "sentence-transformers not available; semantic features are disabled"
            )
        
    async def initialize(self, integration_service):
        """Initialize the Mycology Knowledge agent."""
        await super().initialize(integration_service)
        await self._load_knowledge_base()
        await self._initialize_taxonomies()
        await self._start_background_tasks()
        self.logger.info(f"Mycology Knowledge Agent {self.name} initialized successfully")

    async def add_knowledge_node(self, node_data: Dict) -> Dict:
        """Add a new node to the knowledge graph."""
        try:
            node_id = node_data.get('id', f"node_{uuid.uuid4().hex[:8]}")
            
            if node_id in self.nodes:
                return {"success": False, "message": "Node ID already exists"}
                
            node = KnowledgeNode(
                id=node_id,
                type=KnowledgeType[node_data['type'].upper()],
                name=node_data['name'],
                description=node_data['description'],
                metadata=node_data.get('metadata', {}),
                sources=node_data.get('sources', []),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Validate node
            validation_result = await self._validate_node(node)
            if not validation_result['success']:
                return validation_result
            
            # Add to knowledge graph
            self.knowledge_graph.add_node(
                node_id,
                name=node.name,
                type=node.type.value,
                description=node.description,
                properties=node.metadata,
                references=node.sources,
                created_at=node.created_at,
                updated_at=node.updated_at
            )
            
            # Add to RDF graph
            await self._add_node_to_rdf(node)
            
            # Add to nodes dictionary
            self.nodes[node_id] = node
            
            # Update search index
            await self._update_search_index(node)
            
            # Save node
            node_dir = self.data_directory / 'nodes'
            node_dir.mkdir(exist_ok=True)
            
            node_file = node_dir / f"{node_id}.json"
            async with aiofiles.open(node_file, 'w') as f:
                await f.write(json.dumps(self._node_to_dict(node), default=str))
            
            # Notify about new knowledge
            await self.notification_queue.put({
                'type': 'knowledge_added',
                'node_id': node_id,
                'node_name': node.name,
                'node_type': node.type.value,
                'timestamp': datetime.now()
            })
            
            return {
                "success": True,
                "node_id": node_id,
                "message": "Knowledge node added successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to add knowledge node: {str(e)}")
            return {"success": False, "message": str(e)}

    async def add_knowledge_relation(self, relation_data: Dict) -> Dict:
        """Add a new relation to the knowledge graph."""
        try:
            relation_id = relation_data.get('id', f"rel_{uuid.uuid4().hex[:8]}")
            
            if relation_id in self.relations:
                return {"success": False, "message": "Relation ID already exists"}
                
            # Validate source and target nodes
            source_id = relation_data['source_id']
            target_id = relation_data['target_id']
            
            if source_id not in self.nodes:
                return {"success": False, "message": f"Source node {source_id} not found"}
                
            if target_id not in self.nodes:
                return {"success": False, "message": f"Target node {target_id} not found"}
                
            relation = KnowledgeRelation(
                id=relation_id,
                source_id=source_id,
                target_id=target_id,
                type=RelationType[relation_data['type'].upper()],
                metadata=relation_data.get('metadata', {}),
                confidence=float(relation_data.get('confidence', 0.8)),
                sources=relation_data.get('sources', []),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Validate relation
            validation_result = await self._validate_relation(relation)
            if not validation_result['success']:
                return validation_result
            
            # Add to knowledge graph
            self.knowledge_graph.add_edge(
                source_id,
                target_id,
                id=relation_id,
                type=relation.type.value,
                properties=relation.metadata,
                references=relation.sources,
                confidence=relation.confidence,
                created_at=relation.created_at,
                updated_at=relation.updated_at
            )
            
            # Add to RDF graph
            await self._add_relation_to_rdf(relation)
            
            # Add to relations dictionary
            self.relations[relation_id] = relation
            
            # Save relation
            relation_dir = self.data_directory / 'relations'
            relation_dir.mkdir(exist_ok=True)
            
            relation_file = relation_dir / f"{relation_id}.json"
            async with aiofiles.open(relation_file, 'w') as f:
                await f.write(json.dumps(self._relation_to_dict(relation), default=str))
            
            return {
                "success": True,
                "relation_id": relation_id,
                "message": "Knowledge relation added successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to add knowledge relation: {str(e)}")
            return {"success": False, "message": str(e)}

    async def query_knowledge(self, query: Dict) -> Dict:
        """Query the knowledge graph based on various criteria."""
        try:
            query_type = query.get('type', 'node')
            
            if query_type == 'node':
                results = await self._query_nodes(query)
            elif query_type == 'relation':
                results = await self._query_relations(query)
            elif query_type == 'path':
                results = await self._query_paths(query)
            elif query_type == 'semantic':
                results = await self._semantic_search(query)
            else:
                return {"success": False, "message": f"Unknown query type: {query_type}"}
            
            return {
                "success": True,
                "query_type": query_type,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to query knowledge: {str(e)}")
            return {"success": False, "message": str(e)}

    async def update_knowledge(self, update_data: Dict) -> Dict:
        """Update existing knowledge in the graph."""
        try:
            update_type = update_data.get('type', 'node')
            entity_id = update_data.get('id')
            
            if not entity_id:
                return {"success": False, "message": "Entity ID is required"}
                
            if update_type == 'node':
                if entity_id not in self.nodes:
                    return {"success": False, "message": f"Node {entity_id} not found"}
                    
                node = self.nodes[entity_id]
                updated_node = await self._update_node(node, update_data)
                
                # Update knowledge graph
                self.knowledge_graph.nodes[entity_id].update({
                    'name': updated_node.name,
                    'description': updated_node.description,
                    'properties': updated_node.metadata,
                    'references': updated_node.sources,
                    'updated_at': updated_node.updated_at
                })
                
                # Update RDF graph
                await self._update_node_in_rdf(updated_node)
                
                # Update nodes dictionary
                self.nodes[entity_id] = updated_node
                
                # Update search index
                await self._update_search_index(updated_node)
                
                # Save updated node
                node_dir = self.data_directory / 'nodes'
                node_file = node_dir / f"{entity_id}.json"
                async with aiofiles.open(node_file, 'w') as f:
                    await f.write(json.dumps(self._node_to_dict(updated_node), default=str))
                
                return {
                    "success": True,
                    "node_id": entity_id,
                    "message": "Knowledge node updated successfully"
                }
                
            elif update_type == 'relation':
                if entity_id not in self.relations:
                    return {"success": False, "message": f"Relation {entity_id} not found"}
                    
                relation = self.relations[entity_id]
                updated_relation = await self._update_relation(relation, update_data)
                
                # Update knowledge graph
                source_id = updated_relation.source_id
                target_id = updated_relation.target_id
                
                # Remove old edge
                self.knowledge_graph.remove_edge(source_id, target_id)
                
                # Add updated edge
                self.knowledge_graph.add_edge(
                    source_id,
                    target_id,
                    id=updated_relation.id,
                    type=updated_relation.type.value,
                    properties=updated_relation.metadata,
                    references=updated_relation.sources,
                    confidence=updated_relation.confidence,
                    created_at=updated_relation.created_at,
                    updated_at=updated_relation.updated_at
                )
                
                # Update RDF graph
                await self._update_relation_in_rdf(updated_relation)
                
                # Update relations dictionary
                self.relations[entity_id] = updated_relation
                
                # Save updated relation
                relation_dir = self.data_directory / 'relations'
                relation_file = relation_dir / f"{entity_id}.json"
                async with aiofiles.open(relation_file, 'w') as f:
                    await f.write(json.dumps(self._relation_to_dict(updated_relation), default=str))
                
                return {
                    "success": True,
                    "relation_id": entity_id,
                    "message": "Knowledge relation updated successfully"
                }
                
            else:
                return {"success": False, "message": f"Unknown update type: {update_type}"}
            
        except Exception as e:
            self.logger.error(f"Failed to update knowledge: {str(e)}")
            return {"success": False, "message": str(e)}

    async def import_knowledge(self, import_data: Dict) -> Dict:
        """Import knowledge from external sources."""
        try:
            source_type = import_data.get('source_type', 'file')
            source_path = import_data.get('source_path')
            format_type = import_data.get('format', 'json')
            
            if not source_path:
                return {"success": False, "message": "Source path is required"}
                
            if source_type == 'file':
                if not os.path.exists(source_path):
                    return {"success": False, "message": f"File {source_path} not found"}
                    
                if format_type == 'json':
                    async with aiofiles.open(source_path, 'r') as f:
                        content = await f.read()
                        data = json.loads(content)
                        
                elif format_type == 'csv':
                    data = pd.read_csv(source_path).to_dict('records')
                    
                elif format_type == 'rdf':
                    g = Graph()
                    g.parse(source_path, format='turtle')
                    data = await self._convert_rdf_to_dict(g)
                    
                else:
                    return {"success": False, "message": f"Unsupported format: {format_type}"}
                    
            elif source_type == 'api':
                async with aiohttp.ClientSession() as session:
                    async with session.get(source_path) as response:
                        if response.status != 200:
                            return {"success": False, "message": f"API request failed with status {response.status}"}
                            
                        data = await response.json()
                        
            else:
                return {"success": False, "message": f"Unsupported source type: {source_type}"}
            
            # Process imported data
            import_results = await self._process_imported_data(data, import_data.get('mapping', {}))
            
            return {
                "success": True,
                "imported_nodes": import_results['nodes'],
                "imported_relations": import_results['relations'],
                "message": f"Knowledge imported successfully from {source_path}"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to import knowledge: {str(e)}")
            return {"success": False, "message": str(e)}

    async def export_knowledge(self, export_data: Dict) -> Dict:
        """Export knowledge to various formats."""
        try:
            export_type = export_data.get('type', 'all')
            format_type = export_data.get('format', 'json')
            output_path = export_data.get('output_path')
            
            if not output_path:
                return {"success": False, "message": "Output path is required"}
                
            # Prepare data based on export type
            if export_type == 'all':
                data = {
                    'nodes': [self._node_to_dict(node) for node in self.nodes.values()],
                    'relations': [self._relation_to_dict(rel) for rel in self.relations.values()]
                }
                
            elif export_type == 'nodes':
                data = {
                    'nodes': [self._node_to_dict(node) for node in self.nodes.values()]
                }
                
            elif export_type == 'relations':
                data = {
                    'relations': [self._relation_to_dict(rel) for rel in self.relations.values()]
                }
                
            elif export_type == 'subgraph':
                node_ids = export_data.get('node_ids', [])
                if not node_ids:
                    return {"success": False, "message": "Node IDs are required for subgraph export"}
                    
                subgraph = self.knowledge_graph.subgraph(node_ids)
                data = {
                    'nodes': [self._node_to_dict(self.nodes[node_id]) for node_id in subgraph.nodes()],
                    'relations': [self._relation_to_dict(self.relations[rel_id]) for rel_id in self.relations 
                                if self.relations[rel_id].source_id in node_ids and 
                                self.relations[rel_id].target_id in node_ids]
                }
                
            else:
                return {"success": False, "message": f"Unknown export type: {export_type}"}
            
            # Export data based on format
            if format_type == 'json':
                async with aiofiles.open(output_path, 'w') as f:
                    await f.write(json.dumps(data, default=str))
                    
            elif format_type == 'csv':
                if 'nodes' in data:
                    pd.DataFrame(data['nodes']).to_csv(f"{output_path}_nodes.csv", index=False)
                if 'relations' in data:
                    pd.DataFrame(data['relations']).to_csv(f"{output_path}_relations.csv", index=False)
                    
            elif format_type == 'rdf':
                g = Graph()
                for prefix, namespace in self.namespaces.items():
                    g.bind(prefix, namespace)
                    
                if 'nodes' in data:
                    for node in data['nodes']:
                        await self._add_node_to_rdf_dict(g, node)
                        
                if 'relations' in data:
                    for relation in data['relations']:
                        await self._add_relation_to_rdf_dict(g, relation)
                        
                g.serialize(destination=output_path, format='turtle')
                
            else:
                return {"success": False, "message": f"Unsupported format: {format_type}"}
            
            return {
                "success": True,
                "export_type": export_type,
                "format": format_type,
                "output_path": output_path,
                "message": f"Knowledge exported successfully to {output_path}"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to export knowledge: {str(e)}")
            return {"success": False, "message": str(e)}

    async def generate_insights(self, query: Dict) -> Dict:
        """Generate insights from the knowledge graph."""
        try:
            insight_type = query.get('type', 'general')
            
            if insight_type == 'general':
                insights = await self._generate_general_insights()
            elif insight_type == 'taxonomy':
                insights = await self._generate_taxonomy_insights()
            elif insight_type == 'physiology':
                insights = await self._generate_physiology_insights()
            elif insight_type == 'ecology':
                insights = await self._generate_ecology_insights()
            elif insight_type == 'applications':
                insights = await self._generate_applications_insights()
            elif insight_type == 'research_gaps':
                insights = await self._identify_research_gaps()
            else:
                return {"success": False, "message": f"Unknown insight type: {insight_type}"}
            
            return {
                "success": True,
                "insight_type": insight_type,
                "insights": insights,
                "count": len(insights),
                "message": f"{insight_type.capitalize()} insights generated successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate insights: {str(e)}")
            return {"success": False, "message": str(e)}

    async def _start_background_tasks(self):
        """Start background tasks for the agent."""
        try:
            # Start existing background tasks
            await super()._start_background_tasks()
            
            # Start source discovery task
            asyncio.create_task(self._periodic_source_discovery())
            
            self.logger.info("Started background tasks for Mycology Knowledge Agent")
            
        except Exception as e:
            self.logger.error(f"Error starting background tasks: {str(e)}")

    async def _monitor_knowledge_updates(self):
        """Monitor for knowledge updates and inconsistencies."""
        while True:
            try:
                # Check for inconsistencies
                inconsistencies = await self._check_knowledge_inconsistencies()
                if inconsistencies:
                    await self.notification_queue.put({
                        'type': 'knowledge_inconsistency',
                        'inconsistencies': inconsistencies,
                        'timestamp': datetime.now()
                    })
                    
                # Check for outdated knowledge
                outdated = await self._check_outdated_knowledge()
                if outdated:
                    await self.update_queue.put({
                        'type': 'outdated_knowledge',
                        'items': outdated
                    })
                    
                await asyncio.sleep(3600)  # Check every hour
            except Exception as e:
                self.logger.error(f"Error in knowledge monitoring: {str(e)}")
                await asyncio.sleep(300)  # Retry after 5 minutes

    async def _process_update_queue(self):
        """Process updates in the queue."""
        while True:
            update_item = await self.update_queue.get()
            try:
                if update_item['type'] == 'outdated_knowledge':
                    await self._update_outdated_knowledge(update_item['items'])
                elif update_item['type'] == 'new_knowledge':
                    await self._process_new_knowledge(update_item['data'])
                elif update_item['type'] == 'knowledge_correction':
                    await self._apply_knowledge_correction(update_item['correction'])
            except Exception as e:
                self.logger.error(f"Failed to process update: {str(e)}")
            finally:
                self.update_queue.task_done()

    async def _process_notifications(self):
        """Process notifications in the queue."""
        while True:
            try:
                notification = await self.notification_queue.get()
                # Process notification
                self.logger.info(f"Processing notification: {notification}")
            except Exception as e:
                self.logger.error(f"Error processing notification: {str(e)}")
            await asyncio.sleep(1)

    async def _backup_knowledge_base(self):
        """Periodically backup the knowledge base."""
        while True:
            try:
                # Implementation for knowledge base backup
                await asyncio.sleep(86400)  # Backup once per day
            except Exception as e:
                self.logger.error(f"Failed to backup knowledge base: {str(e)}")
                await asyncio.sleep(3600)  # Retry after an hour

    def _node_to_dict(self, node: KnowledgeNode) -> Dict:
        """Convert KnowledgeNode object to dictionary for JSON serialization."""
        return {
            'id': node.id,
            'name': node.name,
            'type': node.type.value,
            'description': node.description,
            'properties': node.metadata,
            'references': node.sources,
            'created_at': node.created_at.isoformat(),
            'updated_at': node.updated_at.isoformat()
        }

    def _relation_to_dict(self, relation: KnowledgeRelation) -> Dict:
        """Convert KnowledgeRelation object to dictionary for JSON serialization."""
        return {
            'id': relation.id,
            'source_id': relation.source_id,
            'target_id': relation.target_id,
            'type': relation.type.value,
            'properties': relation.metadata,
            'references': relation.sources,
            'confidence': relation.confidence,
            'created_at': relation.created_at.isoformat(),
            'updated_at': relation.updated_at.isoformat()
        }

    async def _query_nodes(self, query: Dict) -> List[Dict]:
        """Query nodes based on specified criteria."""
        try:
            node_type = query.get('node_type')
            properties = query.get('properties', {})
            keywords = query.get('keywords', [])
            limit = query.get('limit', 100)
            
            results = []
            for node_id, node in self.nodes.items():
                # Filter by type if specified
                if node_type and node.type != KnowledgeType[node_type.upper()]:
                    continue
                    
                # Filter by properties
                if properties:
                    match = True
                    for key, value in properties.items():
                        if key not in node.metadata or node.metadata[key] != value:
                            match = False
                            break
                    if not match:
                        continue
                        
                # Filter by keywords
                if keywords:
                    text = f"{node.name} {node.description}"
                    if not any(keyword.lower() in text.lower() for keyword in keywords):
                        continue
                        
                results.append(self._node_to_dict(node))
                if len(results) >= limit:
                    break
                    
            return results
            
        except Exception as e:
            self.logger.error(f"Error in node query: {str(e)}")
            return []

    async def _query_relations(self, query: Dict) -> List[Dict]:
        """Query relations based on specified criteria."""
        try:
            relation_type = query.get('relation_type')
            source_id = query.get('source_id')
            target_id = query.get('target_id')
            min_confidence = float(query.get('min_confidence', 0.0))
            limit = query.get('limit', 100)
            
            results = []
            for relation_id, relation in self.relations.items():
                # Filter by type if specified
                if relation_type and relation.type != RelationType[relation_type.upper()]:
                    continue
                    
                # Filter by source/target
                if source_id and relation.source_id != source_id:
                    continue
                if target_id and relation.target_id != target_id:
                    continue
                    
                # Filter by confidence
                if relation.confidence < min_confidence:
                    continue
                    
                results.append(self._relation_to_dict(relation))
                if len(results) >= limit:
                    break
                    
            return results
            
        except Exception as e:
            self.logger.error(f"Error in relation query: {str(e)}")
            return []

    async def _query_paths(self, query: Dict) -> List[Dict]:
        """Find paths between nodes in the knowledge graph."""
        try:
            source_id = query.get('source_id')
            target_id = query.get('target_id')
            max_length = query.get('max_length', 5)
            relation_types = query.get('relation_types', [])
            
            if not source_id or not target_id:
                return []
                
            # Convert relation types to enums
            if relation_types:
                relation_types = [RelationType[rt.upper()] for rt in relation_types]
            
            # Find all simple paths
            paths = []
            for path in nx.all_simple_paths(self.knowledge_graph, source_id, target_id, cutoff=max_length):
                path_data = []
                for i in range(len(path) - 1):
                    node1, node2 = path[i], path[i + 1]
                    edge_data = self.knowledge_graph.get_edge_data(node1, node2)
                    
                    # Filter by relation type if specified
                    if relation_types and RelationType[edge_data['type'].upper()] not in relation_types:
                        continue
                        
                    path_data.append({
                        'source': self._node_to_dict(self.nodes[node1]),
                        'target': self._node_to_dict(self.nodes[node2]),
                        'relation': edge_data
                    })
                    
                if path_data:  # Only add if path meets relation type criteria
                    paths.append(path_data)
                    
            return paths
            
        except Exception as e:
            self.logger.error(f"Error in path query: {str(e)}")
            return []

    async def _semantic_search(self, query: str, node_type: str = None, threshold: float = 0.5) -> List[Dict]:
        """Perform semantic search over the knowledge graph."""
        try:
            if not self.semantic_model:
                self.logger.warning("Semantic search requested but sentence-transformers is not installed")
                return []

            # Encode the query
            query_embedding = self.semantic_model.encode(query, convert_to_tensor=True)
            
            # Get all nodes of the specified type
            nodes = [node for node in self.knowledge_graph.nodes(data=True) 
                    if node_type is None or node[1].get('type') == node_type]
            
            # Encode all node texts
            node_texts = [node[1].get('text', '') for node in nodes]
            node_embeddings = self.semantic_model.encode(node_texts, convert_to_tensor=True)
            
            # Calculate similarities
            similarities = util.pytorch_cos_sim(query_embedding, node_embeddings)[0]
            
            # Filter and sort results
            results = []
            for i, (node, similarity) in enumerate(zip(nodes, similarities)):
                if similarity > threshold:
                    results.append({
                        'node': node[0],
                        'type': node[1].get('type'),
                        'text': node[1].get('text', ''),
                        'similarity': float(similarity)
                    })
            
            # Sort by similarity score
            results.sort(key=lambda x: x['similarity'], reverse=True)
            return results
            
        except Exception as e:
            self.logger.error(f"Error in semantic search: {str(e)}")
            return []

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts using sentence transformers."""
        try:
            if not self.semantic_model:
                self.logger.warning(
                    "Semantic similarity requested but sentence-transformers is not installed"
                )
                return 0.0

            # Encode both texts
            embeddings = self.semantic_model.encode([text1, text2], convert_to_tensor=True)
            
            # Calculate cosine similarity
            similarity = util.pytorch_cos_sim(embeddings[0], embeddings[1])[0][0]
            
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Error calculating semantic similarity: {str(e)}")
            return 0.0

    async def _validate_node(self, node: KnowledgeNode) -> Dict:
        """Validate a knowledge node."""
        try:
            # Check required fields
            if not node.name or not node.description:
                return {"success": False, "message": "Name and description are required"}
                
            # Validate metadata
            if not isinstance(node.metadata, dict):
                return {"success": False, "message": "Metadata must be a dictionary"}
                
            # Validate sources
            if not isinstance(node.sources, list):
                return {"success": False, "message": "Sources must be a list"}
                
            # Additional validation based on node type
            if node.type == KnowledgeType.SPECIES:
                if 'scientific_name' not in node.metadata:
                    return {"success": False, "message": "Species nodes must have a scientific name"}
                    
            elif node.type == KnowledgeType.COMPOUND:
                if 'molecular_formula' not in node.metadata:
                    return {"success": False, "message": "Compound nodes must have a molecular formula"}
                    
            return {"success": True, "message": "Node validation successful"}
            
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def _validate_relation(self, relation: KnowledgeRelation) -> Dict:
        """Validate a knowledge relation."""
        try:
            # Check required fields
            if not relation.source_id or not relation.target_id:
                return {"success": False, "message": "Source and target IDs are required"}
                
            # Validate metadata
            if not isinstance(relation.metadata, dict):
                return {"success": False, "message": "Metadata must be a dictionary"}
                
            # Validate sources
            if not isinstance(relation.sources, list):
                return {"success": False, "message": "Sources must be a list"}
                
            # Validate confidence
            if not 0.0 <= relation.confidence <= 1.0:
                return {"success": False, "message": "Confidence must be between 0 and 1"}
                
            # Additional validation based on relation type
            if relation.type == RelationType.IS_A:
                source_node = self.nodes[relation.source_id]
                target_node = self.nodes[relation.target_id]
                if source_node.type != target_node.type:
                    return {"success": False, "message": "IS_A relations must connect nodes of the same type"}
                    
            return {"success": True, "message": "Relation validation successful"}
            
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def _add_node_to_rdf(self, node: KnowledgeNode):
        """Add a node to the RDF graph."""
        try:
            node_uri = URIRef(f"{self.myco_ns}{node.id}")
            
            # Add type
            self.rdf_graph.add((node_uri, RDF.type, self.myco_ns[node.type.value]))
            
            # Add basic properties
            self.rdf_graph.add((node_uri, RDFS.label, Literal(node.name)))
            self.rdf_graph.add((node_uri, DCTERMS.description, Literal(node.description)))
            
            # Add metadata
            for key, value in node.metadata.items():
                self.rdf_graph.add((node_uri, self.myco_ns[key], Literal(value)))
                
            # Add sources
            for source in node.sources:
                self.rdf_graph.add((node_uri, DCTERMS.source, Literal(source)))
                
            # Add timestamps
            self.rdf_graph.add((node_uri, DCTERMS.created, Literal(node.created_at.isoformat())))
            self.rdf_graph.add((node_uri, DCTERMS.modified, Literal(node.updated_at.isoformat())))
            
        except Exception as e:
            self.logger.error(f"Error adding node to RDF: {str(e)}")

    async def _add_relation_to_rdf(self, relation: KnowledgeRelation):
        """Add a relation to the RDF graph."""
        try:
            source_uri = URIRef(f"{self.myco_ns}{relation.source_id}")
            target_uri = URIRef(f"{self.myco_ns}{relation.target_id}")
            relation_uri = URIRef(f"{self.myco_ns}{relation.id}")
            
            # Add relation type
            self.rdf_graph.add((relation_uri, RDF.type, self.myco_ns[relation.type.value]))
            
            # Add source and target
            self.rdf_graph.add((relation_uri, self.myco_ns.hasSource, source_uri))
            self.rdf_graph.add((relation_uri, self.myco_ns.hasTarget, target_uri))
            
            # Add metadata
            for key, value in relation.metadata.items():
                self.rdf_graph.add((relation_uri, self.myco_ns[key], Literal(value)))
                
            # Add confidence
            self.rdf_graph.add((relation_uri, self.myco_ns.confidence, Literal(relation.confidence)))
            
            # Add sources
            for source in relation.sources:
                self.rdf_graph.add((relation_uri, DCTERMS.source, Literal(source)))
                
            # Add timestamps
            self.rdf_graph.add((relation_uri, DCTERMS.created, Literal(relation.created_at.isoformat())))
            self.rdf_graph.add((relation_uri, DCTERMS.modified, Literal(relation.updated_at.isoformat())))
            
        except Exception as e:
            self.logger.error(f"Error adding relation to RDF: {str(e)}")

    async def _update_node_in_rdf(self, node: KnowledgeNode):
        """Update a node in the RDF graph."""
        try:
            node_uri = URIRef(f"{self.myco_ns}{node.id}")
            
            # Update basic properties
            self.rdf_graph.add((node_uri, RDFS.label, Literal(node.name)))
            self.rdf_graph.add((node_uri, DCTERMS.description, Literal(node.description)))
            
            # Update metadata
            for key, value in node.metadata.items():
                self.rdf_graph.add((node_uri, self.myco_ns[key], Literal(value)))
                
            # Update sources
            for source in node.sources:
                self.rdf_graph.add((node_uri, DCTERMS.source, Literal(source)))
                
            # Update timestamps
            self.rdf_graph.add((node_uri, DCTERMS.modified, Literal(node.updated_at.isoformat())))
            
        except Exception as e:
            self.logger.error(f"Error updating node in RDF: {str(e)}")

    async def _update_relation_in_rdf(self, relation: KnowledgeRelation):
        """Update a relation in the RDF graph."""
        try:
            source_uri = URIRef(f"{self.myco_ns}{relation.source_id}")
            target_uri = URIRef(f"{self.myco_ns}{relation.target_id}")
            relation_uri = URIRef(f"{self.myco_ns}{relation.id}")
            
            # Update metadata
            for key, value in relation.metadata.items():
                self.rdf_graph.add((relation_uri, self.myco_ns[key], Literal(value)))
                
            # Update confidence
            self.rdf_graph.add((relation_uri, self.myco_ns.confidence, Literal(relation.confidence)))
            
            # Update sources
            for source in relation.sources:
                self.rdf_graph.add((relation_uri, DCTERMS.source, Literal(source)))
                
            # Update timestamps
            self.rdf_graph.add((relation_uri, DCTERMS.modified, Literal(relation.updated_at.isoformat())))
            
        except Exception as e:
            self.logger.error(f"Error updating relation in RDF: {str(e)}")

    async def _update_search_index(self, node: KnowledgeNode):
        """Update the search index for a knowledge node."""
        try:
            # Implementation of search index update
            # This could involve indexing the node in a search engine or updating a database
            pass
            
        except Exception as e:
            self.logger.error(f"Error updating search index: {str(e)}")

    async def _update_outdated_knowledge(self, items: List[Dict]):
        """Update outdated knowledge in the graph."""
        try:
            # Implementation of outdated knowledge update
            pass
            
        except Exception as e:
            self.logger.error(f"Error updating outdated knowledge: {str(e)}")

    async def _process_new_knowledge(self, data: Dict):
        """Process new knowledge from external sources."""
        try:
            # Implementation of new knowledge processing
            pass
            
        except Exception as e:
            self.logger.error(f"Error processing new knowledge: {str(e)}")

    async def _apply_knowledge_correction(self, correction: Dict):
        """Apply a knowledge correction to the graph."""
        try:
            # Implementation of knowledge correction application
            pass
            
        except Exception as e:
            self.logger.error(f"Error applying knowledge correction: {str(e)}")

    async def _generate_general_insights(self) -> List[Dict]:
        """Generate general insights from the knowledge graph."""
        try:
            # Implementation of general insights generation
            pass
            
        except Exception as e:
            self.logger.error(f"Error generating general insights: {str(e)}")
            return []

    async def _generate_taxonomy_insights(self) -> List[Dict]:
        """Generate taxonomy insights from the knowledge graph."""
        try:
            # Implementation of taxonomy insights generation
            pass
            
        except Exception as e:
            self.logger.error(f"Error generating taxonomy insights: {str(e)}")
            return []

    async def _generate_physiology_insights(self) -> List[Dict]:
        """Generate physiology insights from the knowledge graph."""
        try:
            # Implementation of physiology insights generation
            pass
            
        except Exception as e:
            self.logger.error(f"Error generating physiology insights: {str(e)}")
            return []

    async def _generate_ecology_insights(self) -> List[Dict]:
        """Generate ecology insights from the knowledge graph."""
        try:
            # Implementation of ecology insights generation
            pass
            
        except Exception as e:
            self.logger.error(f"Error generating ecology insights: {str(e)}")
            return []

    async def _generate_applications_insights(self) -> List[Dict]:
        """Generate applications insights from the knowledge graph."""
        try:
            # Implementation of applications insights generation
            pass
            
        except Exception as e:
            self.logger.error(f"Error generating applications insights: {str(e)}")
            return []

    async def _identify_research_gaps(self) -> List[Dict]:
        """Identify research gaps in the knowledge graph."""
        try:
            # Implementation of research gap identification
            pass
            
        except Exception as e:
            self.logger.error(f"Error identifying research gaps: {str(e)}")
            return []

    async def _check_knowledge_inconsistencies(self) -> List[Dict]:
        """Check for knowledge inconsistencies in the graph."""
        try:
            # Implementation of knowledge inconsistency checking
            pass
            
        except Exception as e:
            self.logger.error(f"Error checking knowledge inconsistencies: {str(e)}")
            return []

    async def _check_outdated_knowledge(self) -> List[Dict]:
        """Check for outdated knowledge in the graph."""
        try:
            # Implementation of outdated knowledge checking
            pass
            
        except Exception as e:
            self.logger.error(f"Error checking outdated knowledge: {str(e)}")
            return []

    async def _convert_rdf_to_dict(self, g: Graph) -> List[Dict]:
        """Convert RDF graph to a list of dictionaries."""
        try:
            # Implementation of RDF to dictionary conversion
            pass
            
        except Exception as e:
            self.logger.error(f"Error converting RDF to dictionary: {str(e)}")
            return []

    async def _add_node_to_rdf_dict(self, g: Graph, node: Dict):
        """Add a node to the RDF graph from a dictionary."""
        try:
            # Implementation of RDF dictionary node addition
            pass
            
        except Exception as e:
            self.logger.error(f"Error adding node to RDF from dictionary: {str(e)}")

    async def _add_relation_to_rdf_dict(self, g: Graph, relation: Dict):
        """Add a relation to the RDF graph from a dictionary."""
        try:
            # Implementation of RDF dictionary relation addition
            pass
            
        except Exception as e:
            self.logger.error(f"Error adding relation to RDF from dictionary: {str(e)}")

    async def _namespaces(self) -> Dict:
        """Return the RDF graph namespaces."""
        try:
            # Implementation of RDF graph namespace retrieval
            pass
            
        except Exception as e:
            self.logger.error(f"Error retrieving RDF graph namespaces: {str(e)}")
            return {}

    async def _node_to_dict(self, node: KnowledgeNode) -> Dict:
        """Convert KnowledgeNode object to dictionary for JSON serialization."""
        return {
            'id': node.id,
            'name': node.name,
            'type': node.type.value,
            'description': node.description,
            'properties': node.metadata,
            'references': node.sources,
            'created_at': node.created_at.isoformat(),
            'updated_at': node.updated_at.isoformat()
        }

    async def _relation_to_dict(self, relation: KnowledgeRelation) -> Dict:
        """Convert KnowledgeRelation object to dictionary for JSON serialization."""
        return {
            'id': relation.id,
            'source_id': relation.source_id,
            'target_id': relation.target_id,
            'type': relation.type.value,
            'properties': relation.metadata,
            'references': relation.sources,
            'confidence': relation.confidence,
            'created_at': relation.created_at.isoformat(),
            'updated_at': relation.updated_at.isoformat()
        }

    async def scrape_data_sources(self, sources: List[str] = None) -> Dict:
        """Scrape data from specified fungal data sources."""
        try:
            if sources is None:
                sources = ['inaturalist', 'mycobank', 'fungidb', 'atcc', 'researchhub', 'nih', 'sciencedirect']
            
            results = {
                'success': True,
                'sources': {},
                'total_nodes': 0,
                'total_relations': 0
            }
            
            for source in sources:
                try:
                    if source == 'inaturalist':
                        source_data = await self._scrape_inaturalist()
                    elif source == 'mycobank':
                        source_data = await self._scrape_mycobank()
                    elif source == 'fungidb':
                        source_data = await self._scrape_fungidb()
                    elif source == 'atcc':
                        source_data = await self._scrape_atcc()
                    elif source == 'researchhub':
                        source_data = await self._scrape_researchhub()
                    elif source == 'nih':
                        source_data = await self._scrape_nih()
                    elif source == 'sciencedirect':
                        source_data = await self._scrape_sciencedirect()
                    else:
                        continue
                        
                    results['sources'][source] = source_data
                    results['total_nodes'] += source_data.get('nodes_added', 0)
                    results['total_relations'] += source_data.get('relations_added', 0)
                    
                except Exception as e:
                    self.logger.error(f"Error scraping {source}: {str(e)}")
                    results['sources'][source] = {
                        'success': False,
                        'error': str(e)
                    }
                    
            return results
            
        except Exception as e:
            self.logger.error(f"Error in data scraping: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _scrape_inaturalist(self) -> Dict:
        """Scrape fungal data from iNaturalist."""
        try:
            # Initialize API client
            api_url = "https://api.inaturalist.org/v1"
            headers = {
                'User-Agent': 'Mycosoft Knowledge Agent/1.0',
                'Accept': 'application/json'
            }
            
            # Query parameters for fungi
            params = {
                'taxon_id': 47170,  # Fungi taxon ID
                'per_page': 100,
                'order': 'desc',
                'order_by': 'created_at'
            }
            
            nodes_added = 0
            relations_added = 0
            
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(f"{api_url}/observations", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for observation in data['results']:
                            # Create species node
                            species_data = {
                                'id': f"inat_{observation['id']}",
                                'type': 'SPECIES',
                                'name': observation['taxon']['name'],
                                'description': observation.get('description', ''),
                                'metadata': {
                                    'scientific_name': observation['taxon']['name'],
                                    'common_name': observation['taxon'].get('preferred_common_name', ''),
                                    'latitude': observation['geojson']['coordinates'][1],
                                    'longitude': observation['geojson']['coordinates'][0],
                                    'observed_at': observation['observed_on'],
                                    'quality_grade': observation['quality_grade'],
                                    'url': observation['uri']
                                },
                                'sources': [observation['uri']]
                            }
                            
                            await self.add_knowledge_node(species_data)
                            nodes_added += 1
                            
                            # Add location relation
                            location_data = {
                                'id': f"inat_loc_{observation['id']}",
                                'source_id': f"inat_{observation['id']}",
                                'target_id': f"loc_{observation['place_id']}",
                                'type': 'FOUND_IN',
                                'metadata': {
                                    'observed_at': observation['observed_on']
                                },
                                'confidence': 1.0,
                                'sources': [observation['uri']]
                            }
                            
                            await self.add_knowledge_relation(location_data)
                            relations_added += 1
                            
            return {
                'success': True,
                'nodes_added': nodes_added,
                'relations_added': relations_added
            }
            
        except Exception as e:
            self.logger.error(f"Error scraping iNaturalist: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _scrape_mycobank(self) -> Dict:
        """Scrape fungal data from MycoBank."""
        try:
            # Initialize API client
            api_url = "https://www.mycobank.org/api"
            headers = {
                'User-Agent': 'Mycosoft Knowledge Agent/1.0',
                'Accept': 'application/json'
            }
            
            nodes_added = 0
            relations_added = 0
            
            async with aiohttp.ClientSession(headers=headers) as session:
                # Get list of genera
                async with session.get(f"{api_url}/genera") as response:
                    if response.status == 200:
                        genera = await response.json()
                        
                        for genus in genera:
                            # Create genus node
                            genus_data = {
                                'id': f"mycobank_genus_{genus['id']}",
                                'type': 'GENUS',
                                'name': genus['name'],
                                'description': genus.get('description', ''),
                                'metadata': {
                                    'scientific_name': genus['name'],
                                    'author': genus.get('author', ''),
                                    'year': genus.get('year', ''),
                                    'status': genus.get('status', ''),
                                    'url': f"https://www.mycobank.org/page/Name_details/{genus['id']}"
                                },
                                'sources': [f"https://www.mycobank.org/page/Name_details/{genus['id']}"]
                            }
                            
                            await self.add_knowledge_node(genus_data)
                            nodes_added += 1
                            
                            # Get species in genus
                            async with session.get(f"{api_url}/genera/{genus['id']}/species") as species_response:
                                if species_response.status == 200:
                                    species = await species_response.json()
                                    
                                    for sp in species:
                                        # Create species node
                                        species_data = {
                                            'id': f"mycobank_species_{sp['id']}",
                                            'type': 'SPECIES',
                                            'name': sp['name'],
                                            'description': sp.get('description', ''),
                                            'metadata': {
                                                'scientific_name': sp['name'],
                                                'author': sp.get('author', ''),
                                                'year': sp.get('year', ''),
                                                'status': sp.get('status', ''),
                                                'url': f"https://www.mycobank.org/page/Name_details/{sp['id']}"
                                            },
                                            'sources': [f"https://www.mycobank.org/page/Name_details/{sp['id']}"]
                                        }
                                        
                                        await self.add_knowledge_node(species_data)
                                        nodes_added += 1
                                        
                                        # Add genus-species relation
                                        relation_data = {
                                            'id': f"mycobank_relation_{genus['id']}_{sp['id']}",
                                            'source_id': f"mycobank_species_{sp['id']}",
                                            'target_id': f"mycobank_genus_{genus['id']}",
                                            'type': 'BELONGS_TO',
                                            'metadata': {},
                                            'confidence': 1.0,
                                            'sources': [f"https://www.mycobank.org/page/Name_details/{sp['id']}"]
                                        }
                                        
                                        await self.add_knowledge_relation(relation_data)
                                        relations_added += 1
                                        
            return {
                'success': True,
                'nodes_added': nodes_added,
                'relations_added': relations_added
            }
            
        except Exception as e:
            self.logger.error(f"Error scraping MycoBank: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _scrape_fungidb(self) -> Dict:
        """Scrape fungal data from FungiDB."""
        try:
            # Initialize API client
            api_url = "https://fungidb.org/api"
            headers = {
                'User-Agent': 'Mycosoft Knowledge Agent/1.0',
                'Accept': 'application/json'
            }
            
            nodes_added = 0
            relations_added = 0
            
            async with aiohttp.ClientSession(headers=headers) as session:
                # Get list of species
                async with session.get(f"{api_url}/species") as response:
                    if response.status == 200:
                        species = await response.json()
                        
                        for sp in species:
                            # Create species node
                            species_data = {
                                'id': f"fungidb_species_{sp['id']}",
                                'type': 'SPECIES',
                                'name': sp['name'],
                                'description': sp.get('description', ''),
                                'metadata': {
                                    'scientific_name': sp['name'],
                                    'strain': sp.get('strain', ''),
                                    'assembly': sp.get('assembly', ''),
                                    'url': f"https://fungidb.org/fungidb/app/record/Organism/{sp['id']}"
                                },
                                'sources': [f"https://fungidb.org/fungidb/app/record/Organism/{sp['id']}"]
                            }
                            
                            await self.add_knowledge_node(species_data)
                            nodes_added += 1
                            
                            # Get gene data
                            async with session.get(f"{api_url}/species/{sp['id']}/genes") as genes_response:
                                if genes_response.status == 200:
                                    genes = await genes_response.json()
                                    
                                    for gene in genes:
                                        # Create gene node
                                        gene_data = {
                                            'id': f"fungidb_gene_{gene['id']}",
                                            'type': 'GENE',
                                            'name': gene['name'],
                                            'description': gene.get('description', ''),
                                            'metadata': {
                                                'gene_id': gene['id'],
                                                'product': gene.get('product', ''),
                                                'url': f"https://fungidb.org/fungidb/app/record/Gene/{gene['id']}"
                                            },
                                            'sources': [f"https://fungidb.org/fungidb/app/record/Gene/{gene['id']}"]
                                        }
                                        
                                        await self.add_knowledge_node(gene_data)
                                        nodes_added += 1
                                        
                                        # Add species-gene relation
                                        relation_data = {
                                            'id': f"fungidb_relation_{sp['id']}_{gene['id']}",
                                            'source_id': f"fungidb_gene_{gene['id']}",
                                            'target_id': f"fungidb_species_{sp['id']}",
                                            'type': 'PART_OF',
                                            'metadata': {},
                                            'confidence': 1.0,
                                            'sources': [f"https://fungidb.org/fungidb/app/record/Gene/{gene['id']}"]
                                        }
                                        
                                        await self.add_knowledge_relation(relation_data)
                                        relations_added += 1
                                        
            return {
                'success': True,
                'nodes_added': nodes_added,
                'relations_added': relations_added
            }
            
        except Exception as e:
            self.logger.error(f"Error scraping FungiDB: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _scrape_atcc(self) -> Dict:
        """Scrape fungal data from ATCC."""
        try:
            # Initialize API client
            api_url = "https://www.atcc.org/api"
            headers = {
                'User-Agent': 'Mycosoft Knowledge Agent/1.0',
                'Accept': 'application/json',
                'Authorization': f"Bearer {self.config.get('atcc_api_key', '')}"
            }
            
            nodes_added = 0
            relations_added = 0
            
            async with aiohttp.ClientSession(headers=headers) as session:
                # Get list of fungal strains
                params = {
                    'category': 'fungi',
                    'pageSize': 100,
                    'page': 1
                }
                
                async with session.get(f"{api_url}/products", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for strain in data['items']:
                            # Create strain node
                            strain_data = {
                                'id': f"atcc_strain_{strain['id']}",
                                'type': 'STRAIN',
                                'name': strain['name'],
                                'description': strain.get('description', ''),
                                'metadata': {
                                    'strain_id': strain['id'],
                                    'species': strain.get('species', ''),
                                    'deposit_date': strain.get('depositDate', ''),
                                    'url': f"https://www.atcc.org/products/{strain['id']}"
                                },
                                'sources': [f"https://www.atcc.org/products/{strain['id']}"]
                            }
                            
                            await self.add_knowledge_node(strain_data)
                            nodes_added += 1
                            
                            # Add strain-species relation if species exists
                            if strain.get('species'):
                                species_data = {
                                    'id': f"atcc_species_{strain['species'].replace(' ', '_')}",
                                    'type': 'SPECIES',
                                    'name': strain['species'],
                                    'description': '',
                                    'metadata': {},
                                    'sources': []
                                }
                                
                                await self.add_knowledge_node(species_data)
                                nodes_added += 1
                                
                                relation_data = {
                                    'id': f"atcc_relation_{strain['id']}_{strain['species'].replace(' ', '_')}",
                                    'source_id': f"atcc_strain_{strain['id']}",
                                    'target_id': f"atcc_species_{strain['species'].replace(' ', '_')}",
                                    'type': 'IS_A',
                                    'metadata': {},
                                    'confidence': 1.0,
                                    'sources': [f"https://www.atcc.org/products/{strain['id']}"]
                                }
                                
                                await self.add_knowledge_relation(relation_data)
                                relations_added += 1
                                
            return {
                'success': True,
                'nodes_added': nodes_added,
                'relations_added': relations_added
            }
            
        except Exception as e:
            self.logger.error(f"Error scraping ATCC: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _scrape_researchhub(self) -> Dict:
        """Scrape fungal research data from ResearchHub."""
        try:
            # Initialize API client
            api_url = "https://api.researchhub.com/api"
            headers = {
                'User-Agent': 'Mycosoft Knowledge Agent/1.0',
                'Accept': 'application/json'
            }
            
            nodes_added = 0
            relations_added = 0
            
            async with aiohttp.ClientSession(headers=headers) as session:
                # Search for fungal research papers
                params = {
                    'q': 'fungi OR mushroom OR mycology',
                    'limit': 100,
                    'offset': 0
                }
                
                async with session.get(f"{api_url}/search", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for paper in data['results']:
                            # Create paper node
                            paper_data = {
                                'id': f"rh_paper_{paper['id']}",
                                'type': 'RESEARCH',
                                'name': paper['title'],
                                'description': paper.get('abstract', ''),
                                'metadata': {
                                    'authors': paper.get('authors', []),
                                    'publication_date': paper.get('published_date', ''),
                                    'doi': paper.get('doi', ''),
                                    'url': paper.get('url', '')
                                },
                                'sources': [paper.get('url', '')]
                            }
                            
                            await self.add_knowledge_node(paper_data)
                            nodes_added += 1
                            
                            # Extract mentioned species and create relations
                            species_mentions = await self._extract_species_mentions(paper['title'] + ' ' + paper.get('abstract', ''))
                            
                            for species in species_mentions:
                                relation_data = {
                                    'id': f"rh_relation_{paper['id']}_{species.replace(' ', '_')}",
                                    'source_id': f"rh_paper_{paper['id']}",
                                    'target_id': f"species_{species.replace(' ', '_')}",
                                    'type': 'MENTIONS',
                                    'metadata': {},
                                    'confidence': 0.8,
                                    'sources': [paper.get('url', '')]
                                }
                                
                                await self.add_knowledge_relation(relation_data)
                                relations_added += 1
                                
            return {
                'success': True,
                'nodes_added': nodes_added,
                'relations_added': relations_added
            }
            
        except Exception as e:
            self.logger.error(f"Error scraping ResearchHub: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _scrape_nih(self) -> Dict:
        """Scrape fungal research data from NIH."""
        try:
            # Initialize API client
            api_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
            headers = {
                'User-Agent': 'Mycosoft Knowledge Agent/1.0',
                'Accept': 'application/json'
            }
            
            nodes_added = 0
            relations_added = 0
            
            async with aiohttp.ClientSession(headers=headers) as session:
                # Search for fungal research papers
                search_params = {
                    'db': 'pubmed',
                    'term': 'fungi[Title/Abstract] OR mushroom[Title/Abstract] OR mycology[Title/Abstract]',
                    'retmax': 100,
                    'retmode': 'json'
                }
                
                async with session.get(f"{api_url}/esearch.fcgi", params=search_params) as response:
                    if response.status == 200:
                        search_data = await response.json()
                        
                        for pmid in search_data['esearchresult']['idlist']:
                            # Get paper details
                            fetch_params = {
                                'db': 'pubmed',
                                'id': pmid,
                                'retmode': 'json'
                            }
                            
                            async with session.get(f"{api_url}/efetch.fcgi", params=fetch_params) as paper_response:
                                if paper_response.status == 200:
                                    paper_data = await paper_response.json()
                                    paper = paper_data['result'][pmid]
                                    
                                    # Create paper node
                                    node_data = {
                                        'id': f"nih_paper_{pmid}",
                                        'type': 'RESEARCH',
                                        'name': paper['title'],
                                        'description': paper.get('abstract', ''),
                                        'metadata': {
                                            'authors': paper.get('authors', []),
                                            'publication_date': paper.get('pubdate', ''),
                                            'journal': paper.get('journal', ''),
                                            'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                                        },
                                        'sources': [f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"]
                                    }
                                    
                                    await self.add_knowledge_node(node_data)
                                    nodes_added += 1
                                    
                                    # Extract mentioned species and create relations
                                    species_mentions = await self._extract_species_mentions(paper['title'] + ' ' + paper.get('abstract', ''))
                                    
                                    for species in species_mentions:
                                        relation_data = {
                                            'id': f"nih_relation_{pmid}_{species.replace(' ', '_')}",
                                            'source_id': f"nih_paper_{pmid}",
                                            'target_id': f"species_{species.replace(' ', '_')}",
                                            'type': 'MENTIONS',
                                            'metadata': {},
                                            'confidence': 0.8,
                                            'sources': [f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"]
                                        }
                                        
                                        await self.add_knowledge_relation(relation_data)
                                        relations_added += 1
                                        
            return {
                'success': True,
                'nodes_added': nodes_added,
                'relations_added': relations_added
            }
            
        except Exception as e:
            self.logger.error(f"Error scraping NIH: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _scrape_sciencedirect(self) -> Dict:
        """Scrape fungal research data from ScienceDirect."""
        try:
            # Initialize API client
            api_url = "https://api.elsevier.com/content/search/sciencedirect"
            headers = {
                'User-Agent': 'Mycosoft Knowledge Agent/1.0',
                'Accept': 'application/json',
                'X-ELS-APIKey': self.config.get('sciencedirect_api_key', '')
            }
            
            nodes_added = 0
            relations_added = 0
            
            async with aiohttp.ClientSession(headers=headers) as session:
                # Search for fungal research papers
                params = {
                    'query': 'fungi OR mushroom OR mycology',
                    'count': 100,
                    'start': 0
                }
                
                async with session.get(api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for paper in data['results']:
                            # Create paper node
                            paper_data = {
                                'id': f"sd_paper_{paper['id']}",
                                'type': 'RESEARCH',
                                'name': paper['title'],
                                'description': paper.get('abstract', ''),
                                'metadata': {
                                    'authors': paper.get('authors', []),
                                    'publication_date': paper.get('publicationDate', ''),
                                    'doi': paper.get('doi', ''),
                                    'url': paper.get('url', '')
                                },
                                'sources': [paper.get('url', '')]
                            }
                            
                            await self.add_knowledge_node(paper_data)
                            nodes_added += 1
                            
                            # Extract mentioned species and create relations
                            species_mentions = await self._extract_species_mentions(paper['title'] + ' ' + paper.get('abstract', ''))
                            
                            for species in species_mentions:
                                relation_data = {
                                    'id': f"sd_relation_{paper['id']}_{species.replace(' ', '_')}",
                                    'source_id': f"sd_paper_{paper['id']}",
                                    'target_id': f"species_{species.replace(' ', '_')}",
                                    'type': 'MENTIONS',
                                    'metadata': {},
                                    'confidence': 0.8,
                                    'sources': [paper.get('url', '')]
                                }
                                
                                await self.add_knowledge_relation(relation_data)
                                relations_added += 1
                                
            return {
                'success': True,
                'nodes_added': nodes_added,
                'relations_added': relations_added
            }
            
        except Exception as e:
            self.logger.error(f"Error scraping ScienceDirect: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _extract_species_mentions(self, text: str) -> List[str]:
        """Extract fungal species mentions from text using NLP."""
        if spacy is None:
            self.logger.warning("spaCy not available, skipping species extraction")
            return []
        
        try:
            # Load spaCy model
            nlp = spacy.load("en_core_web_sm")
            
            # Process text
            doc = nlp(text)
            
            # Extract species mentions
            species_mentions = []
            
            for ent in doc.ents:
                if ent.label_ in ['ORG', 'PRODUCT']:  # Changed from SPECIES, TAXON to more general labels
                    species_mentions.append(ent.text)
                    
            return list(set(species_mentions))
            
        except Exception as e:
            self.logger.error(f"Error extracting species mentions: {str(e)}")
            return []

    async def discover_new_sources(self) -> Dict:
        """Discover new potential fungal data sources."""
        try:
            self.logger.info("Starting discovery of new fungal data sources")
            
            discovered_sources = []
            
            # Search for new sources using various methods
            web_sources = await self._discover_web_sources()
            api_sources = await self._discover_api_sources()
            academic_sources = await self._discover_academic_sources()
            database_sources = await self._discover_database_sources()
            
            # Combine all discovered sources
            all_sources = web_sources + api_sources + academic_sources + database_sources
            
            # Filter out known sources
            known_sources = set(self.config.get('known_sources', []))
            new_sources = [source for source in all_sources if source['url'] not in known_sources]
            
            # Evaluate each new source
            for source in new_sources:
                evaluation = await self._evaluate_source(source)
                source['evaluation'] = evaluation
                
                if evaluation['viability_score'] >= 0.6:  # Threshold for recommendation
                    discovered_sources.append(source)
            
            # Store discovered sources for review
            if discovered_sources:
                await self._store_discovered_sources(discovered_sources)
                
                # Notify about new sources
                await self.notification_queue.put({
                    'type': 'new_sources_discovered',
                    'sources': discovered_sources,
                    'timestamp': datetime.now()
                })
            
            return {
                'success': True,
                'discovered_sources': discovered_sources,
                'total_evaluated': len(new_sources),
                'total_recommended': len(discovered_sources)
            }
            
        except Exception as e:
            self.logger.error(f"Error discovering new sources: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _discover_web_sources(self) -> List[Dict]:
        """Discover new fungal data sources from web searches."""
        try:
            discovered_sources = []
            
            # Use search engines to find potential sources
            search_queries = [
                "fungal database new",
                "mycology data repository",
                "fungi research database",
                "mushroom species database",
                "fungal genomics database",
                "mycology research platform"
            ]
            
            for query in search_queries:
                # Use a search API to find potential sources
                # This is a placeholder - implement with actual search API
                search_results = await self._search_web(query)
                
                for result in search_results:
                    # Extract source information
                    source = {
                        'name': result.get('title', ''),
                        'url': result.get('url', ''),
                        'description': result.get('description', ''),
                        'discovery_method': 'web_search',
                        'discovery_date': datetime.now().isoformat(),
                        'category': 'web'
                    }
                    
                    discovered_sources.append(source)
            
            return discovered_sources
            
        except Exception as e:
            self.logger.error(f"Error discovering web sources: {str(e)}")
            return []

    async def _discover_api_sources(self) -> List[Dict]:
        """Discover new fungal data sources from API directories."""
        try:
            discovered_sources = []
            
            # Check API directories and registries
            api_directories = [
                "https://apis.guru/api-docs",
                "https://www.programmableweb.com/apis/directory",
                "https://rapidapi.com/collection"
            ]
            
            for directory_url in api_directories:
                # This is a placeholder - implement with actual API directory scraping
                api_results = await self._scrape_api_directory(directory_url)
                
                for api in api_results:
                    # Check if API is related to mycology/fungi
                    if self._is_mycology_related(api):
                        source = {
                            'name': api.get('name', ''),
                            'url': api.get('url', ''),
                            'description': api.get('description', ''),
                            'discovery_method': 'api_directory',
                            'discovery_date': datetime.now().isoformat(),
                            'category': 'api',
                            'api_documentation': api.get('documentation', '')
                        }
                        
                        discovered_sources.append(source)
            
            return discovered_sources
            
        except Exception as e:
            self.logger.error(f"Error discovering API sources: {str(e)}")
            return []

    async def _discover_academic_sources(self) -> List[Dict]:
        """Discover new fungal data sources from academic literature."""
        try:
            discovered_sources = []
            
            # Search academic databases for papers about fungal databases
            academic_queries = [
                "fungal database development",
                "mycology data repository",
                "fungi research platform",
                "mushroom species database"
            ]
            
            for query in academic_queries:
                # Search academic databases
                # This is a placeholder - implement with actual academic search
                academic_results = await self._search_academic(query)
                
                for paper in academic_results:
                    # Extract potential database mentions
                    database_mentions = await self._extract_database_mentions(paper)
                    
                    for mention in database_mentions:
                        source = {
                            'name': mention.get('name', ''),
                            'url': mention.get('url', ''),
                            'description': mention.get('description', ''),
                            'discovery_method': 'academic_literature',
                            'discovery_date': datetime.now().isoformat(),
                            'category': 'academic',
                            'paper_reference': paper.get('citation', '')
                        }
                        
                        discovered_sources.append(source)
            
            return discovered_sources
            
        except Exception as e:
            self.logger.error(f"Error discovering academic sources: {str(e)}")
            return []

    async def _discover_database_sources(self) -> List[Dict]:
        """Discover new fungal data sources from database registries."""
        try:
            discovered_sources = []
            
            # Check database registries and catalogs
            registry_urls = [
                "https://re3data.org/",
                "https://www.fairsharing.org/",
                "https://www.biosharing.org/"
            ]
            
            for registry_url in registry_urls:
                # This is a placeholder - implement with actual registry scraping
                registry_results = await self._scrape_database_registry(registry_url)
                
                for db in registry_results:
                    # Check if database is related to mycology/fungi
                    if self._is_mycology_related(db):
                        source = {
                            'name': db.get('name', ''),
                            'url': db.get('url', ''),
                            'description': db.get('description', ''),
                            'discovery_method': 'database_registry',
                            'discovery_date': datetime.now().isoformat(),
                            'category': 'database',
                            'registry_metadata': db.get('metadata', {})
                        }
                        
                        discovered_sources.append(source)
            
            return discovered_sources
            
        except Exception as e:
            self.logger.error(f"Error discovering database sources: {str(e)}")
            return []

    async def _evaluate_source(self, source: Dict) -> Dict:
        """Evaluate a discovered data source for viability."""
        try:
            evaluation = {
                'viability_score': 0.0,
                'data_quality_score': 0.0,
                'accessibility_score': 0.0,
                'relevance_score': 0.0,
                'recommendation': False,
                'evaluation_date': datetime.now().isoformat(),
                'notes': []
            }
            
            # Check accessibility
            accessibility = await self._check_source_accessibility(source)
            evaluation['accessibility_score'] = accessibility['score']
            evaluation['notes'].extend(accessibility['notes'])
            
            # Check data quality
            data_quality = await self._check_data_quality(source)
            evaluation['data_quality_score'] = data_quality['score']
            evaluation['notes'].extend(data_quality['notes'])
            
            # Check relevance to mycology
            relevance = await self._check_mycology_relevance(source)
            evaluation['relevance_score'] = relevance['score']
            evaluation['notes'].extend(relevance['notes'])
            
            # Calculate overall viability score
            evaluation['viability_score'] = (
                evaluation['accessibility_score'] * 0.3 +
                evaluation['data_quality_score'] * 0.4 +
                evaluation['relevance_score'] * 0.3
            )
            
            # Determine recommendation
            evaluation['recommendation'] = evaluation['viability_score'] >= 0.6
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"Error evaluating source: {str(e)}")
            return {
                'viability_score': 0.0,
                'error': str(e)
            }

    async def _check_source_accessibility(self, source: Dict) -> Dict:
        """Check if a source is accessible and has a stable API or interface."""
        try:
            result = {
                'score': 0.0,
                'notes': []
            }
            
            # Check if URL is accessible
            url = source.get('url', '')
            if not url:
                result['notes'].append("No URL provided")
                return result
                
            # Try to access the URL
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            result['score'] += 0.5
                            result['notes'].append("URL is accessible")
                        else:
                            result['notes'].append(f"URL returned status code {response.status}")
            except Exception as e:
                result['notes'].append(f"Error accessing URL: {str(e)}")
            
            # Check for API documentation
            if source.get('category') == 'api' and source.get('api_documentation'):
                result['score'] += 0.3
                result['notes'].append("API documentation available")
            
            # Check for data download options
            if await self._has_data_download_options(url):
                result['score'] += 0.2
                result['notes'].append("Data download options available")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking source accessibility: {str(e)}")
            return {
                'score': 0.0,
                'notes': [f"Error: {str(e)}"]
            }

    async def _check_data_quality(self, source: Dict) -> Dict:
        """Check the quality of data provided by a source."""
        try:
            result = {
                'score': 0.0,
                'notes': []
            }
            
            # Check for structured data
            if await self._has_structured_data(source):
                result['score'] += 0.3
                result['notes'].append("Provides structured data")
            
            # Check for metadata
            if await self._has_metadata(source):
                result['score'] += 0.2
                result['notes'].append("Includes metadata")
            
            # Check for data freshness
            freshness = await self._check_data_freshness(source)
            result['score'] += freshness['score'] * 0.2
            result['notes'].extend(freshness['notes'])
            
            # Check for data completeness
            completeness = await self._check_data_completeness(source)
            result['score'] += completeness['score'] * 0.3
            result['notes'].extend(completeness['notes'])
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking data quality: {str(e)}")
            return {
                'score': 0.0,
                'notes': [f"Error: {str(e)}"]
            }

    async def _check_mycology_relevance(self, source: Dict) -> Dict:
        """Check how relevant a source is to mycology research."""
        try:
            result = {
                'score': 0.0,
                'notes': []
            }
            
            # Check description for mycology keywords
            description = source.get('description', '')
            name = source.get('name', '')
            
            mycology_keywords = [
                'fungi', 'fungal', 'mycology', 'mushroom', 'mycelium', 
                'mycorrhiza', 'basidiomycota', 'ascomycota', 'chytrid',
                'spore', 'hyphae', 'mycota', 'mycete', 'mycologist'
            ]
            
            keyword_count = sum(1 for keyword in mycology_keywords 
                               if keyword.lower() in description.lower() or 
                               keyword.lower() in name.lower())
            
            if keyword_count > 0:
                result['score'] += min(0.4, keyword_count * 0.1)
                result['notes'].append(f"Contains {keyword_count} mycology-related keywords")
            
            # Check for taxonomic data
            if await self._has_taxonomic_data(source):
                result['score'] += 0.3
                result['notes'].append("Contains taxonomic data")
            
            # Check for research data
            if await self._has_research_data(source):
                result['score'] += 0.3
                result['notes'].append("Contains research data")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error checking mycology relevance: {str(e)}")
            return {
                'score': 0.0,
                'notes': [f"Error: {str(e)}"]
            }

    async def _store_discovered_sources(self, sources: List[Dict]) -> None:
        """Store discovered sources for review."""
        try:
            # Create directory if it doesn't exist
            sources_dir = self.data_directory / 'discovered_sources'
            sources_dir.mkdir(exist_ok=True)
            
            # Store each source
            for source in sources:
                source_id = f"source_{uuid.uuid4().hex[:8]}"
                source_file = sources_dir / f"{source_id}.json"
                
                async with aiofiles.open(source_file, 'w') as f:
                    await f.write(json.dumps(source, default=str))
            
            # Update the list of discovered sources
            discovered_sources_file = self.data_directory / 'discovered_sources.json'
            
            # Load existing sources
            existing_sources = []
            if discovered_sources_file.exists():
                async with aiofiles.open(discovered_sources_file, 'r') as f:
                    content = await f.read()
                    if content:
                        existing_sources = json.loads(content)
            
            # Add new sources
            for source in sources:
                source_id = f"source_{uuid.uuid4().hex[:8]}"
                source['id'] = source_id
                existing_sources.append(source)
            
            # Save updated list
            async with aiofiles.open(discovered_sources_file, 'w') as f:
                await f.write(json.dumps(existing_sources, default=str))
                
        except Exception as e:
            self.logger.error(f"Error storing discovered sources: {str(e)}")

    async def get_discovered_sources(self) -> Dict:
        """Get list of discovered sources for review."""
        try:
            discovered_sources_file = self.data_directory / 'discovered_sources.json'
            
            if not discovered_sources_file.exists():
                return {
                    'success': True,
                    'sources': []
                }
            
            async with aiofiles.open(discovered_sources_file, 'r') as f:
                content = await f.read()
                sources = json.loads(content) if content else []
            
            return {
                'success': True,
                'sources': sources
            }
            
        except Exception as e:
            self.logger.error(f"Error getting discovered sources: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def approve_source(self, source_id: str) -> Dict:
        """Approve a discovered source for integration."""
        try:
            # Get the source
            discovered_sources_file = self.data_directory / 'discovered_sources.json'
            
            if not discovered_sources_file.exists():
                return {
                    'success': False,
                    'message': "No discovered sources found"
                }
            
            async with aiofiles.open(discovered_sources_file, 'r') as f:
                content = await f.read()
                sources = json.loads(content) if content else []
            
            # Find the source
            source = None
            for s in sources:
                if s.get('id') == source_id:
                    source = s
                    break
            
            if not source:
                return {
                    'success': False,
                    'message': f"Source with ID {source_id} not found"
                }
            
            # Add to known sources
            known_sources = self.config.get('known_sources', [])
            if source['url'] not in known_sources:
                known_sources.append(source['url'])
                self.config['known_sources'] = known_sources
                
                # Save updated config
                config_file = self.data_directory / 'config.json'
                async with aiofiles.open(config_file, 'w') as f:
                    await f.write(json.dumps(self.config, default=str))
            
            # Remove from discovered sources
            sources = [s for s in sources if s.get('id') != source_id]
            
            async with aiofiles.open(discovered_sources_file, 'w') as f:
                await f.write(json.dumps(sources, default=str))
            
            # Add scraper for the new source
            await self._add_source_scraper(source)
            
            return {
                'success': True,
                'message': f"Source {source['name']} approved and integrated",
                'source': source
            }
            
        except Exception as e:
            self.logger.error(f"Error approving source: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def reject_source(self, source_id: str, reason: str = None) -> Dict:
        """Reject a discovered source."""
        try:
            # Get the source
            discovered_sources_file = self.data_directory / 'discovered_sources.json'
            
            if not discovered_sources_file.exists():
                return {
                    'success': False,
                    'message': "No discovered sources found"
                }
            
            async with aiofiles.open(discovered_sources_file, 'r') as f:
                content = await f.read()
                sources = json.loads(content) if content else []
            
            # Find the source
            source = None
            for s in sources:
                if s.get('id') == source_id:
                    source = s
                    break
            
            if not source:
                return {
                    'success': False,
                    'message': f"Source with ID {source_id} not found"
                }
            
            # Add to rejected sources
            rejected_sources = self.config.get('rejected_sources', [])
            rejected_sources.append({
                'url': source['url'],
                'name': source['name'],
                'rejection_date': datetime.now().isoformat(),
                'reason': reason
            })
            self.config['rejected_sources'] = rejected_sources
            
            # Save updated config
            config_file = self.data_directory / 'config.json'
            async with aiofiles.open(config_file, 'w') as f:
                await f.write(json.dumps(self.config, default=str))
            
            # Remove from discovered sources
            sources = [s for s in sources if s.get('id') != source_id]
            
            async with aiofiles.open(discovered_sources_file, 'w') as f:
                await f.write(json.dumps(sources, default=str))
            
            return {
                'success': True,
                'message': f"Source {source['name']} rejected",
                'source': source
            }
            
        except Exception as e:
            self.logger.error(f"Error rejecting source: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    async def _add_source_scraper(self, source: Dict) -> None:
        """Add a scraper for a new source."""
        try:
            # Create a new scraper method based on source type
            source_type = source.get('category', '')
            
            if source_type == 'api':
                await self._add_api_scraper(source)
            elif source_type == 'web':
                await self._add_web_scraper(source)
            elif source_type == 'database':
                await self._add_database_scraper(source)
            elif source_type == 'academic':
                await self._add_academic_scraper(source)
            else:
                self.logger.warning(f"Unknown source type: {source_type}")
                
        except Exception as e:
            self.logger.error(f"Error adding source scraper: {str(e)}")

    async def _add_api_scraper(self, source: Dict) -> None:
        """Add a scraper for an API source."""
        try:
            # This would dynamically add a new scraper method to the class
            self.logger.info(f"Adding API scraper for {source['name']}")
            
        except Exception as e:
            self.logger.error(f"Error adding API scraper: {str(e)}")

    async def _add_web_scraper(self, source: Dict) -> None:
        """Add a scraper for a web source."""
        try:
            # This would dynamically add a new scraper method to the class
            self.logger.info(f"Adding web scraper for {source['name']}")
            
        except Exception as e:
            self.logger.error(f"Error adding web scraper: {str(e)}")

    async def _add_database_scraper(self, source: Dict) -> None:
        """Add a scraper for a database source."""
        try:
            # This would dynamically add a new scraper method to the class
            self.logger.info(f"Adding database scraper for {source['name']}")
            
        except Exception as e:
            self.logger.error(f"Error adding database scraper: {str(e)}")

    async def _add_academic_scraper(self, source: Dict) -> None:
        """Add a scraper for an academic source."""
        try:
            # This would dynamically add a new scraper method to the class
            self.logger.info(f"Adding academic scraper for {source['name']}")
            
        except Exception as e:
            self.logger.error(f"Error adding academic scraper: {str(e)}")

    async def _search_web(self, query: str) -> List[Dict]:
        """Search the web for potential sources."""
        # This is a placeholder - implement with actual web search API
        return []

    async def _scrape_api_directory(self, url: str) -> List[Dict]:
        """Scrape an API directory for potential sources."""
        # This is a placeholder - implement with actual API directory scraping
        return []

    async def _search_academic(self, query: str) -> List[Dict]:
        """Search academic databases for potential sources."""
        # This is a placeholder - implement with actual academic search
        return []

    async def _extract_database_mentions(self, paper: Dict) -> List[Dict]:
        """Extract database mentions from academic papers."""
        # This is a placeholder - implement with actual extraction logic
        return []

    async def _scrape_database_registry(self, url: str) -> List[Dict]:
        """Scrape a database registry for potential sources."""
        # This is a placeholder - implement with actual registry scraping
        return []

    def _is_mycology_related(self, item: Dict) -> bool:
        """Check if an item is related to mycology."""
        # This is a placeholder - implement with actual relevance checking
        return True

    async def _has_data_download_options(self, url: str) -> bool:
        """Check if a source has data download options."""
        # This is a placeholder - implement with actual checking logic
        return False

    async def _has_structured_data(self, source: Dict) -> bool:
        """Check if a source provides structured data."""
        # This is a placeholder - implement with actual checking logic
        return False

    async def _has_metadata(self, source: Dict) -> bool:
        """Check if a source includes metadata."""
        # This is a placeholder - implement with actual checking logic
        return False

    async def _check_data_freshness(self, source: Dict) -> Dict:
        """Check how fresh the data in a source is."""
        # This is a placeholder - implement with actual checking logic
        return {
            'score': 0.5,
            'notes': ["Data freshness check not implemented"]
        }

    async def _check_data_completeness(self, source: Dict) -> Dict:
        """Check how complete the data in a source is."""
        # This is a placeholder - implement with actual checking logic
        return {
            'score': 0.5,
            'notes': ["Data completeness check not implemented"]
        }

    async def _has_taxonomic_data(self, source: Dict) -> bool:
        """Check if a source contains taxonomic data."""
        # This is a placeholder - implement with actual checking logic
        return False

    async def _has_research_data(self, source: Dict) -> bool:
        """Check if a source contains research data."""
        # This is a placeholder - implement with actual checking logic
        return False

    async def _start_background_tasks(self):
        """Start background tasks for the agent."""
        try:
            # Start existing background tasks
            await super()._start_background_tasks()
            
            # Start source discovery task
            asyncio.create_task(self._periodic_source_discovery())
            
            self.logger.info("Started background tasks for Mycology Knowledge Agent")
            
        except Exception as e:
            self.logger.error(f"Error starting background tasks: {str(e)}")

    async def _periodic_source_discovery(self):
        """Periodically discover new data sources."""
        try:
            while True:
                # Wait for the configured interval
                interval = self.config.get('source_discovery_interval', 86400)  # Default: daily
                await asyncio.sleep(interval)
                
                # Discover new sources
                result = await self.discover_new_sources()
                
                if result['success'] and result['total_recommended'] > 0:
                    self.logger.info(f"Discovered {result['total_recommended']} new fungal data sources")
                elif not result['success']:
                    self.logger.error(f"Error in periodic source discovery: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.logger.error(f"Error in periodic source discovery task: {str(e)}")
            # Restart the task after a delay
            await asyncio.sleep(300)  # 5 minutes
            asyncio.create_task(self._periodic_source_discovery())

    async def _handle_error_type(self, error_type: str, error_data: Dict) -> Dict:
        """Handle different types of errors that might occur during mycology knowledge operations.
        
        Args:
            error_type: The type of error that occurred
            error_data: Additional data about the error
            
        Returns:
            Dict containing error handling results
        """
        try:
            if error_type == "species_error":
                # Handle species-related errors
                species_id = error_data.get('species_id')
                if species_id in self.species:
                    species = self.species[species_id]
                    species.status = SpeciesStatus.INVALID
                    self.logger.warning(f"Species {species_id} marked as invalid: {error_data.get('message')}")
                    return {"success": True, "action": "species_invalid", "species_id": species_id}
                    
            elif error_type == "research_error":
                # Handle research-related errors
                research_id = error_data.get('research_id')
                if research_id in self.research:
                    research = self.research[research_id]
                    research.status = ResearchStatus.INVALID
                    self.logger.warning(f"Research {research_id} marked as invalid: {error_data.get('message')}")
                    return {"success": True, "action": "research_invalid", "research_id": research_id}
                    
            elif error_type == "taxonomy_error":
                # Handle taxonomy-related errors
                taxonomy_id = error_data.get('taxonomy_id')
                if taxonomy_id in self.taxonomy:
                    taxonomy = self.taxonomy[taxonomy_id]
                    taxonomy.status = TaxonomyStatus.INVALID
                    self.logger.warning(f"Taxonomy {taxonomy_id} marked as invalid: {error_data.get('message')}")
                    return {"success": True, "action": "taxonomy_invalid", "taxonomy_id": taxonomy_id}
                    
            elif error_type == "api_error":
                # Handle API-related errors
                service = error_data.get('service')
                if service in self.api_clients:
                    # Attempt to reinitialize the API client
                    await self._init_api_connection(service)
                    self.logger.warning(f"API client for {service} reinitialized after error")
                    return {"success": True, "action": "api_reinitialized", "service": service}
                    
            # For unknown error types, log and return generic response
            self.logger.error(f"Unknown error type {error_type}: {error_data}")
            return {
                "success": False,
                "error_type": error_type,
                "message": "Unknown error type encountered"
            }
            
        except Exception as e:
            self.logger.error(f"Error handling failed: {str(e)}")
            return {
                "success": False,
                "error_type": "error_handling_failed",
                "message": str(e)
            }