"""Approval Agent - Makes approval decisions with LLM reasoning and generator-critic loop."""

from src.agents.base import BaseAgent
from src.llm import LLMClient
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
    - Use generator-critic loop for LLM confidence
    - Flag high-risk invoices for manual review
    - Return ApprovalResult with reasoning

    Generator-Critic Loop:
    1. Generate: LLM proposes recommendation + analysis
    2. Critique: LLM identifies flaws in the recommendation
    3. Revise: LLM refines based on critique
    """

    def __init__(
        self,
        approval_threshold: float = 10000.0,
        enable_llm: bool = True,
        name: str = "ApprovalAgent",
    ):
        """
        Initialize the approval agent.

        Args:
            approval_threshold: Amount above which invoices need extra scrutiny
            enable_llm: Enable LLM reasoning (vs. rule-based only)
        """
        super().__init__(name)
        self.approval_threshold = approval_threshold
        self.enable_llm = enable_llm
        self.llm = LLMClient() if enable_llm else None

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

        # Auto-reject if validation failed
        if not validation.is_valid:
            self.log_execution("Auto-rejecting due to validation failures")
            return ApprovalResult(
                invoice_number=extracted.invoice_number,
                is_approved=False,
                reasoning=f"Invoice failed validation: {validation.total_issues} issues found",
                requires_manual_review=True,
                approval_confidence=0.95,
            )

        # Auto-reject if amount exceeds threshold (requires manual review)
        if extracted.amount > self.approval_threshold:
            self.log_execution(f"Amount exceeds threshold: ${extracted.amount:.2f}")
            return ApprovalResult(
                invoice_number=extracted.invoice_number,
                is_approved=False,
                reasoning=f"Invoice amount (${extracted.amount:.2f}) exceeds approval threshold (${self.approval_threshold:.2f}). Requires manual review.",
                requires_manual_review=True,
                approval_confidence=0.90,
            )

        # Use LLM reasoning for borderline cases if enabled
        if self.enable_llm:
            self.log_execution("Running generator-critic loop for confidence")
            reasoning = await self._generator_critic_loop(extracted, validation)

            is_approved = reasoning.recommendation == "approve"
            return ApprovalResult(
                invoice_number=extracted.invoice_number,
                is_approved=is_approved,
                reasoning=reasoning.analysis,
                llm_analysis=reasoning,
                requires_manual_review=reasoning.recommendation == "require_manual_review",
                approval_confidence=reasoning.confidence,
            )

        # Rule-based approval for normal invoices
        self.log_execution("Auto-approving: passes all rules")
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
        Generator-Critic loop using LLM for approval confidence.

        Phase 1 (Generate): LLM proposes recommendation + analysis
        Phase 2 (Critique): LLM critiques the recommendation
        Phase 3 (Revise): LLM revises based on critique

        Args:
            extracted: ExtractedInvoice
            validation: ValidationResult

        Returns:
            ApprovalReasoning with analysis and confidence
        """
        if not self.llm:
            return ApprovalReasoning(
                analysis="LLM disabled",
                risk_factors=[],
                recommendation="require_manual_review",
                confidence=0.5,
            )

        # Prepare input data
        items_list = [f"{item.item_name} x{item.quantity}" for item in extracted.items]
        issues_list = [issue.message for issue in validation.issues]

        # Phase 1: Generate initial recommendation
        self.log_execution("  [Phase 1] Generate recommendation")
        reasoning = await self.llm.reason_about_invoice(
            vendor=extracted.vendor,
            amount=extracted.amount,
            items=items_list,
            validation_issues=issues_list,
        )

        # Phase 2: Critique the recommendation
        self.log_execution("  [Phase 2] Critique recommendation")
        critique = await self.llm.critique_approval(reasoning)

        # Phase 3: Revise based on critique if flaws found
        if critique.get("has_flaws"):
            self.log_execution("  [Phase 3] Revise based on critique")
            reasoning = await self.llm.revise_approval(reasoning, critique)
        else:
            self.log_execution("  [Phase 3] No revisions needed")

        return ApprovalReasoning(
            analysis=reasoning.get("analysis", ""),
            risk_factors=reasoning.get("risk_factors", []),
            recommendation=reasoning.get("recommendation", "require_manual_review"),
            confidence=reasoning.get("confidence", 0.5),
        )
