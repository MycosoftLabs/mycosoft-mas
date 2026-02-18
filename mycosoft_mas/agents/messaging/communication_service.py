"""
Communication Service for Mycosoft MAS

This module implements a simple communication service for the Mycosoft MAS.
"""

import asyncio
import logging
import smtplib
import os
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

class CommunicationService:
    """Simple communication service."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the communication service."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.notifications: List[Dict[str, Any]] = []
        self.communication_history: List[Dict[str, Any]] = []
        self.status = "initialized"
        self.smtp_server = None
        self.data_dir = Path("data/communications")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metrics = {
            "notifications_sent": 0,
            "emails_sent": 0,
            "sms_sent": 0,
            "voice_calls_made": 0,
            "failed_communications": 0,
            "error_counts": {
                "validation": 0,
                "email": 0,
                "sms": 0,
                "voice": 0
            }
        }
    
    async def start(self) -> None:
        """Start the communication service."""
        self.logger.info("Starting communication service")
        self.status = "running"
    
    async def stop(self) -> None:
        """Stop the communication service."""
        self.logger.info("Stopping communication service")
        self.status = "stopped"
    
    async def send_notification(self, notification: Dict[str, Any]) -> bool:
        """Send a notification."""
        try:
            self.notifications.append({
                **notification,
                "timestamp": datetime.now().isoformat()
            })
            self.metrics["notifications_sent"] += 1
            self.logger.info(f"Sent notification: {notification}")
            return True
        except Exception as e:
            self.logger.error(f"Error sending notification: {str(e)}")
            self.metrics["errors"] += 1
            return False
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body text
            html_body: Optional HTML body
            attachments: Optional list of attachments
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Validate email
            if not self._validate_email(to_email):
                self.metrics["error_counts"]["validation"] += 1
                self.logger.error(f"Invalid email address: {to_email}")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.config["email"]["username"]
            msg["To"] = to_email
            msg["Subject"] = subject
            
            # Add text body
            msg.attach(MIMEText(body, "plain"))
            
            # Add HTML body if provided
            if html_body:
                msg.attach(MIMEText(html_body, "html"))
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    if isinstance(attachment, dict):
                        filename = attachment.get("filename")
                        content = attachment.get("content")
                        mimetype = attachment.get("mimetype", "application/octet-stream")
                    else:
                        # Assume it's a file path
                        filename = Path(attachment).name
                        with open(attachment, "rb") as f:
                            content = f.read()
                        mimetype = "application/octet-stream"
                    
                    part = MIMEApplication(content, Name=filename)
                    part['Content-Disposition'] = f'attachment; filename="{filename}"'
                    msg.attach(part)
            
            # Connect to SMTP server if not connected
            if not self.smtp_server:
                self.smtp_server = smtplib.SMTP(
                    self.config["email"]["smtp_server"],
                    self.config["email"]["smtp_port"]
                )
                self.smtp_server.starttls()
                self.smtp_server.login(
                    self.config["email"]["username"],
                    self.config["email"]["password"]
                )
            
            # Send email
            self.smtp_server.send_message(msg)
            
            # Update metrics
            self.metrics["emails_sent"] += 1
            
            # Log communication
            self._log_communication({
                "type": "email",
                "to": to_email,
                "subject": subject,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "sent"
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {str(e)}")
            self.metrics["failed_communications"] += 1
            self.metrics["error_counts"]["email"] += 1
            
            # Log failed communication
            self._log_communication({
                "type": "email",
                "to": to_email,
                "subject": subject,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "failed",
                "error": str(e)
            })
            
            return False
    
    async def send_sms(
        self,
        to_number: str,
        message: str,
        sender_id: Optional[str] = None
    ) -> bool:
        """
        Send an SMS.
        
        Args:
            to_number: Recipient phone number
            message: SMS message text
            sender_id: Optional sender ID
            
        Returns:
            bool: True if SMS was sent successfully, False otherwise
        """
        try:
            # Validate phone number
            if not self._validate_phone_number(to_number):
                self.metrics["error_counts"]["validation"] += 1
                self.logger.error(f"Invalid phone number: {to_number}")
                return False
            
            # Implement SMS sending via Twilio (if configured)
            twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
            twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
            twilio_from = os.getenv("TWILIO_PHONE_NUMBER")
            
            if not all([twilio_sid, twilio_token, twilio_from]):
                self.logger.warning("Twilio credentials not configured - SMS not sent")
                self.metrics["error_counts"]["sms"] += 1
                return False
            
            try:
                from twilio.rest import Client
                client = Client(twilio_sid, twilio_token)
                
                message_obj = client.messages.create(
                    body=message,
                    from_=twilio_from,
                    to=to_number
                )
                
                self.logger.info(f"SMS sent successfully: SID {message_obj.sid}")
            except ImportError:
                self.logger.error("Twilio package not installed - run: pip install twilio")
                self.metrics["error_counts"]["sms"] += 1
                return False
            except Exception as e:
                self.logger.error(f"Twilio SMS failed: {str(e)}")
                self.metrics["error_counts"]["sms"] += 1
                return False
            
            # Update metrics
            self.metrics["sms_sent"] += 1
            
            # Log communication
            self._log_communication({
                "type": "sms",
                "to": to_number,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "sent"
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send SMS: {str(e)}")
            self.metrics["failed_communications"] += 1
            self.metrics["error_counts"]["sms"] += 1
            
            # Log failed communication
            self._log_communication({
                "type": "sms",
                "to": to_number,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "failed",
                "error": str(e)
            })
            
            return False
    
    async def send_voice_notification(
        self,
        to_number: str,
        message: str,
        language: str = "en-US",
        voice: str = "en-US-Wavenet-D"
    ) -> bool:
        """
        Send a voice notification.
        
        Args:
            to_number: Recipient phone number
            message: Message to speak
            language: Language code
            voice: Voice to use
            
        Returns:
            bool: True if voice notification was sent successfully, False otherwise
        """
        try:
            # Validate phone number
            if not self._validate_phone_number(to_number):
                self.metrics["error_counts"]["validation"] += 1
                self.logger.error(f"Invalid phone number: {to_number}")
                return False
            
            # Implement voice notification via Twilio TTS (if configured)
            twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
            twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
            twilio_from = os.getenv("TWILIO_PHONE_NUMBER")
            
            if not all([twilio_sid, twilio_token, twilio_from]):
                self.logger.warning("Twilio credentials not configured - Voice call not sent")
                self.metrics["error_counts"]["voice"] += 1
                return False
            
            try:
                from twilio.rest import Client
                from twilio.twiml.voice_response import VoiceResponse
                
                # Create TwiML for voice message
                response = VoiceResponse()
                response.say(message, voice=voice, language=language)
                
                client = Client(twilio_sid, twilio_token)
                call = client.calls.create(
                    twiml=str(response),
                    to=to_number,
                    from_=twilio_from
                )
                
                self.logger.info(f"Voice call initiated successfully: SID {call.sid}")
            except ImportError:
                self.logger.error("Twilio package not installed - run: pip install twilio")
                self.metrics["error_counts"]["voice"] += 1
                return False
            except Exception as e:
                self.logger.error(f"Twilio voice call failed: {str(e)}")
                self.metrics["error_counts"]["voice"] += 1
                return False
            
            # Update metrics
            self.metrics["voice_calls_made"] += 1
            
            # Log communication
            self._log_communication({
                "type": "voice",
                "to": to_number,
                "message": message,
                "language": language,
                "voice": voice,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "sent"
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send voice notification: {str(e)}")
            self.metrics["failed_communications"] += 1
            self.metrics["error_counts"]["voice"] += 1
            
            # Log failed communication
            self._log_communication({
                "type": "voice",
                "to": to_number,
                "message": message,
                "language": language,
                "voice": voice,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "failed",
                "error": str(e)
            })
            
            return False
    
    def _validate_email(self, email: str) -> bool:
        """Validate an email address using regex pattern."""
        import re
        # RFC 5322 compliant email regex
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _validate_phone_number(self, number: str) -> bool:
        """Validate a phone number using phonenumbers library."""
        try:
            import phonenumbers
            parsed = phonenumbers.parse(number, None)
            return phonenumbers.is_valid_number(parsed)
        except ImportError:
            # Fallback to basic validation if phonenumbers not installed
            cleaned = ''.join(filter(str.isdigit, number))
            return len(cleaned) >= 10 and len(cleaned) <= 15
        except Exception:
            return False
    
    def _log_communication(self, communication: Dict[str, Any]) -> None:
        """Log a communication."""
        self.communication_history.append(communication)
    
    async def _save_communications(self) -> None:
        """Save communications to disk"""
        try:
            # Save communication history
            history_file = self.data_dir / "communications.json"
            with open(history_file, "w") as f:
                json.dump(self.communication_history, f, indent=2)
            
            # Save metrics
            metrics_file = self.data_dir / "metrics.json"
            with open(metrics_file, "w") as f:
                json.dump(self.metrics, f, indent=2)
            
        except Exception as e:
            self.logger.error(f"Error saving communications: {str(e)}")
    
    async def _load_communications(self) -> None:
        """Load communications from disk"""
        try:
            # Load communication history
            history_file = self.data_dir / "communications.json"
            if history_file.exists():
                with open(history_file, "r") as f:
                    self.communication_history = json.load(f)
            
            # Load metrics
            metrics_file = self.data_dir / "metrics.json"
            if metrics_file.exists():
                with open(metrics_file, "r") as f:
                    self.metrics = json.load(f)
            
        except Exception as e:
            self.logger.error(f"Error loading communications: {str(e)}")
    
    async def _save_communications_periodically(self) -> None:
        """Save communications periodically"""
        while True:
            try:
                await asyncio.sleep(300)  # Save every 5 minutes
                await self._save_communications()
            except Exception as e:
                self.logger.error(f"Error in periodic save: {str(e)}")
                await asyncio.sleep(60) 