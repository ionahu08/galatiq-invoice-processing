# Repository Architecture & Developer Guide

**Purpose:** Document the system architecture, agent relationships, code organization, and update patterns for anyone working on this codebase.

---

## Quick Overview

This is a **4-stage automated invoice processing system** using a multi-agent orchestration pattern.

```
Invoice File → [Ingestion] → [Validation] → [Approval] → [Payment] → Result
```

**Key Technology:**
- **Framework:** LangGraph (workflow orchestration)
- **Architecture:** Orchestrator-Workers pattern with star topology
- **LLM Integration:** Claude/Grok (in Approval Agent)
- **Database:** SQLite (inventory)
- **Type Safety:** Pydantic models
- **Concurrency:** async/await

---

## Repository Structure

```
galatiq-invoice-processing/
│
├── src/                                 # Main application code
│   ├── agents/                          # 4 specialist agents
│   │   ├── __init__.py                 # Exports all agents
│   │   ├── base.py                     # BaseAgent abstract class
│   │   ├── ingestion.py                # Agent 1: Read & extract
│   │   ├── validation.py               # Agent 2: Check inventory
│   │   ├── approval.py                 # Agent 3: Decide & reason
│   │   └── payment.py                  # Agent 4: Process/reject
│   │
│   ├── orchestrator/                    # Workflow orchestration
│   │   ├── __init__.py                 # Exports orchestrator
│   │   └── langgraph_orchestrator.py   # LangGraph-based workflow
│   │
│   ├── database/                        # Data access layer
│   │   ├── __init__.py
│   │   └── setup.py                    # SQLite operations
│   │
│   ├── utils/                           # Utilities
│   │   ├── __init__.py
│   │   └── logging.py                  # Structured logging
│   │
│   ├── __init__.py                     # Package exports
│   ├── models.py                       # Pydantic data schemas
│   ├── config.py                       # Configuration (from .env)
│   └── llm.py                          # LLM client (Claude/Grok)
│
├── data/
│   └── invoices/                        # 20 sample test invoices
│       ├── invoice_*.txt               # Text format invoices
│       ├── invoice_*.json              # JSON format invoices
│       └── invoice_*.pdf/.csv/.xml     # Other formats (for future)
│
├── tests/
│   └── test_orchestrator.py            # Orchestrator tests
│
├── main.py                             # CLI entry point
├── requirements.txt                    # Production dependencies
├── README.md                           # User documentation
├── CLAUDE.md                           # This file (architecture guide)
├── .env.example                        # Environment template
├── .gitignore                          # Git ignore rules
└── LEARNING_NOTES_PRIVATE.md           # Personal learning (not synced)
```

---

## Agent Architecture

### Agent Relationships (Data Flow)

```
                    ORCHESTRATOR
                    (Conductor)
                         ↓
    ┌────────────────────┼────────────────────┐
    ↓                    ↓                    ↓
 AGENT 1            AGENT 2             AGENT 3            AGENT 4
Ingestion          Validation          Approval            Payment
(Extract)          (Check DB)          (LLM Reasoning)     (Process)
    ↓                    ↓                    ↓                ↓
Read file      Query inventory      Ask Claude      Call Payment API
Extract data   Check stock          Generator       Process transaction
Return         Return issues        Critic          Return status
ExtractedInvoice ValidationResult  ApprovalResult   PaymentResult
```

### Agent Responsibilities

| Agent | Input | Output | Tools Used | File |
|-------|-------|--------|-----------|------|
| **Ingestion** | File path | ExtractedInvoice | File reader, Regex parser, JSON parser | `ingestion.py` |
| **Validation** | ExtractedInvoice | ValidationResult | Database queries, Stock checker | `validation.py` |
| **Approval** | Extracted + Validation | ApprovalResult | Business rules, LLM (Claude) | `approval.py` |
| **Payment** | Extracted + Approval | PaymentResult | Payment API, Logger | `payment.py` |

### Data Flow Through Agents

