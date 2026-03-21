"""
Corporate Operations Agent for Mycosoft MAS

This module implements the CorporateOperationsAgent that handles corporate operations,
including Clerky integration, board resolutions, and corporate governance.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent


class CorporateOperationsAgent(BaseAgent):
    """
    Agent that handles corporate operations for Mycosoft Inc.

    This agent manages:
    - Corporate paperwork through Clerky
    - Board resolutions and governance
    - Corporate records and compliance
    - Document management
    """

    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the Corporate Operations Agent.

        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name for the agent
            config: Configuration dictionary for the agent
        """
        super().__init__(agent_id=agent_id, name=name, config=config)

        # Load configuration
        self.clerky_config = config.get("clerky", {})
        self.corporate_config = config.get("corporate", {})

        # Initialize state
        self.board_members = []
        self.corporate_records = {}
        self.pending_resolutions = []
        self.active_documents = {}

        # Create data directory
        self.data_dir = Path("data/corporate")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Metrics
        self.metrics.update(
            {
                "documents_processed": 0,
                "resolutions_handled": 0,
                "compliance_checks": 0,
                "board_meetings": 0,
            }
        )

    async def _initialize_services(self) -> None:
        """Initialize corporate services."""
        # Initialize Clerky client
        self.clerky_client = await self._initialize_clerky()

        # Load corporate records
        await self._load_corporate_records()

        # Initialize document management
        await self._initialize_document_management()

    async def _initialize_clerky(self) -> Any:
        """Initialize Clerky client."""
        api_key = os.getenv("CLERKY_API_KEY")
        base_url = os.getenv("CLERKY_API_BASE_URL", "https://api.clerky.com").rstrip("/")
        if not api_key:
            self.logger.warning("CLERKY_API_KEY not set - Clerky integration disabled")
            return None
        return {"api_key": api_key, "base_url": base_url}

    async def _load_corporate_records(self) -> None:
        """Load corporate records from storage."""
        records_file = self.data_dir / "corporate_records.json"
        if records_file.exists():
            self.corporate_records = json.loads(records_file.read_text(encoding="utf-8"))
        else:
            self.corporate_records = {"documents": {}, "resolutions": {}, "meetings": {}}

    async def _initialize_document_management(self) -> None:
        """Initialize document management system."""
        self.active_documents = self.corporate_records.get("documents", {})
        self.pending_resolutions = list(self.corporate_records.get("resolutions", {}).keys())

    async def process_board_resolution(self, resolution: Dict[str, Any]) -> bool:
        """
        Process a board resolution.

        Args:
            resolution: Resolution details including title, content, and voting requirements

        Returns:
            bool: True if resolution was processed successfully
        """
        try:
            # Validate resolution
            if not self._validate_resolution(resolution):
                raise ValueError("Invalid resolution format")

            # Create resolution record
            resolution_id = await self._create_resolution_record(resolution)

            # Notify board members
            await self._notify_board_members(resolution)

            # Track resolution
            self.pending_resolutions.append(resolution_id)

            # Update metrics
            self.metrics["resolutions_handled"] += 1

            return True
        except Exception as e:
            self.logger.error(f"Failed to process board resolution: {str(e)}")
            return False

    async def create_corporate_document(self, document: Dict[str, Any]) -> Optional[str]:
        """
        Create a corporate document through Clerky.

        Args:
            document: Document details including type, content, and metadata

        Returns:
            Optional[str]: Document ID if successful, None otherwise
        """
        try:
            # Validate document
            if not self._validate_document(document):
                raise ValueError("Invalid document format")

            # Create document through Clerky
            document_id = await self._create_clerky_document(document)

            # Store document record
            await self._store_document_record(document_id, document)

            # Update metrics
            self.metrics["documents_processed"] += 1

            return document_id
        except Exception as e:
            self.logger.error(f"Failed to create corporate document: {str(e)}")
            return None

    async def schedule_board_meeting(self, meeting: Dict[str, Any]) -> Optional[str]:
        """
        Schedule a board meeting.

        Args:
            meeting: Meeting details including date, time, agenda, and attendees

        Returns:
            Optional[str]: Meeting ID if successful, None otherwise
        """
        try:
            # Validate meeting
            if not self._validate_meeting(meeting):
                raise ValueError("Invalid meeting format")

            # Create meeting record
            meeting_id = await self._create_meeting_record(meeting)

            # Send meeting invitations
            await self._send_meeting_invitations(meeting)

            # Update metrics
            self.metrics["board_meetings"] += 1

            return meeting_id
        except Exception as e:
            self.logger.error(f"Failed to schedule board meeting: {str(e)}")
            return None

    def _validate_resolution(self, resolution: Dict[str, Any]) -> bool:
        """Validate board resolution format."""
        required_fields = ["title", "content", "voting_requirements"]
        return all(field in resolution for field in required_fields)

    def _validate_document(self, document: Dict[str, Any]) -> bool:
        """Validate corporate document format."""
        required_fields = ["type", "content", "metadata"]
        return all(field in document for field in required_fields)

    def _validate_meeting(self, meeting: Dict[str, Any]) -> bool:
        """Validate board meeting format."""
        required_fields = ["date", "time", "agenda", "attendees"]
        return all(field in meeting for field in required_fields)

    async def _create_resolution_record(self, resolution: Dict[str, Any]) -> str:
        """Create a record for a board resolution."""
        resolution_id = f"res-{uuid.uuid4().hex[:10]}"
        self.corporate_records.setdefault("resolutions", {})[resolution_id] = {
            "id": resolution_id,
            "title": resolution["title"],
            "content": resolution["content"],
            "voting_requirements": resolution["voting_requirements"],
            "status": "pending_vote",
            "created_at": datetime.now().isoformat(),
        }
        await self._persist_corporate_records()
        return resolution_id

    async def _notify_board_members(self, resolution: Dict[str, Any]) -> None:
        """Notify board members about a new resolution."""
        self.logger.info(
            "Board notification prepared for resolution '%s' to %d members",
            resolution.get("title", "untitled"),
            len(self.board_members),
        )

    async def _create_clerky_document(self, document: Dict[str, Any]) -> str:
        """Create a document through Clerky."""
        document_id = f"doc-{uuid.uuid4().hex[:10]}"
        payload = {
            "id": document_id,
            "type": document.get("type"),
            "content": document.get("content"),
            "metadata": document.get("metadata", {}),
            "created_at": datetime.now().isoformat(),
            "source": "local",
            "clerky_synced": False,
        }

        if self.clerky_client:
            try:
                import aiohttp

                async with aiohttp.ClientSession(
                    headers={
                        "Authorization": f"Bearer {self.clerky_client['api_key']}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    }
                ) as session:
                    async with session.post(
                        f"{self.clerky_client['base_url']}/v1/documents",
                        json=document,
                        timeout=aiohttp.ClientTimeout(total=20),
                    ) as response:
                        if response.status in (200, 201):
                            remote = await response.json()
                            payload["source"] = "clerky"
                            payload["clerky_synced"] = True
                            payload["remote_id"] = remote.get("id")
                        else:
                            self.logger.warning(
                                "Clerky document create returned status %s", response.status
                            )
            except Exception as exc:
                self.logger.warning("Clerky document create failed, using local record: %s", exc)

        self.active_documents[document_id] = payload
        return document_id

    async def _store_document_record(self, document_id: str, document: Dict[str, Any]) -> None:
        """Store a record of a corporate document."""
        self.corporate_records.setdefault("documents", {})[document_id] = {
            "id": document_id,
            "type": document.get("type"),
            "metadata": document.get("metadata", {}),
            "created_at": datetime.now().isoformat(),
        }
        await self._persist_corporate_records()

    async def _create_meeting_record(self, meeting: Dict[str, Any]) -> str:
        """Create a record for a board meeting."""
        meeting_id = f"mtg-{uuid.uuid4().hex[:10]}"
        self.corporate_records.setdefault("meetings", {})[meeting_id] = {
            "id": meeting_id,
            "date": meeting["date"],
            "time": meeting["time"],
            "agenda": meeting["agenda"],
            "attendees": meeting["attendees"],
            "created_at": datetime.now().isoformat(),
        }
        await self._persist_corporate_records()
        return meeting_id

    async def _send_meeting_invitations(self, meeting: Dict[str, Any]) -> None:
        """Send meeting invitations to board members."""
        attendees = meeting.get("attendees", [])
        self.logger.info("Prepared %d board meeting invitations", len(attendees))

    async def _persist_corporate_records(self) -> None:
        records_file = self.data_dir / "corporate_records.json"
        records_file.write_text(json.dumps(self.corporate_records, indent=2), encoding="utf-8")

    async def _handle_error_type(self, error_type: str, error: Dict) -> Dict:
        """
        Handle specific types of errors.

        Args:
            error_type: Type of error to handle
            error: Error details

        Returns:
            Dict: Result of error handling
        """
        error_handlers = {
            "health_check_error": self._handle_health_check_error,
            "task_error": self._handle_task_error,
            "initialization_error": self._handle_initialization_error,
            "service_error": self._handle_service_error,
            "document_error": self._handle_document_error,
            "resolution_error": self._handle_resolution_error,
            "compliance_error": self._handle_compliance_error,
        }

        handler = error_handlers.get(error_type)
        if handler:
            return await handler(error)

        return {
            "success": False,
            "error": f"Unknown error type: {error_type}",
            "timestamp": datetime.now().isoformat(),
        }

    async def _handle_health_check_error(self, error: Dict) -> Dict:
        """Handle health check errors."""
        self.logger.error(f"Health check error: {error.get('error')}")
        return {"success": True, "action": "logged", "timestamp": datetime.now().isoformat()}

    async def _handle_task_error(self, error: Dict) -> Dict:
        """Handle task processing errors."""
        self.logger.error(f"Task error: {error.get('error')}")
        return {"success": True, "action": "logged", "timestamp": datetime.now().isoformat()}

    async def _handle_initialization_error(self, error: Dict) -> Dict:
        """Handle initialization errors."""
        self.logger.error(f"Initialization error: {error.get('error')}")
        return {"success": True, "action": "logged", "timestamp": datetime.now().isoformat()}

    async def _handle_service_error(self, error: Dict) -> Dict:
        """Handle service-related errors."""
        self.logger.error(f"Service error: {error.get('error')}")
        return {"success": True, "action": "logged", "timestamp": datetime.now().isoformat()}

    async def _handle_document_error(self, error: Dict) -> Dict:
        """Handle document processing errors."""
        self.logger.error(f"Document error: {error.get('error')}")
        return {"success": True, "action": "logged", "timestamp": datetime.now().isoformat()}

    async def _handle_resolution_error(self, error: Dict) -> Dict:
        """Handle board resolution errors."""
        self.logger.error(f"Resolution error: {error.get('error')}")
        return {"success": True, "action": "logged", "timestamp": datetime.now().isoformat()}

    async def _handle_compliance_error(self, error: Dict) -> Dict:
        """Handle compliance-related errors."""
        self.logger.error(f"Compliance error: {error.get('error')}")
        return {"success": True, "action": "logged", "timestamp": datetime.now().isoformat()}
