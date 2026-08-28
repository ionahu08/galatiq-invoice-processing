"""Orchestrator - Coordinates the multi-agent workflow."""

import logging
from pathlib import Path
from typing import Optional

from src.agents import ApprovalAgent, IngestionAgent, PaymentAgent, ValidationAgent
from src.models import ProcessingResult


class InvoiceOrchestrator:
    """
    Orchestrates the invoice processing workflow.

    Workflow:
    1. Ingestion Agent: Extract structured data from invoice file
    2. Validation Agent: Verify data against inventory database
    3. Approval Agent: Make approval decision
    4. Payment Agent: Process payment if approved

    This follows the Orchestrator-Workers pattern (Phase 3.1 of multi-agent study):
    - Star topology: All agents report to Orchestrator
    - Centralized control: Orchestrator decides stage transitions
    - Code-driven planning: Fixed 4-stage workflow
    """

    def __init__(
        self,
        db_path: Path,
        approval_threshold: float = 10000.0,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            db_path: Path to inventory database
            approval_threshold: Amount above which invoices need manual review
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger("orchestrator")
        self.db_path = db_path

        # Initialize agents
        self.ingestion_agent = IngestionAgent()
        self.validation_agent = ValidationAgent(db_path=db_path)
        self.approval_agent = ApprovalAgent(approval_threshold=approval_threshold)
        self.payment_agent = PaymentAgent()

        self.logger.info("Orchestrator initialized with 4 agents")

    async def process_invoice(self, invoice_path: str) -> ProcessingResult:
        """
        Process a single invoice through the entire workflow.

        Args:
            invoice_path: Path to invoice file

        Returns:
            ProcessingResult with full processing output
        """
        self.logger.info(f"Starting invoice processing: {invoice_path}")

        errors = []

        try:
            # Stage 1: Ingestion
            self.logger.info("[1/4] Ingestion: Extracting invoice data")
            extracted = await self.ingestion_agent.run(invoice_path)
            self.logger.info(f"  -> Extracted: {extracted.vendor}, ${extracted.amount}")

            # Stage 2: Validation
            self.logger.info("[2/4] Validation: Checking against inventory")
            validation = await self.validation_agent.run(extracted)
            self.logger.info(
                f"  -> Valid: {validation.is_valid}, Issues: {validation.total_issues}"
            )

            # Stage 3: Approval
            self.logger.info("[3/4] Approval: Making approval decision")
            approval = await self.approval_agent.run(extracted, validation)
            self.logger.info(f"  -> Decision: {'APPROVED' if approval.is_approved else 'REJECTED'}")

            # Stage 4: Payment
            self.logger.info("[4/4] Payment: Processing payment")
            payment = None
            if approval.is_approved or approval.requires_manual_review:
                payment = await self.payment_agent.run(extracted, approval)
                self.logger.info(f"  -> Status: {payment.status}")

            # Determine overall status
            if payment and payment.status == "success":
                overall_status = "success"
            elif approval.requires_manual_review:
                overall_status = "requires_review"
            elif not approval.is_approved:
                overall_status = "rejected"
            else:
                overall_status = "failed"

            result = ProcessingResult(
                invoice_number=extracted.invoice_number,
                vendor=extracted.vendor,
                amount=extracted.amount,
                extraction=extracted,
                validation=validation,
                approval=approval,
                payment=payment,
                overall_status=overall_status,
                processing_errors=errors,
            )

            self.logger.info(f"Processing complete: {overall_status.upper()}")
            return result

        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}", exc_info=True)
            errors.append(str(e))

            # Return partial result with error
            return ProcessingResult(
                invoice_number="UNKNOWN",
                vendor="UNKNOWN",
                amount=0.0,
                extraction=None,  # type: ignore
                validation=None,  # type: ignore
                approval=None,  # type: ignore
                payment=None,
                overall_status="failed",
                processing_errors=errors,
            )

    async def process_batch(
        self, invoice_paths: list[str]
    ) -> list[ProcessingResult]:
        """
        Process multiple invoices.

        Args:
            invoice_paths: List of invoice file paths

        Returns:
            List of ProcessingResults
        """
        self.logger.info(f"Starting batch processing: {len(invoice_paths)} invoices")

        results = []
        for i, path in enumerate(invoice_paths, 1):
            self.logger.info(f"Processing {i}/{len(invoice_paths)}")
            result = await self.process_invoice(path)
            results.append(result)

        # Summary
        successful = sum(1 for r in results if r.overall_status == "success")
        rejected = sum(1 for r in results if r.overall_status == "rejected")
        requires_review = sum(1 for r in results if r.overall_status == "requires_review")
        failed = sum(1 for r in results if r.overall_status == "failed")

        self.logger.info(
            f"Batch complete: {successful} success, {rejected} rejected, "
            f"{requires_review} review, {failed} failed"
        )

        return results
