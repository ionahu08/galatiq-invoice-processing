"""Data models and schemas for invoice processing."""

from typing import Optional
from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """Individual line item on an invoice."""

    item_name: str = Field(..., description="Name or ID of the item")
    quantity: int = Field(..., description="Quantity ordered")
    unit_price: Optional[float] = Field(None, description="Price per unit")
    total_price: Optional[float] = Field(None, description="Total price for this line")


class ExtractedInvoice(BaseModel):
    """Invoice data extracted by the Ingestion Agent."""

    vendor: str = Field(..., description="Vendor/supplier name")
    invoice_number: str = Field(..., description="Invoice ID or number")
    amount: float = Field(..., description="Total invoice amount in USD")
    due_date: str = Field(..., description="Due date (YYYY-MM-DD or natural language)")
    items: list[LineItem] = Field(default_factory=list, description="Line items")
    description: Optional[str] = Field(None, description="Invoice description or notes")
    extraction_confidence: float = Field(
        default=0.9, description="Confidence score of extraction (0-1)"
    )


class ValidationIssue(BaseModel):
    """A single validation issue found during Validation Agent."""

    issue_type: str = Field(
        ...,
        description="Type: out_of_stock, quantity_mismatch, unknown_item, invalid_data",
    )
    item_name: str = Field(..., description="Item affected")
    message: str = Field(..., description="Human-readable description")
    severity: str = Field(default="warning", description="warning or error")


class ValidationResult(BaseModel):
    """Output from the Validation Agent."""

    invoice_number: str
    is_valid: bool = Field(..., description="Pass/fail validation")
    issues: list[ValidationIssue] = Field(
        default_factory=list, description="List of validation issues found"
    )
    stock_check_complete: bool = Field(
        default=False, description="Whether stock was checked"
    )
    total_issues: int = Field(default=0, description="Count of issues")


class ApprovalReasoning(BaseModel):
    """LLM reasoning during approval decision."""

    analysis: str = Field(..., description="LLM's analysis of the invoice")
    risk_factors: list[str] = Field(
        default_factory=list, description="Identified risk factors"
    )
    recommendation: str = Field(..., description="Recommendation: approve or reject")
    confidence: float = Field(
        default=0.8, description="Confidence in this decision (0-1)"
    )


class ApprovalResult(BaseModel):
    """Output from the Approval Agent."""

    invoice_number: str
    is_approved: bool = Field(..., description="Approval decision")
    reasoning: str = Field(..., description="Why approved or rejected")
    llm_analysis: Optional[ApprovalReasoning] = Field(
        None, description="Detailed LLM reasoning"
    )
    requires_manual_review: bool = Field(
        default=False, description="Flag for human review"
    )
    approval_confidence: float = Field(
        default=0.8, description="Confidence in decision (0-1)"
    )


class PaymentResult(BaseModel):
    """Output from the Payment Agent."""

    invoice_number: str
    vendor: str
    amount: float
    status: str = Field(
        ..., description="success, failed, rejected, or requires_review"
    )
    transaction_id: Optional[str] = Field(None, description="Payment transaction ID")
    message: str = Field(..., description="Status message")


class ProcessingResult(BaseModel):
    """Final result from the entire pipeline."""

    invoice_number: str
    vendor: str
    amount: float
    extraction: Optional[ExtractedInvoice] = None
    validation: Optional[ValidationResult] = None
    approval: Optional[ApprovalResult] = None
    payment: Optional[PaymentResult] = None
    overall_status: str = Field(
        ..., description="success, failed, requires_review, rejected"
    )
    processing_errors: list[str] = Field(
        default_factory=list, description="Any errors encountered"
    )
