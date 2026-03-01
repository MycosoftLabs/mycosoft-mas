"""
Board Operations Agent for Mycosoft MAS

This module implements the BoardOperationsAgent that handles board operations,
including meeting management, voting, and board communications.
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.messaging.message_types import Message, MessageType, MessagePriority
from mycosoft_mas.agents.enums import AgentStatus, TaskType, TaskStatus, TaskPriority

class BoardOperationsAgent(BaseAgent):
    """
    Agent that handles board operations for Mycosoft Inc.
    
    This agent manages:
    - Board meeting scheduling and management
    - Board resolution voting
    - Board communications
    - Board member management
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the board operations agent."""
        super().__init__(agent_id, name, config)
        
        # Load configuration
        self.board_config = config.get("board", {})
        self.communication_config = config.get("communication", {})
        
        # Initialize state
        self.board_members = []
        self.meetings = {}
        self.resolutions = {}
        self.votes = {}
        
        # Create data directory
        self.data_dir = Path("data/board")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Metrics
        self.metrics.update({
            "meetings_scheduled": 0,
            "resolutions_processed": 0,
            "votes_recorded": 0,
            "communications_sent": 0
        })
    
    async def _initialize_services(self) -> None:
        """Initialize board services."""
        # Load board members
        await self._load_board_members()
        
        # Initialize communication channels
        await self._initialize_communication_channels()
        
        # Load existing meetings and resolutions
        await self._load_board_records()
    
    async def _load_board_members(self) -> None:
        """Load board member information."""
        members_file = self.data_dir / "board_members.json"
        members = await self._load_json_file(members_file, default=[])
        self.board_members = members if isinstance(members, list) else []
    
    async def _initialize_communication_channels(self) -> None:
        """Initialize board communication channels."""
        channels = self.communication_config.get("channels", [])
        self.communication_config["channels"] = channels
        self.logger.info("Board communication channels configured: %d", len(channels))
    
    async def _load_board_records(self) -> None:
        """Load existing board meetings and resolutions."""
        records_file = self.data_dir / "board_records.json"
        records = await self._load_json_file(records_file, default={})
        if not isinstance(records, dict):
            records = {}
        self.meetings = records.get("meetings", {})
        self.resolutions = records.get("resolutions", {})
        self.votes = records.get("votes", {})
    
    async def schedule_meeting(self, meeting_details: Dict[str, Any]) -> Optional[str]:
        """
        Schedule a board meeting.
        
        Args:
            meeting_details: Meeting details including date, time, agenda, and attendees
            
        Returns:
            Optional[str]: Meeting ID if successful, None otherwise
        """
        try:
            # Validate meeting details
            if not self._validate_meeting_details(meeting_details):
                raise ValueError("Invalid meeting details")
            
            # Create meeting
            meeting_id = await self._create_meeting(meeting_details)
            
            # Send invitations
            await self._send_meeting_invitations(meeting_id, meeting_details)
            
            # Update metrics
            self.metrics["meetings_scheduled"] += 1
            
            return meeting_id
        except Exception as e:
            self.logger.error(f"Failed to schedule meeting: {str(e)}")
            return None
    
    async def create_resolution(self, resolution_details: Dict[str, Any]) -> Optional[str]:
        """
        Create a board resolution.
        
        Args:
            resolution_details: Resolution details including title, content, and voting requirements
            
        Returns:
            Optional[str]: Resolution ID if successful, None otherwise
        """
        try:
            # Validate resolution details
            if not self._validate_resolution_details(resolution_details):
                raise ValueError("Invalid resolution details")
            
            # Create resolution
            resolution_id = await self._create_resolution(resolution_details)
            
            # Notify board members
            await self._notify_resolution(resolution_id, resolution_details)
            
            # Update metrics
            self.metrics["resolutions_processed"] += 1
            
            return resolution_id
        except Exception as e:
            self.logger.error(f"Failed to create resolution: {str(e)}")
            return None
    
    async def record_vote(self, vote_details: Dict[str, Any]) -> bool:
        """
        Record a board member's vote on a resolution.
        
        Args:
            vote_details: Vote details including resolution_id, member_id, and vote
            
        Returns:
            bool: True if vote was recorded successfully
        """
        try:
            # Validate vote details
            if not self._validate_vote_details(vote_details):
                raise ValueError("Invalid vote details")
            
            # Record vote
            await self._record_vote(vote_details)
            
            # Check if resolution is complete
            await self._check_resolution_completion(vote_details["resolution_id"])
            
            # Update metrics
            self.metrics["votes_recorded"] += 1
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to record vote: {str(e)}")
            return False
    
    async def send_board_communication(self, communication: Dict[str, Any]) -> bool:
        """
        Send a communication to board members.
        
        Args:
            communication: Communication details including type, content, and recipients
            
        Returns:
            bool: True if communication was sent successfully
        """
        try:
            # Validate communication
            if not self._validate_communication(communication):
                raise ValueError("Invalid communication format")
            
            # Send communication
            await self._send_communication(communication)
            
            # Update metrics
            self.metrics["communications_sent"] += 1
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to send board communication: {str(e)}")
            return False
    
    def _validate_meeting_details(self, details: Dict[str, Any]) -> bool:
        """Validate meeting details format."""
        required_fields = ["date", "time", "agenda", "attendees"]
        return all(field in details for field in required_fields)
    
    def _validate_resolution_details(self, details: Dict[str, Any]) -> bool:
        """Validate resolution details format."""
        required_fields = ["title", "content", "voting_requirements"]
        return all(field in details for field in required_fields)
    
    def _validate_vote_details(self, details: Dict[str, Any]) -> bool:
        """Validate vote details format."""
        required_fields = ["resolution_id", "member_id", "vote"]
        return all(field in details for field in required_fields)
    
    def _validate_communication(self, communication: Dict[str, Any]) -> bool:
        """Validate communication format."""
        required_fields = ["type", "content", "recipients"]
        return all(field in communication for field in required_fields)

    async def _load_json_file(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.logger.error("Failed to read %s: %s", path, exc)
            return default

    async def _write_json_file(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    async def _persist_board_records(self) -> None:
        records_file = self.data_dir / "board_records.json"
        payload = {
            "meetings": self.meetings,
            "resolutions": self.resolutions,
            "votes": self.votes,
        }
        await self._write_json_file(records_file, payload)
    
    async def _create_meeting(self, details: Dict[str, Any]) -> str:
        """Create a board meeting."""
        meeting_id = f"mtg-{uuid.uuid4().hex[:10]}"
        self.meetings[meeting_id] = {
            "id": meeting_id,
            "date": details["date"],
            "time": details["time"],
            "agenda": details["agenda"],
            "attendees": details["attendees"],
            "status": "scheduled",
            "created_at": datetime.now().isoformat(),
        }
        await self._persist_board_records()
        return meeting_id
    
    async def _send_meeting_invitations(self, meeting_id: str, details: Dict[str, Any]) -> None:
        """Send meeting invitations to board members."""
        communications_file = self.data_dir / "communications_log.json"
        current = await self._load_json_file(communications_file, default=[])
        recipients = details.get("attendees", [])
        current.append({
            "type": "meeting_invite",
            "meeting_id": meeting_id,
            "recipients": recipients,
            "sent_at": datetime.now().isoformat(),
        })
        await self._write_json_file(communications_file, current)
        self.logger.info("Prepared meeting invitations for %d attendees", len(recipients))
    
    async def _create_resolution(self, details: Dict[str, Any]) -> str:
        """Create a board resolution."""
        resolution_id = f"res-{uuid.uuid4().hex[:10]}"
        self.resolutions[resolution_id] = {
            "id": resolution_id,
            "title": details["title"],
            "content": details["content"],
            "voting_requirements": details["voting_requirements"],
            "status": "pending_vote",
            "created_at": datetime.now().isoformat(),
        }
        await self._persist_board_records()
        return resolution_id
    
    async def _notify_resolution(self, resolution_id: str, details: Dict[str, Any]) -> None:
        """Notify board members about a new resolution."""
        communications_file = self.data_dir / "communications_log.json"
        current = await self._load_json_file(communications_file, default=[])
        recipients = [m.get("id") for m in self.board_members if m.get("id")]
        current.append({
            "type": "resolution_notice",
            "resolution_id": resolution_id,
            "recipients": recipients,
            "sent_at": datetime.now().isoformat(),
        })
        await self._write_json_file(communications_file, current)
        self.logger.info("Prepared resolution notice for %d members", len(recipients))
    
    async def _record_vote(self, details: Dict[str, Any]) -> None:
        """Record a board member's vote."""
        resolution_id = details["resolution_id"]
        member_id = details["member_id"]
        vote_value = details["vote"]
        self.votes.setdefault(resolution_id, {})
        self.votes[resolution_id][member_id] = {
            "vote": vote_value,
            "recorded_at": datetime.now().isoformat(),
        }
        await self._persist_board_records()
    
    async def _check_resolution_completion(self, resolution_id: str) -> None:
        """Check if a resolution's voting is complete."""
        resolution = self.resolutions.get(resolution_id)
        if not resolution:
            return
        required = resolution.get("voting_requirements", {})
        required_count = required.get("min_votes")
        votes_for_resolution = self.votes.get(resolution_id, {})
        if required_count and len(votes_for_resolution) >= required_count:
            resolution["status"] = "vote_complete"
            resolution["completed_at"] = datetime.now().isoformat()
            await self._persist_board_records()
    
    async def _send_communication(self, communication: Dict[str, Any]) -> None:
        """Send a communication to board members."""
        communications_file = self.data_dir / "communications_log.json"
        current = await self._load_json_file(communications_file, default=[])
        current.append({
            "type": communication.get("type"),
            "content": communication.get("content"),
            "recipients": communication.get("recipients"),
            "sent_at": datetime.now().isoformat(),
        })
        await self._write_json_file(communications_file, current)
        self.logger.info("Prepared board communication to %d recipients", len(communication.get("recipients", [])))