```
Stage 1 Output: ExtractedInvoice {
  vendor: "Widgets Inc",
  invoice_number: "INV-1001",
  amount: 5000.0,
  items: [...]
}
        ↓
Stage 2 Output: ValidationResult {
  is_valid: true,
  issues: [],
  total_issues: 0
}
        ↓
Stage 3 Output: ApprovalResult {
  is_approved: true,
  reasoning: "...",
  approval_confidence: 0.92
}
        ↓
Stage 4 Output: PaymentResult {
  status: "success",
  transaction_id: "TXN-...",
  message: "Paid $5000 to Widgets Inc"
}
```

---

## Key Files & Their Responsibilities

### `src/agents/base.py` - Abstract Base Class

```python
class BaseAgent(ABC):
    """Base class for all agents."""
    
    @abstractmethod
    async def execute(self, input_data: Any) -> Any:
        """Each agent must implement this."""
        pass
    
    async def run(self, input_data: Any) -> Any:
        """Wrapper that calls execute() with logging."""
        pass
```

**Why:** Ensures all agents follow the same interface (contract).

### `src/agents/ingestion.py` - File Parsing

**Responsibility:** Read invoice files and extract structured data.

**Tools:**
- `_extract_from_text()` - Parse TXT files with regex
- `_extract_from_json()` - Parse JSON files
- `_extract_field()` - Regex helper
- `_extract_items()` - Parse line items

**Extension point:** Add `_extract_from_pdf()` or `_extract_from_csv()` for new formats.

### `src/agents/validation.py` - Inventory Checking

**Responsibility:** Verify items exist and are in stock.

**Tools:**
- Uses `check_stock()` from `database/setup.py`
- Uses `query_inventory()` from `database/setup.py`

**Business rules:**
- Item must exist in database
- Quantity must be in stock
- No negative quantities
- Amount must be > 0

### `src/agents/approval.py` - Decision Making

**Responsibility:** Make approval decision with LLM reasoning.

**Tools:**
- Business rules (amount threshold, validation checks)
- Generator-Critic loop (LLM reasoning)
- Confidence scoring (0-1)

**Decision logic:**
```python
IF validation_failed:
    AUTO-REJECT
ELIF amount > $10K:
    MANUAL_REVIEW (flag for human)
ELSE:
    Use LLM (Claude) with generator-critic loop
    Return approval + confidence
```

### `src/agents/payment.py` - Payment Processing

**Responsibility:** Process approved invoices or log rejections.

**Tools:**
- `_mock_payment_api()` - Simulate payment (for testing)
- Logging - Record transaction status

**States:**
- `success` - Payment processed
- `requires_review` - Needs human approval
- `rejected` - Rejected with reason

### `src/database/setup.py` - Inventory Database

**Responsibility:** Manage SQLite inventory database.

**Functions:**
- `create_inventory_database(db_path)` - Initialize DB with seed data
- `query_inventory(db_path, item_id)` - Look up item
- `check_stock(db_path, item_id, quantity)` - Verify stock

