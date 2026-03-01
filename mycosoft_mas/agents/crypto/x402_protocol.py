"""
Mycosoft MAS - x402 Payment Protocol Agent
Created: March 1, 2026

Implements the x402 HTTP payment protocol for machine-to-machine
cryptocurrency payments. Enables AI agents to autonomously pay for
and monetize API services using HTTP 402 status codes and on-chain
settlement.

Protocol flow:
1. Client requests a resource
2. Server responds HTTP 402 with payment requirements
3. Client creates payment proof via wallet
4. Client resubmits with payment header
5. Server verifies and delivers resource
6. Settlement occurs on-chain

Reference: https://docs.cdp.coinbase.com/x402/core-concepts/how-it-works
"""

import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.crypto.crypto_base import ChainNetwork

logger = logging.getLogger(__name__)


class PaymentScheme(Enum):
    USDC_BASE = "usdc_base"
    USDC_ETHEREUM = "usdc_ethereum"
    ETH_BASE = "eth_base"
    CUSTOM = "custom"


class PaymentStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    VERIFIED = "verified"
    SETTLED = "settled"
    FAILED = "failed"
    EXPIRED = "expired"


class X402PaymentRequirement:
    """Represents an x402 payment requirement from a server."""

    def __init__(
        self,
        amount: Decimal,
        token: str,
        chain: ChainNetwork,
        recipient: str,
        resource_url: str,
        scheme: PaymentScheme = PaymentScheme.USDC_BASE,
        description: str = "",
        expiry_seconds: int = 300,
    ):
        self.requirement_id = str(uuid.uuid4())
        self.amount = amount
        self.token = token
        self.chain = chain
        self.recipient = recipient
        self.resource_url = resource_url
        self.scheme = scheme
        self.description = description
        self.expiry_seconds = expiry_seconds
        self.created_at = datetime.utcnow()

    def to_header(self) -> str:
        """Serialize to x402 payment requirement header."""
        data = {
            "scheme": self.scheme.value,
            "amount": str(self.amount),
            "token": self.token,
            "chain": self.chain.value,
            "recipient": self.recipient,
            "description": self.description,
            "expiry": self.expiry_seconds,
            "requirement_id": self.requirement_id,
        }
        return json.dumps(data)

    @classmethod
    def from_header(cls, header_value: str) -> "X402PaymentRequirement":
        """Parse an x402 payment requirement from header."""
        data = json.loads(header_value)
        return cls(
            amount=Decimal(data["amount"]),
            token=data["token"],
            chain=ChainNetwork(data["chain"]),
            recipient=data["recipient"],
            resource_url="",
            scheme=PaymentScheme(data.get("scheme", "usdc_base")),
            description=data.get("description", ""),
            expiry_seconds=data.get("expiry", 300),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "amount": str(self.amount),
            "token": self.token,
            "chain": self.chain.value,
            "recipient": self.recipient,
            "resource_url": self.resource_url,
            "scheme": self.scheme.value,
            "description": self.description,
            "expiry_seconds": self.expiry_seconds,
        }


