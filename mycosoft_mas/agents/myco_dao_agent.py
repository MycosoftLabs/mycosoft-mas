import asyncio
import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import json
from pathlib import Path
import aiohttp
import aiofiles
from dataclasses import dataclass
from enum import Enum

from .base_agent import BaseAgent

class DAOStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    UPGRADING = "upgrading"

class ProposalStatus(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    VOTING = "voting"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"

class VoteType(Enum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"

@dataclass
class Proposal:
    id: str
    title: str
    description: str
    author: str
    status: ProposalStatus
    created_at: datetime
    updated_at: datetime
    voting_start: Optional[datetime]
    voting_end: Optional[datetime]
    votes: Dict[str, VoteType]
    execution_result: Optional[Dict]
    metadata: Dict[str, Any]

class MycoDAOAgent(BaseAgent):
    """
    MycoDAO Agent - Manages the MycoDAO ecosystem for Mycosoft, Inc.
    Handles governance, proposals, voting, and token economics.
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        super().__init__(agent_id=agent_id, name=name, config=config)
        
        # Initialize DAO state
        self.status = DAOStatus.ACTIVE
        self.proposals = {}
        self.members = {}
        self.tokens = {}
        self.voting_power = {}
        self.treasury = 0.0
        
        # Initialize directories
        self.data_directory = Path(config.get('data_directory', 'data/myco_dao'))
        self.data_directory.mkdir(parents=True, exist_ok=True)
        self.output_directory = Path(config.get('output_directory', 'output/myco_dao'))
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize queues
        self.proposal_queue = asyncio.Queue()
        self.voting_queue = asyncio.Queue()
        self.execution_queue = asyncio.Queue()
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
    async def initialize(self):
        """Initialize the MycoDAO agent."""
        await super().initialize()
        await self._load_dao_data()
        await self._start_background_tasks()
        self.logger.info(f"MycoDAO Agent {self.name} initialized successfully")
        
    async def _load_dao_data(self):
        """Load DAO data from storage."""
        try:
            # Load proposals
            proposals_dir = self.data_directory / 'proposals'
            proposals_dir.mkdir(exist_ok=True)
            
            for proposal_file in proposals_dir.glob('*.json'):
                async with aiofiles.open(proposal_file, 'r') as f:
                    proposal_data = json.loads(await f.read())
                    proposal = self._dict_to_proposal(proposal_data)
                    self.proposals[proposal.id] = proposal
            
            # Load members
            members_file = self.data_directory / 'members.json'
            if members_file.exists():
                async with aiofiles.open(members_file, 'r') as f:
                    self.members = json.loads(await f.read())
            
            # Load tokens
            tokens_file = self.data_directory / 'tokens.json'
            if tokens_file.exists():
                async with aiofiles.open(tokens_file, 'r') as f:
                    self.tokens = json.loads(await f.read())
            
            # Load voting power
            voting_power_file = self.data_directory / 'voting_power.json'
            if voting_power_file.exists():
                async with aiofiles.open(voting_power_file, 'r') as f:
                    self.voting_power = json.loads(await f.read())
            
            # Load treasury
            treasury_file = self.data_directory / 'treasury.json'
            if treasury_file.exists():
                async with aiofiles.open(treasury_file, 'r') as f:
                    treasury_data = json.loads(await f.read())
                    self.treasury = treasury_data.get('amount', 0.0)
            
            self.logger.info(f"Loaded {len(self.proposals)} proposals, {len(self.members)} members")
            
        except Exception as e:
            self.logger.error(f"Error loading DAO data: {str(e)}")
            raise
    
    async def _start_background_tasks(self):
        """Start background tasks for the DAO."""
        asyncio.create_task(self._process_proposal_queue())
        asyncio.create_task(self._process_voting_queue())
        asyncio.create_task(self._process_execution_queue())
        asyncio.create_task(self._update_voting_power())
        asyncio.create_task(self._process_governance_updates())
        self.logger.info("Started MycoDAO background tasks")
    
    async def create_proposal(self, proposal_data: Dict) -> Dict:
        """Create a new proposal."""
        try:
            proposal_id = proposal_data.get('id', f"prop_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            if proposal_id in self.proposals:
                return {"success": False, "message": "Proposal ID already exists"}
            
            proposal = Proposal(
                id=proposal_id,
                title=proposal_data['title'],
                description=proposal_data['description'],
                author=proposal_data['author'],
                status=ProposalStatus.DRAFT,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                voting_start=None,
                voting_end=None,
                votes={},
                execution_result=None,
                metadata=proposal_data.get('metadata', {})
            )
            
            # Add to proposals dictionary
            self.proposals[proposal_id] = proposal
            
            # Save proposal
            proposals_dir = self.data_directory / 'proposals'
            proposals_dir.mkdir(exist_ok=True)
            
            proposal_file = proposals_dir / f"{proposal_id}.json"
            async with aiofiles.open(proposal_file, 'w') as f:
                await f.write(json.dumps(self._proposal_to_dict(proposal), default=str))
            
            # Add to proposal queue
            await self.proposal_queue.put(proposal_id)
            
            # Notify about new proposal
            await self.notification_queue.put({
                'type': 'proposal_created',
                'proposal_id': proposal_id,
                'proposal_title': proposal.title,
                'author': proposal.author,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "proposal_id": proposal_id,
                "message": "Proposal created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create proposal: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def submit_proposal(self, proposal_id: str) -> Dict:
        """Submit a proposal for voting."""
        try:
            if proposal_id not in self.proposals:
                return {"success": False, "message": "Proposal not found"}
            
            proposal = self.proposals[proposal_id]
            
            if proposal.status != ProposalStatus.DRAFT:
                return {"success": False, "message": f"Proposal is already {proposal.status.value}"}
            
            # Update proposal status
            proposal.status = ProposalStatus.SUBMITTED
            proposal.updated_at = datetime.now()
            
            # Save updated proposal
            proposals_dir = self.data_directory / 'proposals'
            proposal_file = proposals_dir / f"{proposal_id}.json"
            async with aiofiles.open(proposal_file, 'w') as f:
                await f.write(json.dumps(self._proposal_to_dict(proposal), default=str))
            
            # Notify about proposal submission
            await self.notification_queue.put({
                'type': 'proposal_submitted',
                'proposal_id': proposal_id,
                'proposal_title': proposal.title,
                'author': proposal.author,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "message": f"Proposal {proposal.title} submitted successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to submit proposal: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def start_voting(self, proposal_id: str, duration_days: int = 7) -> Dict:
        """Start voting on a proposal."""
        try:
            if proposal_id not in self.proposals:
                return {"success": False, "message": "Proposal not found"}
            
            proposal = self.proposals[proposal_id]
            
            if proposal.status != ProposalStatus.SUBMITTED:
                return {"success": False, "message": f"Proposal is {proposal.status.value}, not submitted"}
            
            # Set voting period
            proposal.voting_start = datetime.now()
            proposal.voting_end = proposal.voting_start + asyncio.timedelta(days=duration_days)
            proposal.status = ProposalStatus.VOTING
            proposal.updated_at = datetime.now()
            
            # Save updated proposal
            proposals_dir = self.data_directory / 'proposals'
            proposal_file = proposals_dir / f"{proposal_id}.json"
            async with aiofiles.open(proposal_file, 'w') as f:
                await f.write(json.dumps(self._proposal_to_dict(proposal), default=str))
            
            # Add to voting queue
            await self.voting_queue.put(proposal_id)
            
            # Notify about voting start
            await self.notification_queue.put({
                'type': 'voting_started',
                'proposal_id': proposal_id,
                'proposal_title': proposal.title,
                'voting_start': proposal.voting_start.isoformat(),
                'voting_end': proposal.voting_end.isoformat(),
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "message": f"Voting started for proposal {proposal.title}",
                "voting_start": proposal.voting_start.isoformat(),
                "voting_end": proposal.voting_end.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start voting: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def cast_vote(self, proposal_id: str, member_id: str, vote_type: str) -> Dict:
        """Cast a vote on a proposal."""
        try:
            if proposal_id not in self.proposals:
                return {"success": False, "message": "Proposal not found"}
            
            if member_id not in self.members:
                return {"success": False, "message": "Member not found"}
            
            proposal = self.proposals[proposal_id]
            
            if proposal.status != ProposalStatus.VOTING:
                return {"success": False, "message": f"Proposal is {proposal.status.value}, not in voting"}
            
            if datetime.now() > proposal.voting_end:
                return {"success": False, "message": "Voting period has ended"}
            
            # Cast vote
            vote = VoteType[vote_type.upper()]
            proposal.votes[member_id] = vote
            proposal.updated_at = datetime.now()
            
            # Save updated proposal
            proposals_dir = self.data_directory / 'proposals'
            proposal_file = proposals_dir / f"{proposal_id}.json"
            async with aiofiles.open(proposal_file, 'w') as f:
                await f.write(json.dumps(self._proposal_to_dict(proposal), default=str))
            
            # Notify about vote
            await self.notification_queue.put({
                'type': 'vote_cast',
                'proposal_id': proposal_id,
                'proposal_title': proposal.title,
                'member_id': member_id,
                'vote': vote.value,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "message": f"Vote cast successfully: {vote.value}"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cast vote: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def end_voting(self, proposal_id: str) -> Dict:
        """End voting on a proposal and determine the result."""
        try:
            if proposal_id not in self.proposals:
                return {"success": False, "message": "Proposal not found"}
            
            proposal = self.proposals[proposal_id]
            
            if proposal.status != ProposalStatus.VOTING:
                return {"success": False, "message": f"Proposal is {proposal.status.value}, not in voting"}
            
            # Calculate voting results
            yes_votes = sum(1 for vote in proposal.votes.values() if vote == VoteType.YES)
            no_votes = sum(1 for vote in proposal.votes.values() if vote == VoteType.NO)
            abstain_votes = sum(1 for vote in proposal.votes.values() if vote == VoteType.ABSTAIN)
            
            # Calculate weighted voting power
            yes_power = sum(self.voting_power.get(member_id, 0) for member_id, vote in proposal.votes.items() if vote == VoteType.YES)
            no_power = sum(self.voting_power.get(member_id, 0) for member_id, vote in proposal.votes.items() if vote == VoteType.NO)
            
            # Determine result
            if yes_power > no_power:
                proposal.status = ProposalStatus.PASSED
                result = "passed"
            else:
                proposal.status = ProposalStatus.REJECTED
                result = "rejected"
            
            proposal.updated_at = datetime.now()
            
            # Save updated proposal
            proposals_dir = self.data_directory / 'proposals'
            proposal_file = proposals_dir / f"{proposal_id}.json"
            async with aiofiles.open(proposal_file, 'w') as f:
                await f.write(json.dumps(self._proposal_to_dict(proposal), default=str))
            
            # If passed, add to execution queue
            if proposal.status == ProposalStatus.PASSED:
                await self.execution_queue.put(proposal_id)
            
            # Notify about voting end
            await self.notification_queue.put({
                'type': 'voting_ended',
                'proposal_id': proposal_id,
                'proposal_title': proposal.title,
                'result': result,
                'yes_votes': yes_votes,
                'no_votes': no_votes,
                'abstain_votes': abstain_votes,
                'yes_power': yes_power,
                'no_power': no_power,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "message": f"Voting ended for proposal {proposal.title}",
                "result": result,
                "yes_votes": yes_votes,
                "no_votes": no_votes,
                "abstain_votes": abstain_votes,
                "yes_power": yes_power,
                "no_power": no_power
            }
            
        except Exception as e:
            self.logger.error(f"Failed to end voting: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def execute_proposal(self, proposal_id: str) -> Dict:
        """Execute a passed proposal."""
        try:
            if proposal_id not in self.proposals:
                return {"success": False, "message": "Proposal not found"}
            
            proposal = self.proposals[proposal_id]
            
            if proposal.status != ProposalStatus.PASSED:
                return {"success": False, "message": f"Proposal is {proposal.status.value}, not passed"}
            
            # Execute proposal based on type
            execution_result = await self._execute_proposal_action(proposal)
            
            # Update proposal status
            proposal.status = ProposalStatus.EXECUTED
            proposal.execution_result = execution_result
            proposal.updated_at = datetime.now()
            
            # Save updated proposal
            proposals_dir = self.data_directory / 'proposals'
            proposal_file = proposals_dir / f"{proposal_id}.json"
            async with aiofiles.open(proposal_file, 'w') as f:
                await f.write(json.dumps(self._proposal_to_dict(proposal), default=str))
            
            # Notify about proposal execution
            await self.notification_queue.put({
                'type': 'proposal_executed',
                'proposal_id': proposal_id,
                'proposal_title': proposal.title,
                'execution_result': execution_result,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "message": f"Proposal {proposal.title} executed successfully",
                "execution_result": execution_result
            }
            
        except Exception as e:
            self.logger.error(f"Failed to execute proposal: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def _execute_proposal_action(self, proposal: Proposal) -> Dict:
        """Execute the action specified in the proposal."""
        # This is a placeholder implementation
        # In a real implementation, this would execute the specific action
        # based on the proposal type and parameters
        
        proposal_type = proposal.metadata.get('type', 'unknown')
        
        if proposal_type == 'funding':
            # Handle funding proposal
            amount = proposal.metadata.get('amount', 0)
            recipient = proposal.metadata.get('recipient', '')
            
            if amount > self.treasury:
                return {
                    "success": False,
                    "message": "Insufficient funds in treasury",
                    "requested": amount,
                    "available": self.treasury
                }
            
            # Update treasury
            self.treasury -= amount
            
            # Save updated treasury
            treasury_file = self.data_directory / 'treasury.json'
            async with aiofiles.open(treasury_file, 'w') as f:
                await f.write(json.dumps({"amount": self.treasury}))
            
            return {
                "success": True,
                "message": f"Funded {recipient} with {amount} tokens",
                "recipient": recipient,
                "amount": amount,
                "remaining_treasury": self.treasury
            }
            
        elif proposal_type == 'parameter':
            # Handle parameter change proposal
            parameter = proposal.metadata.get('parameter', '')
            value = proposal.metadata.get('value', None)
            
            # Update parameter
            # This would update a specific parameter in the system
            
            return {
                "success": True,
                "message": f"Updated parameter {parameter} to {value}",
                "parameter": parameter,
                "value": value
            }
            
        else:
            return {
                "success": False,
                "message": f"Unknown proposal type: {proposal_type}"
            }
    
    async def add_member(self, member_data: Dict) -> Dict:
        """Add a new member to the DAO."""
        try:
            member_id = member_data.get('id', f"member_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            if member_id in self.members:
                return {"success": False, "message": "Member ID already exists"}
            
            member = {
                'id': member_id,
                'name': member_data['name'],
                'email': member_data['email'],
                'joined_at': datetime.now().isoformat(),
                'status': 'active',
                'tokens': 0,
                'voting_power': 0,
                'metadata': member_data.get('metadata', {})
            }
            
            # Add to members dictionary
            self.members[member_id] = member
            
            # Save members
            members_file = self.data_directory / 'members.json'
            async with aiofiles.open(members_file, 'w') as f:
                await f.write(json.dumps(self.members))
            
            # Notify about new member
            await self.notification_queue.put({
                'type': 'member_added',
                'member_id': member_id,
                'member_name': member['name'],
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "member_id": member_id,
                "message": "Member added successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to add member: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def update_voting_power(self, member_id: str, voting_power: float) -> Dict:
        """Update a member's voting power."""
        try:
            if member_id not in self.members:
                return {"success": False, "message": "Member not found"}
            
            # Update voting power
            self.voting_power[member_id] = voting_power
            self.members[member_id]['voting_power'] = voting_power
            
            # Save voting power
            voting_power_file = self.data_directory / 'voting_power.json'
            async with aiofiles.open(voting_power_file, 'w') as f:
                await f.write(json.dumps(self.voting_power))
            
            # Save members
            members_file = self.data_directory / 'members.json'
            async with aiofiles.open(members_file, 'w') as f:
                await f.write(json.dumps(self.members))
            
            # Notify about voting power update
            await self.notification_queue.put({
                'type': 'voting_power_updated',
                'member_id': member_id,
                'member_name': self.members[member_id]['name'],
                'voting_power': voting_power,
                'timestamp': datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "message": f"Voting power updated for member {member_id}",
                "voting_power": voting_power
            }
            
        except Exception as e:
            self.logger.error(f"Failed to update voting power: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def _process_proposal_queue(self):
        """Process the proposal queue."""
        while True:
            try:
                proposal_id = await self.proposal_queue.get()
                
                # Process proposal
                proposal = self.proposals.get(proposal_id)
                if proposal:
                    # Validate proposal
                    validation_result = await self._validate_proposal(proposal)
                    
                    if validation_result['success']:
                        # Auto-submit if validation passes
                        await self.submit_proposal(proposal_id)
                    else:
                        # Update proposal with validation errors
                        proposal.status = ProposalStatus.REJECTED
                        proposal.metadata['validation_errors'] = validation_result['errors']
                        proposal.updated_at = datetime.now()
                        
                        # Save updated proposal
                        proposals_dir = self.data_directory / 'proposals'
                        proposal_file = proposals_dir / f"{proposal_id}.json"
                        async with aiofiles.open(proposal_file, 'w') as f:
                            await f.write(json.dumps(self._proposal_to_dict(proposal), default=str))
                        
                        # Notify about validation failure
                        await self.notification_queue.put({
                            'type': 'proposal_validation_failed',
                            'proposal_id': proposal_id,
                            'proposal_title': proposal.title,
                            'errors': validation_result['errors'],
                            'timestamp': datetime.now().isoformat()
                        })
                
                self.proposal_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing proposal queue: {str(e)}")
            
            await asyncio.sleep(1)
    
    async def _process_voting_queue(self):
        """Process the voting queue."""
        while True:
            try:
                proposal_id = await self.voting_queue.get()
                
                # Process voting
                proposal = self.proposals.get(proposal_id)
                if proposal and proposal.status == ProposalStatus.VOTING:
                    # Check if voting period has ended
                    if datetime.now() > proposal.voting_end:
                        await this.end_voting(proposal_id)
                
                self.voting_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing voting queue: {str(e)}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _process_execution_queue(self):
        """Process the execution queue."""
        while True:
            try:
                proposal_id = await self.execution_queue.get()
                
                # Process execution
                proposal = self.proposals.get(proposal_id)
                if proposal and proposal.status == ProposalStatus.PASSED:
                    await this.execute_proposal(proposal_id)
                
                self.execution_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing execution queue: {str(e)}")
            
            await asyncio.sleep(1)
    
    async def _update_voting_power(self):
        """Periodically update voting power based on token holdings."""
        while True:
            try:
                # Update voting power based on token holdings
                for member_id, member in self.members.items():
                    tokens = member.get('tokens', 0)
                    # Simple linear voting power calculation
                    voting_power = tokens
                    self.voting_power[member_id] = voting_power
                    member['voting_power'] = voting_power
                
                # Save voting power
                voting_power_file = self.data_directory / 'voting_power.json'
                async with aiofiles.open(voting_power_file, 'w') as f:
                    await f.write(json.dumps(self.voting_power))
                
                # Save members
                members_file = self.data_directory / 'members.json'
                async with aiofiles.open(members_file, 'w') as f:
                    await f.write(json.dumps(self.members))
                
            except Exception as e:
                self.logger.error(f"Error updating voting power: {str(e)}")
            
            # Update every hour
            await asyncio.sleep(3600)
    
    async def _validate_proposal(self, proposal: Proposal) -> Dict:
        """Validate a proposal."""
        errors = []
        
        # Check title
        if not proposal.title or len(proposal.title) < 5:
            errors.append("Title must be at least 5 characters long")
        
        # Check description
        if not proposal.description or len(proposal.description) < 20:
            errors.append("Description must be at least 20 characters long")
        
        # Check author
        if not proposal.author or proposal.author not in self.members:
            errors.append("Author must be a valid member")
        
        # Check metadata
        if 'type' not in proposal.metadata:
            errors.append("Proposal must have a type")
        
        # Check type-specific validation
        proposal_type = proposal.metadata.get('type', '')
        
        if proposal_type == 'funding':
            amount = proposal.metadata.get('amount', 0)
            recipient = proposal.metadata.get('recipient', '')
            
            if amount <= 0:
                errors.append("Funding amount must be positive")
            
            if amount > this.treasury:
                errors.append(f"Funding amount ({amount}) exceeds treasury ({this.treasury})")
            
            if not recipient:
                errors.append("Recipient must be specified")
        
        elif proposal_type == 'parameter':
            parameter = proposal.metadata.get('parameter', '')
            value = proposal.metadata.get('value', None)
            
            if not parameter:
                errors.append("Parameter must be specified")
            
            if value is None:
                errors.append("Value must be specified")
        
        return {
            "success": len(errors) == 0,
            "errors": errors
        }
    
    def _proposal_to_dict(self, proposal: Proposal) -> Dict:
        """Convert a Proposal object to a dictionary."""
        return {
            'id': proposal.id,
            'title': proposal.title,
            'description': proposal.description,
            'author': proposal.author,
            'status': proposal.status.value,
            'created_at': proposal.created_at.isoformat(),
            'updated_at': proposal.updated_at.isoformat(),
            'voting_start': proposal.voting_start.isoformat() if proposal.voting_start else None,
            'voting_end': proposal.voting_end.isoformat() if proposal.voting_end else None,
            'votes': {k: v.value for k, v in proposal.votes.items()},
            'execution_result': proposal.execution_result,
            'metadata': proposal.metadata
        }
    
    def _dict_to_proposal(self, data: Dict) -> Proposal:
        """Convert a dictionary to a Proposal object."""
        return Proposal(
            id=data['id'],
            title=data['title'],
            description=data['description'],
            author=data['author'],
            status=ProposalStatus[data['status'].upper()],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            voting_start=datetime.fromisoformat(data['voting_start']) if data.get('voting_start') else None,
            voting_end=datetime.fromisoformat(data['voting_end']) if data.get('voting_end') else None,
            votes={k: VoteType[v.upper()] for k, v in data.get('votes', {}).items()},
            execution_result=data.get('execution_result'),
            metadata=data.get('metadata', {})
        )

    async def _process_governance_updates(self):
        """Process governance updates and changes."""
        while True:
            try:
                # Process governance updates
                await asyncio.sleep(300)  # 5 minutes
            except Exception as e:
                self.logger.error(f"Error processing governance updates: {str(e)}")
                await asyncio.sleep(60)

    async def _handle_error_type(self, error_type: str, error: Dict) -> Dict:
        """
        Handle DAO-specific error types.
        
        Args:
            error_type: Type of error to handle
            error: Error data dictionary
            
        Returns:
            Dict: Result of error handling
        """
        try:
            error_msg = error.get('error', 'Unknown error')
            error_data = error.get('data', {})
            
            if error_type == 'proposal_error':
                proposal_id = error_data.get('proposal_id')
                if proposal_id in self.proposals:
                    proposal = self.proposals[proposal_id]
                    # If proposal is in voting, pause it
                    if proposal.status == ProposalStatus.VOTING:
                        proposal.status = ProposalStatus.DRAFT
                        proposal.updated_at = datetime.now()
                        # Save updated proposal
                        proposals_dir = self.data_directory / 'proposals'
                        proposal_file = proposals_dir / f"{proposal_id}.json"
                        async with aiofiles.open(proposal_file, 'w') as f:
                            await f.write(json.dumps(self._proposal_to_dict(proposal), default=str))
                        self.logger.warning(f"Proposal {proposal_id} reverted to draft due to error: {error_msg}")
                        return {"success": True, "message": f"Proposal {proposal_id} reverted to draft", "action_taken": "revert_proposal"}
            
            elif error_type == 'voting_error':
                proposal_id = error_data.get('proposal_id')
                member_id = error_data.get('member_id')
                if proposal_id in self.proposals and member_id in self.members:
                    # Remove problematic vote
                    proposal = self.proposals[proposal_id]
                    if member_id in proposal.votes:
                        del proposal.votes[member_id]
                        proposal.updated_at = datetime.now()
                        # Save updated proposal
                        proposals_dir = self.data_directory / 'proposals'
                        proposal_file = proposals_dir / f"{proposal_id}.json"
                        async with aiofiles.open(proposal_file, 'w') as f:
                            await f.write(json.dumps(self._proposal_to_dict(proposal), default=str))
                        self.logger.warning(f"Vote removed for proposal {proposal_id} by member {member_id} due to error: {error_msg}")
                        return {"success": True, "message": "Vote removed", "action_taken": "remove_vote"}
            
            elif error_type == 'execution_error':
                proposal_id = error_data.get('proposal_id')
                if proposal_id in self.proposals:
                    proposal = self.proposals[proposal_id]
                    # If proposal was being executed, mark as failed
                    if proposal.status == ProposalStatus.PASSED:
                        proposal.status = ProposalStatus.REJECTED
                        proposal.updated_at = datetime.now()
                        proposal.execution_result = {"status": "failed", "error": error_msg}
                        # Save updated proposal
                        proposals_dir = self.data_directory / 'proposals'
                        proposal_file = proposals_dir / f"{proposal_id}.json"
                        async with aiofiles.open(proposal_file, 'w') as f:
                            await f.write(json.dumps(self._proposal_to_dict(proposal), default=str))
                        self.logger.warning(f"Proposal {proposal_id} execution failed: {error_msg}")
                        return {"success": True, "message": "Proposal execution failed", "action_taken": "mark_execution_failed"}
            
            elif error_type == 'member_error':
                member_id = error_data.get('member_id')
                if member_id in self.members:
                    # Temporarily suspend member
                    self.members[member_id]['status'] = 'suspended'
                    self.members[member_id]['suspended_at'] = datetime.now().isoformat()
                    # Save updated members
                    members_file = self.data_directory / 'members.json'
                    async with aiofiles.open(members_file, 'w') as f:
                        await f.write(json.dumps(self.members))
                    self.logger.warning(f"Member {member_id} suspended due to error: {error_msg}")
                    return {"success": True, "message": f"Member {member_id} suspended", "action_taken": "suspend_member"}
            
            # Handle health check errors
            elif error_type == 'health_check_error':
                service = error_data.get('service', 'unknown')
                self.logger.error(f"Health check failed for {service}: {error_msg}")
                # Put DAO in maintenance mode
                self.status = DAOStatus.MAINTENANCE
                # Notify members
                await self.notification_queue.put({
                    'type': 'dao_maintenance',
                    'service': service,
                    'error': error_msg,
                    'timestamp': datetime.now().isoformat()
                })
                return {"success": True, "message": "DAO put in maintenance mode", "action_taken": "maintenance_mode"}
            
            # Default error handling
            self.logger.error(f"Unhandled error type {error_type}: {error_msg}")
            return {"success": False, "message": f"Unhandled error type: {error_type}", "action_taken": "none"}
            
        except Exception as e:
            self.logger.error(f"Error in error handler: {str(e)}")
            return {"success": False, "message": f"Error handler failed: {str(e)}", "action_taken": "none"} 