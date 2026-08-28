"""Ingestion Agent - Extracts structured data from invoice documents."""

from pathlib import Path
from typing import Any, Optional

from src.agents.base import BaseAgent
from src.models import ExtractedInvoice


class IngestionAgent(BaseAgent):
    """
    Extracts structured invoice data from various formats (PDF, TXT, etc).

    Responsibilities:
    - Read invoice files (PDF, text, etc.)
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
            invoice_path: Path to invoice file (PDF, TXT, etc.)

        Returns:
            ExtractedInvoice with structured data
        """
        file_path = Path(invoice_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Invoice file not found: {invoice_path}")

        self.log_execution(f"Processing file: {file_path.name}")

        # Dispatch to appropriate parser based on file type
        if file_path.suffix.lower() == ".pdf":
            return await self._extract_from_pdf(file_path)
        elif file_path.suffix.lower() in [".txt", ".text"]:
            return await self._extract_from_text(file_path)
        elif file_path.suffix.lower() in [".json"]:
            return await self._extract_from_json(file_path)
        elif file_path.suffix.lower() in [".csv"]:
            return await self._extract_from_csv(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

    async def _extract_from_pdf(self, file_path: Path) -> ExtractedInvoice:
        """Extract invoice data from a PDF file."""
        # Placeholder: Will implement with pdfplumber
        self.log_execution(f"Extracting from PDF: {file_path.name}")
        raise NotImplementedError("PDF extraction coming in next phase")

    async def _extract_from_text(self, file_path: Path) -> ExtractedInvoice:
        """Extract invoice data from a text file."""
        # Placeholder: Will implement with LLM parsing
        self.log_execution(f"Extracting from TXT: {file_path.name}")
        raise NotImplementedError("Text extraction coming in next phase")

    async def _extract_from_json(self, file_path: Path) -> ExtractedInvoice:
        """Extract invoice data from a JSON file."""
        # Placeholder: Will implement with JSON parsing
        self.log_execution(f"Extracting from JSON: {file_path.name}")
        raise NotImplementedError("JSON extraction coming in next phase")

    async def _extract_from_csv(self, file_path: Path) -> ExtractedInvoice:
        """Extract invoice data from a CSV file."""
        # Placeholder: Will implement with CSV parsing
        self.log_execution(f"Extracting from CSV: {file_path.name}")
        raise NotImplementedError("CSV extraction coming in next phase")
