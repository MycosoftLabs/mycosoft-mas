"""
Confirmation Gateway for MYCA Voice System
Created: February 4, 2026

Multi-level confirmation system for high-risk voice operations.
"""

import asyncio
import secrets
from typing import Dict, Optional, Callable, Any, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ConfirmationMethod(Enum):
    NONE = "none"
    VERBAL = "verbal"
    REPEAT = "repeat"
    CHALLENGE = "challenge"
    CODE = "code"
    PASSPHRASE = "passphrase"
    MFA = "mfa"


class ConfirmationStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class ConfirmationRequest:
    request_id: str
    action_type: str
    action_description: str
    method: ConfirmationMethod
    user_id: str
    created_at: datetime
    expires_at: datetime
    status: ConfirmationStatus = ConfirmationStatus.PENDING
    challenge_data: Optional[str] = None
    attempts: int = 0
    max_attempts: int = 3
    callback: Optional[Callable[[], Awaitable[Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at
    
    def has_attempts_remaining(self) -> bool:
        return self.attempts < self.max_attempts


@dataclass
class ConfirmationResult:
    request_id: str
    status: ConfirmationStatus
    message: str
    action_executed: bool = False
    action_result: Optional[Any] = None


class ConfirmationGateway:
    """Gateway for handling confirmation of high-risk operations."""
    
    CONFIRM_PHRASES = ["yes", "confirm", "affirmative", "do it", "proceed", "approved", "go ahead", "execute", "authorize"]
    DENY_PHRASES = ["no", "deny", "cancel", "stop", "abort", "reject", "negative"]
    
    def __init__(self, default_timeout_seconds: int = 60, default_max_attempts: int = 3):
        self.pending_requests: Dict[str, ConfirmationRequest] = {}
        self.completed_requests: Dict[str, ConfirmationRequest] = {}
        self.default_timeout = default_timeout_seconds
        self.default_max_attempts = default_max_attempts
        self.challenge_generators = {
            ConfirmationMethod.CODE: self._generate_code_challenge,
            ConfirmationMethod.CHALLENGE: self._generate_question_challenge,
        }
        logger.info("ConfirmationGateway initialized")
    
    def request_confirmation(
        self, action_type: str, action_description: str, user_id: str,
        method: ConfirmationMethod = ConfirmationMethod.VERBAL,
        timeout_seconds: Optional[int] = None,
        callback: Optional[Callable[[], Awaitable[Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConfirmationRequest:
        request_id = secrets.token_hex(8)
        now = datetime.now()
        timeout = timeout_seconds or self.default_timeout
        
        challenge_data = None
        if method in self.challenge_generators:
            challenge_data = self.challenge_generators[method]()
        
        request = ConfirmationRequest(
            request_id=request_id, action_type=action_type,
            action_description=action_description, method=method,
            user_id=user_id, created_at=now,
            expires_at=now + timedelta(seconds=timeout),
            challenge_data=challenge_data, max_attempts=self.default_max_attempts,
            callback=callback, metadata=metadata or {},
        )
        
        self.pending_requests[request_id] = request
        logger.info(f"Confirmation requested: {request_id} for {action_type}")
        return request
    
    async def process_response(self, request_id: str, response: str) -> ConfirmationResult:
        if request_id not in self.pending_requests:
            if request_id in self.completed_requests:
                req = self.completed_requests[request_id]
                return ConfirmationResult(request_id=request_id, status=req.status, message="Already processed.")
            return ConfirmationResult(request_id=request_id, status=ConfirmationStatus.CANCELLED, message="Not found.")
        
        request = self.pending_requests[request_id]
        
        if request.is_expired():
            request.status = ConfirmationStatus.EXPIRED
            self._move_to_completed(request_id)
            return ConfirmationResult(request_id=request_id, status=ConfirmationStatus.EXPIRED, message="Expired.")
        
        request.attempts += 1
        is_confirmed = self._verify_response(request, response)
        is_denied = self._is_denial(response)
        
        if is_denied:
            request.status = ConfirmationStatus.DENIED
            self._move_to_completed(request_id)
            return ConfirmationResult(request_id=request_id, status=ConfirmationStatus.DENIED, message="Cancelled.")
        
        if is_confirmed:
            request.status = ConfirmationStatus.CONFIRMED
            self._move_to_completed(request_id)
            action_result = None
            action_executed = False
            if request.callback:
                try:
                    action_result = await request.callback()
                    action_executed = True
                except Exception as e:
                    return ConfirmationResult(request_id=request_id, status=ConfirmationStatus.CONFIRMED,
                                              message=f"Confirmed but failed: {e}", action_executed=False)
            return ConfirmationResult(request_id=request_id, status=ConfirmationStatus.CONFIRMED,
                                      message="Confirmed.", action_executed=action_executed, action_result=action_result)
        
        if not request.has_attempts_remaining():
            request.status = ConfirmationStatus.DENIED
            self._move_to_completed(request_id)
            return ConfirmationResult(request_id=request_id, status=ConfirmationStatus.DENIED, message="Max attempts.")
        
        remaining = request.max_attempts - request.attempts
        return ConfirmationResult(request_id=request_id, status=ConfirmationStatus.PENDING,
                                  message=f"{remaining} attempts remaining.")
    
    def _verify_response(self, request: ConfirmationRequest, response: str) -> bool:
        response_lower = response.lower().strip()
        if request.method == ConfirmationMethod.NONE:
            return True
        elif request.method == ConfirmationMethod.VERBAL:
            return any(phrase in response_lower for phrase in self.CONFIRM_PHRASES)
        elif request.method == ConfirmationMethod.REPEAT:
            return request.action_description.lower() in response_lower
        elif request.method == ConfirmationMethod.CODE:
            return request.challenge_data and request.challenge_data.lower() in response_lower
        elif request.method == ConfirmationMethod.CHALLENGE:
            if request.challenge_data and "|" in request.challenge_data:
                parts = request.challenge_data.split("|")
                if len(parts) == 2:
                    return parts[1].lower() in response_lower
        return False
    
    def _is_denial(self, response: str) -> bool:
        return any(phrase in response.lower().strip() for phrase in self.DENY_PHRASES)
    
    def _generate_code_challenge(self) -> str:
        return str(secrets.randbelow(9000) + 1000)
    
    def _generate_question_challenge(self) -> str:
        import random
        challenges = [("What is 7 plus 3?", "10"), ("What is 5 times 2?", "10"), ("What is 12 minus 4?", "8")]
        q, a = random.choice(challenges)
        return f"{q}|{a}"
    
    def _move_to_completed(self, request_id: str) -> None:
        if request_id in self.pending_requests:
            self.completed_requests[request_id] = self.pending_requests.pop(request_id)
    
    def get_pending_for_user(self, user_id: str) -> list:
        return [r for r in self.pending_requests.values() if r.user_id == user_id and not r.is_expired()]
    
    def cancel_request(self, request_id: str) -> bool:
        if request_id in self.pending_requests:
            self.pending_requests[request_id].status = ConfirmationStatus.CANCELLED
            self._move_to_completed(request_id)
            return True
        return False
    
    def get_prompt_for_confirmation(self, request: ConfirmationRequest) -> str:
        base = f"Please confirm: {request.action_description}. "
        if request.method == ConfirmationMethod.VERBAL:
            return base + 'Say yes to confirm or no to cancel.'
        elif request.method == ConfirmationMethod.CODE:
            return base + f'Say the code: {request.challenge_data}'
        return base


_gateway_instance: Optional[ConfirmationGateway] = None


def get_confirmation_gateway() -> ConfirmationGateway:
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = ConfirmationGateway()
    return _gateway_instance


__all__ = ["ConfirmationGateway", "ConfirmationRequest", "ConfirmationResult",
           "ConfirmationMethod", "ConfirmationStatus", "get_confirmation_gateway"]
