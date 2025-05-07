import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, Set, Tuple
from datetime import datetime
import json
import uuid
import os
import re
from pathlib import Path
import aiohttp
import aiofiles
import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum
import networkx as nx
from rdflib import Graph, Literal, RDF, URIRef, Namespace, BNode
from rdflib.namespace import RDFS, XSD, OWL, DCTERMS, SKOS, DC, FOAF
import owlready2
from owlready2 import *

class DataCategory(Enum):
    BIOLOGY = "biology"
    CHEMISTRY = "chemistry"
    PHYSICS = "physics"
    MIXED = "mixed"

class DataFormat(Enum):
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    RDF = "rdf"
    OWL = "owl"
    FASTA = "fasta"
    GFF = "gff"
    VCF = "vcf"
    BAM = "bam"
    PDB = "pdb"
    TSV = "tsv"
    BINARY = "binary"
    CUSTOM = "custom"

class DataSource(Enum):
    NCBI = "ncbi"
    UNIPROT = "uniprot"
    PDB = "pdb"
    KEGG = "kegg"
    METACYC = "metacyc"
    ENSEMBL = "ensembl"
    PUBMED = "pubmed"
    CHEBI = "chebi"
    PUBCHEM = "pubchem"
    CUSTOM = "custom"

@dataclass
class DataSchema:
    id: str
    name: str
    category: DataCategory
    format: DataFormat
    source: DataSource
    version: str
    schema_definition: Dict
    created_at: datetime
    updated_at: datetime

@dataclass
class TranslationRule:
    id: str
    name: str
    source_schema_id: str
    target_schema_id: str
    mapping: Dict
    transformation_functions: Dict
    created_at: datetime
    updated_at: datetime

@dataclass
class TranslatedData:
    id: str
    original_data_id: str
    source_schema_id: str
    target_schema_id: str
    translation_rule_id: str
    data: Dict
    metadata: Dict
    created_at: datetime

