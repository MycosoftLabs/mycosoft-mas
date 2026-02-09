import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, Set
from datetime import datetime, timedelta
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
from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import RDFS, XSD, OWL, DCTERMS, SKOS

from .base_agent import BaseAgent

class BioDataType(Enum):
    SEQUENCE = "sequence"
    STRUCTURE = "structure"
    EXPRESSION = "expression"
    METABOLITE = "metabolite"
    PATHWAY = "pathway"
    INTERACTION = "interaction"
    PHENOTYPE = "phenotype"
    ENVIRONMENT = "environment"
    EXPERIMENT = "experiment"
    ANALYSIS = "analysis"

class BioDataFormat(Enum):
    FASTA = "fasta"
    GFF = "gff"
    VCF = "vcf"
    BAM = "bam"
    PDB = "pdb"
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    TSV = "tsv"
    BINARY = "binary"

@dataclass
class BioDataRecord:
    id: str
    type: BioDataType
    format: BioDataFormat
    source: str
    species: str
    description: str
    metadata: Dict
    file_path: str
    created_at: datetime
    updated_at: datetime

class MycologyBioAgent(BaseAgent):
    """
    Mycology BioAgent - Manages biological data processing and analysis for mycology research.
    This agent integrates with the Eliza framework and works with the MycoDAO agent cluster.
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the Mycology BioAgent.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name for the agent
            config: Configuration dictionary for the agent
        """
        super().__init__(agent_id=agent_id, name=name, config=config)
        
        # Initialize bio data state
        self.bio_data_records = {}
        self.analysis_queue = asyncio.Queue()
        self.import_queue = asyncio.Queue()
        self.export_queue = asyncio.Queue()
        
        # Initialize directories
        self.data_directory = Path(config.get('data_directory', 'data/mycology_bio'))
        self.data_directory.mkdir(parents=True, exist_ok=True)
        self.output_directory = Path(config.get('output_directory', 'output/mycology_bio'))
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize knowledge graph connection
        self.knowledge_agent_id = config.get('knowledge_agent_id', 'mycology_knowledge_agent')
        self.knowledge_agent = None
        
        # Initialize DAO connection
        self.dao_agent_id = config.get('dao_agent_id', 'myco_dao_agent')
        self.dao_agent = None
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
    async def initialize(self):
        """Initialize the Mycology BioAgent."""
        await super().initialize()
        await self._load_bio_data()
        await self._connect_to_agents()
        await self._start_background_tasks()
        self.logger.info(f"Mycology BioAgent {self.name} initialized successfully")
        
    async def _load_bio_data(self):
        """Load bio data from storage."""
        try:
            # Load bio data records
            records_dir = self.data_directory / 'records'
            records_dir.mkdir(exist_ok=True)
            
            for record_file in records_dir.glob('*.json'):
                async with aiofiles.open(record_file, 'r') as f:
                    record_data = json.loads(await f.read())
                    record = self._dict_to_record(record_data)
                    self.bio_data_records[record.id] = record
            
            self.logger.info(f"Loaded {len(self.bio_data_records)} bio data records")
            
        except Exception as e:
            self.logger.error(f"Error loading bio data: {str(e)}")
            raise
    
    async def _connect_to_agents(self):
        """Connect to other agents in the system."""
        try:
            # Connect to knowledge agent
            from .mycology_knowledge_agent import MycologyKnowledgeAgent
            self.knowledge_agent = MycologyKnowledgeAgent(
                self.knowledge_agent_id,
                "Mycology Knowledge Agent",
                self.config.get('knowledge_agent_config', {})
            )
            await self.knowledge_agent.initialize()
            self.logger.info("Connected to Mycology Knowledge Agent")
            
            # Connect to DAO agent
            from .myco_dao_agent import MycoDAOAgent
            self.dao_agent = MycoDAOAgent(
                self.dao_agent_id,
                "MycoDAO Agent",
                self.config.get('dao_agent_config', {})
            )
            await self.dao_agent.initialize()
            self.logger.info("Connected to MycoDAO Agent")
            
        except Exception as e:
            self.logger.error(f"Error connecting to agents: {str(e)}")
            raise
    
    async def _start_background_tasks(self):
        """Start background tasks for bio data processing."""
        asyncio.create_task(self._process_analysis_queue())
        asyncio.create_task(self._process_import_queue())
        asyncio.create_task(self._process_export_queue())
        asyncio.create_task(self._monitor_bio_data())
        self.logger.info("Started Mycology BioAgent background tasks")
    
    async def import_bio_data(self, import_data: Dict) -> Dict:
        """Import biological data from various sources."""
        try:
            # Generate import ID
            import_id = f"import_{uuid.uuid4().hex[:8]}"
            
            # Create import record
            import_record = {
                'id': import_id,
                'source': import_data.get('source', ''),
                'type': import_data.get('type', ''),
                'format': import_data.get('format', ''),
                'file_path': import_data.get('file_path', ''),
                'metadata': import_data.get('metadata', {}),
                'created_at': datetime.now().isoformat(),
                'status': 'pending'
            }
            
            # Save import record
            imports_dir = self.data_directory / 'imports'
            imports_dir.mkdir(exist_ok=True)
            
            import_file = imports_dir / f"{import_id}.json"
            async with aiofiles.open(import_file, 'w') as f:
                await f.write(json.dumps(import_record))
            
            # Add to import queue
            await self.import_queue.put({
                'import_id': import_id,
                'import_data': import_data
            })
            
            # Notify about import
            await self.notification_queue.put({
                'type': 'bio_data_import_started',
                'import_id': import_id,
                'source': import_data.get('source', ''),
                'type': import_data.get('type', ''),
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "import_id": import_id,
                "message": "Bio data import started"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to import bio data: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def analyze_bio_data(self, analysis_data: Dict) -> Dict:
        """Analyze biological data using various tools and methods."""
        try:
            # Generate analysis ID
            analysis_id = f"analysis_{uuid.uuid4().hex[:8]}"
            
            # Create analysis record
            analysis_record = {
                'id': analysis_id,
                'data_ids': analysis_data.get('data_ids', []),
                'analysis_type': analysis_data.get('analysis_type', ''),
                'parameters': analysis_data.get('parameters', {}),
                'created_at': datetime.now().isoformat(),
                'status': 'pending'
            }
            
            # Save analysis record
            analyses_dir = self.data_directory / 'analyses'
            analyses_dir.mkdir(exist_ok=True)
            
            analysis_file = analyses_dir / f"{analysis_id}.json"
            async with aiofiles.open(analysis_file, 'w') as f:
                await f.write(json.dumps(analysis_record))
            
            # Add to analysis queue
            await self.analysis_queue.put({
                'analysis_id': analysis_id,
                'analysis_data': analysis_data
            })
            
            # Notify about analysis
            await self.notification_queue.put({
                'type': 'bio_data_analysis_started',
                'analysis_id': analysis_id,
                'data_ids': analysis_data.get('data_ids', []),
                'analysis_type': analysis_data.get('analysis_type', ''),
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "analysis_id": analysis_id,
                "message": "Bio data analysis started"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze bio data: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def export_bio_data(self, export_data: Dict) -> Dict:
        """Export biological data to various formats and destinations."""
        try:
            # Generate export ID
            export_id = f"export_{uuid.uuid4().hex[:8]}"
            
            # Create export record
            export_record = {
                'id': export_id,
                'data_ids': export_data.get('data_ids', []),
                'format': export_data.get('format', ''),
                'destination': export_data.get('destination', ''),
                'parameters': export_data.get('parameters', {}),
                'created_at': datetime.now().isoformat(),
                'status': 'pending'
            }
            
            # Save export record
            exports_dir = self.data_directory / 'exports'
            exports_dir.mkdir(exist_ok=True)
            
            export_file = exports_dir / f"{export_id}.json"
            async with aiofiles.open(export_file, 'w') as f:
                await f.write(json.dumps(export_record))
            
            # Add to export queue
            await self.export_queue.put({
                'export_id': export_id,
                'export_data': export_data
            })
            
            # Notify about export
            await self.notification_queue.put({
                'type': 'bio_data_export_started',
                'export_id': export_id,
                'data_ids': export_data.get('data_ids', []),
                'format': export_data.get('format', ''),
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "export_id": export_id,
                "message": "Bio data export started"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to export bio data: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def create_dao_proposal(self, proposal_data: Dict) -> Dict:
        """Create a DAO proposal for biological research or data analysis."""
        try:
            # Generate proposal ID
            proposal_id = f"proposal_{uuid.uuid4().hex[:8]}"
            
            # Create proposal record
            proposal_record = {
                'id': proposal_id,
                'title': proposal_data.get('title', ''),
                'description': proposal_data.get('description', ''),
                'author': proposal_data.get('author', ''),
                'type': proposal_data.get('type', ''),
                'data_ids': proposal_data.get('data_ids', []),
                'analysis_ids': proposal_data.get('analysis_ids', []),
                'created_at': datetime.now().isoformat(),
                'status': 'draft'
            }
            
            # Save proposal record
            proposals_dir = self.data_directory / 'proposals'
            proposals_dir.mkdir(exist_ok=True)
            
            proposal_file = proposals_dir / f"{proposal_id}.json"
            async with aiofiles.open(proposal_file, 'w') as f:
                await f.write(json.dumps(proposal_record))
            
            # Create DAO proposal
            dao_proposal = {
                'title': proposal_data.get('title', ''),
                'description': proposal_data.get('description', ''),
                'author': proposal_data.get('author', ''),
                'metadata': {
                    'type': 'bio_research',
                    'proposal_id': proposal_id,
                    'data_ids': proposal_data.get('data_ids', []),
                    'analysis_ids': proposal_data.get('analysis_ids', [])
                }
            }
            
            # Submit to DAO
            dao_result = await self.dao_agent.create_proposal(dao_proposal)
            
            # Update proposal record with DAO ID
            proposal_record['dao_id'] = dao_result.get('proposal_id')
            
            # Save updated proposal record
            async with aiofiles.open(proposal_file, 'w') as f:
                await f.write(json.dumps(proposal_record))
            
            # Notify about proposal
            await self.notification_queue.put({
                'type': 'bio_dao_proposal_created',
                'proposal_id': proposal_id,
                'dao_id': dao_result.get('proposal_id'),
                'title': proposal_data.get('title', ''),
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "proposal_id": proposal_id,
                "dao_id": dao_result.get('proposal_id'),
                "message": "Bio DAO proposal created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create bio DAO proposal: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def update_knowledge_graph(self, update_data: Dict) -> Dict:
        """Update the knowledge graph with biological data insights."""
        try:
            # Generate update ID
            update_id = f"update_{uuid.uuid4().hex[:8]}"
            
            # Create update record
            update_record = {
                'id': update_id,
                'data_ids': update_data.get('data_ids', []),
                'analysis_ids': update_data.get('analysis_ids', []),
                'node_type': update_data.get('node_type', ''),
                'relation_type': update_data.get('relation_type', ''),
                'created_at': datetime.now().isoformat(),
                'status': 'pending'
            }
            
            # Save update record
            updates_dir = self.data_directory / 'updates'
            updates_dir.mkdir(exist_ok=True)
            
            update_file = updates_dir / f"{update_id}.json"
            async with aiofiles.open(update_file, 'w') as f:
                await f.write(json.dumps(update_record))
            
            # Prepare knowledge update
            knowledge_update = {
                'type': 'bio_data_update',
                'data': {
                    'data_ids': update_data.get('data_ids', []),
                    'analysis_ids': update_data.get('analysis_ids', []),
                    'node_type': update_data.get('node_type', ''),
                    'relation_type': update_data.get('relation_type', ''),
                    'metadata': update_data.get('metadata', {})
                }
            }
            
            # Submit to knowledge agent
            knowledge_result = await self.knowledge_agent.update_knowledge(knowledge_update)
            
            # Update record with knowledge result
            update_record['knowledge_result'] = knowledge_result
            update_record['status'] = 'completed'
            
            # Save updated record
            async with aiofiles.open(update_file, 'w') as f:
                await f.write(json.dumps(update_record))
            
            # Notify about update
            await self.notification_queue.put({
                'type': 'knowledge_graph_updated',
                'update_id': update_id,
                'data_ids': update_data.get('data_ids', []),
                'node_type': update_data.get('node_type', ''),
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "update_id": update_id,
                "knowledge_result": knowledge_result,
                "message": "Knowledge graph updated successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to update knowledge graph: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def _process_analysis_queue(self):
        """Process the analysis queue."""
        while True:
            try:
                analysis_item = await self.analysis_queue.get()
                
                # Process analysis
                analysis_id = analysis_item['analysis_id']
                analysis_data = analysis_item['analysis_data']
                
                # Get analysis type
                analysis_type = analysis_data.get('analysis_type', '')
                
                # Process based on analysis type
                if analysis_type == 'sequence_analysis':
                    await self._process_sequence_analysis(analysis_id, analysis_data)
                elif analysis_type == 'structure_analysis':
                    await self._process_structure_analysis(analysis_id, analysis_data)
                elif analysis_type == 'expression_analysis':
                    await self._process_expression_analysis(analysis_id, analysis_data)
                elif analysis_type == 'metabolite_analysis':
                    await self._process_metabolite_analysis(analysis_id, analysis_data)
                elif analysis_type == 'pathway_analysis':
                    await self._process_pathway_analysis(analysis_id, analysis_data)
                elif analysis_type == 'interaction_analysis':
                    await self._process_interaction_analysis(analysis_id, analysis_data)
                elif analysis_type == 'phenotype_analysis':
                    await self._process_phenotype_analysis(analysis_id, analysis_data)
                else:
                    self.logger.warning(f"Unknown analysis type: {analysis_type}")
                
                self.analysis_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing analysis queue: {str(e)}")
            
            await asyncio.sleep(1)
    
    async def _process_import_queue(self):
        """Process the import queue."""
        while True:
            try:
                import_item = await self.import_queue.get()
                
                # Process import
                import_id = import_item['import_id']
                import_data = import_item['import_data']
                
                # Get import source and format
                source = import_data.get('source', '')
                format = import_data.get('format', '')
                
                # Process based on source and format
                if source == 'ncbi' and format == 'fasta':
                    await self._import_ncbi_fasta(import_id, import_data)
                elif source == 'uniprot' and format == 'fasta':
                    await self._import_uniprot_fasta(import_id, import_data)
                elif source == 'pdb' and format == 'pdb':
                    await self._import_pdb_structure(import_id, import_data)
                elif source == 'kegg' and format == 'json':
                    await self._import_kegg_data(import_id, import_data)
                elif source == 'metacyc' and format == 'csv':
                    await self._import_metacyc_data(import_id, import_data)
                else:
                    self.logger.warning(f"Unknown import source/format: {source}/{format}")
                
                self.import_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing import queue: {str(e)}")
            
            await asyncio.sleep(1)
    
    async def _process_export_queue(self):
        """Process the export queue."""
        while True:
            try:
                export_item = await self.export_queue.get()
                
                # Process export
                export_id = export_item['export_id']
                export_data = export_item['export_data']
                
                # Get export format and destination
                format = export_data.get('format', '')
                destination = export_data.get('destination', '')
                
                # Process based on format and destination
                if format == 'fasta' and destination == 'file':
                    await self._export_fasta_file(export_id, export_data)
                elif format == 'json' and destination == 'api':
                    await self._export_json_api(export_id, export_data)
                elif format == 'csv' and destination == 'database':
                    await self._export_csv_database(export_id, export_data)
                else:
                    self.logger.warning(f"Unknown export format/destination: {format}/{destination}")
                
                self.export_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing export queue: {str(e)}")
            
            await asyncio.sleep(1)
    
    async def _monitor_bio_data(self):
        """Monitor bio data and send notifications."""
        while True:
            try:
                # Check for bio data that needs analysis
                for record in self.bio_data_records.values():
                    if record.updated_at < datetime.now() - timedelta(days=7):
                        # Suggest analysis
                        await self.notification_queue.put({
                            'type': 'bio_data_analysis_suggested',
                            'data_id': record.id,
                            'type': record.type.value,
                            'updated_at': record.updated_at.isoformat(),
                            'timestamp': datetime.now().isoformat()
                        })
                
            except Exception as e:
                self.logger.error(f"Error monitoring bio data: {str(e)}")
            
            await asyncio.sleep(3600)  # Check every hour
    
    async def _process_sequence_analysis(self, analysis_id: str, analysis_data: Dict):
        """Process sequence analysis."""
        try:
            # Get data IDs
            data_ids = analysis_data.get('data_ids', [])
            
            # Get parameters
            parameters = analysis_data.get('parameters', {})
            
            # Perform sequence analysis
            # This is a placeholder for actual sequence analysis implementation
            analysis_result = {
                'analysis_id': analysis_id,
                'data_ids': data_ids,
                'result_type': 'sequence_analysis',
                'result_data': {
                    'sequence_length': 1000,
                    'gc_content': 0.5,
                    'repeat_regions': [],
                    'coding_regions': []
                },
                'created_at': datetime.now().isoformat()
            }
            
            # Save analysis result
            results_dir = self.data_directory / 'results'
            results_dir.mkdir(exist_ok=True)
            
            result_file = results_dir / f"{analysis_id}.json"
            async with aiofiles.open(result_file, 'w') as f:
                await f.write(json.dumps(analysis_result))
            
            # Update analysis record
            analyses_dir = self.data_directory / 'analyses'
            analysis_file = analyses_dir / f"{analysis_id}.json"
            
            async with aiofiles.open(analysis_file, 'r') as f:
                analysis_record = json.loads(await f.read())
            
            analysis_record['status'] = 'completed'
            analysis_record['result_file'] = str(result_file)
            analysis_record['completed_at'] = datetime.now().isoformat()
            
            async with aiofiles.open(analysis_file, 'w') as f:
                await f.write(json.dumps(analysis_record))
            
            # Notify about analysis completion
            await self.notification_queue.put({
                'type': 'bio_data_analysis_completed',
                'analysis_id': analysis_id,
                'data_ids': data_ids,
                'result_type': 'sequence_analysis',
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error processing sequence analysis: {str(e)}")
    
    async def _process_structure_analysis(self, analysis_id: str, analysis_data: Dict):
        """Process structure analysis."""
        # Implementation for structure analysis
        pass
    
    async def _process_expression_analysis(self, analysis_id: str, analysis_data: Dict):
        """Process expression analysis."""
        # Implementation for expression analysis
        pass
    
    async def _process_metabolite_analysis(self, analysis_id: str, analysis_data: Dict):
        """Process metabolite analysis."""
        # Implementation for metabolite analysis
        pass
    
    async def _process_pathway_analysis(self, analysis_id: str, analysis_data: Dict):
        """Process pathway analysis."""
        # Implementation for pathway analysis
        pass
    
    async def _process_interaction_analysis(self, analysis_id: str, analysis_data: Dict):
        """Process interaction analysis."""
        # Implementation for interaction analysis
        pass
    
    async def _process_phenotype_analysis(self, analysis_id: str, analysis_data: Dict):
        """Process phenotype analysis."""
        # Implementation for phenotype analysis
        pass
    
    async def _import_ncbi_fasta(self, import_id: str, import_data: Dict):
        """Import FASTA data from NCBI."""
        # Implementation for importing NCBI FASTA data
        pass
    
    async def _import_uniprot_fasta(self, import_id: str, import_data: Dict):
        """Import FASTA data from UniProt."""
        # Implementation for importing UniProt FASTA data
        pass
    
    async def _import_pdb_structure(self, import_id: str, import_data: Dict):
        """Import PDB structure data."""
        # Implementation for importing PDB structure data
        pass
    
    async def _import_kegg_data(self, import_id: str, import_data: Dict):
        """Import data from KEGG."""
        # Implementation for importing KEGG data
        pass
    
    async def _import_metacyc_data(self, import_id: str, import_data: Dict):
        """Import data from MetaCyc."""
        # Implementation for importing MetaCyc data
        pass
    
    async def _export_fasta_file(self, export_id: str, export_data: Dict):
        """Export data to FASTA file."""
        # Implementation for exporting to FASTA file
        pass
    
    async def _export_json_api(self, export_id: str, export_data: Dict):
        """Export data to JSON API."""
        # Implementation for exporting to JSON API
        pass
    
    async def _export_csv_database(self, export_id: str, export_data: Dict):
        """Export data to CSV database."""
        # Implementation for exporting to CSV database
        pass
    
    def _record_to_dict(self, record: BioDataRecord) -> Dict:
        """Convert a BioDataRecord object to a dictionary."""
        return {
            'id': record.id,
            'type': record.type.value,
            'format': record.format.value,
            'source': record.source,
            'species': record.species,
            'description': record.description,
            'metadata': record.metadata,
            'file_path': record.file_path,
            'created_at': record.created_at.isoformat(),
            'updated_at': record.updated_at.isoformat()
        }
    
    def _dict_to_record(self, data: Dict) -> BioDataRecord:
        """Convert a dictionary to a BioDataRecord object."""
        return BioDataRecord(
            id=data['id'],
            type=BioDataType[data['type'].upper()],
            format=BioDataFormat[data['format'].upper()],
            source=data['source'],
            species=data['species'],
            description=data['description'],
            metadata=data.get('metadata', {}),
            file_path=data['file_path'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )

    async def _handle_error_type(self, error_type: str, error_data: Dict) -> Dict:
        """Handle different types of errors that might occur during biological operations.
        
        Args:
            error_type: The type of error that occurred
            error_data: Additional data about the error
            
        Returns:
            Dict containing error handling results
        """
        try:
            if error_type == "culture_error":
                # Handle culture-related errors
                culture_id = error_data.get('culture_id')
                if culture_id in self.cultures:
                    culture = self.cultures[culture_id]
                    culture.status = CultureStatus.CONTAMINATED
                    self.logger.warning(f"Culture {culture_id} marked as contaminated: {error_data.get('message')}")
                    return {"success": True, "action": "culture_contaminated", "culture_id": culture_id}
                    
            elif error_type == "experiment_error":
                # Handle experiment-related errors
                experiment_id = error_data.get('experiment_id')
                if experiment_id in self.experiments:
                    experiment = self.experiments[experiment_id]
                    experiment.status = ExperimentStatus.FAILED
                    self.logger.warning(f"Experiment {experiment_id} marked as failed: {error_data.get('message')}")
                    return {"success": True, "action": "experiment_failed", "experiment_id": experiment_id}
                    
            elif error_type == "sample_error":
                # Handle sample-related errors
                sample_id = error_data.get('sample_id')
                if sample_id in self.samples:
                    sample = self.samples[sample_id]
                    sample.status = SampleStatus.INVALID
                    self.logger.warning(f"Sample {sample_id} marked as invalid: {error_data.get('message')}")
                    return {"success": True, "action": "sample_invalid", "sample_id": sample_id}
                    
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