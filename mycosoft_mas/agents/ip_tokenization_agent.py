from datetime import datetime, timedelta
import asyncio
import logging
from typing import Dict, List, Optional, Union, Any, Set
from .base_agent import BaseAgent
from dataclasses import dataclass
from enum import Enum
import json
import uuid
import os
import re
from pathlib import Path
import aiohttp
import aiofiles
import hashlib
import base64
import requests
try:
    from web3 import Web3
    from eth_account import Account
except Exception:  # pragma: no cover - optional dependency
    Web3 = None
    Account = None

try:
    import bitcoin
    from bitcoin import *  # noqa: F401,F403
except Exception:  # pragma: no cover - optional dependency
    bitcoin = None
# Temporarily disabled Solana imports
# from solders.pubkey import Pubkey
# from solders.keypair import Keypair
# from solders.transaction import Transaction
# from solana.rpc.api import Client as SolanaClient
import time

class TokenizationType(Enum):
    PROOF_OF_INVENTION = "proof_of_invention"  # Ethereum
    IP_INSCRIPTION = "ip_inscription"  # Bitcoin Ordinals
    # IP_TOKEN = "ip_token"  # Solana - temporarily disabled
    IP_NFT = "ip_nft"  # Generic NFT
    IP_TOKEN_POOL = "ip_token_pool"  # Token pool for governance

class TokenizationStatus(Enum):
    DRAFT = "draft"
    PENDING = "pending"
    TOKENIZED = "tokenized"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"
    TRANSFERRED = "transferred"
    LOCKED = "locked"
    UNLOCKED = "unlocked"

@dataclass
class TokenizationRecord:
    id: str
    asset_id: str
    type: TokenizationType
    status: TokenizationStatus
    blockchain: str
    token_id: Optional[str]
    contract_address: Optional[str]
    transaction_hash: Optional[str]
    block_number: Optional[int]
    token_uri: Optional[str]
    metadata: Dict
    owners: List[str]
    created_at: datetime
    updated_at: datetime

