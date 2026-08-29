#!/usr/bin/env python3
"""
Demo script showing the generator-critic loop in action.

Run this to see how Claude analyzes invoices through the 3-phase loop.

Usage:
    python demo_generator_critic.py
"""

import asyncio
from src.models import ExtractedInvoice, LineItem, ValidationResult
from src.agents.approval import ApprovalAgent


async def demo_simple_invoice():
    """Demo: Simple approval case."""
    print("\n" + "="*80)
    print("DEMO 1: Simple Approval (Low Value, No Issues)")
    print("="*80)

    # Create sample invoice
    invoice = ExtractedInvoice(
        vendor="TechSupplies Inc",
        invoice_number="INV-1001",
        amount=5000.00,
        due_date="2026-09-15",
        items=[
            LineItem(item_name="WidgetA", quantity=10, unit_price=250.00),
            LineItem(item_name="WidgetB", quantity=5, unit_price=100.00),
        ],
    )

    # Validation passed
    validation = ValidationResult(
        invoice_number="INV-1001",
        is_valid=True,
        issues=[],
    )

    # Run approval with LLM
    agent = ApprovalAgent(enable_llm=True)
    result = await agent.execute(invoice, validation)

    print(f"\nInvoice: {invoice.vendor} - ${invoice.amount:.2f}")
    print(f"Approved: {result.is_approved}")
    print(f"Confidence: {result.approval_confidence:.2f}")
    print(f"Reasoning: {result.reasoning}")


async def demo_high_value_invoice():
    """Demo: High-value invoice (should flag for manual review)."""
    print("\n" + "="*80)
    print("DEMO 2: High-Value Invoice (>$10K)")
    print("="*80)

    invoice = ExtractedInvoice(
        vendor="Atlas Industrial Supply",
        invoice_number="INV-1013",
        amount=22562.80,
        due_date="2026-03-24",
        items=[
            LineItem(item_name="GadgetX", quantity=15, unit_price=1500.00),
        ],
    )

    validation = ValidationResult(
        invoice_number="INV-1013",
        is_valid=True,
        issues=[],
    )

    agent = ApprovalAgent(enable_llm=True)
    result = await agent.execute(invoice, validation)

    print(f"\nInvoice: {invoice.vendor} - ${invoice.amount:.2f}")
    print(f"Approved: {result.is_approved}")
    print(f"Requires Manual Review: {result.requires_manual_review}")
    print(f"Confidence: {result.approval_confidence:.2f}")
    print(f"Reasoning: {result.reasoning}")


async def demo_validation_failed():
    """Demo: Validation failed (should auto-reject)."""
    print("\n" + "="*80)
    print("DEMO 3: Validation Failed (Out of Stock)")
    print("="*80)

    invoice = ExtractedInvoice(
        vendor="Unknown Vendor",
        invoice_number="INV-UNKNOWN",
        amount=5000.00,
        due_date="2026-09-15",
        items=[
            LineItem(item_name="FAKEITEM", quantity=100),
        ],
    )

    from src.models import ValidationIssue
    validation = ValidationResult(
        invoice_number="INV-UNKNOWN",
        is_valid=False,
        issues=[
            ValidationIssue(
                issue_type="unknown_item",
                item_name="FAKEITEM",
                message="Item not found in inventory",
                severity="error",
            )
        ],
    )

    agent = ApprovalAgent(enable_llm=True)
    result = await agent.execute(invoice, validation)

    print(f"\nInvoice: {invoice.vendor} - ${invoice.amount:.2f}")
    print(f"Approved: {result.is_approved}")
    print(f"Requires Manual Review: {result.requires_manual_review}")
    print(f"Confidence: {result.approval_confidence:.2f}")
    print(f"Reasoning: {result.reasoning}")


async def main():
    """Run all demos."""
    print("\n" + "="*80)
    print("GENERATOR-CRITIC LOOP DEMO")
    print("="*80)
    print("\nThis demo shows how the ApprovalAgent uses Claude's generator-critic")
    print("loop to make intelligent approval decisions.")
    print("\nThe loop has 3 phases:")
    print("  1. Generate: Claude proposes an initial recommendation")
    print("  2. Critique: Claude reviews its own recommendation for flaws")
    print("  3. Revise: Claude refines based on critique (if needed)")
    print("\nWatch the logs to see each phase in action.")

    await demo_simple_invoice()
    await demo_high_value_invoice()
    await demo_validation_failed()

    print("\n" + "="*80)
    print("DEMO COMPLETE")
    print("="*80)
    print("\nTo use real Claude API:")
    print("  1. Add ANTHROPIC_API_KEY to .env")
    print("  2. Run: python demo_generator_critic.py")
    print("\nTo process invoices:")
    print("  1. Single: python main.py --invoice_path=data/invoices/invoice_1001.txt")
    print("  2. Batch:  python main.py --batch --dir=data/invoices")
    print()


if __name__ == "__main__":
    asyncio.run(main())