**Schema:**
```sql
CREATE TABLE inventory (
    item_id TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    unit_price REAL NOT NULL DEFAULT 0.0,
    category TEXT DEFAULT 'General',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Seed data:**
```
WIDGETA: 15 in stock
WIDGETB: 10 in stock
GADGETX: 5 in stock
FAKEITEM: 0 in stock (test case)
```

### `src/models.py` - Data Schemas

**Responsibility:** Define data structures with type safety.

**Models:**
- `ExtractedInvoice` - Ingestion output
- `LineItem` - Single line item
- `ValidationResult` - Validation findings
- `ApprovalResult` - Approval decision
- `PaymentResult` - Payment status
- `ProcessingResult` - Final pipeline output

**Why:** Pydantic validates data at runtime, prevents type errors.

### `src/config.py` - Configuration

**Responsibility:** Load and validate settings from environment.

**Settings loaded:**
- LLM provider and model
- API keys (Anthropic, xAI)
- Database path
- Approval threshold ($10,000)
- Logging configuration

**How to use:**
```python
from src.config import settings
print(settings.approval_threshold)  # 10000.0
```

### `src/llm.py` - LLM Integration

**Responsibility:** Communicate with Claude/Grok API.

**Methods:**
- `reason_about_invoice()` - Generate initial reasoning
- `critique_approval()` - Review the reasoning
- `revise_approval()` - Refine based on critique

**Used by:** Approval Agent only (for generator-critic loop)

### `src/orchestrator/langgraph_orchestrator.py` - Workflow

**Responsibility:** Orchestrate all 4 agents in sequence.

**Implementation:**
- Uses LangGraph `StateGraph`
- Manages state flowing through agents
- Conditional routing (if validation fails, skip to end)
- Error handling wrapper

**Key methods:**
- `process_invoice()` - Single invoice
- `process_batch()` - Multiple invoices
- `_node_*()` - Stage implementations
- `_route_*()` - Conditional logic

### `main.py` - Entry Point

**Responsibility:** CLI interface and orchestration setup.

**Commands:**
```bash
python main.py --invoice_path=<path>           # Single invoice
python main.py --batch --dir=<dir>             # All invoices
python main.py --batch --debug                 # With logging
```

---

## How to Work With This Codebase

### Adding a New Validation Rule

**File:** `src/agents/validation.py`

1. Open `_validate_item()` method
2. Add new check after line 90
3. Return `ValidationIssue` if problem found
4. Test with sample invoices

```python
# Example: Add blacklist check
blacklist = ["UntrustVendor", "FraudCorp"]
if extracted.vendor in blacklist:
    issues.append(ValidationIssue(
        issue_type="blacklisted_vendor",
        message=f"Vendor {vendor} is blacklisted"
    ))
```

### Adding Support for New File Format

**File:** `src/agents/ingestion.py`

1. Open `execute()` method (line 27)
2. Add new file type condition
3. Implement `_extract_from_<format>()` method
4. Test with sample files in `data/invoices/`

```python
# Example: Add CSV support
elif file_path.suffix.lower() == ".csv":
    return await self._extract_from_csv(file_path)

async def _extract_from_csv(self, file_path: Path):
    import csv
    with open(file_path) as f:
        reader = csv.DictReader(f)
        # Parse and return ExtractedInvoice
```

### Modifying Approval Logic

**File:** `src/agents/approval.py`

1. Open `execute()` method (line 48)
2. Add new business rule (check, threshold, etc.)
3. Test with different invoices

```python
# Example: Add vendor trust score check
if extracted.vendor not in TRUSTED_VENDORS:
    return ApprovalResult(
        requires_manual_review=True,
        reasoning="Unknown vendor - manual review required"
    )
```

### Adding New Agent

1. Create `src/agents/new_agent.py`
2. Inherit from `BaseAgent`
3. Implement `async def execute()`
4. Add to `src/agents/__init__.py` exports
5. Add node to orchestrator in `langgraph_orchestrator.py`

```python
# Template
from src.agents.base import BaseAgent

class NewAgent(BaseAgent):
    async def execute(self, input_data):
        # Do work
        # Return output
        pass
```

---

## Testing & Development

### Run System

```bash
# Single invoice
python main.py --invoice_path=data/invoices/invoice_1001.txt

# Batch processing (all 20 invoices)
python main.py --batch --dir=data/invoices

