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
        elif file_path.suffix.lower() == ".xml":
            return await self._extract_from_xml(file_path)
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
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pdfplumber required for PDF extraction. Install with: pip install pdfplumber")

        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception as e:
            self.log_execution(f"PDF extraction error: {str(e)}", level="error")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")

        if not text.strip():
            raise ValueError("PDF appears to be empty or contains no extractable text")

        # Use regex patterns to extract fields from PDF text
        vendor = self._extract_field(text, r"(?:Vendor|Vndr|supplier)[:\s]+([^\n]+)", "Unknown Vendor")
        invoice_number = self._extract_field(text, r"(?:Invoice\s*(?:Number|#|ID)?|Inv\s*#?)[:\s]+([^\n]+)", "INV-UNKNOWN")
        amount_str = self._extract_field(text, r"(?:Total|Amount|Amt)[:\s]*\$?([\d,]+\.?\d*)", "0")
        due_date = self._extract_field(text, r"(?:Due\s*Date|Due\s*Dt)[:\s]+([^\n]+)", "")

        try:
            amount = float(amount_str.replace(",", "").strip())
        except ValueError:
            amount = 0.0

        items = self._extract_items(text)

        return ExtractedInvoice(
            vendor=vendor.strip(),
            invoice_number=invoice_number.strip(),
            amount=amount,
            due_date=due_date.strip(),
            items=items,
            extraction_confidence=0.75,
        )

    async def _extract_from_csv(self, file_path: Path) -> ExtractedInvoice:
        """Extract invoice data from a CSV file."""
        self.log_execution(f"Extracting from CSV: {file_path.name}")
        import csv

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                if not rows:
                    raise ValueError("CSV file is empty")

                # Get first row (header should be DictReader)
                first_row = rows[0]

                # Extract fields - support various column name variations
                vendor = None
                for key in first_row.keys():
                    if key.lower() in ['vendor', 'supplier', 'company', 'from']:
                        vendor = first_row[key]
                        break
                vendor = vendor or "Unknown Vendor"

                invoice_number = None
                for key in first_row.keys():
                    if key.lower() in ['invoice', 'invoice_number', 'invoice_id', 'inv', 'invoice#']:
                        invoice_number = first_row[key]
                        break
                invoice_number = invoice_number or "INV-UNKNOWN"

                amount = 0.0
                for key in first_row.keys():
                    if key.lower() in ['total', 'amount', 'amt', 'total_amount']:
                        try:
                            amount_str = first_row[key]
                            amount = float(str(amount_str).replace("$", "").replace(",", "").strip())
                        except (ValueError, AttributeError):
                            amount = 0.0
                        break

                due_date = None
                for key in first_row.keys():
                    if key.lower() in ['due_date', 'due', 'duedate', 'due_dt']:
                        due_date = first_row[key]
                        break
                due_date = due_date or ""

                # Extract items from CSV rows
                items = []
                for row in rows:
                    item_name = None
                    quantity = 0
                    unit_price = 0.0

                    for key in row.keys():
                        if key.lower() in ['item', 'item_name', 'product', 'description', 'product_name']:
                            item_name = row[key]
                        elif key.lower() in ['qty', 'quantity', 'qty_ordered', 'quantity_ordered']:
                            try:
                                quantity = int(row[key])
                            except (ValueError, TypeError):
                                quantity = 0
                        elif key.lower() in ['price', 'unit_price', 'unit_cost', 'cost']:
                            try:
                                unit_price = float(str(row[key]).replace("$", "").replace(",", ""))
                            except (ValueError, TypeError):
                                unit_price = 0.0

                    if item_name and quantity != 0:
                        items.append(LineItem(
                            item_name=item_name.strip(),
                            quantity=quantity,
                            unit_price=unit_price
                        ))

                return ExtractedInvoice(
                    vendor=vendor.strip(),
                    invoice_number=invoice_number.strip(),
                    amount=amount,
                    due_date=due_date.strip(),
                    items=items,
                    extraction_confidence=0.80,
                )

        except Exception as e:
            self.log_execution(f"CSV extraction error: {str(e)}", level="error")
            raise ValueError(f"Failed to parse CSV file: {str(e)}")

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

    async def _extract_from_xml(self, file_path: Path) -> ExtractedInvoice:
        """Extract invoice data from an XML file."""
        self.log_execution(f"Extracting from XML: {file_path.name}")
        import xml.etree.ElementTree as ET

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML file: {str(e)}")

        # Helper to find element text (case-insensitive tag search)
        def find_text(element, tag_names, default=""):
            """Find element by any of the given tag names."""
            for tag in tag_names:
                # Direct child search
                for child in element:
                    if child.tag.lower() == tag.lower():
                        return child.text or default
            return default

        # Extract vendor
        vendor = find_text(root, ['vendor', 'supplier', 'company', 'from'], "Unknown Vendor")

        # Extract invoice number
        invoice_number = find_text(root, ['invoice', 'invoice_number', 'invoice_id', 'inv'], "INV-UNKNOWN")

        # Extract amount
        amount_str = find_text(root, ['total', 'amount', 'amt', 'total_amount'], "0")
        try:
            amount = float(amount_str.replace("$", "").replace(",", "").strip())
        except ValueError:
            amount = 0.0

        # Extract due date
        due_date = find_text(root, ['due_date', 'due', 'duedate', 'due_dt'], "")

        # Extract items
        items = []
        items_element = None
        for child in root:
            if child.tag.lower() in ['items', 'line_items', 'lineitems', 'products']:
                items_element = child
                break

        if items_element is not None:
            for item_elem in items_element:
                item_name = find_text(item_elem, ['item', 'item_name', 'product', 'product_name', 'name'], "")
                quantity_str = find_text(item_elem, ['qty', 'quantity', 'quantity_ordered', 'qty_ordered'], "0")
                unit_price_str = find_text(item_elem, ['price', 'unit_price', 'unit_cost', 'cost'], "0")

                try:
                    quantity = int(quantity_str)
                    unit_price = float(unit_price_str.replace("$", "").replace(",", ""))
                except (ValueError, AttributeError):
                    continue

                if item_name and quantity != 0:
                    items.append(LineItem(
                        item_name=item_name.strip(),
                        quantity=quantity,
                        unit_price=unit_price
                    ))

        return ExtractedInvoice(
            vendor=vendor.strip(),
            invoice_number=invoice_number.strip(),
            amount=amount,
            due_date=due_date.strip(),
            items=items,
            extraction_confidence=0.78,
        )
