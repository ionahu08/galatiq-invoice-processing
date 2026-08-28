#!/usr/bin/env python3
"""
Main entry point for the invoice processing system.

Usage:
    python main.py --invoice_path=data/invoices/invoice1.txt
    python main.py --batch --dir=data/invoices
"""

import argparse
import asyncio
import json
from pathlib import Path

from src.config import settings
from src.database import create_inventory_database
from src.orchestrator import InvoiceOrchestrator, LangGraphInvoiceOrchestrator
from src.utils.logging import get_logger, setup_logging


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated invoice processing system for Acme Corp"
    )

    parser.add_argument(
        "--invoice_path",
        type=str,
        help="Path to a single invoice file to process",
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="Process all invoices in a directory",
    )

    parser.add_argument(
        "--dir",
        type=str,
        default=str(settings.data_dir),
        help="Directory containing invoices (for batch processing)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    parser.add_argument(
        "--orchestrator",
        type=str,
        default="langgraph",
        choices=["langgraph", "custom"],
        help="Orchestrator implementation to use (default: langgraph)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(settings.logs_path, debug=args.debug)
    logger = get_logger("main")

    logger.info("Starting invoice processing system")

    # Initialize database
    logger.info(f"Initializing database: {settings.db_path}")
    create_inventory_database(settings.db_path)

    # Create orchestrator (LangGraph by default)
    if args.orchestrator == "langgraph":
        logger.info("Using LangGraph orchestrator")
        orchestrator = LangGraphInvoiceOrchestrator(
            db_path=settings.db_path,
            approval_threshold=settings.approval_threshold,
        )
    else:
        logger.info("Using custom orchestrator")
        orchestrator = InvoiceOrchestrator(
            db_path=settings.db_path,
            approval_threshold=settings.approval_threshold,
        )

    try:
        if args.batch:
            # Process all invoices in directory
            invoice_dir = Path(args.dir)
            if not invoice_dir.exists():
                logger.error(f"Directory not found: {invoice_dir}")
                return

            invoice_files = list(invoice_dir.glob("*"))
            if not invoice_files:
                logger.warning(f"No invoices found in {invoice_dir}")
                return

            logger.info(f"Processing {len(invoice_files)} invoices from {invoice_dir}")
            results = await orchestrator.process_batch(
                [str(f) for f in invoice_files]
            )

            # Print results
            print_batch_results(results)

        elif args.invoice_path:
            # Process single invoice
            invoice_path = Path(args.invoice_path)
            if not invoice_path.exists():
                logger.error(f"Invoice file not found: {invoice_path}")
                return

            logger.info(f"Processing single invoice: {invoice_path}")
            result = await orchestrator.process_invoice(str(invoice_path))

            # Print result
            print_result(result)

        else:
            # No input provided
            parser.print_help()

    except Exception as e:
        logger.error(f"Processing failed: {str(e)}", exc_info=True)
        raise


def print_result(result):
    """Print a single processing result."""
    print("\n" + "=" * 80)
    print("INVOICE PROCESSING RESULT")
    print("=" * 80)
    print(f"Invoice Number: {result.invoice_number}")
    print(f"Vendor: {result.vendor}")
    print(f"Amount: ${result.amount:.2f}")
    print(f"Overall Status: {result.overall_status.upper()}")
    print()

    if result.extraction:
        print("EXTRACTION:")
        print(f"  Vendor: {result.extraction.vendor}")
        print(f"  Items: {len(result.extraction.items)}")
        print(f"  Confidence: {result.extraction.extraction_confidence * 100:.1f}%")

    if result.validation:
        print("VALIDATION:")
        print(f"  Valid: {result.validation.is_valid}")
        print(f"  Issues: {result.validation.total_issues}")
        for issue in result.validation.issues:
            print(f"    - [{issue.severity}] {issue.issue_type}: {issue.message}")

    if result.approval:
        print("APPROVAL:")
        print(f"  Approved: {result.approval.is_approved}")
        print(f"  Confidence: {result.approval.approval_confidence * 100:.1f}%")
        print(f"  Manual Review: {result.approval.requires_manual_review}")
        print(f"  Reasoning: {result.approval.reasoning}")

    if result.payment:
        print("PAYMENT:")
        print(f"  Status: {result.payment.status}")
        print(f"  Message: {result.payment.message}")
        if result.payment.transaction_id:
            print(f"  Transaction ID: {result.payment.transaction_id}")

    if result.processing_errors:
        print("ERRORS:")
        for error in result.processing_errors:
            print(f"  - {error}")

    print("=" * 80 + "\n")


def print_batch_results(results):
    """Print batch processing results."""
    print("\n" + "=" * 80)
    print("BATCH PROCESSING RESULTS")
    print("=" * 80)

    # Summary
    successful = sum(1 for r in results if r.overall_status == "success")
    rejected = sum(1 for r in results if r.overall_status == "rejected")
    requires_review = sum(1 for r in results if r.overall_status == "requires_review")
    failed = sum(1 for r in results if r.overall_status == "failed")

    total = len(results)

    print(f"Total: {total}")
    print(f"  Successful: {successful} ({successful/total*100:.1f}%)")
    print(f"  Rejected: {rejected} ({rejected/total*100:.1f}%)")
    print(f"  Requires Review: {requires_review} ({requires_review/total*100:.1f}%)")
    print(f"  Failed: {failed} ({failed/total*100:.1f}%)")

    # Individual results
    print("\nDETAILS:")
    for result in results:
        status_symbol = {
            "success": "[✓]",
            "rejected": "[✗]",
            "requires_review": "[?]",
            "failed": "[!]",
        }.get(result.overall_status, "[?]")

        print(f"{status_symbol} {result.invoice_number}: {result.vendor} - ${result.amount:.2f}")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
