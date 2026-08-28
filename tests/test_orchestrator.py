"""Tests for the invoice orchestrator."""

import pytest
from pathlib import Path

from src.database import create_inventory_database
from src.orchestrator import LangGraphInvoiceOrchestrator


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_inventory.db"
    create_inventory_database(db_path)
    return db_path


@pytest.fixture
def orchestrator(temp_db):
    """Create an orchestrator with a temporary database."""
    return LangGraphInvoiceOrchestrator(
        db_path=temp_db,
        approval_threshold=10000.0,
    )


@pytest.mark.asyncio
async def test_orchestrator_initialization(orchestrator):
    """Test that the orchestrator initializes with all agents."""
    assert orchestrator.ingestion_agent is not None
    assert orchestrator.validation_agent is not None
    assert orchestrator.approval_agent is not None
    assert orchestrator.payment_agent is not None


@pytest.mark.asyncio
async def test_process_invoice_not_found(orchestrator):
    """Test processing a non-existent invoice file."""
    with pytest.raises(FileNotFoundError):
        await orchestrator.process_invoice("/path/to/nonexistent/invoice.txt")
