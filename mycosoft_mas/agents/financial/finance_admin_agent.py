"""
Finance Administration Agent for Mycosoft MAS

This module implements the FinanceAdminAgent that handles financial administration,
working with the FinancialOperationsAgent for banking, accounting, and financial management.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from mycosoft_mas.agents.base_agent import BaseAgent
from mycosoft_mas.agents.financial.financial_operations_agent import FinancialOperationsAgent


class FinanceAdminAgent(BaseAgent):
    """
    Agent that handles financial administration for Mycosoft Inc.

    This agent manages:
    - Financial planning and budgeting
    - Expense management and approval
    - Financial reporting and analysis
    - Investment tracking
    - Working with FinancialOperationsAgent for transactions
    """

    def __init__(self, agent_id: str, name: str, config: dict):
        """Initialize the finance administration agent."""
        super().__init__(agent_id, name, config)

        # Initialize FinancialOperationsAgent
        self.financial_ops = FinancialOperationsAgent(
            agent_id=f"{agent_id}_ops", name="FinancialOperations", config=config
        )

        # Load configuration
        self.budget_config = config.get("budget", {})
        self.expense_config = config.get("expense", {})

        # Initialize state
        self.budgets = {}
        self.expenses = {}
        self.approvals = {}
        self.investments = {}

        # Create data directory
        self.data_dir = Path("data/finance_admin")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Metrics
        self.metrics.update(
            {
                "budgets_created": 0,
                "expenses_processed": 0,
                "approvals_handled": 0,
                "reports_generated": 0,
            }
        )

    async def _initialize_services(self) -> None:
        """Initialize finance administration services."""
        # Initialize FinancialOperationsAgent
        await self.financial_ops.initialize()

        # Load financial data
        await self._load_financial_data()

        # Initialize approval workflows
        await self._initialize_approval_workflows()

    async def _load_financial_data(self) -> None:
        """Load financial data from storage (local JSON files)."""
        import json

        for name, store in [
            ("budgets", self.budgets),
            ("expenses", self.expenses),
            ("approvals", self.approvals),
            ("investments", self.investments),
        ]:
            path = self.data_dir / f"{name}.json"
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    store.update(data)
                    self.logger.info(f"Loaded {len(data)} {name} records")
                except Exception as e:
                    self.logger.warning(f"Failed to load {name}: {e}")

    async def _initialize_approval_workflows(self) -> None:
        """Initialize expense approval workflows with configured thresholds."""
        self.approval_thresholds = {
            "auto_approve": self.expense_config.get("auto_approve_limit", 100.0),
            "manager_approve": self.expense_config.get("manager_approve_limit", 1000.0),
            "director_approve": self.expense_config.get("director_approve_limit", 10000.0),
        }
        self.logger.info(f"Approval workflows initialized: {self.approval_thresholds}")

    async def create_budget(self, budget_details: Dict[str, Any]) -> Optional[str]:
        """
        Create a new budget.

        Args:
            budget_details: Budget details including period, categories, and amounts

        Returns:
            Optional[str]: Budget ID if successful, None otherwise
        """
        try:
            # Validate budget details
            if not self._validate_budget_details(budget_details):
                raise ValueError("Invalid budget details")

            # Create budget
            budget_id = await self._create_budget_record(budget_details)

            # Update metrics
            self.metrics["budgets_created"] += 1

            return budget_id
        except Exception as e:
            self.logger.error(f"Failed to create budget: {str(e)}")
            return None

    async def process_expense(self, expense: Dict[str, Any]) -> Optional[str]:
        """
        Process an expense request.

        Args:
            expense: Expense details including amount, category, and description

        Returns:
            Optional[str]: Expense ID if successful, None otherwise
        """
        try:
            # Validate expense
            if not self._validate_expense(expense):
                raise ValueError("Invalid expense format")

            # Check budget
            if not await self._check_budget_availability(expense):
                raise ValueError("Insufficient budget")

            # Create expense record
            expense_id = await self._create_expense_record(expense)

            # Process payment if auto-approved
            if await self._is_auto_approved(expense):
                await self.financial_ops.process_transaction(
                    {
                        "type": "expense",
                        "amount": expense["amount"],
                        "from_account": expense["account"],
                        "to_account": expense["payee"],
                        "description": expense["description"],
                    }
                )

            # Update metrics
            self.metrics["expenses_processed"] += 1

            return expense_id
        except Exception as e:
            self.logger.error(f"Failed to process expense: {str(e)}")
            return None

    async def handle_approval(self, approval_request: Dict[str, Any]) -> bool:
        """
        Handle an expense approval request.

        Args:
            approval_request: Approval request details

        Returns:
            bool: True if approval was handled successfully
        """
        try:
            # Validate approval request
            if not self._validate_approval_request(approval_request):
                raise ValueError("Invalid approval request")

            # Process approval
            approved = await self._process_approval(approval_request)

            # Process payment if approved
            if approved:
                await self.financial_ops.process_transaction(
                    {
                        "type": "expense",
                        "amount": approval_request["expense"]["amount"],
                        "from_account": approval_request["expense"]["account"],
                        "to_account": approval_request["expense"]["payee"],
                        "description": approval_request["expense"]["description"],
                    }
                )

            # Update metrics
            self.metrics["approvals_handled"] += 1

            return True
        except Exception as e:
            self.logger.error(f"Failed to handle approval: {str(e)}")
            return False

    async def generate_financial_report(
        self, report_type: str, period: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
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
            report_data = await self.financial_ops.generate_financial_report(report_type, period)

            # Add budget analysis
            report_data["budget_analysis"] = await self._analyze_budgets(period)

            # Update metrics
            self.metrics["reports_generated"] += 1

            return report_data
        except Exception as e:
            self.logger.error(f"Failed to generate financial report: {str(e)}")
            return None

    def _validate_budget_details(self, details: Dict[str, Any]) -> bool:
        """Validate budget details format."""
        required_fields = ["period", "categories", "amounts"]
        return all(field in details for field in required_fields)

    def _validate_expense(self, expense: Dict[str, Any]) -> bool:
        """Validate expense format."""
        required_fields = ["amount", "category", "description", "account", "payee"]
        return all(field in expense for field in required_fields)

    def _validate_approval_request(self, request: Dict[str, Any]) -> bool:
        """Validate approval request format."""
        required_fields = ["expense_id", "approver_id", "decision"]
        return all(field in request for field in required_fields)

    def _validate_report_request(self, report_type: str, period: Dict[str, Any]) -> bool:
        """Validate financial report request."""
        required_fields = ["start_date", "end_date"]
        return all(field in period for field in required_fields)

    async def _create_budget_record(self, details: Dict[str, Any]) -> str:
        """Create a budget record in local state."""
        budget_id = f"budget_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{len(self.budgets)}"
        self.budgets[budget_id] = {
            "id": budget_id,
            "period": details["period"],
            "categories": details["categories"],
            "amounts": details["amounts"],
            "spent": {cat: 0.0 for cat in details["categories"]},
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
        }
        self.logger.info(f"Created budget record: {budget_id}")
        return budget_id

    async def _check_budget_availability(self, expense: Dict[str, Any]) -> bool:
        """Check if there is sufficient budget for an expense."""
        category = expense.get("category", "")
        amount = expense.get("amount", 0)
        for budget in self.budgets.values():
            if budget["status"] != "active":
                continue
            if category in budget.get("amounts", {}):
                allocated = budget["amounts"][category]
                spent = budget["spent"].get(category, 0)
                if allocated - spent >= amount:
                    return True
        # If no active budget covers this category, allow it (no budget constraint)
        if not any(category in b.get("amounts", {}) for b in self.budgets.values()):
            return True
        return False

    async def _create_expense_record(self, expense: Dict[str, Any]) -> str:
        """Create an expense record in local state."""
        expense_id = f"exp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{len(self.expenses)}"
        self.expenses[expense_id] = {
            "id": expense_id,
            **expense,
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending",
        }
        # Update budget spent tracking
        category = expense.get("category", "")
        amount = expense.get("amount", 0)
        for budget in self.budgets.values():
            if budget["status"] == "active" and category in budget.get("spent", {}):
                budget["spent"][category] += amount
                break
        self.logger.info(f"Created expense record: {expense_id}")
        return expense_id

    async def _is_auto_approved(self, expense: Dict[str, Any]) -> bool:
        """Check if an expense can be auto-approved based on threshold."""
        auto_approve_limit = self.expense_config.get("auto_approve_limit", 100.0)
        return expense.get("amount", float("inf")) <= auto_approve_limit

    async def _process_approval(self, request: Dict[str, Any]) -> bool:
        """Process an approval request and update expense status."""
        expense_id = request.get("expense_id", "")
        decision = request.get("decision", "rejected")
        approved = decision.lower() in ("approved", "approve", "yes")
        if expense_id in self.expenses:
            self.expenses[expense_id]["status"] = "approved" if approved else "rejected"
            self.expenses[expense_id]["approved_by"] = request.get("approver_id")
            self.expenses[expense_id]["approved_at"] = datetime.utcnow().isoformat()
        self.approvals[f"appr_{len(self.approvals)}"] = {
            "expense_id": expense_id,
            "decision": decision,
            "approver_id": request.get("approver_id"),
            "timestamp": datetime.utcnow().isoformat(),
        }
        return approved

    async def _analyze_budgets(self, period: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze budgets for a period and return summary metrics."""
        total_allocated = 0.0
        total_spent = 0.0
        category_breakdown: Dict[str, Dict[str, float]] = {}
        for budget in self.budgets.values():
            if budget["status"] != "active":
                continue
            for cat, allocated in budget.get("amounts", {}).items():
                spent = budget.get("spent", {}).get(cat, 0)
                total_allocated += allocated
                total_spent += spent
                category_breakdown[cat] = {
                    "allocated": allocated,
                    "spent": spent,
                    "remaining": allocated - spent,
                    "utilization_pct": round((spent / allocated) * 100, 1) if allocated > 0 else 0,
                }
        return {
            "total_allocated": total_allocated,
            "total_spent": total_spent,
            "total_remaining": total_allocated - total_spent,
            "utilization_pct": (
                round((total_spent / total_allocated) * 100, 1) if total_allocated > 0 else 0
            ),
            "category_breakdown": category_breakdown,
            "active_budgets": sum(1 for b in self.budgets.values() if b["status"] == "active"),
        }
