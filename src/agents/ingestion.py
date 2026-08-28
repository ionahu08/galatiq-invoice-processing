"""Ingestion Agent - Extracts structured data from invoice documents."""

import json
import re
from pathlib import Path
from typing import Optional

from src.agents.base import BaseAgent
from src.models import ExtractedInvoice, LineItem


class IngestionAgent(BaseAgent):
    """
    Extracts structured invoice data from various formats (PDF, TXT, JSON).

    Responsibilities:
    - Read invoice files (TXT, JSON, etc.)
    - Extract: Vendor, Amount, Items, Due Date
    - Handle missing/malformed data gracefully
    - Return structured ExtractedInvoice output
    """

    def __init__(self, name: str = "IngestionAgent"):
        """Initialize the ingestion agent."""
        super().__init__(name)

    async def execute(self, invoice_path: str) -> ExtractedInvoice:
        """
        Execute ingestion from an invoice file.

        Args:
            invoice_path: Path to invoice file (TXT, JSON, etc.)

        Returns:
            ExtractedInvoice with structured data
        """
        file_path = Path(invoice_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Invoice file not found: {invoice_path}")

        self.log_execution(f"Processing file: {file_path.name}")

        # Dispatch to appropriate parser based on file type
        if file_path.suffix.lower() in [".txt", ".text"]:
            return await self._extract_from_text(file_path)
        elif file_path.suffix.lower() in [".json"]:
            return await self._extract_from_json(file_path)
        elif file_path.suffix.lower() == ".pdf":
            return await self._extract_from_pdf(file_path)
        elif file_path.suffix.lower() in [".csv"]:
            return await self._extract_from_csv(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

    async def _extract_from_text(self, file_path: Path) -> ExtractedInvoice:
        """Extract invoice data from a text file using regex."""
        self.log_execution(f"Parsing TXT: {file_path.name}")

        text = file_path.read_text()

        # Extract fields using regex patterns
        vendor = self._extract_field(text, r"(?:Vendor|Vndr|supplier)[:\s]+([^\n]+)", "Unknown Vendor")
        invoice_number = self._extract_field(
            text,
            r"(?:Invoice\s*(?:Number|#|ID)?|Inv\s*#?)[:\s]+([^\n]+)",
            "INV-UNKNOWN",
        )
        amount_str = self._extract_field(text, r"(?:Total|Amount|Amt)[:\s]*\$?([\d,]+\.?\d*)", "0")
        due_date = self._extract_field(text, r"(?:Due\s*Date|Due\s*Dt)[:\s]+([^\n]+)", "")

        # Parse amount
        try:
            amount = float(amount_str.replace(",", "").strip())
        except ValueError:
            amount = 0.0

        # Extract items (look for patterns like "ItemName qty: N" or "ItemName qty N")
        items = self._extract_items(text)

        return ExtractedInvoice(
            vendor=vendor.strip(),
            invoice_number=invoice_number.strip(),
            amount=amount,
            due_date=due_date.strip(),
            items=items,
            extraction_confidence=0.8,
        )

    async def _extract_from_json(self, file_path: Path) -> ExtractedInvoice:
        """Extract invoice data from a JSON file."""
        self.log_execution(f"Parsing JSON: {file_path.name}")

        data = json.loads(file_path.read_text())

        # Extract fields from JSON structure
        vendor = data.get("vendor", {})
        if isinstance(vendor, dict):
            vendor_name = vendor.get("name", "Unknown Vendor")
        else:
            vendor_name = str(vendor)

        invoice_number = data.get("invoice_number", "INV-UNKNOWN")
        amount = float(data.get("total", 0.0))
        due_date = data.get("due_date", "")

        # Extract items
        items = []
        for line_item in data.get("line_items", []):
            items.append(
                LineItem(
                    item_name=line_item.get("item", ""),
                    quantity=int(line_item.get("quantity", 0)),
                    unit_price=float(line_item.get("unit_price", 0.0)),
                )
            )

        return ExtractedInvoice(
            vendor=vendor_name,
            invoice_number=invoice_number,
            amount=amount,
            due_date=due_date,
            items=items,
            extraction_confidence=0.95,
        )

    async def _extract_from_pdf(self, file_path: Path) -> ExtractedInvoice:
        """Extract invoice data from a PDF file."""
        self.log_execution(f"Extracting from PDF: {file_path.name}")
        raise NotImplementedError("PDF extraction requires pdfplumber integration")

    async def _extract_from_csv(self, file_path: Path) -> ExtractedInvoice:
        """Extract invoice data from a CSV file."""
        self.log_execution(f"Extracting from CSV: {file_path.name}")
        raise NotImplementedError("CSV extraction requires CSV parsing")

    # Helper methods
    def _extract_field(self, text: str, pattern: str, default: str) -> str:
        """Extract a field using regex pattern."""
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        return default

    def _extract_items(self, text: str) -> list[LineItem]:
        """Extract line items from text."""
        items = []

        # Pattern: ItemName qty: N or ItemName qty N @ $price
        pattern = r"(\w+)\s+(?:qty|quantity)[:\s]+(-?\d+)\s*(?:@|\$)?[\s$]*(\d*\.?\d*)?(?:[eE][aA])?"
        matches = re.findall(pattern, text, re.IGNORECASE)

        for item_name, qty_str, price_str in matches:
            try:
                qty = int(qty_str)
                price = float(price_str) if price_str else 0.0
                items.append(
                    LineItem(item_name=item_name.strip(), quantity=qty, unit_price=price)
                )
            except ValueError:
                continue

        return items
