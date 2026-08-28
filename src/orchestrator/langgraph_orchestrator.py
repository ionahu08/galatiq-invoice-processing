"""LangGraph-based orchestrator for invoice processing workflow."""

import logging
from pathlib import Path
from typing import Optional

from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from src.agents import ApprovalAgent, IngestionAgent, PaymentAgent, ValidationAgent
from src.models import ApprovalResult, ExtractedInvoice, PaymentResult, ProcessingResult, ValidationResult


class InvoiceProcessingState(BaseModel):
    """State shared across all nodes in the LangGraph workflow."""

    invoice_path: str = Field(..., description="Path to invoice file")
    invoice_number: str = Field(default="", description="Invoice ID")
    vendor: str = Field(default="", description="Vendor name")
    amount: float = Field(default=0.0, description="Invoice amount")

    # Stage outputs
    extraction: Optional[ExtractedInvoice] = Field(None, description="Ingestion result")
    validation: Optional[ValidationResult] = Field(None, description="Validation result")
    approval: Optional[ApprovalResult] = Field(None, description="Approval result")
    payment: Optional[PaymentResult] = Field(None, description="Payment result")

    # Metadata
    processing_errors: list[str] = Field(default_factory=list, description="Error log")
    overall_status: str = Field(default="in_progress", description="Current status")


