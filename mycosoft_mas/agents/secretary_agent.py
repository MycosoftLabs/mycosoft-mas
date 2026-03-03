from datetime import datetime, timedelta
import asyncio
import logging
from typing import Dict, List, Optional, Union
from .base_agent import BaseAgent
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pytz

class SecretaryAgent(BaseAgent):
    def __init__(self, agent_id: str, name: str, config: dict):
        super().__init__(agent_id, name, config)
        self.calendar_service = None
        self.gmail_service = None
        self.drive_service = None
        self.timezone = pytz.timezone(config.get('timezone', 'America/Los_Angeles'))
        self.meeting_buffer = timedelta(minutes=config.get('meeting_buffer_minutes', 15))
        self.working_hours = config.get('working_hours', {'start': '09:00', 'end': '17:00'})
        self.priority_contacts = config.get('priority_contacts', [])
        self.auto_reply_templates = config.get('auto_reply_templates', {})
        self.task_queue = asyncio.Queue()
        self.meeting_reminders = {}
        self.document_templates = {}
        
    async def initialize(self):
        """Initialize the secretary agent with necessary services and configurations."""
        await super().initialize()
        await self._init_google_services()
        await self._load_templates()
        await self._start_background_tasks()
        self.logger.info(f"Secretary Agent {self.name} initialized successfully")

    async def _init_google_services(self):
        """Initialize Google Workspace services with proper authentication."""
        SCOPES = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/drive'
        ]
        try:
            creds = None
            # Load credentials from token file or initiate OAuth2 flow
            # Implementation depends on your authentication setup
            self.calendar_service = build('calendar', 'v3', credentials=creds)
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
        except Exception as e:
            self.logger.error(f"Failed to initialize Google services: {str(e)}")
            raise

    async def schedule_meeting(self, attendees: List[str], duration: int, 
                             subject: str, description: str, 
                             preferred_time_range: Optional[Dict] = None) -> Dict:
        """Schedule a meeting with given parameters and find optimal time slot."""
        try:
            # Find available time slots
            available_slots = await self._find_available_time_slots(
                attendees, duration, preferred_time_range
            )
            
            if not available_slots:
                return {"success": False, "message": "No suitable time slots found"}
            
            # Select optimal slot (first available for now)
            selected_slot = available_slots[0]
            
            # Create calendar event
            event = {
                'summary': subject,
                'description': description,
                'start': {'dateTime': selected_slot['start'].isoformat()},
                'end': {'dateTime': selected_slot['end'].isoformat()},
                'attendees': [{'email': attendee} for attendee in attendees],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 15},
                    ],
                }
            }
            
            event = self.calendar_service.events().insert(
                calendarId='primary', body=event, sendUpdates='all'
            ).execute()
            
            # Set up reminder
            self.meeting_reminders[event['id']] = {
                'time': selected_slot['start'],
                'subject': subject,
                'attendees': attendees
            }
            
            return {
                "success": True,
                "meeting_id": event['id'],
                "scheduled_time": selected_slot['start'].isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to schedule meeting: {str(e)}")
            return {"success": False, "message": str(e)}

    async def process_email(self, email_data: Dict) -> Dict:
        """Process incoming emails and generate appropriate responses."""
        try:
            sender = email_data.get('sender')
            subject = email_data.get('subject', '').lower()
            content = email_data.get('content', '')
            
            # Priority handling for specific contacts
            is_priority = sender in self.priority_contacts
            
            # Analyze email content and determine response type
            response_type = await self._analyze_email_content(subject, content)
            
            # Generate response using appropriate template
            response = await self._generate_email_response(
                response_type, sender, subject, content
            )
            
            # Send response if auto-reply is appropriate
            if response:
                await self._send_email_response(sender, subject, response)
            
            # Create follow-up tasks if needed
            if is_priority or 'urgent' in subject:
                await self.task_queue.put({
                    'type': 'follow_up',
                    'email': email_data,
                    'deadline': datetime.now() + timedelta(hours=2)
                })
            
            return {"success": True, "action_taken": response_type}
            
        except Exception as e:
            self.logger.error(f"Failed to process email: {str(e)}")
            return {"success": False, "message": str(e)}

    async def manage_documents(self, doc_type: str, context: Dict) -> Dict:
        """Create and manage documents using templates."""
        try:
            template = self.document_templates.get(doc_type)
            if not template:
                return {"success": False, "message": f"No template found for {doc_type}"}
            
            # Generate document content
            content = await self._fill_template(template, context)
            
            # Create document in Google Drive
            file_metadata = {
                'name': f"{doc_type}_{datetime.now().strftime('%Y%m%d')}",
                'mimeType': 'application/vnd.google-apps.document'
            }
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=content,
                fields='id'
            ).execute()
            
            return {
                "success": True,
                "document_id": file.get('id'),
                "message": f"Document created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to manage document: {str(e)}")
            return {"success": False, "message": str(e)}

    async def _find_available_time_slots(self, attendees: List[str], 
                                       duration: int,
                                       preferred_time_range: Optional[Dict] = None) -> List[Dict]:
        """Find available time slots for all attendees."""
        # Implementation for finding available time slots
        # This would check calendar availability for all attendees
        # and return a list of possible time slots
        pass

    async def _analyze_email_content(self, subject: str, content: str) -> str:
        """Analyze email content to determine appropriate response type."""
        # Implementation for email content analysis
        pass

    async def _generate_email_response(self, response_type: str,
                                     sender: str, subject: str,
                                     content: str) -> str:
        """Generate appropriate email response based on type and content."""
        # Implementation for email response generation
        pass

    async def _fill_template(self, template: str, context: Dict) -> str:
        """Fill document template with provided context."""
        # Implementation for template filling
        pass

    async def _start_background_tasks(self):
        """Start background tasks for monitoring and maintenance."""
        asyncio.create_task(self._monitor_upcoming_meetings())
        asyncio.create_task(self._process_task_queue())
        asyncio.create_task(self._sync_calendar())

    async def _monitor_upcoming_meetings(self):
        """Monitor and send notifications for upcoming meetings."""
        while True:
            now = datetime.now(self.timezone)
            for meeting_id, reminder in self.meeting_reminders.items():
                if (reminder['time'] - now) <= timedelta(minutes=15):
                    await self._send_meeting_reminder(meeting_id, reminder)
            await asyncio.sleep(300)  # Check every 5 minutes

    async def _process_task_queue(self):
        """Process tasks in the task queue."""
        while True:
            task = await self.task_queue.get()
            await self._handle_task(task)
            self.task_queue.task_done()

    async def _sync_calendar(self):
        """Sync calendar events and update local cache."""
        # Implementation for calendar syncing
        pass

    async def _handle_error_type(self, error_type: str, error: Dict) -> Dict:
        """
        Handle secretary-specific error types.
        
        Args:
            error_type: Type of error to handle
            error: Error data dictionary
            
        Returns:
            Dict: Result of error handling
        """
        try:
            error_msg = error.get('error', 'Unknown error')
            error_data = error.get('data', {})
            
            if error_type == 'meeting_error':
                meeting_id = error_data.get('meeting_id')
                attendees = error_data.get('attendees', [])
                # Handle meeting scheduling errors
                if meeting_id:
                    try:
                        # Try to reschedule the meeting
                        self.calendar_service.events().delete(
                            calendarId='primary', eventId=meeting_id
                        ).execute()
                        # Notify attendees
                        for attendee in attendees:
                            asyncio.create_task(self._send_email_response(
                                attendee,
                                "Meeting Scheduling Error",
                                f"There was an error with the scheduled meeting. We will reschedule shortly.\nError: {error_msg}"
                            ))
                        self.logger.warning(f"Meeting {meeting_id} cancelled due to error: {error_msg}")
                        return {"success": True, "message": "Meeting cancelled and attendees notified", "action_taken": "cancel_meeting"}
                    except Exception as e:
                        self.logger.error(f"Failed to cancel meeting {meeting_id}: {str(e)}")
            
            elif error_type == 'email_error':
                email_id = error_data.get('email_id')
                sender = error_data.get('sender')
                # Handle email processing errors
                if email_id and sender:
                    try:
                        # Send error notification to sender
                        asyncio.create_task(self._send_email_response(
                            sender,
                            "Email Processing Error",
                            "We encountered an error processing your email. Please try again or contact support."
                        ))
                        # Add to task queue for manual review
                        asyncio.create_task(self.task_queue.put({
                            'type': 'review_failed_email',
                            'email_id': email_id,
                            'error': error_msg,
                            'timestamp': datetime.now()
                        }))
                        self.logger.warning(f"Email {email_id} processing failed: {error_msg}")
                        return {"success": True, "message": "Sender notified and email queued for review", "action_taken": "queue_for_review"}
                    except Exception as e:
                        self.logger.error(f"Failed to handle email error for {email_id}: {str(e)}")
            
            elif error_type == 'document_error':
                doc_type = error_data.get('doc_type')
                context = error_data.get('context', {})
                # Handle document management errors
                if doc_type:
                    try:
                        # Save document draft locally
                        draft_path = f"drafts/{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        with open(draft_path, 'w') as f:
                            f.write(str(context))
                        # Add to task queue for manual review
                        asyncio.create_task(self.task_queue.put({
                            'type': 'review_failed_document',
                            'doc_type': doc_type,
                            'draft_path': draft_path,
                            'error': error_msg,
                            'timestamp': datetime.now()
                        }))
                        self.logger.warning(f"Document creation failed for type {doc_type}: {error_msg}")
                        return {"success": True, "message": "Document draft saved for review", "action_taken": "save_draft"}
                    except Exception as e:
                        self.logger.error(f"Failed to save document draft for {doc_type}: {str(e)}")
            
            elif error_type == 'service_error':
                service_name = error_data.get('service')
                # Handle Google service errors
                if service_name:
                    try:
                        # Attempt to reinitialize the service
                        await self._init_google_services()
                        self.logger.warning(f"Reinitialized Google services after error: {error_msg}")
                        return {"success": True, "message": "Services reinitialized", "action_taken": "reinit_services"}
                    except Exception as e:
                        self.logger.error(f"Failed to reinitialize services: {str(e)}")
            
            # Handle health check errors
            elif error_type == 'health_check_error':
                service = error_data.get('service', 'unknown')
                self.logger.error(f"Health check failed for {service}: {error_msg}")
                # Attempt to reconnect to Google services
                try:
                    await self._init_google_services()
                    return {"success": True, "message": "Reconnected to Google services", "action_taken": "reconnect_services"}
                except Exception as e:
                    self.logger.error(f"Failed to reconnect to Google services: {str(e)}")
                    return {"success": False, "message": "Failed to reconnect to services", "action_taken": "none"}
            
            # Default error handling
            self.logger.error(f"Unhandled error type {error_type}: {error_msg}")
            return {"success": False, "message": f"Unhandled error type: {error_type}", "action_taken": "none"}
            
        except Exception as e:
            self.logger.error(f"Error in error handler: {str(e)}")
            return {"success": False, "message": f"Error handler failed: {str(e)}", "action_taken": "none"} 