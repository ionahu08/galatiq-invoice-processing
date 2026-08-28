"""Payment Agent - Processes approved invoices for payment."""

from src.agents.base import BaseAgent
from src.models import ApprovalResult, ExtractedInvoice, PaymentResult


class PaymentAgent(BaseAgent):
    """
    Processes payments for approved invoices.

    Responsibilities:
    - Call mock payment API for approved invoices
    - Log rejections with reasoning
    - Track transaction status
    - Return PaymentResult
    """

    def __init__(self, name: str = "PaymentAgent"):
        """Initialize the payment agent."""
        super().__init__(name)

    async def execute(
        self, extracted: ExtractedInvoice, approval: ApprovalResult
    ) -> PaymentResult:
        """
        Process payment for an invoice.

        Args:
            extracted: ExtractedInvoice from IngestionAgent
            approval: ApprovalResult from ApprovalAgent

        Returns:
            PaymentResult with payment status
        """
        self.log_execution(f"Processing payment for {extracted.invoice_number}")

        if approval.requires_manual_review:
            return PaymentResult(
                invoice_number=extracted.invoice_number,
                vendor=extracted.vendor,
                amount=extracted.amount,
                status="requires_review",
                message=f"Invoice requires manual review: {approval.reasoning}",
            )

        if not approval.is_approved:
            return PaymentResult(
                invoice_number=extracted.invoice_number,
                vendor=extracted.vendor,
                amount=extracted.amount,
                status="rejected",
                message=f"Invoice rejected: {approval.reasoning}",
            )

        # Process payment
        try:
            result = await self._call_mock_payment_api(
                extracted.vendor, extracted.amount
            )
            self.log_execution(f"Payment processed: {result}")
            return result
        except Exception as e:
            self.log_execution(f"Payment failed: {str(e)}", level="error")
            return PaymentResult(
                invoice_number=extracted.invoice_number,
                vendor=extracted.vendor,
                amount=extracted.amount,
                status="failed",
                message=f"Payment processing failed: {str(e)}",
            )

    async def _call_mock_payment_api(
        self, vendor: str, amount: float
    ) -> PaymentResult:
        """
        Call the mock payment API.

        Args:
            vendor: Vendor name
            amount: Payment amount

        Returns:
            PaymentResult from the API
        """
        # Mock implementation - would call real payment API in production
        self.log_execution(f"Calling mock payment API: {vendor}, ${amount:.2f}")

        # For now, always succeed
        return PaymentResult(
            invoice_number="",  # Set by caller
            vendor=vendor,
            amount=amount,
            status="success",
            transaction_id=f"TXN-{vendor[:3].upper()}-12345",
            message=f"Paid ${amount:.2f} to {vendor}",
        )
