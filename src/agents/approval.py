"""Approval Agent - Makes approval decisions with LLM reasoning and critique loop."""

from src.agents.base import BaseAgent
from src.models import (
    ApprovalReasoning,
    ApprovalResult,
    ExtractedInvoice,
    ValidationResult,
)


class ApprovalAgent(BaseAgent):
    """
    Makes approval decisions on invoices using LLM reasoning.

    Responsibilities:
    - Analyze invoice amount, vendor, items
    - Apply business rules (e.g., >$10K requires scrutiny)
    - Use generator-critic loop for confidence
    - Flag high-risk invoices for manual review
    - Return ApprovalResult with reasoning
    """

    def __init__(
        self, approval_threshold: float = 10000.0, name: str = "ApprovalAgent"
    ):
        """
        Initialize the approval agent.

        Args:
            approval_threshold: Amount above which invoices need extra scrutiny
        """
        super().__init__(name)
        self.approval_threshold = approval_threshold

    async def execute(
        self, extracted: ExtractedInvoice, validation: ValidationResult
    ) -> ApprovalResult:
        """
        Make an approval decision.

        Args:
            extracted: ExtractedInvoice from IngestionAgent
            validation: ValidationResult from ValidationAgent

        Returns:
            ApprovalResult with decision and reasoning
        """
        self.log_execution(f"Approving invoice {extracted.invoice_number}")

        # Apply business rules
        if not validation.is_valid:
            return ApprovalResult(
                invoice_number=extracted.invoice_number,
                is_approved=False,
                reasoning=f"Invoice failed validation: {validation.total_issues} issues found",
                requires_manual_review=True,
                approval_confidence=0.95,
            )

        # Check if amount exceeds threshold
        if extracted.amount > self.approval_threshold:
            return ApprovalResult(
                invoice_number=extracted.invoice_number,
                is_approved=False,
                reasoning=f"Invoice amount (${extracted.amount:.2f}) exceeds approval threshold (${self.approval_threshold:.2f}). Requires manual review.",
                requires_manual_review=True,
                approval_confidence=0.90,
            )

        # Basic approval for normal invoices
        return ApprovalResult(
            invoice_number=extracted.invoice_number,
            is_approved=True,
            reasoning=f"Invoice approved: {extracted.vendor}, ${extracted.amount:.2f}, all validations passed",
            requires_manual_review=False,
            approval_confidence=0.85,
        )

    async def _generator_critic_loop(
        self, extracted: ExtractedInvoice, validation: ValidationResult
    ) -> ApprovalReasoning:
        """
        Generator-Critic loop for high-confidence approval decisions.

        Phase 1: Generate initial recommendation
        Phase 2: Critique for flaws
        Phase 3: Revise based on critique

        Args:
            extracted: ExtractedInvoice
            validation: ValidationResult

        Returns:
            ApprovalReasoning with analysis
        """
        # This will be implemented with LLM reasoning in the next phase
        # Placeholder for the architecture
        self.log_execution("Running generator-critic loop (not yet implemented)")

        return ApprovalReasoning(
            analysis="Placeholder for LLM analysis",
            risk_factors=[],
            recommendation="approve",
            confidence=0.8,
        )
