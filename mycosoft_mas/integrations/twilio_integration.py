"""
Twilio Integration for Mycosoft MAS

Provides SMS and voice call capabilities via Twilio API.
"""

import os
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class TwilioIntegration:
    """Twilio client for SMS and voice capabilities."""

    def __init__(self, account_sid: Optional[str] = None, auth_token: Optional[str] = None, phone_number: Optional[str] = None):
        """
        Initialize Twilio integration.
        
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            phone_number: Your Twilio phone number (E.164 format)
        """
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN", "")
        self.phone_number = phone_number or os.getenv("TWILIO_PHONE_NUMBER", "")
        
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"
        self.logger = logging.getLogger(__name__)

    def is_configured(self) -> bool:
        """Check if Twilio credentials are configured."""
        return bool(self.account_sid and self.auth_token and self.phone_number)

    async def send_sms(self, to: str, message: str) -> Dict[str, Any]:
        """
        Send SMS message via Twilio.
        
        Args:
            to: Recipient phone number (E.164 format, e.g., +12025551234)
            message: Message text (max 1600 chars)
            
        Returns:
            Dict with status and message SID
        """
        if not self.is_configured():
            raise ValueError("Twilio not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER")

        url = f"{self.base_url}/Messages.json"
        data = {
            "From": self.phone_number,
            "To": to,
            "Body": message[:1600],  # Twilio SMS limit
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    auth=(self.account_sid, self.auth_token),
                    data=data,
                )
                resp.raise_for_status()
                result = resp.json()
                
                self.logger.info(f"SMS sent to {to}, SID: {result.get('sid')}")
                return {
                    "status": "success",
                    "sid": result.get("sid"),
                    "to": to,
                    "from": self.phone_number,
                }
        except Exception as e:
            self.logger.error(f"Failed to send SMS: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    async def make_call(self, to: str, twiml_url: str) -> Dict[str, Any]:
        """
        Initiate outbound call via Twilio.
        
        Args:
            to: Recipient phone number (E.164 format)
            twiml_url: URL that returns TwiML instructions for the call
            
        Returns:
            Dict with status and call SID
        """
        if not self.is_configured():
            raise ValueError("Twilio not configured")

        url = f"{self.base_url}/Calls.json"
        data = {
            "From": self.phone_number,
            "To": to,
            "Url": twiml_url,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    auth=(self.account_sid, self.auth_token),
                    data=data,
                )
                resp.raise_for_status()
                result = resp.json()
                
                self.logger.info(f"Call initiated to {to}, SID: {result.get('sid')}")
                return {
                    "status": "success",
                    "sid": result.get("sid"),
                    "to": to,
                    "from": self.phone_number,
                }
        except Exception as e:
            self.logger.error(f"Failed to initiate call: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    async def send_voice_message(self, to: str, message_text: str, voice: str = "alice") -> Dict[str, Any]:
        """
        Send a voice message (text-to-speech call) via Twilio.
        
        Args:
            to: Recipient phone number
            message_text: Text to speak
            voice: Twilio voice (alice, man, woman)
            
        Returns:
            Dict with status and call SID
        """
        if not self.is_configured():
            raise ValueError("Twilio not configured")

        # Create TwiML for text-to-speech
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="{voice}">{message_text}</Say>
</Response>"""

        # For production, host this TwiML on your server
        # For now, use Twilio's TwiML Bin feature or inline Say verb
        url = f"{self.base_url}/Calls.json"
        data = {
            "From": self.phone_number,
            "To": to,
            "Twiml": twiml,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    url,
                    auth=(self.account_sid, self.auth_token),
                    data=data,
                )
                resp.raise_for_status()
                result = resp.json()
                
                self.logger.info(f"Voice message sent to {to}, SID: {result.get('sid')}")
                return {
                    "status": "success",
                    "sid": result.get("sid"),
                    "to": to,
                    "message": message_text,
                }
        except Exception as e:
            self.logger.error(f"Failed to send voice message: {e}")
            return {
                "status": "error",
                "error": str(e),
            }

    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """Get status of a sent message."""
        if not self.is_configured():
            raise ValueError("Twilio not configured")

        url = f"{self.base_url}/Messages/{message_sid}.json"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    url,
                    auth=(self.account_sid, self.auth_token),
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            self.logger.error(f"Failed to get message status: {e}")
            return {"status": "error", "error": str(e)}