class BioDataTranslator:
    """
    BioDataTranslator - A plugin for the Eliza framework that enables data sharing and normalization
    between bio agents. This plugin translates biological, chemical, and physics data into formats
    compatible with the MycoDAO agent cluster.
    """
    
    def __init__(self, config: dict):
        # Initialize configuration
        self.config = config
        self.plugin_id = config.get('plugin_id', 'bio_data_translator')
        self.name = config.get('name', 'Bio Data Translator')
        
        # Initialize directories
        self.data_directory = Path(config.get('data_directory', 'data/bio_translator'))
        self.data_directory.mkdir(parents=True, exist_ok=True)
        self.output_directory = Path(config.get('output_directory', 'output/bio_translator'))
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize state
        self.schemas = {}
        self.translation_rules = {}
        self.translated_data = {}
        self.translation_queue = asyncio.Queue()
        self.schema_queue = asyncio.Queue()
        self.rule_queue = asyncio.Queue()
        
        # Initialize ontology
        self.ontology = None
        self.ontology_path = self.data_directory / 'ontology'
        self.ontology_path.mkdir(exist_ok=True)
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Initialize agent connections
        self.connected_agents = {}
        
    async def initialize(self):
        """Initialize the BioDataTranslator plugin."""
        try:
            # Load schemas
            await self._load_schemas()
            
            # Load translation rules
            await self._load_translation_rules()
            
            # Load translated data
            await self._load_translated_data()
            
            # Load ontology
            await self._load_ontology()
            
            # Start background tasks
            await self._start_background_tasks()
            
            self.logger.info(f"BioDataTranslator plugin {self.name} initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize BioDataTranslator plugin: {str(e)}")
            return False
    
    async def _load_schemas(self):
        """Load data schemas from storage."""
        try:
            schemas_dir = self.data_directory / 'schemas'
            schemas_dir.mkdir(exist_ok=True)
            
            for schema_file in schemas_dir.glob('*.json'):
                async with aiofiles.open(schema_file, 'r') as f:
                    schema_data = json.loads(await f.read())
                    schema = self._dict_to_schema(schema_data)
                    self.schemas[schema.id] = schema
            
            self.logger.info(f"Loaded {len(self.schemas)} data schemas")
            
        except Exception as e:
            self.logger.error(f"Error loading data schemas: {str(e)}")
            raise
    
    async def _load_translation_rules(self):
        """Load translation rules from storage."""
        try:
            rules_dir = self.data_directory / 'rules'
            rules_dir.mkdir(exist_ok=True)
            
            for rule_file in rules_dir.glob('*.json'):
                async with aiofiles.open(rule_file, 'r') as f:
                    rule_data = json.loads(await f.read())
                    rule = self._dict_to_rule(rule_data)
                    self.translation_rules[rule.id] = rule
            
            self.logger.info(f"Loaded {len(self.translation_rules)} translation rules")
            
        except Exception as e:
            self.logger.error(f"Error loading translation rules: {str(e)}")
            raise
    
    async def _load_translated_data(self):
        """Load translated data from storage."""
        try:
            translated_dir = self.data_directory / 'translated'
            translated_dir.mkdir(exist_ok=True)
            
            for data_file in translated_dir.glob('*.json'):
                async with aiofiles.open(data_file, 'r') as f:
                    data_record = json.loads(await f.read())
                    translated_data = self._dict_to_translated_data(data_record)
                    self.translated_data[translated_data.id] = translated_data
            
            self.logger.info(f"Loaded {len(self.translated_data)} translated data records")
            
        except Exception as e:
            self.logger.error(f"Error loading translated data: {str(e)}")
            raise
    
    async def _load_ontology(self):
        """Load ontology for semantic mapping."""
        try:
            ontology_file = self.ontology_path / 'bio_ontology.owl'
            
            if ontology_file.exists():
                self.ontology = owlready2.get_ontology(str(ontology_file)).load()
                self.logger.info("Loaded bio ontology")
            else:
                # Create a new ontology if it doesn't exist
                self.ontology = owlready2.Ontology("http://mycosoft.org/ontology/bio")
                
                # Add basic classes
                with self.ontology:
                    class BiologicalEntity(Thing): pass
                    class ChemicalEntity(Thing): pass
                    class PhysicalEntity(Thing): pass
                    
                    class Molecule(BiologicalEntity): pass
                    class Protein(Molecule): pass
                    class Gene(Molecule): pass
                    class Pathway(BiologicalEntity): pass
                    class Organism(BiologicalEntity): pass
                    class Fungus(Organism): pass
                    
                    class ChemicalCompound(ChemicalEntity): pass
                    class Metabolite(ChemicalCompound): pass
                    class Enzyme(ChemicalCompound): pass
                    
                    class PhysicalProperty(PhysicalEntity): pass
                    class Structure(PhysicalProperty): pass
                    class Interaction(PhysicalProperty): pass
                
                # Save the ontology
                self.ontology.save(file=str(ontology_file), format="rdfxml")
                self.logger.info("Created new bio ontology")
            
        except Exception as e:
            self.logger.error(f"Error loading ontology: {str(e)}")
            raise
    
    async def _start_background_tasks(self):
        """Start background tasks for data translation."""
        asyncio.create_task(self._process_translation_queue())
        asyncio.create_task(self._process_schema_queue())
        asyncio.create_task(self._process_rule_queue())
        self.logger.info("Started BioDataTranslator background tasks")
    
    async def register_agent(self, agent_id: str, agent_info: Dict) -> Dict:
        """Register a new agent with the translator."""
        try:
            # Check if agent already exists
            if agent_id in self.connected_agents:
                return {
                    "success": False,
                    "message": f"Agent {agent_id} already registered"
                }
            
            # Register the agent
            self.connected_agents[agent_id] = {
                "id": agent_id,
                "name": agent_info.get("name", ""),
                "capabilities": agent_info.get("capabilities", []),
                "data_schemas": agent_info.get("data_schemas", []),
                "registered_at": datetime.now().isoformat()
            }
            
            # Save agent info
            agents_dir = self.data_directory / 'agents'
            agents_dir.mkdir(exist_ok=True)
            
            agent_file = agents_dir / f"{agent_id}.json"
            async with aiofiles.open(agent_file, 'w') as f:
                await f.write(json.dumps(self.connected_agents[agent_id]))
            
            self.logger.info(f"Registered agent {agent_id}")
            
            return {
                "success": True,
                "agent_id": agent_id,
                "message": f"Agent {agent_id} registered successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to register agent: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def unregister_agent(self, agent_id: str) -> Dict:
        """Unregister an agent from the translator."""
        try:
            # Check if agent exists
            if agent_id not in self.connected_agents:
                return {
                    "success": False,
                    "message": f"Agent {agent_id} not found"
                }
            
            # Remove agent
            del self.connected_agents[agent_id]
            
            # Remove agent file
            agents_dir = self.data_directory / 'agents'
            agent_file = agents_dir / f"{agent_id}.json"
            
            if agent_file.exists():
                agent_file.unlink()
            
            self.logger.info(f"Unregistered agent {agent_id}")
            
            return {
                "success": True,
                "agent_id": agent_id,
                "message": f"Agent {agent_id} unregistered successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to unregister agent: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def register_schema(self, schema_data: Dict) -> Dict:
        """Register a new data schema."""
        try:
            # Generate schema ID
            schema_id = schema_data.get('id', f"schema_{uuid.uuid4().hex[:8]}")
            
            # Create schema
            schema = DataSchema(
                id=schema_id,
                name=schema_data.get('name', ''),
                category=DataCategory[schema_data.get('category', 'BIOLOGY').upper()],
                format=DataFormat[schema_data.get('format', 'JSON').upper()],
                source=DataSource[schema_data.get('source', 'CUSTOM').upper()],
                version=schema_data.get('version', '1.0'),
                schema_definition=schema_data.get('schema_definition', {}),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Save schema
            self.schemas[schema_id] = schema
            
            schemas_dir = self.data_directory / 'schemas'
            schemas_dir.mkdir(exist_ok=True)
            
            schema_file = schemas_dir / f"{schema_id}.json"
            async with aiofiles.open(schema_file, 'w') as f:
                await f.write(json.dumps(self._schema_to_dict(schema)))
            
            # Add to schema queue for processing
            await self.schema_queue.put({
                'schema_id': schema_id,
                'action': 'register'
            })
            
            self.logger.info(f"Registered schema {schema_id}")
            
            return {
                "success": True,
                "schema_id": schema_id,
                "message": f"Schema {schema_id} registered successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to register schema: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def update_schema(self, schema_id: str, schema_data: Dict) -> Dict:
        """Update an existing data schema."""
        try:
            # Check if schema exists
            if schema_id not in self.schemas:
                return {
                    "success": False,
                    "message": f"Schema {schema_id} not found"
                }
            
            # Update schema
            schema = self.schemas[schema_id]
            
            if 'name' in schema_data:
                schema.name = schema_data['name']
            if 'category' in schema_data:
                schema.category = DataCategory[schema_data['category'].upper()]
            if 'format' in schema_data:
                schema.format = DataFormat[schema_data['format'].upper()]
            if 'source' in schema_data:
                schema.source = DataSource[schema_data['source'].upper()]
            if 'version' in schema_data:
                schema.version = schema_data['version']
            if 'schema_definition' in schema_data:
                schema.schema_definition = schema_data['schema_definition']
            
            schema.updated_at = datetime.now()
            
            # Save updated schema
            schemas_dir = self.data_directory / 'schemas'
            schema_file = schemas_dir / f"{schema_id}.json"
            
            async with aiofiles.open(schema_file, 'w') as f:
                await f.write(json.dumps(self._schema_to_dict(schema)))
            
            # Add to schema queue for processing
            await self.schema_queue.put({
                'schema_id': schema_id,
                'action': 'update'
            })
            
            self.logger.info(f"Updated schema {schema_id}")
            
            return {
                "success": True,
                "schema_id": schema_id,
                "message": f"Schema {schema_id} updated successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to update schema: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def delete_schema(self, schema_id: str) -> Dict:
        """Delete a data schema."""
        try:
            # Check if schema exists
            if schema_id not in self.schemas:
                return {
                    "success": False,
                    "message": f"Schema {schema_id} not found"
                }
            
            # Remove schema
            del self.schemas[schema_id]
            
            # Remove schema file
            schemas_dir = self.data_directory / 'schemas'
            schema_file = schemas_dir / f"{schema_id}.json"
            
            if schema_file.exists():
                schema_file.unlink()
            
            # Add to schema queue for processing
            await self.schema_queue.put({
                'schema_id': schema_id,
                'action': 'delete'
            })
            
            self.logger.info(f"Deleted schema {schema_id}")
            
            return {
                "success": True,
                "schema_id": schema_id,
                "message": f"Schema {schema_id} deleted successfully"
            }
            
        except Exception as e:
            this.logger.error(f"Failed to delete schema: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def create_translation_rule(self, rule_data: Dict) -> Dict:
        """Create a new translation rule."""
        try:
            # Generate rule ID
            rule_id = rule_data.get('id', f"rule_{uuid.uuid4().hex[:8]}")
            
            # Check if source and target schemas exist
            source_schema_id = rule_data.get('source_schema_id', '')
            target_schema_id = rule_data.get('target_schema_id', '')
            
            if source_schema_id not in this.schemas:
                return {
                    "success": False,
                    "message": f"Source schema {source_schema_id} not found"
                }
            
            if target_schema_id not in this.schemas:
                return {
                    "success": False,
                    "message": f"Target schema {target_schema_id} not found"
                }
            
            # Create rule
            rule = TranslationRule(
                id=rule_id,
                name=rule_data.get('name', ''),
                source_schema_id=source_schema_id,
                target_schema_id=target_schema_id,
                mapping=rule_data.get('mapping', {}),
                transformation_functions=rule_data.get('transformation_functions', {}),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Save rule
            this.translation_rules[rule_id] = rule
            
            rules_dir = this.data_directory / 'rules'
            rules_dir.mkdir(exist_ok=True)
            
            rule_file = rules_dir / f"{rule_id}.json"
            async with aiofiles.open(rule_file, 'w') as f:
                await f.write(json.dumps(this._rule_to_dict(rule)))
            
            # Add to rule queue for processing
            await this.rule_queue.put({
                'rule_id': rule_id,
                'action': 'create'
            })
            
            this.logger.info(f"Created translation rule {rule_id}")
            
            return {
                "success": True,
                "rule_id": rule_id,
                "message": f"Translation rule {rule_id} created successfully"
            }
            
        except Exception as e:
            this.logger.error(f"Failed to create translation rule: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def update_translation_rule(self, rule_id: str, rule_data: Dict) -> Dict:
        """Update an existing translation rule."""
        try:
            # Check if rule exists
            if rule_id not in this.translation_rules:
                return {
                    "success": False,
                    "message": f"Translation rule {rule_id} not found"
                }
            
            # Update rule
            rule = this.translation_rules[rule_id]
            
            if 'name' in rule_data:
                rule.name = rule_data['name']
            if 'source_schema_id' in rule_data:
                # Check if source schema exists
                if rule_data['source_schema_id'] not in this.schemas:
                    return {
                        "success": False,
                        "message": f"Source schema {rule_data['source_schema_id']} not found"
                    }
                rule.source_schema_id = rule_data['source_schema_id']
            if 'target_schema_id' in rule_data:
                # Check if target schema exists
                if rule_data['target_schema_id'] not in this.schemas:
                    return {
                        "success": False,
                        "message": f"Target schema {rule_data['target_schema_id']} not found"
                    }
                rule.target_schema_id = rule_data['target_schema_id']
            if 'mapping' in rule_data:
                rule.mapping = rule_data['mapping']
            if 'transformation_functions' in rule_data:
                rule.transformation_functions = rule_data['transformation_functions']
            
            rule.updated_at = datetime.now()
            
            # Save updated rule
            rules_dir = this.data_directory / 'rules'
            rule_file = rules_dir / f"{rule_id}.json"
            
            async with aiofiles.open(rule_file, 'w') as f:
                await f.write(json.dumps(this._rule_to_dict(rule)))
            
            # Add to rule queue for processing
            await this.rule_queue.put({
                'rule_id': rule_id,
                'action': 'update'
            })
            
            this.logger.info(f"Updated translation rule {rule_id}")
            
            return {
                "success": True,
                "rule_id": rule_id,
                "message": f"Translation rule {rule_id} updated successfully"
            }
            
        except Exception as e:
            this.logger.error(f"Failed to update translation rule: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def delete_translation_rule(self, rule_id: str) -> Dict:
        """Delete a translation rule."""
        try:
            # Check if rule exists
            if rule_id not in this.translation_rules:
                return {
                    "success": False,
                    "message": f"Translation rule {rule_id} not found"
                }
            
            # Remove rule
            del this.translation_rules[rule_id]
            
            # Remove rule file
            rules_dir = this.data_directory / 'rules'
            rule_file = rules_dir / f"{rule_id}.json"
            
            if rule_file.exists():
                rule_file.unlink()
            
            # Add to rule queue for processing
            await this.rule_queue.put({
                'rule_id': rule_id,
                'action': 'delete'
            })
            
            this.logger.info(f"Deleted translation rule {rule_id}")
            
            return {
                "success": True,
                "rule_id": rule_id,
                "message": f"Translation rule {rule_id} deleted successfully"
            }
            
        except Exception as e:
            this.logger.error(f"Failed to delete translation rule: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def translate_data(self, data: Dict, source_schema_id: str, target_schema_id: str) -> Dict:
        """Translate data from one schema to another."""
        try:
            # Check if schemas exist
            if source_schema_id not in this.schemas:
                return {
                    "success": False,
                    "message": f"Source schema {source_schema_id} not found"
                }
            
            if target_schema_id not in this.schemas:
                return {
                    "success": False,
                    "message": f"Target schema {target_schema_id} not found"
                }
            
            # Find applicable translation rule
            rule_id = None
            for r_id, rule in this.translation_rules.items():
                if rule.source_schema_id == source_schema_id and rule.target_schema_id == target_schema_id:
                    rule_id = r_id
                    break
            
            if not rule_id:
                # Try to find a path through intermediate schemas
                path = await this._find_translation_path(source_schema_id, target_schema_id)
                
                if not path:
                    return {
                        "success": False,
                        "message": f"No translation path found from {source_schema_id} to {target_schema_id}"
                    }
                
                # Generate a composite rule ID
                rule_id = f"composite_{uuid.uuid4().hex[:8]}"
                
                # Create a composite rule
                composite_rule = await this._create_composite_rule(path)
                this.translation_rules[rule_id] = composite_rule
            
            # Generate translation ID
            translation_id = f"translation_{uuid.uuid4().hex[:8]}"
            
            # Add to translation queue
            await this.translation_queue.put({
                'translation_id': translation_id,
                'data': data,
                'source_schema_id': source_schema_id,
                'target_schema_id': target_schema_id,
                'rule_id': rule_id
            })
            
            this.logger.info(f"Queued data translation {translation_id}")
            
            return {
                "success": True,
                "translation_id": translation_id,
                "message": f"Data translation {translation_id} queued successfully"
            }
            
        except Exception as e:
            this.logger.error(f"Failed to queue data translation: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def get_translation_status(self, translation_id: str) -> Dict:
        """Get the status of a data translation."""
        try:
            # Check if translation exists
            if translation_id not in this.translated_data:
                return {
                    "success": False,
                    "message": f"Translation {translation_id} not found"
                }
            
            # Get translation
            translation = this.translated_data[translation_id]
            
            return {
                "success": True,
                "translation_id": translation_id,
                "status": "completed",
                "original_data_id": translation.original_data_id,
                "source_schema_id": translation.source_schema_id,
                "target_schema_id": translation.target_schema_id,
                "translation_rule_id": translation.translation_rule_id,
                "created_at": translation.created_at.isoformat()
            }
            
        except Exception as e:
            this.logger.error(f"Failed to get translation status: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def get_translated_data(self, translation_id: str) -> Dict:
        """Get the translated data."""
        try:
            # Check if translation exists
            if translation_id not in this.translated_data:
                return {
                    "success": False,
                    "message": f"Translation {translation_id} not found"
                }
            
            # Get translation
            translation = this.translated_data[translation_id]
            
            return {
                "success": True,
                "translation_id": translation_id,
                "data": translation.data,
                "metadata": translation.metadata
            }
            
        except Exception as e:
            this.logger.error(f"Failed to get translated data: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def _process_translation_queue(self):
        """Process the translation queue."""
        while True:
            try:
                translation_item = await this.translation_queue.get()
                
                # Process translation
                translation_id = translation_item['translation_id']
                data = translation_item['data']
                source_schema_id = translation_item['source_schema_id']
                target_schema_id = translation_item['target_schema_id']
                rule_id = translation_item['rule_id']
                
                # Get rule
                rule = this.translation_rules[rule_id]
                
                # Translate data
                translated_data = await this._apply_translation_rule(data, rule)
                
                # Create translation record
                translation = TranslatedData(
                    id=translation_id,
                    original_data_id=data.get('id', ''),
                    source_schema_id=source_schema_id,
                    target_schema_id=target_schema_id,
                    translation_rule_id=rule_id,
                    data=translated_data,
                    metadata={
                        'source_schema': this.schemas[source_schema_id].name,
                        'target_schema': this.schemas[target_schema_id].name,
                        'rule_name': rule.name
                    },
                    created_at=datetime.now()
                )
                
                # Save translation
                this.translated_data[translation_id] = translation
                
                translated_dir = this.data_directory / 'translated'
                translated_dir.mkdir(exist_ok=True)
                
                translation_file = translated_dir / f"{translation_id}.json"
                async with aiofiles.open(translation_file, 'w') as f:
                    await f.write(json.dumps(this._translated_data_to_dict(translation)))
                
                this.logger.info(f"Completed data translation {translation_id}")
                
                this.translation_queue.task_done()
                
            except Exception as e:
                this.logger.error(f"Error processing translation queue: {str(e)}")
            
            await asyncio.sleep(1)
    
    async def _process_schema_queue(self):
        """Process the schema queue."""
        while True:
            try:
                schema_item = await this.schema_queue.get()
                
                # Process schema
                schema_id = schema_item['schema_id']
                action = schema_item['action']
                
                if action == 'register':
                    # Update ontology with new schema
                    await this._update_ontology_with_schema(schema_id)
                elif action == 'update':
                    # Update ontology with updated schema
                    await this._update_ontology_with_schema(schema_id)
                elif action == 'delete':
                    # Remove schema from ontology
                    await this._remove_schema_from_ontology(schema_id)
                
                this.schema_queue.task_done()
                
            except Exception as e:
                this.logger.error(f"Error processing schema queue: {str(e)}")
            
            await asyncio.sleep(1)
    
    async def _process_rule_queue(self):
        """Process the rule queue."""
        while True:
            try:
                rule_item = await this.rule_queue.get()
                
                # Process rule
                rule_id = rule_item['rule_id']
                action = rule_item['action']
                
                if action == 'create':
                    # Update ontology with new rule
                    await this._update_ontology_with_rule(rule_id)
                elif action == 'update':
                    # Update ontology with updated rule
                    await this._update_ontology_with_rule(rule_id)
                elif action == 'delete':
                    # Remove rule from ontology
                    await this._remove_rule_from_ontology(rule_id)
                
                this.rule_queue.task_done()
                
            except Exception as e:
                this.logger.error(f"Error processing rule queue: {str(e)}")
            
            await asyncio.sleep(1)
    
    async def _find_translation_path(self, source_schema_id: str, target_schema_id: str) -> List[str]:
        """Find a path of translation rules from source schema to target schema."""
        try:
            # Create a graph of schemas and rules
            G = nx.DiGraph()
            
            # Add nodes for schemas
            for schema_id in this.schemas:
                G.add_node(schema_id, type='schema')
            
            # Add edges for rules
            for rule_id, rule in this.translation_rules.items():
                G.add_edge(rule.source_schema_id, rule.target_schema_id, rule_id=rule_id)
            
            # Find shortest path
            if nx.has_path(G, source_schema_id, target_schema_id):
                path = nx.shortest_path(G, source_schema_id, target_schema_id)
                
                # Extract rule IDs along the path
                rule_path = []
                for i in range(len(path) - 1):
                    source = path[i]
                    target = path[i + 1]
                    
                    # Find rule ID for this edge
                    for rule_id, rule in this.translation_rules.items():
                        if rule.source_schema_id == source and rule.target_schema_id == target:
                            rule_path.append(rule_id)
                            break
                
                return rule_path
            
            return []
            
        except Exception as e:
            this.logger.error(f"Error finding translation path: {str(e)}")
            return []
    
    async def _create_composite_rule(self, rule_path: List[str]) -> TranslationRule:
        """Create a composite translation rule from a path of rules."""
        try:
            # Get first and last rules
            first_rule = this.translation_rules[rule_path[0]]
            last_rule = this.translation_rules[rule_path[-1]]
            
            # Create composite rule
            composite_rule = TranslationRule(
                id=f"composite_{uuid.uuid4().hex[:8]}",
                name=f"Composite rule from {first_rule.source_schema_id} to {last_rule.target_schema_id}",
                source_schema_id=first_rule.source_schema_id,
                target_schema_id=last_rule.target_schema_id,
                mapping={},
                transformation_functions={},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Combine mappings and transformation functions
            for rule_id in rule_path:
                rule = this.translation_rules[rule_id]
                
                # Add mappings
                for source_key, target_key in rule.mapping.items():
                    composite_rule.mapping[source_key] = target_key
                
                # Add transformation functions
                for func_name, func_code in rule.transformation_functions.items():
                    composite_rule.transformation_functions[func_name] = func_code
            
            return composite_rule
            
        except Exception as e:
            this.logger.error(f"Error creating composite rule: {str(e)}")
            raise
    
    async def _apply_translation_rule(self, data: Dict, rule: TranslationRule) -> Dict:
        """Apply a translation rule to data."""
        try:
            # Create a copy of the data
            translated_data = data.copy()
            
            # Apply mapping
            for source_key, target_key in rule.mapping.items():
                if source_key in translated_data:
                    translated_data[target_key] = translated_data.pop(source_key)
            
            # Apply transformation functions
            for func_name, func_code in rule.transformation_functions.items():
                # Create a function from the code
                func = eval(func_code)
                
                # Apply the function to the data
                translated_data = func(translated_data)
            
            return translated_data
            
        except Exception as e:
            this.logger.error(f"Error applying translation rule: {str(e)}")
            raise
    
    async def _update_ontology_with_schema(self, schema_id: str):
        """Update the ontology with a new or updated schema."""
        try:
            # Get schema
            schema = this.schemas[schema_id]
            
            # Create a class for the schema
            with this.ontology:
                # Create a new class for the schema
                schema_class = type(schema.name, (Thing,), {})
                
                # Add properties based on schema definition
                for field_name, field_type in schema.schema_definition.items():
                    # Create a property for the field
                    property_name = f"has_{field_name}"
                    property_class = type(property_name, (ObjectProperty,), {
                        "domain": [schema_class],
                        "range": [Thing]
                    })
            
            # Save the ontology
            this.ontology.save(file=str(this.ontology_path / 'bio_ontology.owl'), format="rdfxml")
            
        except Exception as e:
            this.logger.error(f"Error updating ontology with schema: {str(e)}")
    
    async def _remove_schema_from_ontology(self, schema_id: str):
        """Remove a schema from the ontology."""
        try:
            # Get schema
            schema = this.schemas[schema_id]
            
            # Remove the class for the schema
            if hasattr(this.ontology, schema.name):
                delattr(this.ontology, schema.name)
            
            # Save the ontology
            this.ontology.save(file=str(this.ontology_path / 'bio_ontology.owl'), format="rdfxml")
            
        except Exception as e:
            this.logger.error(f"Error removing schema from ontology: {str(e)}")
    
    async def _update_ontology_with_rule(self, rule_id: str):
        """Update the ontology with a new or updated rule."""
        try:
            # Get rule
            rule = this.translation_rules[rule_id]
            
            # Get source and target schemas
            source_schema = this.schemas[rule.source_schema_id]
            target_schema = this.schemas[rule.target_schema_id]
            
            # Create a property for the rule
            with this.ontology:
                # Create a new property for the rule
                rule_property = type(f"transforms_to_{target_schema.name}", (ObjectProperty,), {
                    "domain": [getattr(this.ontology, source_schema.name)],
                    "range": [getattr(this.ontology, target_schema.name)]
                })
            
            # Save the ontology
            this.ontology.save(file=str(this.ontology_path / 'bio_ontology.owl'), format="rdfxml")
            
        except Exception as e:
            this.logger.error(f"Error updating ontology with rule: {str(e)}")
    
    async def _remove_rule_from_ontology(self, rule_id: str):
        """Remove a rule from the ontology."""
        try:
            # Get rule
            rule = this.translation_rules[rule_id]
            
            # Get source and target schemas
            source_schema = this.schemas[rule.source_schema_id]
            target_schema = this.schemas[rule.target_schema_id]
            
            # Remove the property for the rule
            property_name = f"transforms_to_{target_schema.name}"
            if hasattr(this.ontology, property_name):
                delattr(this.ontology, property_name)
            
            # Save the ontology
            this.ontology.save(file=str(this.ontology_path / 'bio_ontology.owl'), format="rdfxml")
            
        except Exception as e:
            this.logger.error(f"Error removing rule from ontology: {str(e)}")
    
    def _schema_to_dict(self, schema: DataSchema) -> Dict:
        """Convert a DataSchema object to a dictionary."""
        return {
            'id': schema.id,
            'name': schema.name,
            'category': schema.category.value,
            'format': schema.format.value,
            'source': schema.source.value,
            'version': schema.version,
            'schema_definition': schema.schema_definition,
            'created_at': schema.created_at.isoformat(),
            'updated_at': schema.updated_at.isoformat()
        }
    
    def _dict_to_schema(self, data: Dict) -> DataSchema:
        """Convert a dictionary to a DataSchema object."""
        return DataSchema(
            id=data['id'],
            name=data['name'],
            category=DataCategory[data['category'].upper()],
            format=DataFormat[data['format'].upper()],
            source=DataSource[data['source'].upper()],
            version=data['version'],
            schema_definition=data['schema_definition'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )
    
    def _rule_to_dict(self, rule: TranslationRule) -> Dict:
        """Convert a TranslationRule object to a dictionary."""
        return {
            'id': rule.id,
            'name': rule.name,
            'source_schema_id': rule.source_schema_id,
            'target_schema_id': rule.target_schema_id,
            'mapping': rule.mapping,
            'transformation_functions': rule.transformation_functions,
            'created_at': rule.created_at.isoformat(),
            'updated_at': rule.updated_at.isoformat()
        }
    
    def _dict_to_rule(self, data: Dict) -> TranslationRule:
        """Convert a dictionary to a TranslationRule object."""
        return TranslationRule(
            id=data['id'],
            name=data['name'],
            source_schema_id=data['source_schema_id'],
            target_schema_id=data['target_schema_id'],
            mapping=data['mapping'],
            transformation_functions=data['transformation_functions'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )
    
    def _translated_data_to_dict(self, translated_data: TranslatedData) -> Dict:
        """Convert a TranslatedData object to a dictionary."""
        return {
            'id': translated_data.id,
            'original_data_id': translated_data.original_data_id,
            'source_schema_id': translated_data.source_schema_id,
            'target_schema_id': translated_data.target_schema_id,
            'translation_rule_id': translated_data.translation_rule_id,
            'data': translated_data.data,
            'metadata': translated_data.metadata,
            'created_at': translated_data.created_at.isoformat()
        }
    
    def _dict_to_translated_data(self, data: Dict) -> TranslatedData:
        """Convert a dictionary to a TranslatedData object."""
        return TranslatedData(
            id=data['id'],
            original_data_id=data['original_data_id'],
            source_schema_id=data['source_schema_id'],
            target_schema_id=data['target_schema_id'],
            translation_rule_id=data['translation_rule_id'],
            data=data['data'],
            metadata=data['metadata'],
            created_at=datetime.fromisoformat(data['created_at'])
        ) 