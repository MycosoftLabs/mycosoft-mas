"""
Financial Operations Agent for Mycosoft MAS

This module implements the FinancialOperationsAgent that handles financial operations,
including banking through Mercury, accounting through QuickBooks, and SAFE agreements.
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.messaging.message_types import Message, MessageType, MessagePriority
from mycosoft_mas.agents.enums import AgentStatus, TaskType, TaskStatus, TaskPriority

class FinancialOperationsAgent(BaseAgent):
    """
    Agent that handles financial operations for Mycosoft Inc.
    
    This agent manages:
    - Banking operations through Mercury
    - Accounting through QuickBooks
    - SAFE agreement generation and management
    - Cap table management through Pulley
    - Financial reporting and compliance
    """
    
    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the financial operations agent."""
        super().__init__(agent_id, name, config)
        
        # Load configuration
        self.mercury_config = config.get("mercury", {})
        self.quickbooks_config = config.get("quickbooks", {})
        self.pulley_config = config.get("pulley", {})
        
        # Initialize state
        self.bank_accounts = {}
        self.transactions = {}
        self.safe_agreements = {}
        self.cap_table = {}
        
        # Create data directory
        self.data_dir = Path("data/financial")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Metrics
        self.metrics.update({
            "transactions_processed": 0,
            "safe_agreements_created": 0,
            "financial_reports_generated": 0,
            "cap_table_updates": 0
        })
    
    async def _initialize_services(self) -> None:
        """Initialize financial services."""
        # Initialize Mercury client
        self.mercury_client = await self._initialize_mercury()
        
        # Initialize QuickBooks client
        self.quickbooks_client = await self._initialize_quickbooks()
        
        # Initialize Pulley client
        self.pulley_client = await self._initialize_pulley()
        
        # Load financial data
        await self._load_financial_data()
    
    async def _initialize_mercury(self) -> Optional[Dict[str, Any]]:
        """
        Initialize Mercury Bank client.
        
        Mercury Banking API: https://docs.mercury.com/
        
        Setup requirements:
        1. Create Mercury account at https://mercury.com
        2. Generate API key from Mercury Dashboard > API Keys
        3. Set environment variable: MERCURY_API_KEY=your_key_here
        4. Set environment variable: MERCURY_API_BASE_URL (defaults to https://api.mercury.com)
        
        Returns:
            Dict containing Mercury client configuration, or None if initialization fails
        """
        try:
            api_key = os.getenv("MERCURY_API_KEY")
            if not api_key:
                self.logger.warning("MERCURY_API_KEY not set - Mercury integration disabled")
                return None
            
            base_url = os.getenv("MERCURY_API_BASE_URL", "https://api.mercury.com")
            
            # Create HTTP session with authentication
            timeout = ClientTimeout(total=30)
            self.mercury_session = ClientSession(
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            mercury_client = {
                "base_url": base_url,
                "session": self.mercury_session,
                "api_key": api_key
            }
            
            # Test connection by fetching accounts
            try:
                async with self.mercury_session.get(f"{base_url}/api/v1/accounts") as response:
                    if response.status == 200:
                        accounts = await response.json()
                        self.bank_accounts = {acc["id"]: acc for acc in accounts.get("accounts", [])}
                        self.logger.info(f"Mercury initialized successfully - {len(self.bank_accounts)} accounts found")
                    elif response.status == 401:
                        self.logger.error("Mercury authentication failed - check API key")
                        return None
                    else:
                        self.logger.warning(f"Mercury connection test returned status {response.status}")
            except Exception as e:
                self.logger.error(f"Mercury connection test failed: {str(e)}")
                return None
            
            return mercury_client
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Mercury client: {str(e)}")
            return None
    
    async def _initialize_quickbooks(self) -> Optional[Dict[str, Any]]:
        """
        Initialize QuickBooks Online client.
        
        QuickBooks API: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/
        
        Setup requirements:
        1. Create Intuit Developer account at https://developer.intuit.com
        2. Create an app and get OAuth 2.0 credentials
        3. Set environment variables:
           - QUICKBOOKS_CLIENT_ID=your_client_id
           - QUICKBOOKS_CLIENT_SECRET=your_client_secret
           - QUICKBOOKS_REALM_ID=your_company_id
           - QUICKBOOKS_REFRESH_TOKEN=your_refresh_token (from OAuth flow)
           - QUICKBOOKS_ENVIRONMENT=production (or sandbox)
        4. Implement OAuth 2.0 flow to get initial tokens
        
        Returns:
            Dict containing QuickBooks client configuration, or None if initialization fails
        """
        try:
            client_id = os.getenv("QUICKBOOKS_CLIENT_ID")
            client_secret = os.getenv("QUICKBOOKS_CLIENT_SECRET")
            realm_id = os.getenv("QUICKBOOKS_REALM_ID")
            refresh_token = os.getenv("QUICKBOOKS_REFRESH_TOKEN")
            
            if not all([client_id, client_secret, realm_id, refresh_token]):
                self.logger.warning("QuickBooks credentials not fully configured - QuickBooks integration disabled")
                return None
            
            environment = os.getenv("QUICKBOOKS_ENVIRONMENT", "production")
            base_url = (
                "https://quickbooks.api.intuit.com" if environment == "production"
                else "https://sandbox-quickbooks.api.intuit.com"
            )
            
            # Create HTTP session
            timeout = ClientTimeout(total=30)
            self.quickbooks_session = ClientSession(timeout=timeout)
            
            quickbooks_client = {
                "base_url": base_url,
                "session": self.quickbooks_session,
                "client_id": client_id,
                "client_secret": client_secret,
                "realm_id": realm_id,
                "refresh_token": refresh_token,
                "access_token": None,
                "token_expires_at": None
            }
            
            # Get initial access token
            access_token = await self._refresh_quickbooks_token(quickbooks_client)
            if not access_token:
                self.logger.error("Failed to obtain QuickBooks access token")
                return None
            
            quickbooks_client["access_token"] = access_token
            quickbooks_client["token_expires_at"] = datetime.now().timestamp() + 3600  # Tokens expire in 1 hour
            
            # Test connection by fetching company info
            try:
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json"
                }
                url = f"{base_url}/v3/company/{realm_id}/companyinfo/{realm_id}"
                async with self.quickbooks_session.get(url, headers=headers) as response:
                    if response.status == 200:
                        company_info = await response.json()
                        self.logger.info(
                            f"QuickBooks initialized successfully - "
                            f"Company: {company_info.get('CompanyInfo', {}).get('CompanyName', 'Unknown')}"
                        )
                    elif response.status == 401:
                        self.logger.error("QuickBooks authentication failed - check credentials")
                        return None
                    else:
                        self.logger.warning(f"QuickBooks connection test returned status {response.status}")
            except Exception as e:
                self.logger.error(f"QuickBooks connection test failed: {str(e)}")
                return None
            
            return quickbooks_client
            
        except Exception as e:
            self.logger.error(f"Failed to initialize QuickBooks client: {str(e)}")
            return None
    
    async def _refresh_quickbooks_token(self, client: Dict[str, Any]) -> Optional[str]:
        """
        Refresh QuickBooks OAuth 2.0 access token.
        
        Args:
            client: QuickBooks client configuration dict
            
        Returns:
            New access token or None if refresh fails
        """
        try:
            token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
            
            data = {
                "grant_type": "refresh_token",
                "refresh_token": client["refresh_token"],
                "client_id": client["client_id"],
                "client_secret": client["client_secret"]
            }
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            async with client["session"].post(token_url, data=data, headers=headers) as response:
                if response.status == 200:
                    token_data = await response.json()
                    # Update refresh token if a new one is provided
                    if "refresh_token" in token_data:
                        client["refresh_token"] = token_data["refresh_token"]
                    return token_data.get("access_token")
                else:
                    self.logger.error(f"Failed to refresh QuickBooks token: status {response.status}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error refreshing QuickBooks token: {str(e)}")
            return None
    
    async def _ensure_quickbooks_token(self) -> bool:
        """
        Ensure QuickBooks access token is valid, refresh if needed.
        
        Returns:
            True if valid token is available, False otherwise
        """
        if not self.quickbooks_client:
            return False
        
        # Check if token is expired or about to expire (within 5 minutes)
        if (
            not self.quickbooks_client.get("access_token") or
            not self.quickbooks_client.get("token_expires_at") or
            datetime.now().timestamp() >= self.quickbooks_client["token_expires_at"] - 300
        ):
            access_token = await self._refresh_quickbooks_token(self.quickbooks_client)
            if access_token:
                self.quickbooks_client["access_token"] = access_token
                self.quickbooks_client["token_expires_at"] = datetime.now().timestamp() + 3600
                return True
            return False
        
        return True
    
    async def _initialize_pulley(self) -> Optional[Dict[str, Any]]:
        """
        Initialize Pulley cap table management client.
        
        Pulley API: https://docs.pulley.com/
        
        Setup requirements:
        1. Create Pulley account at https://pulley.com
        2. Generate API key from Pulley Dashboard > Settings > API
        3. Set environment variable: PULLEY_API_KEY=your_key_here
        4. Set environment variable: PULLEY_API_BASE_URL (defaults to https://api.pulley.com)
        
        Returns:
            Dict containing Pulley client configuration, or None if initialization fails
        """
        try:
            api_key = os.getenv("PULLEY_API_KEY")
            if not api_key:
                self.logger.warning("PULLEY_API_KEY not set - Pulley integration disabled")
                return None
            
            base_url = os.getenv("PULLEY_API_BASE_URL", "https://api.pulley.com")
            
            # Create HTTP session with authentication
            timeout = ClientTimeout(total=30)
            self.pulley_session = ClientSession(
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            pulley_client = {
                "base_url": base_url,
                "session": self.pulley_session,
                "api_key": api_key
            }
            
            # Test connection by fetching company info
            try:
                async with self.pulley_session.get(f"{base_url}/v1/company") as response:
                    if response.status == 200:
                        company_info = await response.json()
                        self.logger.info(
                            f"Pulley initialized successfully - "
                            f"Company: {company_info.get('name', 'Unknown')}"
                        )
                        
                        # Fetch initial cap table data
                        await self._fetch_pulley_cap_table(pulley_client)
                        
                    elif response.status == 401:
                        self.logger.error("Pulley authentication failed - check API key")
                        return None
                    else:
                        self.logger.warning(f"Pulley connection test returned status {response.status}")
            except Exception as e:
                self.logger.error(f"Pulley connection test failed: {str(e)}")
                return None
            
            return pulley_client
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Pulley client: {str(e)}")
            return None
    
    async def _fetch_pulley_cap_table(self, client: Dict[str, Any]) -> None:
        """
        Fetch current cap table from Pulley.
        
        Args:
            client: Pulley client configuration dict
        """
        try:
            base_url = client["base_url"]
            session = client["session"]
            
            # Fetch stakeholders
            async with session.get(f"{base_url}/v1/stakeholders") as response:
                if response.status == 200:
                    stakeholders_data = await response.json()
                    self.cap_table["stakeholders"] = stakeholders_data.get("stakeholders", [])
                    self.logger.info(f"Fetched {len(self.cap_table['stakeholders'])} stakeholders from Pulley")
            
            # Fetch securities
            async with session.get(f"{base_url}/v1/securities") as response:
                if response.status == 200:
                    securities_data = await response.json()
                    self.cap_table["securities"] = securities_data.get("securities", [])
                    self.logger.info(f"Fetched {len(self.cap_table['securities'])} securities from Pulley")
            
            # Fetch option grants
            async with session.get(f"{base_url}/v1/option_grants") as response:
                if response.status == 200:
                    grants_data = await response.json()
                    self.cap_table["option_grants"] = grants_data.get("option_grants", [])
                    self.logger.info(f"Fetched {len(self.cap_table['option_grants'])} option grants from Pulley")
                    
        except Exception as e:
            self.logger.error(f"Failed to fetch Pulley cap table: {str(e)}")
    
    async def _load_financial_data(self) -> None:
        """Load financial data from various services."""
        try:
            # Load recent transactions from Mercury
            if self.mercury_client:
                await self._load_mercury_transactions()
            
            # Load QuickBooks accounts
            if self.quickbooks_client:
                await self._load_quickbooks_accounts()
            
            # Cap table already loaded during Pulley initialization
            
            self.logger.info("Financial data loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading financial data: {str(e)}")
    
    async def _load_mercury_transactions(self) -> None:
        """Load recent transactions from Mercury."""
        if not self.mercury_client:
            return
        
        try:
            base_url = self.mercury_client["base_url"]
            session = self.mercury_client["session"]
            
            # Load transactions for each account
            for account_id in self.bank_accounts.keys():
                url = f"{base_url}/api/v1/account/{account_id}/transactions?limit=100"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        transactions = data.get("transactions", [])
                        
                        for txn in transactions:
                            self.transactions[txn["id"]] = txn
                        
                        self.logger.info(f"Loaded {len(transactions)} transactions for account {account_id}")
                        
        except Exception as e:
            self.logger.error(f"Error loading Mercury transactions: {str(e)}")
    
    async def _load_quickbooks_accounts(self) -> None:
        """Load accounts from QuickBooks."""
        if not self.quickbooks_client or not await self._ensure_quickbooks_token():
            return
        
        try:
            base_url = self.quickbooks_client["base_url"]
            realm_id = self.quickbooks_client["realm_id"]
            session = self.quickbooks_client["session"]
            access_token = self.quickbooks_client["access_token"]
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            url = f"{base_url}/v3/company/{realm_id}/query?query=select * from Account"
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    accounts = data.get("QueryResponse", {}).get("Account", [])
                    self.logger.info(f"Loaded {len(accounts)} QuickBooks accounts")
                    
        except Exception as e:
            self.logger.error(f"Error loading QuickBooks accounts: {str(e)}")
    
    async def get_mercury_account_balance(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current balance for a Mercury account.
        
        Args:
            account_id: Mercury account ID
            
        Returns:
            Balance data with available and current balances
        """
        if not self.mercury_client:
            self.logger.error("Mercury client not initialized")
            return None
        
        try:
            base_url = self.mercury_client["base_url"]
            session = self.mercury_client["session"]
            
            url = f"{base_url}/api/v1/account/{account_id}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    account_data = await response.json()
                    balance = {
                        "account_id": account_id,
                        "available_balance": account_data.get("availableBalance"),
                        "current_balance": account_data.get("currentBalance"),
                        "currency": account_data.get("currency", "USD"),
                        "as_of": datetime.now().isoformat()
                    }
                    self.logger.info(f"Retrieved balance for account {account_id}")
                    return balance
                else:
                    error_text = await response.text()
                    self.logger.error(f"Failed to get Mercury balance: {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error getting Mercury account balance: {str(e)}")
            return None
    
    async def get_mercury_transactions(
        self,
        account_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get transactions for a Mercury account.
        
        Args:
            account_id: Mercury account ID
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            limit: Maximum number of transactions to return
            
        Returns:
            List of transactions if successful, None otherwise
        """
        if not self.mercury_client:
            self.logger.error("Mercury client not initialized")
            return None
        
        try:
            base_url = self.mercury_client["base_url"]
            session = self.mercury_client["session"]
            
            url = f"{base_url}/api/v1/account/{account_id}/transactions?limit={limit}"
            
            if start_date:
                url += f"&start={start_date}"
            if end_date:
                url += f"&end={end_date}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    transactions = data.get("transactions", [])
                    self.logger.info(f"Retrieved {len(transactions)} transactions for account {account_id}")
                    return transactions
                else:
                    error_text = await response.text()
                    self.logger.error(f"Failed to get Mercury transactions: {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error getting Mercury transactions: {str(e)}")
            return None
    
    async def process_transaction(self, transaction: Dict[str, Any]) -> Optional[str]:
        """
        Process a financial transaction.
        
        Args:
            transaction: Transaction details including type, amount, and accounts
            
        Returns:
            Optional[str]: Transaction ID if successful, None otherwise
        """
        try:
            # Validate transaction
            if not self._validate_transaction(transaction):
                raise ValueError("Invalid transaction format")
            
            # Process through Mercury
            transaction_id = await self._process_mercury_transaction(transaction)
            
            # Record in QuickBooks
            await self._record_quickbooks_transaction(transaction)
            
            # Update metrics
            self.metrics["transactions_processed"] += 1
            
            return transaction_id
        except Exception as e:
            self.logger.error(f"Failed to process transaction: {str(e)}")
            return None
    
    async def create_safe_agreement(self, agreement_details: Dict[str, Any]) -> Optional[str]:
        """
        Create a SAFE agreement.
        
        Args:
            agreement_details: Agreement details including investor, amount, and terms
            
        Returns:
            Optional[str]: Agreement ID if successful, None otherwise
        """
        try:
            # Validate agreement details
            if not self._validate_safe_agreement(agreement_details):
                raise ValueError("Invalid agreement details")
            
            # Generate agreement
            agreement_id = await self._generate_safe_agreement(agreement_details)
            
            # Update cap table
            await self._update_cap_table(agreement_details)
            
            # Update metrics
            self.metrics["safe_agreements_created"] += 1
            self.metrics["cap_table_updates"] += 1
            
            return agreement_id
        except Exception as e:
            self.logger.error(f"Failed to create SAFE agreement: {str(e)}")
            return None
    
    async def generate_financial_report(self, report_type: str, period: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate a financial report.
        
        Args:
            report_type: Type of report to generate
            period: Report period details
            
        Returns:
            Optional[Dict[str, Any]]: Report data if successful, None otherwise
        """
        try:
            # Validate report request
            if not self._validate_report_request(report_type, period):
                raise ValueError("Invalid report request")
            
            # Generate report
            report_data = await self._generate_report(report_type, period)
            
            # Update metrics
            self.metrics["financial_reports_generated"] += 1
            
            return report_data
        except Exception as e:
            self.logger.error(f"Failed to generate financial report: {str(e)}")
            return None
    
    async def update_cap_table(self, update_details: Dict[str, Any]) -> bool:
        """
        Update the cap table.
        
        Args:
            update_details: Cap table update details
            
        Returns:
            bool: True if update was successful
        """
        try:
            # Validate update details
            if not self._validate_cap_table_update(update_details):
                raise ValueError("Invalid cap table update")
            
            # Update cap table
            await self._process_cap_table_update(update_details)
            
            # Update metrics
            self.metrics["cap_table_updates"] += 1
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to update cap table: {str(e)}")
            return False
    
    def _validate_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Validate transaction format."""
        required_fields = ["type", "amount", "from_account", "to_account"]
        return all(field in transaction for field in required_fields)
    
    def _validate_safe_agreement(self, agreement: Dict[str, Any]) -> bool:
        """Validate SAFE agreement format."""
        required_fields = ["investor", "amount", "terms", "valuation_cap"]
        return all(field in agreement for field in required_fields)
    
    def _validate_report_request(self, report_type: str, period: Dict[str, Any]) -> bool:
        """Validate financial report request."""
        required_fields = ["start_date", "end_date"]
        return all(field in period for field in required_fields)
    
    def _validate_cap_table_update(self, update: Dict[str, Any]) -> bool:
        """Validate cap table update format."""
        required_fields = ["type", "details", "effective_date"]
        return all(field in update for field in required_fields)
    
    async def _process_mercury_transaction(self, transaction: Dict[str, Any]) -> Optional[str]:
        """
        Process a transaction through Mercury Bank.
        
        Args:
            transaction: Transaction details with keys:
                - type: "transfer", "payment", "wire"
                - amount: Amount in cents (integer)
                - from_account: Source account ID
                - to_account: Destination (account ID for internal, or external details)
                - description: Transaction description
                
        Returns:
            Transaction ID if successful, None otherwise
        """
        if not self.mercury_client:
            self.logger.error("Mercury client not initialized")
            return None
        
        try:
            base_url = self.mercury_client["base_url"]
            session = self.mercury_client["session"]
            
            transaction_type = transaction.get("type", "transfer")
            
            if transaction_type == "transfer":
                # Internal transfer between Mercury accounts
                url = f"{base_url}/api/v1/account/{transaction['from_account']}/transactions"
                payload = {
                    "amount": transaction["amount"],
                    "counterpartyId": transaction["to_account"],
                    "note": transaction.get("description", ""),
                    "idempotencyKey": f"txn_{datetime.now().timestamp()}_{transaction['amount']}"
                }
                
            elif transaction_type == "payment":
                # ACH payment
                url = f"{base_url}/api/v1/account/{transaction['from_account']}/transactions"
                payload = {
                    "amount": transaction["amount"],
                    "recipient": transaction["to_account"],
                    "note": transaction.get("description", ""),
                    "paymentType": "ach",
                    "idempotencyKey": f"pay_{datetime.now().timestamp()}_{transaction['amount']}"
                }
                
            elif transaction_type == "wire":
                # Wire transfer
                url = f"{base_url}/api/v1/account/{transaction['from_account']}/transactions"
                payload = {
                    "amount": transaction["amount"],
                    "recipient": transaction["to_account"],
                    "note": transaction.get("description", ""),
                    "paymentType": "wire",
                    "idempotencyKey": f"wire_{datetime.now().timestamp()}_{transaction['amount']}"
                }
            else:
                self.logger.error(f"Unsupported transaction type: {transaction_type}")
                return None
            
            async with session.post(url, json=payload) as response:
                if response.status == 200 or response.status == 201:
                    result = await response.json()
                    transaction_id = result.get("id", result.get("transactionId"))
                    self.logger.info(f"Mercury transaction successful: {transaction_id}")
                    
                    # Store transaction locally
                    self.transactions[transaction_id] = {
                        **transaction,
                        "id": transaction_id,
                        "timestamp": datetime.now().isoformat(),
                        "status": "completed"
                    }
                    
                    return transaction_id
                else:
                    error_text = await response.text()
                    self.logger.error(f"Mercury transaction failed: status {response.status}, {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error processing Mercury transaction: {str(e)}")
            return None
    
    async def _record_quickbooks_transaction(self, transaction: Dict[str, Any]) -> Optional[str]:
        """
        Record a transaction in QuickBooks Online.
        
        Args:
            transaction: Transaction details to record
            
        Returns:
            QuickBooks transaction ID if successful, None otherwise
        """
        if not self.quickbooks_client:
            self.logger.error("QuickBooks client not initialized")
            return None
        
        # Ensure we have a valid access token
        if not await self._ensure_quickbooks_token():
            self.logger.error("Failed to ensure valid QuickBooks token")
            return None
        
        try:
            base_url = self.quickbooks_client["base_url"]
            realm_id = self.quickbooks_client["realm_id"]
            session = self.quickbooks_client["session"]
            access_token = self.quickbooks_client["access_token"]
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            transaction_type = transaction.get("type", "transfer")
            
            if transaction_type == "transfer":
                # Create a Transfer entry
                url = f"{base_url}/v3/company/{realm_id}/transfer"
                payload = {
                    "Amount": transaction["amount"] / 100,  # Convert cents to dollars
                    "FromAccountRef": {"value": transaction["from_account"]},
                    "ToAccountRef": {"value": transaction["to_account"]},
                    "PrivateNote": transaction.get("description", ""),
                    "TxnDate": datetime.now().strftime("%Y-%m-%d")
                }
                
            elif transaction_type in ["payment", "wire"]:
                # Create a Bill Payment or Check
                url = f"{base_url}/v3/company/{realm_id}/purchase"
                payload = {
                    "PaymentType": "Check",
                    "AccountRef": {"value": transaction["from_account"]},
                    "EntityRef": {"value": transaction.get("vendor_id", "")},
                    "TotalAmt": transaction["amount"] / 100,
                    "PrivateNote": transaction.get("description", ""),
                    "TxnDate": datetime.now().strftime("%Y-%m-%d"),
                    "Line": [
                        {
                            "Amount": transaction["amount"] / 100,
                            "DetailType": "AccountBasedExpenseLineDetail",
                            "AccountBasedExpenseLineDetail": {
                                "AccountRef": {"value": transaction.get("expense_account", "1")}
                            }
                        }
                    ]
                }
            else:
                self.logger.error(f"Unsupported QuickBooks transaction type: {transaction_type}")
                return None
            
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    entity_type = "Transfer" if transaction_type == "transfer" else "Purchase"
                    qb_transaction = result.get(entity_type, {})
                    qb_id = qb_transaction.get("Id")
                    
                    self.logger.info(f"QuickBooks transaction recorded: {qb_id}")
                    return qb_id
                else:
                    error_text = await response.text()
                    self.logger.error(f"QuickBooks transaction failed: status {response.status}, {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error recording QuickBooks transaction: {str(e)}")
            return None
    
    async def create_quickbooks_invoice(
        self,
        customer_id: str,
        line_items: List[Dict[str, Any]],
        due_date: str,
        memo: Optional[str] = None
    ) -> Optional[str]:
        """
        Create an invoice in QuickBooks.
        
        Args:
            customer_id: QuickBooks customer ID
            line_items: List of invoice line items with Amount, Description, DetailType
            due_date: Invoice due date (YYYY-MM-DD)
            memo: Optional invoice memo
            
        Returns:
            Invoice ID if successful, None otherwise
        """
        if not self.quickbooks_client or not await self._ensure_quickbooks_token():
            return None
        
        try:
            base_url = self.quickbooks_client["base_url"]
            realm_id = self.quickbooks_client["realm_id"]
            session = self.quickbooks_client["session"]
            access_token = self.quickbooks_client["access_token"]
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            url = f"{base_url}/v3/company/{realm_id}/invoice"
            payload = {
                "CustomerRef": {"value": customer_id},
                "DueDate": due_date,
                "Line": line_items,
                "PrivateNote": memo or ""
            }
            
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    invoice_id = result.get("Invoice", {}).get("Id")
                    self.logger.info(f"QuickBooks invoice created: {invoice_id}")
                    return invoice_id
                else:
                    error_text = await response.text()
                    self.logger.error(f"QuickBooks invoice creation failed: {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error creating QuickBooks invoice: {str(e)}")
            return None
    
    async def get_quickbooks_financial_report(
        self,
        report_type: str,
        start_date: str,
        end_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a financial report from QuickBooks.
        
        Args:
            report_type: Report type (ProfitAndLoss, BalanceSheet, CashFlow)
            start_date: Report start date (YYYY-MM-DD)
            end_date: Report end date (YYYY-MM-DD)
            
        Returns:
            Report data if successful, None otherwise
        """
        if not self.quickbooks_client or not await self._ensure_quickbooks_token():
            return None
        
        try:
            base_url = self.quickbooks_client["base_url"]
            realm_id = self.quickbooks_client["realm_id"]
            session = self.quickbooks_client["session"]
            access_token = self.quickbooks_client["access_token"]
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            url = (
                f"{base_url}/v3/company/{realm_id}/reports/{report_type}"
                f"?start_date={start_date}&end_date={end_date}"
            )
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    report_data = await response.json()
                    self.logger.info(f"QuickBooks {report_type} report retrieved successfully")
                    return report_data
                else:
                    error_text = await response.text()
                    self.logger.error(f"QuickBooks report retrieval failed: {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error getting QuickBooks report: {str(e)}")
            return None
    
    async def _generate_safe_agreement(self, details: Dict[str, Any]) -> str:
        """Generate a SAFE agreement."""
        # TODO: Implement SAFE agreement generation
        pass
    
    async def _update_cap_table(self, details: Dict[str, Any]) -> bool:
        """
        Update the cap table in Pulley after a SAFE agreement.
        
        Args:
            details: SAFE agreement details with investor, amount, terms
            
        Returns:
            True if update was successful, False otherwise
        """
        if not self.pulley_client:
            self.logger.error("Pulley client not initialized")
            return False
        
        try:
            base_url = self.pulley_client["base_url"]
            session = self.pulley_client["session"]
            
            # Create a new SAFE note in Pulley
            url = f"{base_url}/v1/safe_notes"
            payload = {
                "stakeholderId": details.get("investor_id"),
                "investmentAmount": details["amount"],
                "valuationCap": details.get("valuation_cap"),
                "discount": details.get("discount", 0),
                "issueDate": details.get("issue_date", datetime.now().strftime("%Y-%m-%d")),
                "notes": details.get("notes", "")
            }
            
            async with session.post(url, json=payload) as response:
                if response.status == 200 or response.status == 201:
                    result = await response.json()
                    safe_id = result.get("id")
                    self.logger.info(f"Pulley SAFE note created: {safe_id}")
                    
                    # Refresh cap table data
                    await self._fetch_pulley_cap_table(self.pulley_client)
                    
                    return True
                else:
                    error_text = await response.text()
                    self.logger.error(f"Pulley SAFE creation failed: status {response.status}, {error_text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error updating Pulley cap table: {str(e)}")
            return False
    
    async def _generate_report(self, report_type: str, period: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate a financial report using QuickBooks data.
        
        Args:
            report_type: Type of report (balance_sheet, profit_loss, cash_flow)
            period: Period with start_date and end_date
            
        Returns:
            Report data if successful, None otherwise
        """
        if not self.quickbooks_client:
            self.logger.error("QuickBooks client not initialized - cannot generate report")
            return None
        
        try:
            # Map internal report types to QuickBooks report types
            qb_report_types = {
                "balance_sheet": "BalanceSheet",
                "profit_loss": "ProfitAndLoss",
                "cash_flow": "CashFlow"
            }
            
            qb_report_type = qb_report_types.get(report_type)
            if not qb_report_type:
                self.logger.error(f"Unsupported report type: {report_type}")
                return None
            
            # Get report from QuickBooks
            report_data = await self.get_quickbooks_financial_report(
                qb_report_type,
                period["start_date"],
                period["end_date"]
            )
            
            if not report_data:
                return None
            
            # Enhance with Mercury account balances
            if self.mercury_client and report_type == "balance_sheet":
                mercury_balances = []
                for account_id in self.bank_accounts.keys():
                    balance = await self.get_mercury_account_balance(account_id)
                    if balance:
                        mercury_balances.append(balance)
                
                report_data["mercury_balances"] = mercury_balances
            
            # Add cap table summary if available
            if self.pulley_client and report_type == "balance_sheet":
                cap_table_snapshot = await self.get_pulley_cap_table_snapshot()
                if cap_table_snapshot:
                    report_data["cap_table"] = cap_table_snapshot
            
            return report_data
            
        except Exception as e:
            self.logger.error(f"Error generating financial report: {str(e)}")
            return None
    
    async def cleanup(self) -> None:
        """Clean up resources when agent shuts down."""
        try:
            # Close HTTP sessions
            if hasattr(self, "mercury_session") and self.mercury_session:
                await self.mercury_session.close()
            
            if hasattr(self, "quickbooks_session") and self.quickbooks_session:
                await self.quickbooks_session.close()
            
            if hasattr(self, "pulley_session") and self.pulley_session:
                await self.pulley_session.close()
            
            self.logger.info("Financial operations agent cleaned up successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
    
    async def _process_cap_table_update(self, update: Dict[str, Any]) -> bool:
        """
        Process a cap table update in Pulley.
        
        Args:
            update: Cap table update with type, details, effective_date
            
        Returns:
            True if update was successful, False otherwise
        """
        if not self.pulley_client:
            self.logger.error("Pulley client not initialized")
            return False
        
        try:
            base_url = self.pulley_client["base_url"]
            session = self.pulley_client["session"]
            
            update_type = update.get("type")
            details = update.get("details", {})
            
            if update_type == "option_grant":
                # Create option grant
                url = f"{base_url}/v1/option_grants"
                payload = {
                    "stakeholderId": details["stakeholder_id"],
                    "quantity": details["quantity"],
                    "exercisePrice": details.get("exercise_price", 0),
                    "vestingScheduleId": details.get("vesting_schedule_id"),
                    "grantDate": update.get("effective_date", datetime.now().strftime("%Y-%m-%d"))
                }
                
            elif update_type == "stock_issuance":
                # Issue stock
                url = f"{base_url}/v1/securities"
                payload = {
                    "stakeholderId": details["stakeholder_id"],
                    "securityType": details.get("security_type", "common"),
                    "shares": details["shares"],
                    "pricePerShare": details.get("price_per_share", 0),
                    "issueDate": update.get("effective_date", datetime.now().strftime("%Y-%m-%d"))
                }
                
            elif update_type == "stakeholder":
                # Add or update stakeholder
                if details.get("stakeholder_id"):
                    # Update existing
                    url = f"{base_url}/v1/stakeholders/{details['stakeholder_id']}"
                    method = "PATCH"
                else:
                    # Create new
                    url = f"{base_url}/v1/stakeholders"
                    method = "POST"
                    
                payload = {
                    "name": details["name"],
                    "email": details.get("email"),
                    "type": details.get("type", "individual"),
                    "address": details.get("address")
                }
            else:
                self.logger.error(f"Unsupported cap table update type: {update_type}")
                return False
            
            # Make the API request
            if update_type == "stakeholder" and method == "PATCH":
                async with session.patch(url, json=payload) as response:
                    success = response.status in [200, 201]
            else:
                async with session.post(url, json=payload) as response:
                    success = response.status in [200, 201]
            
            if success:
                self.logger.info(f"Pulley cap table update successful: {update_type}")
                
                # Refresh cap table data
                await self._fetch_pulley_cap_table(self.pulley_client)
                
                return True
            else:
                error_text = await response.text()
                self.logger.error(f"Pulley cap table update failed: {error_text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing Pulley cap table update: {str(e)}")
            return False
    
    async def get_pulley_vesting_schedule(self, stakeholder_id: str) -> Optional[Dict[str, Any]]:
        """
        Get vesting schedule for a stakeholder from Pulley.
        
        Args:
            stakeholder_id: Pulley stakeholder ID
            
        Returns:
            Vesting schedule data if successful, None otherwise
        """
        if not self.pulley_client:
            self.logger.error("Pulley client not initialized")
            return None
        
        try:
            base_url = self.pulley_client["base_url"]
            session = self.pulley_client["session"]
            
            url = f"{base_url}/v1/stakeholders/{stakeholder_id}/vesting"
            
            async with session.get(url) as response:
                if response.status == 200:
                    vesting_data = await response.json()
                    self.logger.info(f"Pulley vesting schedule retrieved for {stakeholder_id}")
                    return vesting_data
                else:
                    error_text = await response.text()
                    self.logger.error(f"Pulley vesting schedule retrieval failed: {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error getting Pulley vesting schedule: {str(e)}")
            return None
    
    async def get_pulley_cap_table_snapshot(self) -> Optional[Dict[str, Any]]:
        """
        Get a snapshot of the current cap table from Pulley.
        
        Returns:
            Cap table snapshot with ownership percentages, valuations, etc.
        """
        if not self.pulley_client:
            self.logger.error("Pulley client not initialized")
            return None
        
        try:
            base_url = self.pulley_client["base_url"]
            session = self.pulley_client["session"]
            
            url = f"{base_url}/v1/cap_table/snapshot"
            
            async with session.get(url) as response:
                if response.status == 200:
                    snapshot = await response.json()
                    self.logger.info("Pulley cap table snapshot retrieved")
                    return snapshot
                else:
                    error_text = await response.text()
                    self.logger.error(f"Pulley cap table snapshot retrieval failed: {error_text}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error getting Pulley cap table snapshot: {str(e)}")
            return None 