class LangGraphInvoiceOrchestrator:
    """
    LangGraph-based orchestrator for invoice processing.

    Workflow:
    1. Ingestion Node: Extract data from invoice file
    2. Validation Node: Check inventory database
    3. Approval Node: Make approval decision with LLM reasoning
    4. Payment Node: Process payment or reject

    Graph Structure:
    START → Ingestion → Validation → Approval → Payment → END

    Conditional edges:
    - If extraction fails → END (error)
    - If validation fails → Approval (rejected)
    - If approval requires review → END (review)
    - Payment succeeds/fails → END
    """

    def __init__(
        self,
        db_path: Path,
        approval_threshold: float = 10000.0,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize LangGraph orchestrator."""
        self.logger = logger or logging.getLogger("langgraph_orchestrator")
        self.db_path = db_path

        # Initialize agents
        self.ingestion_agent = IngestionAgent()
        self.validation_agent = ValidationAgent(db_path=db_path)
        self.approval_agent = ApprovalAgent(
            approval_threshold=approval_threshold, enable_llm=True
        )
        self.payment_agent = PaymentAgent()

        # Build LangGraph
        self.graph = self._build_graph()
        self.logger.info("LangGraph orchestrator initialized")

    def _build_graph(self):
        """Build the LangGraph workflow."""
        workflow = StateGraph(InvoiceProcessingState)

        # Define nodes
        workflow.add_node("ingestion", self._node_ingestion)
        workflow.add_node("validation", self._node_validation)
        workflow.add_node("approval", self._node_approval)
        workflow.add_node("payment", self._node_payment)
        workflow.add_node("end", self._node_end)

        # Define edges
        workflow.add_edge("ingestion", "validation")
        workflow.add_conditional_edges(
            "validation",
            self._route_validation,
            {"approval": "approval", "end": "end"},
        )
        workflow.add_conditional_edges(
            "approval",
            self._route_approval,
            {"payment": "payment", "end": "end"},
        )
        workflow.add_edge("payment", "end")

        # Set entry point
        workflow.set_entry_point("ingestion")

        return workflow.compile()

    # Node Implementations
    async def _node_ingestion(self, state: InvoiceProcessingState):
        """Ingestion node: Extract invoice data."""
        self.logger.info(f"[Ingestion] Processing {state.invoice_path}")

        try:
            extraction = await self.ingestion_agent.run(state.invoice_path)
            state.extraction = extraction
            state.invoice_number = extraction.invoice_number
            state.vendor = extraction.vendor
            state.amount = extraction.amount
            state.overall_status = "extracted"
            self.logger.info(f"  → Extracted: {extraction.vendor}, ${extraction.amount:.2f}")

        except Exception as e:
            state.processing_errors.append(f"Ingestion failed: {str(e)}")
            state.overall_status = "failed"
            self.logger.error(f"  → Error: {str(e)}")

        return state

    async def _node_validation(self, state: InvoiceProcessingState):
        """Validation node: Check inventory."""
        if state.overall_status == "failed":
            return state

        self.logger.info(f"[Validation] Checking inventory for {state.invoice_number}")

        try:
            validation = await self.validation_agent.run(state.extraction)
            state.validation = validation
            state.overall_status = "validated"
            self.logger.info(f"  → Valid: {validation.is_valid}, Issues: {validation.total_issues}")

        except Exception as e:
            state.processing_errors.append(f"Validation failed: {str(e)}")
            state.overall_status = "failed"
            self.logger.error(f"  → Error: {str(e)}")

        return state

    async def _node_approval(self, state: InvoiceProcessingState):
        """Approval node: Make approval decision with LLM."""
        if state.overall_status == "failed":
            return state

        self.logger.info(f"[Approval] Making decision for {state.invoice_number}")

        try:
            approval = await self.approval_agent.execute(state.extraction, state.validation)
            state.approval = approval
            state.overall_status = "approved" if approval.is_approved else "rejected"
            self.logger.info(f"  → Decision: {'APPROVED' if approval.is_approved else 'REJECTED'}")
            self.logger.info(f"  → Confidence: {approval.approval_confidence * 100:.1f}%")
            if approval.llm_analysis:
                self.logger.info(f"  → LLM Reasoning: {approval.llm_analysis.analysis[:100]}...")

        except Exception as e:
            state.processing_errors.append(f"Approval failed: {str(e)}")
            state.overall_status = "failed"
            self.logger.error(f"  → Error: {str(e)}")

        return state

    async def _node_payment(self, state: InvoiceProcessingState):
        """Payment node: Process payment."""
        if state.overall_status in ["failed", "rejected"]:
            return state

        self.logger.info(f"[Payment] Processing payment for {state.invoice_number}")

        try:
            payment = await self.payment_agent.execute(state.extraction, state.approval)
            state.payment = payment
            state.overall_status = payment.status
            self.logger.info(f"  → Payment Status: {payment.status}")

        except Exception as e:
            state.processing_errors.append(f"Payment failed: {str(e)}")
            state.overall_status = "failed"
            self.logger.error(f"  → Error: {str(e)}")

        return state

    async def _node_end(self, state: InvoiceProcessingState):
        """End node: Finalize processing."""
        self.logger.info(f"[End] Processing complete: {state.overall_status.upper()}")
        return state

    # Routing Logic
    def _route_validation(self, state: InvoiceProcessingState) -> str:
        """Route based on validation result."""
        if state.overall_status == "failed":
            return "end"
        return "approval"

    def _route_approval(self, state: InvoiceProcessingState) -> str:
        """Route based on approval result."""
        if state.overall_status == "failed":
            return "end"
        if state.approval.requires_manual_review:
            state.overall_status = "requires_review"
            return "end"
        return "payment"

    # Public API
    async def process_invoice(self, invoice_path: str) -> ProcessingResult:
        """
        Process a single invoice through the workflow.

        Args:
            invoice_path: Path to invoice file

        Returns:
            ProcessingResult with full pipeline output
        """
        self.logger.info(f"Starting invoice processing: {invoice_path}")

        # Initialize state
        state = InvoiceProcessingState(invoice_path=invoice_path)

        # Run the graph
        try:
            # Note: LangGraph's invoke is synchronous
            # We'll need to handle async properly in the node implementations
            output_state = await self._run_graph(state)
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}", exc_info=True)
            output_state = state
            output_state.processing_errors.append(str(e))
            output_state.overall_status = "failed"

        # Convert state to ProcessingResult
        return self._state_to_result(output_state)

    async def _run_graph(self, state: InvoiceProcessingState) -> InvoiceProcessingState:
        """Run the compiled LangGraph."""
        # For now, run nodes sequentially (proper async support in future)
        state = await self._node_ingestion(state)
        if state.overall_status != "failed":
            state = await self._node_validation(state)
        if state.overall_status not in ["failed", "requires_review"]:
            state = await self._node_approval(state)
        if state.overall_status == "approved":
            state = await self._node_payment(state)
        state = await self._node_end(state)
        return state

    async def process_batch(self, invoice_paths: list[str]) -> list[ProcessingResult]:
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

    def _state_to_result(self, state: InvoiceProcessingState) -> ProcessingResult:
        """Convert workflow state to ProcessingResult."""
        return ProcessingResult(
            invoice_number=state.invoice_number or "UNKNOWN",
            vendor=state.vendor or "UNKNOWN",
            amount=state.amount,
            extraction=state.extraction,
            validation=state.validation,
            approval=state.approval,
            payment=state.payment,
            overall_status=state.overall_status,
            processing_errors=state.processing_errors,
        )