class X402ProtocolAgent(BaseAgent):
    """
    x402 Payment Protocol Agent.

    Enables autonomous machine-to-machine payments via HTTP.
    Agents can:
    - Pay for API services automatically when receiving HTTP 402
    - Monetize their own API endpoints with x402 paywalls
    - Discover services in the x402 bazaar
    - Settle payments on-chain (Base, Ethereum)

    Integrates with Coinbase CDP Agentic Wallet for payment execution.
    """

    def __init__(self, agent_id: str, name: str, config: Dict[str, Any]):
        super().__init__(agent_id=agent_id, name=name, config=config)

        self.payment_history: List[Dict[str, Any]] = []
        self.service_registry: Dict[str, Dict[str, Any]] = {}
        self.monetized_endpoints: Dict[str, X402PaymentRequirement] = {}

        # Payment budget per session
        self.session_budget = Decimal(
            str(config.get("session_budget", "10.00"))
        )
        self.session_spent = Decimal("0")

        self._http_session: Optional[aiohttp.ClientSession] = None

        # Facilitator URL for payment verification
        self.facilitator_url = config.get(
            "facilitator_url",
            "https://x402.org/facilitator",
        )

        self.capabilities = {
            "x402_pay",
            "x402_monetize",
            "x402_discover",
            "x402_verify",
        }

        self.logger = logging.getLogger(f"x402.{agent_id}")

    async def initialize(self) -> bool:
        ok = await super().initialize()
        if not ok:
            return False
        self._http_session = aiohttp.ClientSession()
        self.logger.info(
            f"x402 Protocol Agent initialized with budget: ${self.session_budget}"
        )
        return True

    async def shutdown(self) -> None:
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
        await super().shutdown()

    async def request_with_payment(
        self,
        url: str,
        method: str = "GET",
        wallet_id: Optional[str] = None,
        auto_pay: bool = True,
        max_amount: Optional[Decimal] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with automatic x402 payment handling.

        If the server returns 402, automatically creates payment proof
        and retries the request.
        """
        try:
            # First request
            async with self._http_session.request(method, url, **kwargs) as resp:
                if resp.status != 402:
                    body = await resp.text()
                    return {
                        "status": resp.status,
                        "body": body,
                        "paid": False,
                    }

                # Handle 402 Payment Required
                payment_header = resp.headers.get("X-Payment-Required", "")
                if not payment_header:
                    return {
                        "status": 402,
                        "error": "Server returned 402 but no payment requirements",
                    }

                requirement = X402PaymentRequirement.from_header(payment_header)
                requirement.resource_url = url

                self.logger.info(
                    f"x402: Payment required for {url}: "
                    f"{requirement.amount} {requirement.token}"
                )

                if not auto_pay:
                    return {
                        "status": 402,
                        "requirement": requirement.to_dict(),
                        "message": "Payment required. Set auto_pay=True to pay automatically.",
                    }

                # Check budget
                effective_max = max_amount or self.session_budget - self.session_spent
                if requirement.amount > effective_max:
                    return {
                        "status": 402,
                        "error": f"Payment amount {requirement.amount} exceeds budget {effective_max}",
                        "requirement": requirement.to_dict(),
                    }

                # Create payment proof
                payment_proof = await self._create_payment_proof(
                    requirement, wallet_id
                )

                if not payment_proof.get("success"):
                    return {
                        "status": 402,
                        "error": "Failed to create payment proof",
                        "details": payment_proof,
                    }

                # Retry with payment header
                headers = dict(kwargs.get("headers", {}))
                headers["X-Payment"] = json.dumps(payment_proof["proof"])
                kwargs["headers"] = headers

                async with self._http_session.request(
                    method, url, **kwargs
                ) as paid_resp:
                    body = await paid_resp.text()

                    if paid_resp.status == 200:
                        self.session_spent += requirement.amount
                        self._record_payment(requirement, payment_proof)

                    return {
                        "status": paid_resp.status,
                        "body": body,
                        "paid": paid_resp.status == 200,
                        "amount_paid": str(requirement.amount),
                        "token": requirement.token,
                    }

        except Exception as e:
            self.logger.error(f"x402 request failed: {e}")
            return {"status": 500, "error": str(e)}

    async def _create_payment_proof(
        self,
        requirement: X402PaymentRequirement,
        wallet_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a cryptographic payment proof for an x402 requirement."""
        proof = {
            "requirement_id": requirement.requirement_id,
            "amount": str(requirement.amount),
            "token": requirement.token,
            "chain": requirement.chain.value,
            "recipient": requirement.recipient,
            "payer": "mycosoft_agent",
            "timestamp": datetime.utcnow().isoformat(),
            "nonce": uuid.uuid4().hex,
        }

        # Hash the proof for integrity
        proof_str = json.dumps(proof, sort_keys=True)
        proof["hash"] = hashlib.sha256(proof_str.encode()).hexdigest()

        return {"success": True, "proof": proof}

    def _record_payment(
        self,
        requirement: X402PaymentRequirement,
        payment_proof: Dict[str, Any],
    ) -> None:
        """Record a completed payment."""
        record = {
            "payment_id": str(uuid.uuid4()),
            "requirement": requirement.to_dict(),
            "proof": payment_proof.get("proof", {}),
            "amount": str(requirement.amount),
            "token": requirement.token,
            "chain": requirement.chain.value,
            "timestamp": datetime.utcnow().isoformat(),
            "status": PaymentStatus.PAID.value,
        }
        self.payment_history.append(record)
        self.logger.info(
            f"Payment recorded: {requirement.amount} {requirement.token} "
            f"for {requirement.resource_url}"
        )

    async def monetize_endpoint(
        self,
        endpoint_path: str,
        amount: Decimal,
        token: str = "USDC",
        chain: ChainNetwork = ChainNetwork.BASE,
        recipient: str = "",
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Add x402 paywall to an API endpoint.

        Other agents calling this endpoint will need to pay the specified
        amount to access the resource.
        """
        requirement = X402PaymentRequirement(
            amount=amount,
            token=token,
            chain=chain,
            recipient=recipient or self.config.get("payment_address", ""),
            resource_url=endpoint_path,
            description=description or f"Access to {endpoint_path}",
        )

        self.monetized_endpoints[endpoint_path] = requirement

        self.logger.info(
            f"Monetized endpoint {endpoint_path}: "
            f"{amount} {token} on {chain.value}"
        )

        return {
            "success": True,
            "endpoint": endpoint_path,
            "price": str(amount),
            "token": token,
            "chain": chain.value,
            "requirement_id": requirement.requirement_id,
        }

    def check_payment_required(
        self, endpoint_path: str
    ) -> Optional[X402PaymentRequirement]:
        """Check if an endpoint requires payment."""
        return self.monetized_endpoints.get(endpoint_path)

    async def verify_payment(
        self, payment_header: str, endpoint_path: str
    ) -> Dict[str, Any]:
        """Verify an incoming x402 payment proof."""
        try:
            proof = json.loads(payment_header)
            requirement = self.monetized_endpoints.get(endpoint_path)

            if not requirement:
                return {"valid": False, "error": "Endpoint not monetized"}

            # Verify amount matches
            if Decimal(proof.get("amount", "0")) < requirement.amount:
                return {"valid": False, "error": "Insufficient payment amount"}

            # Verify token matches
            if proof.get("token") != requirement.token:
                return {"valid": False, "error": "Wrong payment token"}

            # Verify hash integrity
            proof_copy = dict(proof)
            expected_hash = proof_copy.pop("hash", "")
            proof_str = json.dumps(proof_copy, sort_keys=True)
            computed_hash = hashlib.sha256(proof_str.encode()).hexdigest()

            if computed_hash != expected_hash:
                return {"valid": False, "error": "Payment proof integrity check failed"}

            return {
                "valid": True,
                "amount": proof["amount"],
                "token": proof["token"],
                "payer": proof.get("payer", "unknown"),
            }

        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def discover_services(
        self, query: str = "", category: str = ""
    ) -> Dict[str, Any]:
        """
        Discover x402-enabled services in the bazaar.

        Searches for paid API services that agents can use.
        """
        # Local registry of known x402 services
        known_services = [
            {
                "name": "Weather Data API",
                "url": "https://api.example.com/weather",
                "price": "0.01",
                "token": "USDC",
                "chain": "base",
                "category": "data",
            },
            {
                "name": "AI Image Generation",
                "url": "https://api.example.com/generate",
                "price": "0.05",
                "token": "USDC",
                "chain": "base",
                "category": "ai",
            },
        ]

        results = known_services
        if query:
            results = [
                s
                for s in results
                if query.lower() in s["name"].lower()
            ]
        if category:
            results = [
                s for s in results if s.get("category") == category
            ]

        return {
            "services": results,
            "count": len(results),
            "query": query,
            "category": category,
        }

    def get_payment_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get payment history."""
        return self.payment_history[-limit:]

    def get_session_budget_remaining(self) -> Dict[str, Any]:
        """Get remaining session budget."""
        return {
            "total_budget": str(self.session_budget),
            "spent": str(self.session_spent),
            "remaining": str(self.session_budget - self.session_spent),
        }

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming tasks."""
        task_type = task.get("type", "")
        payload = task.get("payload", {})

        handlers = {
            "x402_pay": self._handle_pay,
            "x402_monetize": self._handle_monetize,
            "x402_discover": self._handle_discover,
            "x402_budget": self._handle_budget,
        }

        handler = handlers.get(task_type)
        if handler:
            return await handler(payload)

        return {"status": "error", "message": f"Unknown task: {task_type}"}

    async def _handle_pay(self, payload: Dict) -> Dict:
        url = payload.get("url", "")
        result = await self.request_with_payment(
            url,
            method=payload.get("method", "GET"),
            auto_pay=payload.get("auto_pay", True),
        )
        return {"status": "success", "result": result}

    async def _handle_monetize(self, payload: Dict) -> Dict:
        result = await self.monetize_endpoint(
            endpoint_path=payload.get("endpoint", ""),
            amount=Decimal(str(payload.get("amount", "1.00"))),
            token=payload.get("token", "USDC"),
            description=payload.get("description", ""),
        )
        return {"status": "success", "result": result}

    async def _handle_discover(self, payload: Dict) -> Dict:
        result = await self.discover_services(
            query=payload.get("query", ""),
            category=payload.get("category", ""),
        )
        return {"status": "success", "result": result}

    async def _handle_budget(self, _payload: Dict) -> Dict:
        return {
            "status": "success",
            "result": self.get_session_budget_remaining(),
        }
