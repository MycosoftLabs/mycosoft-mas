"""
Financial Agent for Mycosoft MAS

This module implements the FinancialAgent class that coordinates financial operations
using Stripe for payments and SQLite for transaction tracking.
"""

import asyncio
import logging
import sqlite3
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from mycosoft_mas.agents.integrations.stripe_client import StripeClient
from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.messaging.message_types import Message, MessageType, MessagePriority

class FinancialAgent(BaseAgent):
    """
    Agent responsible for managing financial operations.
    
    This agent coordinates:
    - Payment processing through Stripe
    - Transaction tracking through SQLite
    - Financial reporting and analytics
    - Transaction monitoring and reconciliation
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        """
        Initialize the Financial Agent.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name for the agent
            config: Configuration dictionary for the agent
        """
        super().__init__(agent_id=agent_id, name=name, config=config)
        
        # Initialize Stripe client
        self.stripe_client = StripeClient(
            api_key=config["stripe_api_key"]
        )
        
        # Initialize SQLite database
        self.db_path = Path(config.get("data_dir", "data/financial")) / "transactions.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Initialize metrics
        self.metrics = {
            "transactions_processed": 0,
            "payments_processed": 0,
            "subscriptions_managed": 0,
            "errors_encountered": 0
        }
    
    def _init_database(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT NOT NULL,
                    description TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS balances (
                    currency TEXT PRIMARY KEY,
                    amount REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Insert initial balance if not exists
            conn.execute("""
                INSERT OR IGNORE INTO balances (currency, amount)
                VALUES ('USD', 0.0)
            """)
            conn.commit()
    
    async def handle_message(self, message: Message) -> None:
        """
        Handle incoming messages.
        
        Args:
            message: Message to handle
        """
        try:
            if message.type == MessageType.FINANCIAL:
                await self._handle_financial_message(message)
            elif message.type == MessageType.PAYMENT:
                await self._handle_payment_message(message)
            elif message.type == MessageType.SUBSCRIPTION:
                await self._handle_subscription_message(message)
            else:
                self.logger.warning(f"Unhandled message type: {message.type}")
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")
            self.metrics["errors_encountered"] += 1
            raise
    
    async def _handle_financial_message(self, message: Message) -> None:
        """
        Handle financial-related messages.
        
        Args:
            message: Financial message to handle
        """
        action = message.data.get("action")
        
        if action == "get_balance":
            await self._handle_get_balance(message)
        elif action == "get_transactions":
            await self._handle_get_transactions(message)
        elif action == "create_transaction":
            await self._handle_create_transaction(message)
        elif action == "get_statement":
            await self._handle_get_statement(message)
        else:
            self.logger.warning(f"Unhandled financial action: {action}")
    
    async def _handle_payment_message(self, message: Message) -> None:
        """
        Handle payment-related messages.
        
        Args:
            message: Payment message to handle
        """
        action = message.data.get("action")
        
        if action == "process_payment":
            await self._handle_process_payment(message)
        elif action == "create_payment_method":
            await self._handle_create_payment_method(message)
        elif action == "get_payment_history":
            await self._handle_get_payment_history(message)
        else:
            self.logger.warning(f"Unhandled payment action: {action}")
    
    async def _handle_subscription_message(self, message: Message) -> None:
        """
        Handle subscription-related messages.
        
        Args:
            message: Subscription message to handle
        """
        action = message.data.get("action")
        
        if action == "create_subscription":
            await self._handle_create_subscription(message)
        elif action == "update_subscription":
            await self._handle_update_subscription(message)
        elif action == "cancel_subscription":
            await self._handle_cancel_subscription(message)
        else:
            self.logger.warning(f"Unhandled subscription action: {action}")
    
    async def _handle_get_balance(self, message: Message) -> None:
        """
        Handle get balance request.
        
        Args:
            message: Message containing balance request
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT currency, amount FROM balances")
                balances = {row[0]: row[1] for row in cursor.fetchall()}
            
            await self.send_message(
                Message(
                    type=MessageType.FINANCIAL,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "balance_response",
                        "balances": balances
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error getting balance: {str(e)}")
            raise
    
    async def _handle_get_transactions(self, message: Message) -> None:
        """
        Handle get transactions request.
        
        Args:
            message: Message containing transactions request
        """
        try:
            start_date = message.data.get("start_date")
            end_date = message.data.get("end_date")
            
            query = "SELECT * FROM transactions WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND created_at >= ?"
                params.append(start_date)
            if end_date:
                query += " AND created_at <= ?"
                params.append(end_date)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                transactions = [dict(row) for row in cursor.fetchall()]
            
            await self.send_message(
                Message(
                    type=MessageType.FINANCIAL,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "transactions_response",
                        "transactions": transactions
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error getting transactions: {str(e)}")
            raise
    
    async def _handle_create_transaction(self, message: Message) -> None:
        """
        Handle create transaction request.
        
        Args:
            message: Message containing transaction creation request
        """
        try:
            transaction_data = message.data.get("transaction_data", {})
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO transactions (id, type, amount, currency, description, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    transaction_data.get("id"),
                    transaction_data.get("type"),
                    transaction_data.get("amount"),
                    transaction_data.get("currency", "USD"),
                    transaction_data.get("description"),
                    json.dumps(transaction_data.get("metadata", {}))
                ))
                
                # Update balance
                conn.execute("""
                    UPDATE balances 
                    SET amount = amount + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE currency = ?
                """, (transaction_data.get("amount", 0), transaction_data.get("currency", "USD")))
                
                conn.commit()
            
            self.metrics["transactions_processed"] += 1
            
            await self.send_message(
                Message(
                    type=MessageType.FINANCIAL,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "transaction_created",
                        "transaction_id": transaction_data.get("id")
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error creating transaction: {str(e)}")
            raise
    
    async def _handle_get_statement(self, message: Message) -> None:
        """
        Handle get statement request.
        
        Args:
            message: Message containing statement request
        """
        try:
            start_date = message.data.get("start_date")
            end_date = message.data.get("end_date")
            format = message.data.get("format", "pdf")
            
            statement = await self.mercury_client.get_account_statement(
                start_date=start_date,
                end_date=end_date,
                format=format
            )
            
            await self.send_message(
                Message(
                    type=MessageType.FINANCIAL,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "statement_response",
                        "statement": statement
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error getting statement: {str(e)}")
            raise
    
    async def _handle_process_payment(self, message: Message) -> None:
        """
        Handle payment processing request.
        
        Args:
            message: Message containing payment request
        """
        try:
            payment_data = message.data.get("payment_data")
            
            # Create payment intent
            payment_intent = await self.stripe_client.create_payment_intent(payment_data)
            
            # Confirm payment intent
            confirmed_intent = await self.stripe_client.confirm_payment_intent(
                payment_intent["id"]
            )
            
            self.metrics["payments_processed"] += 1
            
            await self.send_message(
                Message(
                    type=MessageType.PAYMENT,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "payment_processed",
                        "payment_intent": confirmed_intent
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error processing payment: {str(e)}")
            raise
    
    async def _handle_create_payment_method(self, message: Message) -> None:
        """
        Handle payment method creation request.
        
        Args:
            message: Message containing payment method creation request
        """
        try:
            payment_method_data = message.data.get("payment_method_data")
            customer_id = message.data.get("customer_id")
            
            # Create payment method
            payment_method = await self.stripe_client.create_payment_method(
                payment_method_data
            )
            
            # Attach to customer
            attached_method = await self.stripe_client.attach_payment_method(
                payment_method["id"],
                customer_id
            )
            
            await self.send_message(
                Message(
                    type=MessageType.PAYMENT,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "payment_method_created",
                        "payment_method": attached_method
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error creating payment method: {str(e)}")
            raise
    
    async def _handle_get_payment_history(self, message: Message) -> None:
        """
        Handle payment history request.
        
        Args:
            message: Message containing payment history request
        """
        try:
            customer_id = message.data.get("customer_id")
            start_date = message.data.get("start_date")
            end_date = message.data.get("end_date")
            
            payments = await self.stripe_client.list_events(
                event_types=["payment_intent.succeeded"],
                limit=100
            )
            
            await self.send_message(
                Message(
                    type=MessageType.PAYMENT,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "payment_history_response",
                        "payments": payments
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error getting payment history: {str(e)}")
            raise
    
    async def _handle_create_subscription(self, message: Message) -> None:
        """
        Handle subscription creation request.
        
        Args:
            message: Message containing subscription creation request
        """
        try:
            subscription_data = message.data.get("subscription_data")
            
            subscription = await self.stripe_client.create_subscription(
                subscription_data
            )
            
            self.metrics["subscriptions_managed"] += 1
            
            await self.send_message(
                Message(
                    type=MessageType.SUBSCRIPTION,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "subscription_created",
                        "subscription": subscription
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error creating subscription: {str(e)}")
            raise
    
    async def _handle_update_subscription(self, message: Message) -> None:
        """
        Handle subscription update request.
        
        Args:
            message: Message containing subscription update request
        """
        try:
            subscription_id = message.data.get("subscription_id")
            subscription_data = message.data.get("subscription_data")
            
            subscription = await self.stripe_client.update_subscription(
                subscription_id,
                subscription_data
            )
            
            await self.send_message(
                Message(
                    type=MessageType.SUBSCRIPTION,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "subscription_updated",
                        "subscription": subscription
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error updating subscription: {str(e)}")
            raise
    
    async def _handle_cancel_subscription(self, message: Message) -> None:
        """
        Handle subscription cancellation request.
        
        Args:
            message: Message containing subscription cancellation request
        """
        try:
            subscription_id = message.data.get("subscription_id")
            cancellation_data = message.data.get("cancellation_data")
            
            subscription = await self.stripe_client.cancel_subscription(
                subscription_id,
                cancellation_data
            )
            
            await self.send_message(
                Message(
                    type=MessageType.SUBSCRIPTION,
                    priority=MessagePriority.NORMAL,
                    data={
                        "action": "subscription_cancelled",
                        "subscription": subscription
                    }
                )
            )
        except Exception as e:
            self.logger.error(f"Error cancelling subscription: {str(e)}")
            raise
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Get agent metrics.
        
        Returns:
            Dict[str, Any]: Agent metrics
        """
        return self.metrics 