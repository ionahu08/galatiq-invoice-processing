"""Validation Agent - Verifies extracted invoice data against inventory database."""

from pathlib import Path

from src.agents.base import BaseAgent
from src.database.setup import check_stock, query_inventory
from src.models import ExtractedInvoice, ValidationIssue, ValidationResult


class ValidationAgent(BaseAgent):
    """
    Validates invoice data against inventory database.

    Responsibilities:
    - Check if items exist in inventory
    - Verify quantities are in stock
    - Flag mismatches and invalid data
    - Return ValidationResult with all issues
    """

    def __init__(self, db_path: Path, name: str = "ValidationAgent"):
        """
        Initialize the validation agent.

        Args:
            db_path: Path to inventory database
        """
        super().__init__(name)
        self.db_path = db_path

    async def execute(self, extracted_invoice: ExtractedInvoice) -> ValidationResult:
        """
        Validate an extracted invoice.

        Args:
            extracted_invoice: ExtractedInvoice from IngestionAgent

        Returns:
            ValidationResult with all validation findings
        """
        self.log_execution(f"Validating invoice {extracted_invoice.invoice_number}")

        issues = []

        # Validate basic invoice data
        if extracted_invoice.amount <= 0:
            issues.append(
                ValidationIssue(
                    issue_type="invalid_data",
                    item_name="Invoice Amount",
                    message=f"Invalid amount: {extracted_invoice.amount}",
                    severity="error",
                )
            )

        # Validate each line item
        for item in extracted_invoice.items:
            item_issues = await self._validate_item(item.item_name, item.quantity)
            issues.extend(item_issues)

        # Determine overall validity
        is_valid = not any(issue.severity == "error" for issue in issues)

        result = ValidationResult(
            invoice_number=extracted_invoice.invoice_number,
            is_valid=is_valid,
            issues=issues,
            stock_check_complete=True,
            total_issues=len(issues),
        )

        self.log_execution(
            f"Validation complete. Issues: {len(issues)}, Valid: {is_valid}"
        )

        return result

    async def _validate_item(self, item_name: str, quantity: int) -> list[ValidationIssue]:
        """
        Validate a single line item.

        Args:
            item_name: Name/ID of the item
            quantity: Requested quantity

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        # Check for negative quantities
        if quantity < 0:
            issues.append(
                ValidationIssue(
                    issue_type="invalid_data",
                    item_name=item_name,
                    message=f"Negative quantity requested: {quantity}",
                    severity="error",
                )
            )
            return issues

        # Check stock availability
        is_available, message = check_stock(self.db_path, item_name, quantity)

        if not is_available:
            severity = "error" if quantity > 0 else "warning"
            issues.append(
                ValidationIssue(
                    issue_type=(
                        "out_of_stock"
                        if "out of stock" in message.lower()
                        else "quantity_mismatch"
                        if "Insufficient" in message
                        else "unknown_item"
                    ),
                    item_name=item_name,
                    message=message,
                    severity=severity,
                )
            )

        return issues
