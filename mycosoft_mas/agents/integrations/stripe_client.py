"""
Stripe API Client for Mycosoft MAS

This module implements the Stripe API client for handling payment processing,
subscription management, and customer billing.
"""

import asyncio
import logging
import stripe
from typing import Dict, Any, List, Optional
from datetime import datetime

class StripeClient:
    """
    Client for interacting with the Stripe API.
    
    This client handles:
    - Payment processing
    - Subscription management
    - Customer billing
    - Payment method management
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the Stripe API client.
        
        Args:
            api_key: Stripe API key
        """
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
        stripe.api_key = api_key
    
    async def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new customer in Stripe.
        
        Args:
            customer_data: Customer details including email, name, etc.
            
        Returns:
            Dict[str, Any]: Created customer details
        """
        try:
            customer = stripe.Customer.create(**customer_data)
            return customer.to_dict()
        except stripe.error.StripeError as e:
            self.logger.error(f"Error creating customer: {str(e)}")
            raise
    
    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """
        Get details of a specific customer.
        
        Args:
            customer_id: ID of the customer to retrieve
            
        Returns:
            Dict[str, Any]: Customer details
        """
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return customer.to_dict()
        except stripe.error.StripeError as e:
            self.logger.error(f"Error getting customer: {str(e)}")
            raise
    
    async def update_customer(self, customer_id: str, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a customer's details.
        
        Args:
            customer_id: ID of the customer to update
            customer_data: Updated customer details
            
        Returns:
            Dict[str, Any]: Updated customer details
        """
        try:
            customer = stripe.Customer.modify(customer_id, **customer_data)
            return customer.to_dict()
        except stripe.error.StripeError as e:
            self.logger.error(f"Error updating customer: {str(e)}")
            raise
    
    async def create_payment_method(self, payment_method_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new payment method.
        
        Args:
            payment_method_data: Payment method details
            
        Returns:
            Dict[str, Any]: Created payment method details
        """
        try:
            payment_method = stripe.PaymentMethod.create(**payment_method_data)
            return payment_method.to_dict()
        except stripe.error.StripeError as e:
            self.logger.error(f"Error creating payment method: {str(e)}")
            raise
    
    async def attach_payment_method(self, payment_method_id: str, customer_id: str) -> Dict[str, Any]:
        """
        Attach a payment method to a customer.
        
        Args:
            payment_method_id: ID of the payment method
            customer_id: ID of the customer
            
        Returns:
            Dict[str, Any]: Attached payment method details
        """
        try:
            payment_method = stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
            return payment_method.to_dict()
        except stripe.error.StripeError as e:
            self.logger.error(f"Error attaching payment method: {str(e)}")
            raise
    
    async def create_payment_intent(self, payment_intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new payment intent.
        
        Args:
            payment_intent_data: Payment intent details
            
        Returns:
            Dict[str, Any]: Created payment intent details
        """
        try:
            payment_intent = stripe.PaymentIntent.create(**payment_intent_data)
            return payment_intent.to_dict()
        except stripe.error.StripeError as e:
            self.logger.error(f"Error creating payment intent: {str(e)}")
            raise
    
    async def confirm_payment_intent(self, payment_intent_id: str, 
                                   confirmation_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Confirm a payment intent.
        
        Args:
            payment_intent_id: ID of the payment intent
            confirmation_data: Additional confirmation data
            
        Returns:
            Dict[str, Any]: Confirmed payment intent details
        """
        try:
            confirmation_data = confirmation_data or {}
            payment_intent = stripe.PaymentIntent.confirm(payment_intent_id, **confirmation_data)
            return payment_intent.to_dict()
        except stripe.error.StripeError as e:
            self.logger.error(f"Error confirming payment intent: {str(e)}")
            raise
    
    async def create_subscription(self, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new subscription.
        
        Args:
            subscription_data: Subscription details
            
        Returns:
            Dict[str, Any]: Created subscription details
        """
        try:
            subscription = stripe.Subscription.create(**subscription_data)
            return subscription.to_dict()
        except stripe.error.StripeError as e:
            self.logger.error(f"Error creating subscription: {str(e)}")
            raise
    
    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Get details of a specific subscription.
        
        Args:
            subscription_id: ID of the subscription to retrieve
            
        Returns:
            Dict[str, Any]: Subscription details
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription.to_dict()
        except stripe.error.StripeError as e:
            self.logger.error(f"Error getting subscription: {str(e)}")
            raise
    
    async def update_subscription(self, subscription_id: str, 
                                subscription_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a subscription's details.
        
        Args:
            subscription_id: ID of the subscription to update
            subscription_data: Updated subscription details
            
        Returns:
            Dict[str, Any]: Updated subscription details
        """
        try:
            subscription = stripe.Subscription.modify(subscription_id, **subscription_data)
            return subscription.to_dict()
        except stripe.error.StripeError as e:
            self.logger.error(f"Error updating subscription: {str(e)}")
            raise
    
    async def cancel_subscription(self, subscription_id: str, 
                                cancellation_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: ID of the subscription to cancel
            cancellation_data: Additional cancellation data
            
        Returns:
            Dict[str, Any]: Cancelled subscription details
        """
        try:
            cancellation_data = cancellation_data or {}
            subscription = stripe.Subscription.delete(subscription_id, **cancellation_data)
            return subscription.to_dict()
        except stripe.error.StripeError as e:
            self.logger.error(f"Error cancelling subscription: {str(e)}")
            raise
    
    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new invoice.
        
        Args:
            invoice_data: Invoice details
            
        Returns:
            Dict[str, Any]: Created invoice details
        """
        try:
            invoice = stripe.Invoice.create(**invoice_data)
            return invoice.to_dict()
        except stripe.error.StripeError as e:
            self.logger.error(f"Error creating invoice: {str(e)}")
            raise
    
    async def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """
        Get details of a specific invoice.
        
        Args:
            invoice_id: ID of the invoice to retrieve
            
        Returns:
            Dict[str, Any]: Invoice details
        """
        try:
            invoice = stripe.Invoice.retrieve(invoice_id)
            return invoice.to_dict()
        except stripe.error.StripeError as e:
            self.logger.error(f"Error getting invoice: {str(e)}")
            raise
    
    async def pay_invoice(self, invoice_id: str, 
                         payment_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Pay an invoice.
        
        Args:
            invoice_id: ID of the invoice to pay
            payment_data: Payment details
            
        Returns:
            Dict[str, Any]: Paid invoice details
        """
        try:
            payment_data = payment_data or {}
            invoice = stripe.Invoice.pay(invoice_id, **payment_data)
            return invoice.to_dict()
        except stripe.error.StripeError as e:
            self.logger.error(f"Error paying invoice: {str(e)}")
            raise
    
    async def list_events(self, event_types: Optional[List[str]] = None, 
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        List recent events.
        
        Args:
            event_types: List of event types to filter by
            limit: Maximum number of events to return
            
        Returns:
            List[Dict[str, Any]]: List of events
        """
        try:
            params = {"limit": limit}
            if event_types:
                params["types"] = event_types
            
            events = stripe.Event.list(**params)
            return [event.to_dict() for event in events.data]
        except stripe.error.StripeError as e:
            self.logger.error(f"Error listing events: {str(e)}")
            raise 