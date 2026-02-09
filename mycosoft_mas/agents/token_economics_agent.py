import asyncio
import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
import json
from pathlib import Path
import aiofiles
from dataclasses import dataclass
from enum import Enum

from .base_agent import BaseAgent

class TokenType(Enum):
    GOVERNANCE = "governance"
    UTILITY = "utility"
    REWARD = "reward"

class StakingStatus(Enum):
    ACTIVE = "active"
    LOCKED = "locked"
    UNSTAKING = "unstaking"
    UNSTAKED = "unstaked"

@dataclass
class TokenPool:
    id: str
    type: TokenType
    total_supply: float
    circulating_supply: float
    locked_supply: float
    staked_supply: float
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]

@dataclass
class StakingPosition:
    id: str
    member_id: str
    token_type: TokenType
    amount: float
    status: StakingStatus
    start_time: datetime
    end_time: Optional[datetime]
    rewards_earned: float
    metadata: Dict[str, Any]

class TokenEconomicsAgent(BaseAgent):
    """
    Token Economics Agent - Manages token distribution, staking, and economic parameters
    for the MycoDAO ecosystem.
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        super().__init__(agent_id, name, config)
        
        # Initialize token economics state
        self.token_pools = {}
        self.staking_positions = {}
        self.reward_rates = {}
        self.lockup_periods = {}
        
        # Initialize directories
        self.data_directory = Path(config.get('data_directory', 'data/token_economics'))
        self.data_directory.mkdir(parents=True, exist_ok=True)
        self.output_directory = Path(config.get('output_directory', 'output/token_economics'))
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize queues
        self.staking_queue = asyncio.Queue()
        self.reward_queue = asyncio.Queue()
        self.distribution_queue = asyncio.Queue()
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
    async def initialize(self):
        """Initialize the Token Economics Agent."""
        await super().initialize()
        await self._load_token_data()
        await self._start_background_tasks()
        self.logger.info(f"Token Economics Agent {self.name} initialized successfully")
        
    async def _load_token_data(self):
        """Load token economics data from storage."""
        try:
            # Load token pools
            pools_dir = self.data_directory / 'pools'
            pools_dir.mkdir(exist_ok=True)
            
            for pool_file in pools_dir.glob('*.json'):
                async with aiofiles.open(pool_file, 'r') as f:
                    pool_data = json.loads(await f.read())
                    pool = self._dict_to_pool(pool_data)
                    self.token_pools[pool.id] = pool
            
            # Load staking positions
            positions_dir = self.data_directory / 'positions'
            positions_dir.mkdir(exist_ok=True)
            
            for position_file in positions_dir.glob('*.json'):
                async with aiofiles.open(position_file, 'r') as f:
                    position_data = json.loads(await f.read())
                    position = self._dict_to_position(position_data)
                    self.staking_positions[position.id] = position
            
            # Load reward rates
            rates_file = self.data_directory / 'reward_rates.json'
            if rates_file.exists():
                async with aiofiles.open(rates_file, 'r') as f:
                    self.reward_rates = json.loads(await f.read())
            
            # Load lockup periods
            periods_file = self.data_directory / 'lockup_periods.json'
            if periods_file.exists():
                async with aiofiles.open(periods_file, 'r') as f:
                    self.lockup_periods = json.loads(await f.read())
            
            self.logger.info(f"Loaded {len(self.token_pools)} token pools, {len(self.staking_positions)} staking positions")
            
        except Exception as e:
            self.logger.error(f"Error loading token data: {str(e)}")
            raise
    
    async def _start_background_tasks(self):
        """Start background tasks for token economics."""
        asyncio.create_task(self._process_staking_queue())
        asyncio.create_task(self._process_reward_queue())
        asyncio.create_task(self._process_distribution_queue())
        asyncio.create_task(self._update_rewards())
        self.logger.info("Started Token Economics background tasks")
    
    async def create_token_pool(self, pool_data: Dict) -> Dict:
        """Create a new token pool."""
        try:
            pool_id = pool_data.get('id', f"pool_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            if pool_id in self.token_pools:
                return {"success": False, "message": "Pool ID already exists"}
            
            pool = TokenPool(
                id=pool_id,
                type=TokenType[pool_data['type'].upper()],
                total_supply=pool_data['total_supply'],
                circulating_supply=0.0,
                locked_supply=0.0,
                staked_supply=0.0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata=pool_data.get('metadata', {})
            )
            
            # Add to pools dictionary
            self.token_pools[pool_id] = pool
            
            # Save pool
            pools_dir = self.data_directory / 'pools'
            pools_dir.mkdir(exist_ok=True)
            
            pool_file = pools_dir / f"{pool_id}.json"
            async with aiofiles.open(pool_file, 'w') as f:
                await f.write(json.dumps(self._pool_to_dict(pool), default=str))
            
            # Notify about new pool
            await self.notification_queue.put({
                'type': 'pool_created',
                'pool_id': pool_id,
                'pool_type': pool.type.value,
                'total_supply': pool.total_supply,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "pool_id": pool_id,
                "message": "Token pool created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create token pool: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def distribute_tokens(self, distribution_data: Dict) -> Dict:
        """Distribute tokens to members."""
        try:
            pool_id = distribution_data['pool_id']
            member_id = distribution_data['member_id']
            amount = distribution_data['amount']
            
            if pool_id not in self.token_pools:
                return {"success": False, "message": "Token pool not found"}
            
            pool = self.token_pools[pool_id]
            
            # Check available supply
            available = pool.total_supply - pool.circulating_supply - pool.locked_supply - pool.staked_supply
            if amount > available:
                return {
                    "success": False,
                    "message": f"Insufficient tokens available: {available}",
                    "requested": amount
                }
            
            # Update pool
            pool.circulating_supply += amount
            pool.updated_at = datetime.now()
            
            # Save updated pool
            pools_dir = self.data_directory / 'pools'
            pool_file = pools_dir / f"{pool_id}.json"
            async with aiofiles.open(pool_file, 'w') as f:
                await f.write(json.dumps(self._pool_to_dict(pool), default=str))
            
            # Add to distribution queue for member update
            await self.distribution_queue.put({
                'pool_id': pool_id,
                'member_id': member_id,
                'amount': amount
            })
            
            # Notify about distribution
            await self.notification_queue.put({
                'type': 'tokens_distributed',
                'pool_id': pool_id,
                'member_id': member_id,
                'amount': amount,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "message": f"Distributed {amount} tokens to member {member_id}",
                "remaining_supply": available - amount
            }
            
        except Exception as e:
            self.logger.error(f"Failed to distribute tokens: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def stake_tokens(self, staking_data: Dict) -> Dict:
        """Stake tokens for rewards."""
        try:
            pool_id = staking_data['pool_id']
            member_id = staking_data['member_id']
            amount = staking_data['amount']
            duration_days = staking_data.get('duration_days', 30)
            
            if pool_id not in self.token_pools:
                return {"success": False, "message": "Token pool not found"}
            
            pool = self.token_pools[pool_id]
            
            # Check available tokens
            if amount > pool.circulating_supply:
                return {
                    "success": False,
                    "message": f"Insufficient tokens available: {pool.circulating_supply}",
                    "requested": amount
                }
            
            # Create staking position
            position_id = f"pos_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            position = StakingPosition(
                id=position_id,
                member_id=member_id,
                token_type=pool.type,
                amount=amount,
                status=StakingStatus.ACTIVE,
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(days=duration_days),
                rewards_earned=0.0,
                metadata={
                    'pool_id': pool_id,
                    'duration_days': duration_days
                }
            )
            
            # Add to positions dictionary
            self.staking_positions[position_id] = position
            
            # Update pool
            pool.circulating_supply -= amount
            pool.staked_supply += amount
            pool.updated_at = datetime.now()
            
            # Save position
            positions_dir = self.data_directory / 'positions'
            positions_dir.mkdir(exist_ok=True)
            
            position_file = positions_dir / f"{position_id}.json"
            async with aiofiles.open(position_file, 'w') as f:
                await f.write(json.dumps(self._position_to_dict(position), default=str))
            
            # Save updated pool
            pools_dir = self.data_directory / 'pools'
            pool_file = pools_dir / f"{pool_id}.json"
            async with aiofiles.open(pool_file, 'w') as f:
                await f.write(json.dumps(self._pool_to_dict(pool), default=str))
            
            # Add to staking queue
            await self.staking_queue.put(position_id)
            
            # Notify about staking
            await self.notification_queue.put({
                'type': 'tokens_staked',
                'position_id': position_id,
                'pool_id': pool_id,
                'member_id': member_id,
                'amount': amount,
                'duration_days': duration_days,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "position_id": position_id,
                "message": f"Staked {amount} tokens for {duration_days} days"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to stake tokens: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def unstake_tokens(self, position_id: str) -> Dict:
        """Unstake tokens from a position."""
        try:
            if position_id not in self.staking_positions:
                return {"success": False, "message": "Staking position not found"}
            
            position = self.staking_positions[position_id]
            
            if position.status != StakingStatus.ACTIVE:
                return {"success": False, "message": f"Position is {position.status.value}, not active"}
            
            # Update position status
            position.status = StakingStatus.UNSTAKING
            position.end_time = datetime.now()
            
            # Get pool
            pool_id = position.metadata['pool_id']
            pool = self.token_pools[pool_id]
            
            # Update pool
            pool.staked_supply -= position.amount
            pool.circulating_supply += position.amount
            pool.updated_at = datetime.now()
            
            # Save position
            positions_dir = self.data_directory / 'positions'
            position_file = positions_dir / f"{position_id}.json"
            async with aiofiles.open(position_file, 'w') as f:
                await f.write(json.dumps(self._position_to_dict(position), default=str))
            
            # Save updated pool
            pools_dir = self.data_directory / 'pools'
            pool_file = pools_dir / f"{pool_id}.json"
            async with aiofiles.open(pool_file, 'w') as f:
                await f.write(json.dumps(self._pool_to_dict(pool), default=str))
            
            # Notify about unstaking
            await self.notification_queue.put({
                'type': 'tokens_unstaked',
                'position_id': position_id,
                'pool_id': pool_id,
                'member_id': position.member_id,
                'amount': position.amount,
                'rewards_earned': position.rewards_earned,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "message": f"Unstaked {position.amount} tokens",
                "rewards_earned": position.rewards_earned
            }
            
        except Exception as e:
            self.logger.error(f"Failed to unstake tokens: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def set_reward_rate(self, pool_id: str, rate: float) -> Dict:
        """Set the reward rate for a token pool."""
        try:
            if pool_id not in self.token_pools:
                return {"success": False, "message": "Token pool not found"}
            
            # Update reward rate
            self.reward_rates[pool_id] = rate
            
            # Save reward rates
            rates_file = self.data_directory / 'reward_rates.json'
            async with aiofiles.open(rates_file, 'w') as f:
                await f.write(json.dumps(self.reward_rates))
            
            # Notify about reward rate update
            await self.notification_queue.put({
                'type': 'reward_rate_updated',
                'pool_id': pool_id,
                'rate': rate,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "message": f"Updated reward rate for pool {pool_id} to {rate}"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to set reward rate: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def set_lockup_period(self, pool_id: str, days: int) -> Dict:
        """Set the lockup period for a token pool."""
        try:
            if pool_id not in self.token_pools:
                return {"success": False, "message": "Token pool not found"}
            
            # Update lockup period
            self.lockup_periods[pool_id] = days
            
            # Save lockup periods
            periods_file = self.data_directory / 'lockup_periods.json'
            async with aiofiles.open(periods_file, 'w') as f:
                await f.write(json.dumps(self.lockup_periods))
            
            # Notify about lockup period update
            await self.notification_queue.put({
                'type': 'lockup_period_updated',
                'pool_id': pool_id,
                'days': days,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "message": f"Updated lockup period for pool {pool_id} to {days} days"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to set lockup period: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def _process_staking_queue(self):
        """Process the staking queue."""
        while True:
            try:
                position_id = await self.staking_queue.get()
                
                # Process staking position
                position = self.staking_positions.get(position_id)
                if position and position.status == StakingStatus.ACTIVE:
                    # Check if staking period has ended
                    if datetime.now() >= position.end_time:
                        await self.unstake_tokens(position_id)
                
                self.staking_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing staking queue: {str(e)}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _process_reward_queue(self):
        """Process the reward queue."""
        while True:
            try:
                position_id = await self.reward_queue.get()
                
                # Process reward calculation
                position = self.staking_positions.get(position_id)
                if position and position.status == StakingStatus.ACTIVE:
                    # Calculate and distribute rewards
                    await self._calculate_rewards(position)
                
                self.reward_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing reward queue: {str(e)}")
            
            await asyncio.sleep(3600)  # Check every hour
    
    async def _process_distribution_queue(self):
        """Process the distribution queue."""
        while True:
            try:
                distribution = await self.distribution_queue.get()
                
                # Process token distribution
                pool_id = distribution['pool_id']
                member_id = distribution['member_id']
                amount = distribution['amount']
                
                # Update member's token balance
                # This would update the member's balance in the DAO
                
                self.distribution_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing distribution queue: {str(e)}")
            
            await asyncio.sleep(1)
    
    async def _update_rewards(self):
        """Periodically update rewards for all active staking positions."""
        while True:
            try:
                # Update rewards for all active positions
                for position in self.staking_positions.values():
                    if position.status == StakingStatus.ACTIVE:
                        await self._calculate_rewards(position)
                
            except Exception as e:
                self.logger.error(f"Error updating rewards: {str(e)}")
            
            # Update every hour
            await asyncio.sleep(3600)
    
    async def _calculate_rewards(self, position: StakingPosition):
        """Calculate and distribute rewards for a staking position."""
        try:
            pool_id = position.metadata['pool_id']
            pool = self.token_pools[pool_id]
            
            # Get reward rate
            rate = self.reward_rates.get(pool_id, 0.0)
            
            # Calculate time elapsed
            elapsed = datetime.now() - position.start_time
            days_elapsed = elapsed.total_seconds() / (24 * 3600)
            
            # Calculate rewards
            rewards = position.amount * rate * days_elapsed / 365
            
            # Update position
            position.rewards_earned += rewards
            position.updated_at = datetime.now()
            
            # Save updated position
            positions_dir = self.data_directory / 'positions'
            position_file = positions_dir / f"{position.id}.json"
            async with aiofiles.open(position_file, 'w') as f:
                await f.write(json.dumps(self._position_to_dict(position), default=str))
            
            # Add to reward queue for distribution
            await self.reward_queue.put(position.id)
            
            # Notify about rewards
            await self.notification_queue.put({
                'type': 'rewards_calculated',
                'position_id': position.id,
                'pool_id': pool_id,
                'member_id': position.member_id,
                'rewards': rewards,
                'total_rewards': position.rewards_earned,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error calculating rewards: {str(e)}")
    
    def _pool_to_dict(self, pool: TokenPool) -> Dict:
        """Convert a TokenPool object to a dictionary."""
        return {
            'id': pool.id,
            'type': pool.type.value,
            'total_supply': pool.total_supply,
            'circulating_supply': pool.circulating_supply,
            'locked_supply': pool.locked_supply,
            'staked_supply': pool.staked_supply,
            'created_at': pool.created_at.isoformat(),
            'updated_at': pool.updated_at.isoformat(),
            'metadata': pool.metadata
        }
    
    def _dict_to_pool(self, data: Dict) -> TokenPool:
        """Convert a dictionary to a TokenPool object."""
        return TokenPool(
            id=data['id'],
            type=TokenType[data['type'].upper()],
            total_supply=data['total_supply'],
            circulating_supply=data['circulating_supply'],
            locked_supply=data['locked_supply'],
            staked_supply=data['staked_supply'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            metadata=data.get('metadata', {})
        )
    
    def _position_to_dict(self, position: StakingPosition) -> Dict:
        """Convert a StakingPosition object to a dictionary."""
        return {
            'id': position.id,
            'member_id': position.member_id,
            'token_type': position.token_type.value,
            'amount': position.amount,
            'status': position.status.value,
            'start_time': position.start_time.isoformat(),
            'end_time': position.end_time.isoformat() if position.end_time else None,
            'rewards_earned': position.rewards_earned,
            'metadata': position.metadata
        }
    
    def _dict_to_position(self, data: Dict) -> StakingPosition:
        """Convert a dictionary to a StakingPosition object."""
        return StakingPosition(
            id=data['id'],
            member_id=data['member_id'],
            token_type=TokenType[data['token_type'].upper()],
            amount=data['amount'],
            status=StakingStatus[data['status'].upper()],
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
            rewards_earned=data['rewards_earned'],
            metadata=data.get('metadata', {})
        )
    
    async def _handle_error_type(self, error_type: str, error_data: Dict) -> Dict:
        """Handle different types of errors that might occur during token economics operations.
        
        Args:
            error_type: The type of error that occurred
            error_data: Additional data about the error
            
        Returns:
            Dict containing error handling results
        """
        try:
            if error_type == "token_error":
                # Handle token-related errors
                token_id = error_data.get('token_id')
                if token_id in self.tokens:
                    token = self.tokens[token_id]
                    token.status = TokenStatus.SUSPENDED
                    self.logger.warning(f"Token {token_id} suspended due to error: {error_data.get('message')}")
                    return {"success": True, "action": "token_suspended", "token_id": token_id}
                    
            elif error_type == "transaction_error":
                # Handle transaction-related errors
                transaction_id = error_data.get('transaction_id')
                if transaction_id in self.transactions:
                    transaction = self.transactions[transaction_id]
                    transaction.status = TransactionStatus.FAILED
                    self.logger.warning(f"Transaction {transaction_id} marked as failed: {error_data.get('message')}")
                    return {"success": True, "action": "transaction_failed", "transaction_id": transaction_id}
                    
            elif error_type == "market_error":
                # Handle market-related errors
                market_id = error_data.get('market_id')
                if market_id in self.markets:
                    market = self.markets[market_id]
                    market.status = MarketStatus.HALTED
                    self.logger.warning(f"Market {market_id} halted due to error: {error_data.get('message')}")
                    return {"success": True, "action": "market_halted", "market_id": market_id}
                    
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