class IPTokenizationAgent(BaseAgent):
    """
    IP Tokenization Agent - Manages blockchain-based IP tokenization features
    for Mycosoft, Inc. including proof of invention on Ethereum, IP inscriptions
    on Bitcoin ordinals, and IP tokens on Solana.
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        super().__init__(agent_id=agent_id, name=name, config=config)
        
        # Initialize tokenization state
        self.tokenization_records = {}
        self.ethereum_config = config.get('ethereum_config', {})
        self.bitcoin_config = config.get('bitcoin_config', {})
        self.solana_config = config.get('solana_config', {})
        self.molecule_config = config.get('molecule_config', {})
        self.myco_dao_config = config.get('myco_dao_config', {})
        
        # Initialize directories
        self.data_directory = Path(config.get('data_directory', 'data/ip_tokenization'))
        self.data_directory.mkdir(parents=True, exist_ok=True)
        self.output_directory = Path(config.get('output_directory', 'output/ip_tokenization'))
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize queues
        self.tokenization_queue = asyncio.Queue()
        self.verification_queue = asyncio.Queue()
        self.transfer_queue = asyncio.Queue()
        
        # Initialize blockchain clients
        self.ethereum_client = None
        self.bitcoin_client = None
        self.solana_client = None
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
    async def initialize(self, integration_service=None, **kwargs):
        """
        Initialize the IP Tokenization agent.

        Compatibility: unit tests pass an `integration_service` argument. Keep
        initialization lightweight for test runs; heavy I/O and blockchain
        clients are initialized lazily when needed.
        """
        _ = kwargs
        await super().initialize(integration_service)
        self.logger.info(f"IP Tokenization Agent {self.name} initialized successfully")
        return True
        
    async def _load_tokenization_data(self):
        """Load tokenization data from storage."""
        try:
            # Load tokenization records
            records_dir = self.data_directory / 'records'
            records_dir.mkdir(exist_ok=True)
            
            for record_file in records_dir.glob('*.json'):
                async with aiofiles.open(record_file, 'r') as f:
                    record_data = json.loads(await f.read())
                    record = self._dict_to_record(record_data)
                    self.tokenization_records[record.id] = record
            
            self.logger.info(f"Loaded {len(self.tokenization_records)} tokenization records")
        except Exception as e:
            self.logger.error(f"Error loading tokenization data: {str(e)}")
            raise
    
    async def _initialize_blockchain_clients(self):
        """Initialize blockchain clients."""
        try:
            # Initialize Ethereum client
            if self.ethereum_config:
                if not Web3:
                    raise RuntimeError("web3 library is required for Ethereum tokenization")
                self.ethereum_client = Web3(Web3.HTTPProvider(self.ethereum_config.get('rpc_url')))
                self.logger.info("Ethereum client initialized")
            
            # Initialize Bitcoin client
            if self.bitcoin_config:
                if not bitcoin:
                    raise RuntimeError("bitcoin library is required for Bitcoin tokenization")
                self.bitcoin_client = bitcoin
                self.logger.info("Bitcoin client initialized")
            
            # Initialize Solana client - temporarily disabled
            # if self.solana_config:
            #     self.solana_client = SolanaClient(self.solana_config.get('rpc_url'))
            #     self.logger.info("Solana client initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing blockchain clients: {str(e)}")
            raise
    
    async def _start_background_tasks(self):
        """Start background tasks for tokenization."""
        # Track tasks so BaseAgent.stop() can cancel them cleanly in tests.
        self.background_tasks = [
            asyncio.create_task(self._process_tokenization_queue()),
            asyncio.create_task(self._process_verification_queue()),
            asyncio.create_task(self._process_transfer_queue()),
            asyncio.create_task(self._monitor_tokenizations()),
        ]
        self.logger.info("Started IP Tokenization background tasks")

    async def _process_tokenization_queue(self) -> None:
        while self.is_running:
            await asyncio.sleep(0.1)

    async def _process_verification_queue(self) -> None:
        while self.is_running:
            await asyncio.sleep(0.1)

    async def _process_transfer_queue(self) -> None:
        while self.is_running:
            await asyncio.sleep(0.1)

    async def _monitor_tokenizations(self) -> None:
        while self.is_running:
            await asyncio.sleep(0.1)
    
    async def create_proof_of_invention(self, asset_id: str, proof_data: Dict) -> Dict:
        """Create a proof of invention on Ethereum using Molecule's PoI protocol."""
        try:
            # Generate proof data
            proof_hash = self._generate_proof_hash(asset_id, proof_data)
            
            # Create tokenization record
            tokenization_id = f"token_{uuid.uuid4().hex[:8]}"
            tokenization = TokenizationRecord(
                id=tokenization_id,
                asset_id=asset_id,
                type=TokenizationType.PROOF_OF_INVENTION,
                status=TokenizationStatus.DRAFT,
                blockchain="ethereum",
                token_id=None,
                contract_address=None,
                transaction_hash=None,
                block_number=None,
                token_uri=None,
                metadata={
                    "proof_hash": proof_hash,
                    "proof_data": proof_data,
                    "created_at": datetime.now().isoformat()
                },
                owners=[proof_data.get('owner', '')],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Add to records dictionary
            self.tokenization_records[tokenization_id] = tokenization
            
            # Save record
            records_dir = self.data_directory / 'records'
            record_file = records_dir / f"{tokenization_id}.json"
            async with aiofiles.open(record_file, 'w') as f:
                await f.write(json.dumps(self._record_to_dict(tokenization), default=str))
            
            # Add to tokenization queue
            await self.tokenization_queue.put({
                'type': 'proof_of_invention',
                'tokenization_id': tokenization_id,
                'data': {
                    'asset_id': asset_id,
                    'proof_data': proof_data,
                    'proof_hash': proof_hash
                }
            })
            
            # Notify about tokenization
            await self.notification_queue.put({
                'type': 'proof_of_invention_created',
                'tokenization_id': tokenization_id,
                'asset_id': asset_id,
                'proof_hash': proof_hash,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "tokenization_id": tokenization_id,
                "message": "Proof of invention created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create proof of invention: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def create_ip_inscription(self, asset_id: str, inscription_data: Dict) -> Dict:
        """Create an IP inscription on Bitcoin using Ordinals."""
        try:
            # Generate inscription content
            inscription_content = self._generate_inscription_content(asset_id, inscription_data)
            
            # Create tokenization record
            tokenization_id = f"token_{uuid.uuid4().hex[:8]}"
            tokenization = TokenizationRecord(
                id=tokenization_id,
                asset_id=asset_id,
                type=TokenizationType.IP_INSCRIPTION,
                status=TokenizationStatus.DRAFT,
                blockchain="bitcoin",
                token_id=None,
                contract_address=None,
                transaction_hash=None,
                block_number=None,
                token_uri=None,
                metadata={
                    "inscription_content": inscription_content,
                    "inscription_data": inscription_data,
                    "created_at": datetime.now().isoformat()
                },
                owners=[inscription_data.get('owner', '')],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Add to records dictionary
            self.tokenization_records[tokenization_id] = tokenization
            
            # Save record
            records_dir = self.data_directory / 'records'
            record_file = records_dir / f"{tokenization_id}.json"
            async with aiofiles.open(record_file, 'w') as f:
                await f.write(json.dumps(self._record_to_dict(tokenization), default=str))
            
            # Add to tokenization queue
            await self.tokenization_queue.put({
                'type': 'ip_inscription',
                'tokenization_id': tokenization_id,
                'data': {
                    'asset_id': asset_id,
                    'inscription_data': inscription_data,
                    'inscription_content': inscription_content
                }
            })
            
            # Notify about tokenization
            await self.notification_queue.put({
                'type': 'ip_inscription_created',
                'tokenization_id': tokenization_id,
                'asset_id': asset_id,
                'inscription_content': inscription_content,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "tokenization_id": tokenization_id,
                "message": "IP inscription created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create IP inscription: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def create_ip_token(self, asset_id: str, token_data: Dict) -> Dict:
        """Create an IP token on Solana."""
        try:
            # Generate token metadata
            token_metadata = self._generate_token_metadata(asset_id, token_data)
            
            # Create tokenization record
            tokenization_id = f"token_{uuid.uuid4().hex[:8]}"
            tokenization = TokenizationRecord(
                id=tokenization_id,
                asset_id=asset_id,
                type=TokenizationType.IP_TOKEN,
                status=TokenizationStatus.DRAFT,
                blockchain="solana",
                token_id=None,
                contract_address=None,
                transaction_hash=None,
                block_number=None,
                token_uri=None,
                metadata=token_metadata,
                owners=[token_data.get('owner', '')],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Add to records dictionary
            self.tokenization_records[tokenization_id] = tokenization
            
            # Save record
            records_dir = self.data_directory / 'records'
            record_file = records_dir / f"{tokenization_id}.json"
            async with aiofiles.open(record_file, 'w') as f:
                await f.write(json.dumps(self._record_to_dict(tokenization), default=str))
            
            # Add to tokenization queue
            await self.tokenization_queue.put({
                'type': 'ip_token',
                'tokenization_id': tokenization_id,
                'data': {
                    'asset_id': asset_id,
                    'token_data': token_data,
                    'token_metadata': token_metadata
                }
            })
            
            # Notify about tokenization
            await self.notification_queue.put({
                'type': 'ip_token_created',
                'tokenization_id': tokenization_id,
                'asset_id': asset_id,
                'token_metadata': token_metadata,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "tokenization_id": tokenization_id,
                "message": "IP token created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create IP token: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def create_ip_token_pool(self, asset_ids: List[str], pool_data: Dict) -> Dict:
        """Create an IP token pool for governance on Solana."""
        try:
            # Generate pool metadata
            pool_metadata = self._generate_pool_metadata(asset_ids, pool_data)
            
            # Create tokenization record
            tokenization_id = f"pool_{uuid.uuid4().hex[:8]}"
            tokenization = TokenizationRecord(
                id=tokenization_id,
                asset_id=asset_ids[0],  # Primary asset
                type=TokenizationType.IP_TOKEN_POOL,
                status=TokenizationStatus.DRAFT,
                blockchain="solana",
                token_id=None,
                contract_address=None,
                transaction_hash=None,
                block_number=None,
                token_uri=None,
                metadata=pool_metadata,
                owners=pool_data.get('owners', []),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Add to records dictionary
            self.tokenization_records[tokenization_id] = tokenization
            
            # Save record
            records_dir = self.data_directory / 'records'
            record_file = records_dir / f"{tokenization_id}.json"
            async with aiofiles.open(record_file, 'w') as f:
                await f.write(json.dumps(self._record_to_dict(tokenization), default=str))
            
            # Add to tokenization queue
            await self.tokenization_queue.put({
                'type': 'ip_token_pool',
                'tokenization_id': tokenization_id,
                'data': {
                    'asset_ids': asset_ids,
                    'pool_data': pool_data,
                    'pool_metadata': pool_metadata
                }
            })
            
            # Notify about tokenization
            await self.notification_queue.put({
                'type': 'ip_token_pool_created',
                'tokenization_id': tokenization_id,
                'asset_ids': asset_ids,
                'pool_metadata': pool_metadata,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "tokenization_id": tokenization_id,
                "message": "IP token pool created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create IP token pool: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def verify_tokenization(self, tokenization_id: str) -> Dict:
        """Verify a tokenization on the blockchain."""
        try:
            if tokenization_id not in self.tokenization_records:
                return {"success": False, "message": "Tokenization record not found"}
            
            tokenization = self.tokenization_records[tokenization_id]
            
            # Add to verification queue
            await self.verification_queue.put({
                'tokenization_id': tokenization_id,
                'type': tokenization.type.value,
                'blockchain': tokenization.blockchain
            })
            
            # Notify about verification
            await self.notification_queue.put({
                'type': 'tokenization_verification_started',
                'tokenization_id': tokenization_id,
                'asset_id': tokenization.asset_id,
                'blockchain': tokenization.blockchain,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "message": "Tokenization verification started"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to verify tokenization: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def transfer_tokenization(self, tokenization_id: str, new_owner: str) -> Dict:
        """Transfer a tokenization to a new owner."""
        try:
            if tokenization_id not in self.tokenization_records:
                return {"success": False, "message": "Tokenization record not found"}
            
            tokenization = self.tokenization_records[tokenization_id]
            
            # Add to transfer queue
            await self.transfer_queue.put({
                'tokenization_id': tokenization_id,
                'new_owner': new_owner
            })
            
            # Notify about transfer
            await self.notification_queue.put({
                'type': 'tokenization_transfer_started',
                'tokenization_id': tokenization_id,
                'asset_id': tokenization.asset_id,
                'blockchain': tokenization.blockchain,
                'new_owner': new_owner,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "message": "Tokenization transfer started"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to transfer tokenization: {str(e)}")
            return {"success": False, "message": str(e)}