# Debug mode (verbose logging)
python main.py --batch --debug
```

### Run Tests

```bash
pytest tests/ -v
```

### Test Coverage

- 20 sample invoices from galatiq case repo
- Formats: TXT (7), JSON (6), CSV (3), PDF (3), XML (1)
- Scenarios: Valid, high amount, out-of-stock, fraud, invalid data

---

## Personal Learning Resources

### Learning Notes

**File:** `LEARNING_NOTES_PRIVATE.md` (NOT synced to git)

This file contains comprehensive learning notes about:
- System overview and business problem
- Architecture deep dive
- Key concepts explained (models, async/await, LangGraph, etc.)
- Detailed agent explanations
- Tools reference
- End-to-end code walkthrough
- Common confusions clarified
- Quick reference guide

**Note:** This file is in `.gitignore` and stays on your machine only.

### Study Path

1. **Start:** Read `LEARNING_NOTES_PRIVATE.md` - System Overview
2. **Understand:** Read architecture sections
3. **Deep dive:** Read each agent's section + look at code
4. **Experiment:** Modify code and test changes
5. **Build:** Add new features or agents

---

## Key Design Decisions

### Why Orchestrator-Workers?
- **Modularity:** Each agent is independent
- **Scalability:** Can add agents without changing core logic
- **Testability:** Test each agent separately

### Why Star Topology?
- **Simplicity:** All agents report to orchestrator
- **Communication:** O(n) instead of O(n²)
- **Deadlock prevention:** Single coordinator

### Why LangGraph?
- **State management:** Tracks data through workflow
- **Conditional routing:** Branch based on validation/approval
- **Production-ready:** Error handling, observability built-in

### Why Pydantic Models?
- **Type safety:** Runtime validation
- **Self-documenting:** Code shows data shape
- **Serialization:** Easy JSON conversion
- **Schema:** Can generate JSON schema for documentation

### Why Generator-Critic Loop?
- **Higher confidence:** LLM self-reviews decisions
- **Better reasoning:** Claude refines based on critique
- **Auditable:** Can explain why decision was made

---

## Common Patterns

### Pattern 1: Adding a Conditional Route

In `langgraph_orchestrator.py`:

```python
def _route_approval(self, state):
    if state.approval.requires_manual_review:
        return "end"  # Skip payment
    return "payment"  # Continue
```

### Pattern 2: Adding a Tool

In any agent's file:

```python
async def _new_tool(self, param1, param2):
    """Tool description."""
    # Implementation
    return result
```

### Pattern 3: Adding a Validation Check

In `validation.py`:

```python
if some_condition:
    issues.append(ValidationIssue(
        issue_type="issue_type",
        item_name="item",
        message="Human-readable message",
        severity="error"
    ))
```

---

## Debugging Tips

### Enable Debug Logging

```bash
python main.py --batch --debug
```

### Print Intermediate States

In any agent's `execute()`:

```python
self.log_execution(f"DEBUG: {variable_name} = {value}", level="info")
```

### Trace Agent Calls

LangGraph logs each node execution:

```
[Ingestion] Processing file...
[Ingestion] Completed successfully
[Validation] Checking inventory...
[Validation] Completed successfully
```

---

## Performance Targets

- **Latency:** < 30 seconds per invoice
- **Throughput:** 200+ invoices/day (with parallelism)
- **Accuracy:** > 95% after LLM integration
- **Cost:** Reduce from $2M/year manual to ~$100k/year

---

## Future Enhancements

### Phase 1 (Done)
- [x] 4-stage workflow
- [x] LangGraph orchestration
- [x] LLM reasoning (generator-critic)
- [x] 20 test invoices

### Phase 2 (Future)
- [ ] PDF extraction (pdfplumber integration)
- [ ] CSV parsing
- [ ] Fraud detection agent
- [ ] Vendor reputation scoring

### Phase 3 (Future)
- [ ] Hierarchical orchestration (50+ agents)
- [ ] Blackboard pattern (loose coupling)
- [ ] Dynamic agent discovery
- [ ] High-stakes ensemble voting

---

## References

### Files to Read

1. **Understanding the flow:** `main.py` → `src/orchestrator/langgraph_orchestrator.py`
2. **Understanding agents:** `src/agents/base.py` → each agent file
3. **Understanding data:** `src/models.py`
4. **Understanding database:** `src/database/setup.py`

### Key Concepts

- Orchestrator-Workers Pattern
- Star Topology
- Code-Driven Planning
- Ephemeral Agents
- Generator-Critic Loop
- LangGraph StateGraph
- Pydantic Models
- async/await concurrency

---

## Questions?

Refer to:
- `LEARNING_NOTES_PRIVATE.md` - Comprehensive learning guide
- `README.md` - User-facing documentation
- Code comments - Implementation details
- Agent docstrings - Method documentation

---

**Last Updated:** 2026-08-28
**Status:** Production Ready ✅
